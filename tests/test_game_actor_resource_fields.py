"""Direct retail match, independent ordered references and owner/linked audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_actor_resource_fields_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_child_actor_constructor as constructor
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

S = screen.SYMBOLS
STACK, ACTOR, RESOURCE, CONFIGURATION = guest.STACK, 0x24000, 0x26000, 0x27000


def fixture(identity=7, configuration=CONFIGURATION, value=0, world=0, count=3,
        extra=255, callback=1, actor=ACTOR, resource=RESOURCE, symbols=S):
    entry = (symbols['D_800D1C90'] + identity*4) & 0xFFFFFFFF
    memory = {}
    for start, length in ((STACK-0x500, 0x600), (actor, 812), (resource, 64),
            (CONFIGURATION, 64), (symbols['D_800D1C90'], 1024), (entry, 4),
            (symbols['D_80086CAC'], 1024), (symbols['D_800BE9F0'], 4)):
        for i in range(length):
            memory.setdefault((start+i)&0xFFFFFFFF, 0xA5)
    for i in range(256):
        put(memory, symbols['D_80086CAC']+i*4, 0x11000099+i*0x100)
    put(memory, resource+2, 0x8001, 2)
    for offset, byte in ((4, count), (5, 137), (0x12, 89), (0x29, callback),
            (0x33, 0xFE), (0x38, extra), (0x39, 0xC7), (0x3B, 0xD2), (0x3C, 0x83)):
        put(memory, resource+offset, byte, 1)
    put(memory, resource+0x2A, 0xFEDC, 2)
    put(memory, resource+0x34, 0x89ABCDEF)
    if configuration:
        for i in range(64):
            memory.setdefault(configuration+i, 0xA5)
        put(memory, configuration+0x2C, value, 2)
    put(memory, symbols['D_800BE9F0'], world)
    put(memory, entry, resource)
    return memory


def reference(memory, identity=7, configuration=CONFIGURATION, actor=ACTOR,
        symbols=S, phase=0, mutations=()):
    state, events, calls = memory.copy(), [], []
    def get(where, size=1):
        assert all(where+i in state for i in range(size)), ('reference unmapped read', where, size)
        value = read(state, where, size)
        events.append(('R', where, size, value))
        return value
    def store(where, value, size=1):
        assert all(where+i in state for i in range(size)), ('reference unmapped write', where, size)
        value &= (1 << (size*8))-1
        put(state, where, value, size)
        events.append(('W', where, size, value))
    frame = STACK+phase-24
    store(frame+20, 0xDEAD0000, 4)
    if identity & 0xFFFFFFFF != 255:
        resource = get((symbols['D_800D1C90']+identity*4)&0xFFFFFFFF, 4)
        if configuration:
            value = get(configuration+44, 2)
            store(actor+16, get(resource+42, 2) if value == 0 else 0 if value == 1 else value, 2)
            if get(symbols['D_800BE9F0'], 4) == 29:
                store(actor+16, 1000, 2)
        else:
            store(actor+16, 0, 2)
        for source, destination, size in ((57, 315, 1), (51, 715, 1), (52, 716, 4),
                (18, 5, 1), (59, 104, 1), (60, 105, 1), (2, 352, 2)):
            store(actor+destination, get(resource+source, size), size)
        if get(resource+4):
            index = get(resource+5)
            store(actor+708, get(symbols['D_80086CAC']+index*4, 4), 4)
            store(actor+712, get(resource+4))
        count = get(actor+712)
        extra = get(resource+56)
        store(actor+713, count+extra)
        if get(resource+41):
            target = symbols['func_15036C70']
            calls.append((target, actor)); events.append(('CALL', target, (actor,)))
            for where, value, size in mutations:
                store(where, value, size)
    get(frame+20, 4)
    return state, events, calls


class FieldsOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, identity=7, configuration=CONFIGURATION, actor=ACTOR,
            symbols=S, phase=0, entry=screen.ENTRY, mutations=()):
        super().__init__(words, memory, arguments=(actor, identity, configuration), phase=phase, entry=entry)
        self.symbols, self.mutations = symbols, mutations
    def execute(self, word):
        if word >> 26 == 32:
            CopyOracle.execute(self, word)
        else:
            super().execute(word)
    def record_call(self, target):
        assert target == self.symbols['func_15036C70']
        args = self.arguments(1)
        self.calls.append((target, *args)); self.events.append(('CALL', target, args))
    def hook(self, target):
        assert target == self.symbols['func_15036C70']
        for where, value, size in self.mutations:
            self.put(where, value, size)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]


class GameActorResourceFieldsTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-actor-resource-fields-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes, indent=2)+'\n')
        cls.baseline = json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>68I', cls.rom, screen.ROM))
        cls.before = (cls.out/'before-elf').read_bytes()
        body = (cls.root/'conker/asm/AEB40.s').read_text().split('glabel '+screen.FUNCTION, 1)[1].split(
            'endlabel '+screen.FUNCTION, 1)[0]
        cls.slot = cls.out/'slot.s'
        cls.slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', cls.slot,
            filename='generated_AEB40'))
        cls.padded = cls.link('padded')
    @classmethod
    def link(cls, name, symbols=S, entry=screen.ENTRY):
        script = cls.out/('%s-%X.ld' % (name, entry)); elf = script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf),
            str(cls.out/(name+'.o'))], check=True, capture_output=True)
        return list(struct.unpack_from('>68I', sections(elf)['.text'][1]))
    def receipt(self, name, **values):
        if name == 'baseline':
            raise ValueError('immutable baseline is not a receipt')
        (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')
    def compare(self, memory, forms=None, **settings):
        state, events, calls = reference(memory, **{k:v for k,v in settings.items() if k != 'entry'})
        models = [FieldsOracle(words, memory, **settings).run() for words in (forms or (self.retail, self.raw))]
        for model in models:
            self.assertEqual(model.memory, state); self.assertEqual(model.events, events)
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[29], STACK+settings.get('phase', 0))
            self.assertEqual(model.r[16:24], [0x5A000000+i for i in range(16, 24)])
            self.assertEqual(model.f[20:], model.saved_f)
        return models

    def test_01_direct_shape_and_symbolic_provenance(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (68, 24, 0, 0, ''))
        self.assertEqual(self.raw, self.retail); self.assertEqual(self.padded, self.retail)
        _, functions, relocations = parse_object(self.out/'selected.o')
        self.assertEqual(functions[screen.FUNCTION]['size'], 272)
        self.assertEqual(relocations, self.meta['relocations'])
        self.assertEqual(len(relocations), 7)
        self.assertEqual(self.link('original'), self.retail)
        self.receipt('shape', words=68, frame=24, direct_compiler_match=True,
            original_assembly_ROM_and_production_padding_exact=True, relocations=7, guards_added=0)

    def test_02_full_width_identity_configuration_and_count_domains(self):
        cases = 0; coverage = set()
        for identity, value, world, phase in itertools.product(range(256),
                (None, 0, 1, 2, 0x7FFF, 0x8000, 0xFFFF), (0, 29), (0, 8)):
            configuration = 0 if value is None else CONFIGURATION
            memory = fixture(identity=identity, configuration=configuration, value=value or 0,
                world=world, count=identity, extra=255-identity, callback=identity&1)
            models = self.compare(memory, identity=identity, configuration=configuration, phase=phase)
            coverage.update(models[0].visits); cases += 1
        for identity, world in itertools.product((0x100, 0x1FF, 0xFFFF, 0x7FFFFFFF, 0xFFFFFFFF),
                (-1, 28, 30, 0x7FFFFFFF, -0x80000000)):
            memory = fixture(identity=identity, world=world)
            self.compare(memory, identity=identity); cases += 1
        for count, extra in itertools.product(range(256), (0, 1, 255)):
            memory = fixture(count=count, extra=extra)
            self.compare(memory); cases += 1
        self.assertEqual(coverage, set(range(screen.ENTRY, screen.ENTRY+272, 4))-{screen.ENTRY+0x54})
        memory = fixture(identity=255, actor=0, configuration=0)
        for where in list(memory):
            if not STACK-0x500 <= where < STACK+0x100:
                del memory[where]
        self.compare(memory, identity=255, actor=0, configuration=0); cases += 1
        self.receipt('guest', cases=cases, executions=cases*2, reached_words=len(coverage),
            unreachable_duplicate_store_offset=84, all_identity_and_count_bytes=True,
            full_word_sentinel_and_wrapped_table_index=True, void_return_not_compared=True,
            sentinel_skips_unmapped_actor_resource_configuration_and_world=True)

    def test_03_aliases_live_reload_and_every_fired_access_fault(self):
        cases = prefixes = 0
        for resource, configuration, phase in itertools.product(
                (RESOURCE, ACTOR, ACTOR+0x2C0, ACTOR+0x290, STACK-0x18+0x14-2),
                (0, CONFIGURATION, ACTOR-0x1C, STACK-0x18+0x14-0x2C), (0, 8)):
            memory = fixture(resource=resource, configuration=configuration, value=0, count=1)
            mutations = ((ACTOR+0x324, 0xFEDCBA98, 4), (S['D_800BE9F0'], -1, 4))
            models = self.compare(memory, configuration=configuration, phase=phase, mutations=mutations)
            for ordinal in range(models[0].accesses):
                failed = []
                for words in (self.retail, self.raw):
                    model = FieldsOracle(words, memory, configuration=configuration, phase=phase, mutations=mutations)
                    model.fault = ordinal
                    with self.assertRaises(guest.AccessFault) as caught:
                        model.run()
                    self.assertEqual(caught.exception.args, (ordinal,))
                    self.assertEqual(model.accesses, ordinal)
                    failed.append((model.memory, model.events, model.calls))
                self.assertEqual(*failed); prefixes += 1
            cases += 1
        plans = ({'D_800BE9F0':ACTOR+0xE}, {'D_800D1C90':ACTOR+0x10-28},
            {'D_80086CAC':ACTOR+0x2C4-137*4})
        for changes in plans:
            symbols = dict(S, **changes)
            forms = tuple(self.link(name, symbols) for name in ('original', 'selected'))
            memory = fixture(symbols=symbols, value=0)
            if 'D_800BE9F0' in changes:
                put(memory, RESOURCE+0x2A, 29, 2)
                put(memory, ACTOR+0xE, 0, 2)
            self.compare(memory, forms=forms, symbols=symbols); cases += 1
        self.receipt('aliases-faults', cases=cases, full_access_fault_pairs=prefixes,
            failed_runs=prefixes*2, each_fault_gate_confirmed=True,
            resource_and_configuration_actor_private_aliases=True,
            world_read_after_store_cached_resource_table_and_live_count_reload=True)

    def test_04_independent_symbol_links_and_signed_HILO_carries(self):
        links = ((0x15207FF0, 0x80117FFC, 0x80128004, 0x80137FFC, 0x15218004),
            (0x15308004, 0x80218004, 0x80227FFC, 0x80238004, 0x15327FFC),
            (0x15417FFC, 0x80327FFC, 0x80338004, 0x80348004, 0x15437FF0))
        cases = 0
        for entry, table, world, indices, helper in links:
            symbols = dict(zip(S, (table, world, indices, helper)))
            forms = tuple(self.link(name, symbols, entry) for name in ('original', 'selected', 'padded'))
            self.assertEqual(forms[0], forms[1]); self.assertEqual(forms[0], forms[2])
            for identity, value, count in ((7, 0, 0), (0, 1, 1), (254, 65535, 255), (255, 2, 9), (0x1FF, 32768, 1)):
                memory = fixture(identity=identity, value=value, count=count, symbols=symbols, world=29)
                self.compare(memory, forms=forms, identity=identity, symbols=symbols, entry=entry)
                cases += 1
        self.receipt('links', symbol_sets=3, links=9, cases=cases, executions=cases*3,
            all_three_global_pairs_and_helper_rebased=True, original_independently_assembled=True)

    def test_05_copied_owner_all_neighbors_pools_relocations_and_padding(self):
        before = (self.out/'before-source').read_text(); objects = []; diagnostics = []
        for name, source in (('owner-before', before), ('owner-after', screen.install(before))):
            obj, warnings = compile_owner(self.root, self.out, source, name)
            diagnostics.append(warnings)
            subprocess.run(['python3', str(self.root/'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')), '--post-process',
                str(obj.relative_to(self.root/'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root/'conker', check=True, capture_output=True)
            objects.append(obj)
        self.assertEqual(diagnostics[0], diagnostics[1])
        parsed = [parse_object(obj) for obj in objects]
        def body(data, name):
            text, functions, relocations = data; target = functions[name]
            start, size = target['value'], target['size']
            return size, text[start:start+size], {o-start:v for o,v in relocations.items() if start<=o<start+size}
        self.assertEqual(parsed[0][1].keys(), parsed[1][1].keys())
        for name in parsed[0][1]:
            if name != screen.FUNCTION:
                self.assertEqual(body(parsed[0], name), body(parsed[1], name), name)
        self.assertEqual(body(parsed[1], screen.FUNCTION), body(parse_object(self.out/'selected.o'), screen.FUNCTION))
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        for i, obj in enumerate(objects):
            assembly = self.out/('owner-padded-%d.s' % i)
            subprocess.run(['python3', str(self.root/'tools/pad_c_object.py'), str(obj),
                str(self.root/'conker/retail_layout.us.txt'), 'generated_AEB40', str(assembly),
                '--word-patches', str(self.out/'before-guards')], check=True, capture_output=True)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(assembly.with_suffix('.o')),
                str(assembly)], check=True, capture_output=True)
        padded = [parse_object(self.out/('owner-padded-%d.o' % i)) for i in (0, 1)]
        base = padded[1][1][screen.FUNCTION]['value']; expected = bytearray(padded[0][0])
        expected[base:base+272] = padded[1][0][base:base+272]
        self.assertEqual(bytes(expected), padded[1][0])
        self.assertEqual({o:v for o,v in padded[0][2].items() if not base<=o<base+272},
            {o:v for o,v in padded[1][2].items() if not base<=o<base+272})
        self.assertEqual({o-base:v for o,v in padded[1][2].items() if base<=o<base+272}, self.meta['relocations'])
        self.receipt('owner', neighbors=len(parsed[0][1])-1, diagnostics=len(diagnostics[1]),
            all_other_bytes_extents_pools_and_relocations_exact=True, constructor_182_word_guards_unchanged=True,
            only_one_272_byte_slot_changes=True, guards_added=0)

    def test_06_effective_fresh_IDO_semantic_and_load_order_negatives(self):
        controls = (
            ('sentinel', 'identity != 255', '(u8)identity != 255', dict(identity=0x1FF)),
            ('default', '*(u16 *)(resource + 0x2A)', '*(u16 *)(resource + 0x28)', {}),
            ('one', 'value == 1', 'value == 2', dict(value=1)),
            ('world', 'D_800BE9F0 == 0x1D', 'D_800BE9F0 == 0x1E', dict(world=29)),
            ('field', 'resource[0x39]', 'resource[0x38]', {}),
            ('live-count', 'actor[0x2C8] = resource[4]', 'actor[0x2C8] = 1', dict(count=3)),
            ('sum', 'resource[0x38] + actor[0x2C8]', 'resource[0x38] - actor[0x2C8]', {}),
            ('callback', 'resource[0x29] != 0', 'resource[0x29] == 0', {}),
            ('load-order', 'resource[0x38] + actor[0x2C8]', 'actor[0x2C8] + resource[0x38]', {}))
        public = lambda m: {a:v for a,v in m.items() if not STACK-0x500<=a<STACK+0x100}
        trace = lambda es: [e for e in es if e[0]=='CALL' or not STACK-0x500<=e[1]<STACK+0x100]
        for name, old, new, settings in controls:
            self.assertIn(old, screen.SELECTED)
            _, words = screen.compile_candidate(self.root, self.out, 'negative-'+name, screen.SELECTED.replace(old, new))
            self.assertNotEqual(words, self.raw, name)
            memory = fixture(**settings)
            arguments = {k:v for k,v in settings.items() if k == 'identity'}
            correct = FieldsOracle(self.raw, memory, **arguments).run()
            wrong = FieldsOracle(words, memory, **arguments).run()
            self.assertNotEqual((public(correct.memory), trace(correct.events), correct.calls),
                (public(wrong.memory), trace(wrong.events), wrong.calls), name)
        self.receipt('negatives', fresh_IDO_controls=len(controls), all_effective=True,
            reversed_commutative_operand_changes_observable_load_order=True)

    def test_07_actual_complete_constructor_calls_initializer(self):
        outer = list(struct.unpack_from('>182I', self.rom, constructor.screen.ROM))
        self.assertEqual(outer, list(struct.unpack_from('>182I', self.before,
            elf_slot_offset(self.before, constructor.screen.ENTRY, 728))))
        class Connected(constructor.ChildOracle):
            def __init__(model, memory, args, created, inner, phase):
                code = {screen.ENTRY+i*4:w for i,w in enumerate(inner)}
                super().__init__(outer, memory, args, created, phase=phase, connected=code)
                model.counts[S['func_15036C70']] = 1
            def execute(model, word):
                if word >> 26 == 32:
                    CopyOracle.execute(model, word)
                else:
                    super().execute(word)
            def hook(model, target):
                if target in model.roles:
                    return super().hook(target)
                assert target == S['func_15036C70']
                model.put(model.r[4]+0x324, 0xFEDCBA98, 4)
                for register in (1, 2, 3, *range(4, 16), 24, 25):
                    model.r[register] = 0xA5000000+register
                model.f[:20] = [0xA5000000+i for i in range(20)]
        cases = calls = 0
        for identity, flags, active, phase in itertools.product((7, 254, 255, 0x1FF), (0, 3), (0, 1), (0, 8)):
            memory, args, created = constructor.fixture(identity=identity, flags=flags, active=active, count=-1)
            entry = (S['D_800D1C90']+identity*4)&0xFFFFFFFF
            memory.update({entry+i:0 for i in range(4)})
            put(memory, entry, constructor.RESOURCE)
            memory.update({S['D_80086CAC']+i:0 for i in range(1024)})
            for i in range(256):
                put(memory, S['D_80086CAC']+i*4, 0x33000+i*4)
            models = [Connected(memory, args, created, inner, phase).run() for inner in (self.retail, self.raw)]
            self.assertEqual((models[0].memory, models[0].events, models[0].calls, models[0].r, models[0].f),
                (models[1].memory, models[1].events, models[1].calls, models[1].r, models[1].f))
            calls += sum(c[0] == screen.ENTRY for c in models[0].calls); cases += 1
        self.assertEqual(calls, cases)
        self.receipt('connected', cases=cases, executions=cases*2, initializer_calls_per_form=calls,
            complete_actual_matched_182_word_constructor=True, deep_callbacks_and_resource_transition_bounded=True)

    def test_08_native32_profiles_aliases_and_effective_negative(self):
        for profile in ('-O2', '-O0'):
            result, detail = self.run_native('native-'+profile[1:], NATIVE_PREFIX+screen.SELECTED+NATIVE_RUNNER, profile)
            self.assertEqual((result, detail), (0, [8192, 0, 0]))
        bad = screen.SELECTED.replace('resource[0x39]', 'resource[0x38]')
        result, _ = self.run_native('native-negative', NATIVE_PREFIX+bad+NATIVE_RUNNER)
        self.assertNotEqual(result, 0)
        self.receipt('native', cases_per_profile=8192, executions=16384, profiles=['O2', 'O0'],
            native32_widths_checked=True, resource_configuration_aliases=True, effective_negative=1,
            wrapped_guest_addresses_and_fault_order_not_native_claims=True)

    def test_09_immutable_baselines_and_whole_linked_installation(self):
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.receipt('baseline')
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
        source = (self.root/screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            for name, path in self.paths.items():
                self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(), self.baseline[name])
            self.receipt('linked', installed=False); return
        self.assertEqual(source, screen.install((self.out/'before-source').read_text()))
        expected = bytearray(self.before)
        struct.pack_into('>68I', expected, elf_slot_offset(self.before, screen.ENTRY, 272), *self.retail)
        extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.before, extent)[0], 12)
        struct.pack_into('>I', expected, extent, 272)
        actual = (self.root/self.paths['elf']).read_bytes()
        self.assertEqual(bytes(expected), actual)
        for name in ('guards', 'progress', 'rodata', 'symbols', 'undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(), (self.out/('before-'+name)).read_bytes())
        audit = audit_layout(self.root/self.paths['elf'], self.root/'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('linked', installed=True, ELF_bytes=len(actual), ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before, actual)),
            only_target_slot_and_12_to_272_symbol_extent_change=True, all_other_ELF_bytes_metadata_exact=True,
            guards_and_conversion_rows_unchanged=True, protected_data=audit)


NATIVE_PREFIX = r'''
#include <stddef.h>
typedef unsigned char u8; typedef signed char s8; typedef unsigned short u16;
typedef short s16; typedef unsigned int u32; typedef int s32;
typedef char widths[(sizeof(void*)==4 && sizeof(u16)==2 && sizeof(s32)==4)?1:-1];
u8 *D_800D1C90[256]; s32 D_800BE9F0; u32 D_80086CAC[256];
static u32 calls, observed;
static u32 load32(const u8 *p) { u32 v; unsigned i; for(i=0;i<4;i++) ((u8*)&v)[i]=p[i]; return v; }
static u16 load16(const u8 *p) { u16 v; unsigned i; for(i=0;i<2;i++) ((u8*)&v)[i]=p[i]; return v; }
static void store32(u8 *p,u32 v) { unsigned i; for(i=0;i<4;i++) p[i]=((u8*)&v)[i]; }
static void store16(u8 *p,u16 v) { unsigned i; for(i=0;i<2;i++) p[i]=((u8*)&v)[i]; }
void func_15036C70(u8 *actor) {
    calls++; observed=load32(actor+0x2CC)^load16(actor+0x10)^actor[0x2C8]^actor[0x2C9];
    store32(actor+0x324,0xFEDCBA98); D_800BE9F0=-1;
}
'''
NATIVE_RUNNER = r'''
static void expected(u8 *actor, s32 identity, u8 *configuration) {
    u8 *resource; u16 value; u8 count, extra;
    if(identity==255) return;
    resource=D_800D1C90[identity];
    if(configuration) {
        value=load16(configuration+44);
        store16(actor+16,value==0?load16(resource+42):value==1?0:value);
        if(D_800BE9F0==29) store16(actor+16,1000);
    } else store16(actor+16,0);
    actor[315]=resource[57]; actor[715]=resource[51]; store32(actor+716,load32(resource+52));
    actor[5]=resource[18]; actor[104]=resource[59]; actor[105]=resource[60];
    store16(actor+352,load16(resource+2));
    if(resource[4]) { store32(actor+708,D_80086CAC[resource[5]]); actor[712]=resource[4]; }
    count=actor[712]; extra=resource[56]; actor[713]=(u8)(count+extra);
    if(resource[41]) func_15036C70(actor);
}
static u8 blocks[2][4096];
static u32 results[3];
static int run(void) {
    unsigned identity, value, world, alias, form, i, cases=0;
    const u16 values[4]={0,1,2,65535}; u32 got[2], seen[2], worlds[2];
    for(identity=0;identity<256;identity++) for(value=0;value<4;value++)
    for(world=0;world<2;world++) for(alias=0;alias<4;alias++) {
        for(form=0;form<2;form++) {
            u8 *actor=blocks[form]+0x400, *resource=blocks[form]+0x800;
            u8 *configuration=blocks[form]+0x900;
            for(i=0;i<4096;i++) blocks[form][i]=(u8)(i*31+identity);
            if(alias==1) resource=actor;
            if(alias==2) resource=actor+0x2C0;
            if(alias==3) resource=actor+0x290;
            if(value==1) configuration=NULL;
            if(value==2) configuration=actor-0x1C;
            store16(resource+2,0x8001); store16(resource+42,0xFEDC);
            store32(resource+52,0x89ABCDEF); resource[4]=(u8)identity; resource[5]=137;
            resource[18]=89; resource[41]=(u8)(identity&1); resource[51]=0xFE;
            resource[56]=(u8)(255-identity); resource[57]=0xC7; resource[59]=0xD2; resource[60]=0x83;
            if(configuration) store16(configuration+44,values[value]);
            for(i=0;i<256;i++) { D_800D1C90[i]=resource; D_80086CAC[i]=0x11000099+i*0x100; }
            D_800BE9F0=world?29:0; calls=observed=0;
            if(form) expected(actor,(s32)identity,configuration);
            else func_150839B8(actor,(s32)identity,configuration);
            got[form]=calls; seen[form]=observed; worlds[form]=(u32)D_800BE9F0;
        }
        if(got[0]!=got[1] || seen[0]!=seen[1] || worlds[0]!=worlds[1]) return 1;
        for(i=0;i<4096;i++) if(blocks[0][i]!=blocks[1][i]) return 2;
        cases++;
    }
    results[0]=cases;
    return 0;
}
void _start(void) {
    int result=run();
    __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(results),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");
    __builtin_unreachable();
}
'''


if __name__ == '__main__':
    unittest.main()
