"""Direct complete allocation match, mutable homes, mixed ABI and linked audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_actor_animation_allocation_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_actor_resource_fields as fields
from tools.tests import test_game_actor_resource_transition_match as transition
from tools.tests import test_game_child_actor_constructor as constructor
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

S = screen.SYMBOLS
STACK, ACTOR, OTHER, BUFFER = guest.STACK, 0x24000, 0x25000, 0x26000
FLOATS = (0, 0x80000000, 0x3F800000, 0xC0200000, 1, 0x7F800000,
    0xFF800000, 0x7FC12345, 0x7F812345, 0x807FFFFF)
COUNTS = dict(allocate_memory=4, bzero=2, func_1505E650=7)


def fixture(identity=7, presence=1, count=1, actor=ACTOR, result=BUFFER, symbols=S):
    memory = {}
    for start, length in ((STACK-0x500, 0x700), (actor, 812), (OTHER, 812), (BUFFER, 0x400),
            (symbols['D_800D1588'], 1024), (symbols['D_800C5A90'], 512)):
        for i in range(length):
            memory.setdefault(start+i, (i*17+35)&255)
    if result:
        for i in range(0x3E0):
            memory.setdefault(result+i, (i*31+7)&255)
    put(memory, actor+4, identity, 1)
    put(memory, actor+0x2D0, 0xFEDCBA98)
    put(memory, symbols['D_800D1588']+identity*4, presence)
    put(memory, symbols['D_800C5A90']+identity*2, count, 2)
    return memory


def reference(memory, state=0xFEDCBA98, mode=0x81234567, scale=0x7F812345,
        actor=ACTOR, result=BUFFER, symbols=S, phase=0, mutations=None):
    memory = memory.copy(); events, calls = [], []; frame = STACK+phase-40
    def get(where, size=4):
        assert all(where+i in memory for i in range(size)), ('reference unmapped read', where, size)
        value = read(memory, where, size); events.append(('R', where, size, value)); return value
    def store(where, value, size=4):
        assert all(where+i in memory for i in range(size)), ('reference unmapped write', where, size)
        value &= (1<<(size*8))-1
        put(memory, where, value, size); events.append(('W', where, size, value))
    def call(name, args):
        target = symbols[name]; calls.append((target, *args)); events.append(('CALL', target, args))
        if name == 'bzero':
            for i in range(args[1]): store(args[0]+i, 0, 1)
        for where, value, size in (mutations or {}).get(name, ()):
            store(where, value, size)
    store(frame+36, 0xDEAD0000)
    for i, value in enumerate((actor, state, mode, scale)): store(frame+40+i*4, value)
    current = get(frame+40); identity = get(current+4, 1); returned = 0
    if get(symbols['D_800D1588']+identity*4) and get(symbols['D_800C5A90']+identity*2, 2):
        call('allocate_memory', (0x3E0, 1, 2, 0))
        current = get(frame+40); store(current+0x2D0, result)
        if result == 0: returned = 1
        else:
            target = get(current+0x2D0); call('bzero', (target, 64))
            current_mode = get(frame+48); current = get(frame+40)
            current_state = get(frame+46, 2); current_scale = get(frame+52)
            store(frame+24, current_mode); store(frame+16, 0); store(frame+20, 0)
            outgoing = (0, 0, current_mode)
            call('func_1505E650', (current, current_state, current_scale, 0, *outgoing))
    get(frame+36)
    return memory, events, calls, returned


class AllocationOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, state=0xFEDCBA98, mode=0x81234567, scale=0x7F812345,
            actor=ACTOR, result=BUFFER, symbols=S, phase=0, mutations=None, entry=screen.ENTRY):
        super().__init__(words, memory, arguments=(actor, state, mode, scale), phase=phase, entry=entry)
        self.result, self.symbols, self.mutations = result, symbols, mutations or {}
    def record_call(self, target):
        name = next(n for n in COUNTS if self.symbols[n] == target)
        args = self.arguments(COUNTS[name])
        self.calls.append((target, *args)); self.events.append(('CALL', target, args))
    def hook(self, target):
        name = next(n for n in COUNTS if self.symbols[n] == target)
        if name == 'bzero':
            address, count = self.r[4:6]
            assert count == 64, ('bounded bzero length', count, 'expected 64')
            for i in range(count): self.put(address+i, 0, 1)
        for where, value, size in self.mutations.get(name, ()):
            self.put(where, value, size)
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]
        if name == 'allocate_memory': self.r[2] = self.result


class GameActorAnimationAllocationTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-actor-animation-allocation-test'; cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text(); hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes, indent=2)+'\n')
        cls.baseline = json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>51I', cls.rom, screen.ROM)); cls.before = (cls.out/'before-elf').read_bytes()
        body = (cls.root/'conker/asm/AEB40.s').read_text().split('glabel '+screen.FUNCTION, 1)[1].split(
            'endlabel '+screen.FUNCTION, 1)[0]
        slot = cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', slot, filename='generated_AEB40'))
        cls.padded = cls.link('padded')
    @classmethod
    def link(cls, name, symbols=S, entry=screen.ENTRY):
        script = cls.out/('%s-%X.ld' % (name, entry)); elf = script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(cls.out/(name+'.o'))],
            check=True, capture_output=True)
        return list(struct.unpack_from('>51I', sections(elf)['.text'][1]))
    def receipt(self, name, **values):
        if name == 'baseline': raise ValueError('immutable baseline is not a receipt')
        (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')
    def compare(self, memory, forms=None, **settings):
        expected = reference(memory, **{k:v for k,v in settings.items() if k != 'entry'})
        models = [AllocationOracle(w, memory, **settings).run() for w in (forms or (self.retail, self.raw))]
        for model in models:
            self.assertEqual((model.memory, model.events, model.calls, model.r[2]), expected)
        return models
    def test_01_complete_direct_shape_and_relocations(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (51, 40, 0, 0, ''))
        self.assertEqual(self.raw, self.retail); self.assertEqual(self.padded, self.retail)
        self.assertEqual(self.link('original'), self.retail)
        _, functions, relocations = parse_object(self.out/'selected.o')
        self.assertEqual(functions[screen.FUNCTION]['size'], 204); self.assertEqual(len(relocations), 7)
        self.receipt('shape', words=51, frame=40, direct_compiler_match=True, guards_added=0,
            original_ROM_assembly_and_padding_exact=True, relocations=7, typed_float_interface=True)
    def test_02_independent_domains_return_paths_and_full_float_words(self):
        cases = 0; coverage = set()
        for identity, path, scale, phase in itertools.product(range(256), range(4), FLOATS, (0, 8)):
            presence = 0 if path == 0 else 0x80000000
            count = 0 if path == 1 else (1 if identity&1 else 65535)
            result = 0 if path == 2 else BUFFER
            memory = fixture(identity, presence, count, result=result)
            models = self.compare(memory, result=result, scale=scale, phase=phase,
                state=(0, 1, 65535, 65536, 0xFEDCBA98)[identity%5],
                mode=(0, 1, 0xFFFFFFFF, 0x80000000)[identity%4])
            coverage.update(models[0].visits); cases += 1
        self.assertEqual(coverage, set(range(screen.ENTRY, screen.ENTRY+204, 4)))
        memory = fixture(presence=0)
        for where in list(memory):
            if S['D_800C5A90'] <= where < S['D_800C5A90']+512: del memory[where]
        self.compare(memory); cases += 1
        self.receipt('guest', cases=cases, executions=cases*2, reached_words=51, all_identity_bytes=True,
            presence_gate_skips_unmapped_count_table=True, full_state_mode_float_words=True,
            zero_count_and_allocation_failure_and_success=True, GP_FPR_clobber_and_restore_checked=True)
    def test_03_live_homes_aliases_clear_length_and_fired_fault_prefixes(self):
        cases = faults = corrupted_returns = 0
        for phase, result, plan in itertools.product((0, 8), (0, BUFFER, ACTOR, ACTOR+0x2A0, STACK), range(4)):
            memory = fixture(result=result); homes = STACK+phase
            mutations = {}
            if plan == 1:
                mutations['allocate_memory'] = ((homes, OTHER, 4), (homes+4, 0x1234ABCD, 4),
                    (homes+8, 0xFEDCBA98, 4), (homes+12, 0x7F812345, 4))
            if plan == 2:
                mutations['bzero'] = ((homes, OTHER, 4), (homes+4, 0x87654321, 4),
                    (homes+8, 0xA5A5A5A5, 4), (homes+12, 0x80000000, 4))
            if plan == 3:
                mutations['allocate_memory'] = ((ACTOR+4, 19, 1), (S['D_800D1588']+28, 0, 4),
                    (S['D_800C5A90']+14, 0, 2))
                mutations['func_1505E650'] = ((ACTOR+0x2D0, 0xDEADBEEF, 4),)
            if phase == 8 and result == STACK:
                expected = reference(memory, result=result, phase=phase, mutations=mutations)
                models = []
                for words in (self.retail, self.raw):
                    model = AllocationOracle(words, memory, result=result, phase=phase, mutations=mutations)
                    with self.assertRaises(AssertionError) as caught:
                        model.run()
                    self.assertEqual(caught.exception.args, (('unowned jump', 0),))
                    self.assertEqual((model.memory, model.events, model.calls, model.r[2]), expected)
                    self.assertEqual(model.r[31], 0)
                    models.append(model)
                corrupted_returns += 1
            else:
                models = self.compare(memory, result=result, phase=phase, mutations=mutations)
            for ordinal in range(models[0].accesses):
                failed = []
                for words in (self.retail, self.raw):
                    model = AllocationOracle(words, memory, result=result, phase=phase, mutations=mutations)
                    model.fault = ordinal
                    with self.assertRaises(guest.AccessFault) as caught: model.run()
                    self.assertEqual(caught.exception.args, (ordinal,)); self.assertEqual(model.accesses, ordinal)
                    failed.append((model.memory, model.events, model.calls))
                self.assertEqual(*failed); faults += 1
            cases += 1
        for changes in ({'D_800D1588':STACK+8-28}, {'D_800C5A90':STACK+6-14},
                {'D_800D1588':ACTOR+0x2D0-28}):
            symbols = dict(S, **changes)
            forms = tuple(self.link(n, symbols) for n in ('original', 'selected'))
            memory = fixture(symbols=symbols)
            self.compare(memory, forms=forms, symbols=symbols); cases += 1
        self.receipt('aliases-faults', cases=cases, modeled_full_access_fault_pairs=faults, failed_runs=faults*2,
            corrupted_return_pairs=corrupted_returns, original_and_C_jump_to_zero_after_RA_clear=True,
            all_fault_gates_fired=True, live_all_four_homes_after_both_callbacks=True,
            clear_64_bytes_not_entire_992_byte_allocation=True, buffer_actor_and_private_aliases=True,
            SDK_bzero_and_allocator_and_animation_callbacks_bounded=True)
    def test_04_independent_symbol_links_and_signed_low_half_carries(self):
        cases = 0
        for entry, table, counts, allocation, zero, animation in (
                (0x15207FF0, 0x80117FFC, 0x80128004, 0x10237FFC, 0x10248004, 0x15258004),
                (0x15308004, 0x80218004, 0x80227FFC, 0x10348004, 0x10357FFC, 0x15368004),
                (0x15417FFC, 0x80327FFC, 0x80338004, 0x10457FF0, 0x10467FFC, 0x15478004)):
            symbols = dict(zip(S, (table, counts, allocation, zero, animation)))
            forms = tuple(self.link(n, symbols, entry) for n in ('original', 'selected', 'padded'))
            self.assertEqual(forms[0], forms[1]); self.assertEqual(forms[0], forms[2])
            for path in range(4):
                result = 0 if path == 2 else BUFFER
                memory = fixture(presence=path != 0, count=path != 1, result=result, symbols=symbols)
                self.compare(memory, forms=forms, result=result, symbols=symbols, entry=entry); cases += 1
        self.receipt('links', symbol_sets=3, links=9, cases=cases, executions=cases*3,
            two_table_pairs_three_JAL_sites_independently_rebased=True)
    def test_05_actual_copied_owner_typed_constructor_and_all_neighbors(self):
        before = (self.out/'before-source').read_text(); objects = []; warnings = []
        for name, source in (('owner-before', before), ('owner-after', screen.install(before))):
            obj, diagnostics = compile_owner(self.root, self.out, source, name); warnings.append(diagnostics)
            subprocess.run(['python3', str(self.root/'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')), '--post-process',
                str(obj.relative_to(self.root/'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root/'conker', check=True, capture_output=True)
            objects.append(obj)
        self.assertEqual(warnings, [[], []]); parsed = [parse_object(o) for o in objects]
        def body(data, name):
            text, functions, relocations = data; f = functions[name]; start, end = f['value'], f['value']+f['size']
            return f['size'], text[start:end], {o-start:v for o,v in relocations.items() if start<=o<end}
        self.assertEqual(parsed[0][1].keys(), parsed[1][1].keys())
        for name in parsed[0][1]:
            if name != screen.FUNCTION: self.assertEqual(body(parsed[0], name), body(parsed[1], name), name)
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
        start = padded[1][1][screen.FUNCTION]['value']; expected = bytearray(padded[0][0])
        expected[start:start+204] = padded[1][0][start:start+204]; self.assertEqual(bytes(expected), padded[1][0])
        self.assertEqual({o:v for o,v in padded[0][2].items() if not start<=o<start+204},
            {o:v for o,v in padded[1][2].items() if not start<=o<start+204})
        self.receipt('owner', neighbors=len(parsed[0][1])-1, diagnostics=0,
            typed_scale_constructor_call_entire_182_word_fingerprint_unchanged=True,
            all_neighbor_bytes_extents_relocations_pools_and_existing_guards_exact=True)
    def test_06_effective_fresh_IDO_complete_semantic_controls(self):
        controls = (
            ('presence', 'D_800D1588[identity] == 0', 'D_800D1588[identity] != 0', {}),
            ('count', 'D_800C5A90[identity] == 0', 'D_800C5A90[identity] > 1', dict(count=0)),
            ('allocation', '0x3E0, 1, 2, 0', '0x3E4, 1, 2, 0', {}),
            ('failure', 'return 1;', 'return 0;', dict(result=0)),
            ('field', 'destination + 0x2D0', 'destination + 0x2D4', {}),
            ('clear', ', 0x40);', ', 0x3C);', {}),
            ('state', '(u16)state', '(u8)state', {}),
            ('scale', 'state, scale,', 'state, 0.0f,', {}),
            ('mode', '0.0f, mode)', '0.0f, 0)', {}))
        public = lambda m: {a:v for a,v in m.items() if not STACK-0x500<=a<STACK+0x200}
        trace = lambda es: [e for e in es if e[0]=='CALL' or not STACK-0x500<=e[1]<STACK+0x200]
        for name, old, new, case in controls:
            self.assertIn(old, screen.SELECTED)
            _, words = screen.compile_candidate(self.root, self.out, 'negative-'+name, screen.SELECTED.replace(old, new))
            self.assertNotEqual(words, self.raw)
            memory = fixture(**case); args = {k:v for k,v in case.items() if k == 'result'}
            correct = AllocationOracle(self.raw, memory, **args).run()
            wrong = AllocationOracle(words, memory, **args)
            try: wrong.run()
            except AssertionError as error:
                self.assertEqual(name, 'clear'); self.assertIn('64', str(error)); continue
            self.assertNotEqual((public(correct.memory), trace(correct.events), correct.calls, correct.r[2]),
                (public(wrong.memory), trace(wrong.events), wrong.calls, wrong.r[2]), name)
        self.receipt('negative', fresh_IDO_controls=len(controls), all_effective=True)
    def test_07_complete_actual_constructor_initializer_and_resource_helper(self):
        outer = list(struct.unpack_from('>182I', self.rom, constructor.screen.ROM))
        bodies = ((fields.screen.ENTRY, 68, fields.screen.ROM),
            (transition.screen.ENTRY, 70, transition.screen.ROM), (constructor.screen.ENTRY, 182, constructor.screen.ROM))
        for entry, length, rom in bodies:
            self.assertEqual(list(struct.unpack_from('>%dI'%length, self.before, elf_slot_offset(self.before, entry, length*4))),
                list(struct.unpack_from('>%dI'%length, self.rom, rom)))
        class Connected(constructor.ChildOracle):
            def __init__(model, memory, args, created, inner, phase, result):
                code = {screen.ENTRY+i*4:w for i,w in enumerate(inner)}
                for entry, length, _ in bodies[:2]:
                    words = struct.unpack_from('>%dI'%length, self.before, elf_slot_offset(self.before, entry, length*4))
                    code.update({entry+i*4:w for i,w in enumerate(words)})
                super().__init__(outer, memory, args, created, phase=phase, connected=code)
                model.result = result
                model.counts.update({S[n]:c for n,c in COUNTS.items()})
                model.counts.update({transition.S[n]:c for n,c in transition.COUNTS.items()})
                model.counts[fields.S['func_15036C70']] = 1
            def execute(model, word):
                if word >> 26 == 32: CopyOracle.execute(model, word)
                else: super().execute(word)
            def hook(model, target):
                if target in model.roles: return super().hook(target)
                assert target in model.counts
                if target == S['bzero']:
                    for i in range(model.r[5]): model.put(model.r[4]+i, 0, 1)
                for register in (1, 2, 3, *range(4, 16), 24, 25): model.r[register] = 0xA5000000+register
                model.f[:20] = [0xA5000000+i for i in range(20)]
                if target == S['allocate_memory']: model.r[2] = model.result
                if target == transition.S['func_15084D00']: model.r[2] = 8
                if target == transition.S['func_1502B020']: model.r[2] = 0x33000
        cases = delegated = 0
        for identity, path, scale, phase in itertools.product((7, 255, 0x1FF), range(4), FLOATS[:5], (0, 8)):
            memory, args, created = constructor.fixture(identity=identity, count=-1, scale=scale, active=path&1)
            entry = (constructor.S['D_800D1C90']+identity*4)&0xFFFFFFFF
            memory.update({entry+i:0 for i in range(4)}); put(memory, entry, constructor.RESOURCE)
            memory.update({fields.S['D_80086CAC']+i:0 for i in range(1024)})
            memory.update({S['D_800D1588']+i:0 for i in range(1024)})
            memory.update({S['D_800C5A90']+i:0 for i in range(512)})
            memory.update({BUFFER+i:0xA5 for i in range(0x400)})
            put(memory, S['D_800D1588']+(identity&255)*4, path != 0)
            put(memory, S['D_800C5A90']+(identity&255)*2, path != 1, 2)
            put(memory, S['D_800C5A90']+16, 1, 2)
            result = 0 if path == 2 else BUFFER
            models = [Connected(memory, args, created, inner, phase, result).run() for inner in (self.retail, self.raw)]
            self.assertEqual((models[0].memory, models[0].events, models[0].calls, models[0].r, models[0].f),
                (models[1].memory, models[1].events, models[1].calls, models[1].r, models[1].f))
            delegated += sum(c[0] == S['func_1505E650'] for c in models[0].calls); cases += 1
        self.assertGreater(delegated, 0)
        self.receipt('connected', cases=cases, executions=cases*2, animation_calls_per_form=delegated,
            actual_complete_182_word_constructor_68_word_initializer_70_word_resource_helper=True,
            allocator_SDK_and_animation_and_deeper_resource_callbacks_bounded=True)
    def test_08_native32_profiles_float_bits_and_effective_negative(self):
        for profile in ('-O2', '-O0'):
            result, detail = self.run_native('native-'+profile[1:], NATIVE_PREFIX+screen.SELECTED+NATIVE_RUNNER, profile)
            self.assertEqual((result, detail), (0, [16384, 0, 0]))
        bad = screen.SELECTED.replace('state, scale,', 'state, 0.0f,')
        result, _ = self.run_native('native-negative', NATIVE_PREFIX+bad+NATIVE_RUNNER)
        self.assertNotEqual(result, 0)
        self.receipt('native', cases_per_profile=16384, executions=32768, profiles=['O2', 'O0'],
            typed_float_bits_not_numeric_conversion=True, effective_negative=1, private_homes_guest_only=True)
    def test_09_whole_linked_installation_and_immutable_baselines(self):
        with self.assertRaisesRegex(ValueError, 'immutable'): self.receipt('baseline')
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
        source = (self.root/screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            for name, path in self.paths.items():
                self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(), self.baseline[name])
            self.receipt('linked', installed=False); return
        self.assertEqual(source, screen.install((self.out/'before-source').read_text()))
        expected = bytearray(self.before)
        struct.pack_into('>51I', expected, elf_slot_offset(self.before, screen.ENTRY, 204), *self.retail)
        extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.before, extent)[0], 12)
        struct.pack_into('>I', expected, extent, 204)
        actual = (self.root/self.paths['elf']).read_bytes(); self.assertEqual(bytes(expected), actual)
        for name in ('guards', 'progress', 'rodata', 'symbols', 'undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(), (self.out/('before-'+name)).read_bytes())
        audit = audit_layout(self.root/self.paths['elf'], self.root/'conker'); self.assertTrue(audit['exact'], audit)
        self.receipt('linked', installed=True, ELF_bytes=len(actual), ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before, actual)), only_target_slot_and_12_to_204_extent_change=True,
            all_other_ELF_bytes_metadata_and_guards_conversion_rows_exact=True, protected_data=audit)
    def test_10_numeric_float_conversion_constructor_rejected_by_original_guards(self):
        source = screen.install((self.out/'before-source').read_text())
        good = 'func_150838EC(created, state, mode, scale);'
        self.assertEqual(source.count(good), 1)
        source = source.replace(good, 'func_150838EC(created, state, mode, (f32)*(u32 *)&scale);')
        obj, diagnostics = compile_owner(self.root, self.out, source, 'numeric-scale-negative')
        self.assertEqual(diagnostics, [])
        subprocess.run(['python3', str(self.root/'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
            str((self.out/'numeric-scale-negative.c').relative_to(self.root/'conker')), '--post-process',
            str(obj.relative_to(self.root/'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
            '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root/'conker', check=True, capture_output=True)
        result = subprocess.run(['python3', str(self.root/'tools/pad_c_object.py'), str(obj),
            str(self.root/'conker/retail_layout.us.txt'), 'generated_AEB40', str(self.out/'numeric-negative-padded.s'),
            '--word-patches', str(self.out/'before-guards')], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('func_15083AC8', result.stderr+result.stdout)
        self.receipt('constructor-negative', actual_production_pad_rejects_numeric_float_conversion=True,
            original_guard_manifest_used_unchanged=True, rejection=result.stderr+result.stdout)


NATIVE_PREFIX = r'''
#include <stddef.h>
typedef unsigned char u8; typedef unsigned short u16; typedef unsigned int u32;
typedef int s32; typedef float f32;
typedef char widths[(sizeof(void*)==4 && sizeof(f32)==4 && sizeof(s32)==4)?1:-1];
u32 D_800D1588[256]; u16 D_800C5A90[256];
static u8 memory[4096], initial[4096], saved[4096];
static u32 observed[7], calls[3], failure; static u8 *result;
static u32 word(const void *p) {u32 v; unsigned i; for(i=0;i<4;i++) ((u8*)&v)[i]=((const u8*)p)[i]; return v;}
static void store(u8 *p,u32 v) {unsigned i; for(i=0;i<4;i++) p[i]=((u8*)&v)[i];}
void *allocate_memory(s32 size,s32 mode,s32 kind,s32 zero) {
    calls[0]++; if(size!=992 || mode!=1 || kind!=2 || zero!=0) failure++;
    D_800D1588[memory[0x404]]=0; D_800C5A90[memory[0x404]]=0;
    memory[0x404]=19; return result;
}
void bzero(void *p,int count) {
    int i; calls[1]++; if(count!=64) failure++;
    for(i=0;i<count;i++) ((u8*)p)[i]=0;
}
void func_1505E650(u8 *actor,u16 state,f32 scale,f32 x,f32 y,f32 z,s32 mode) {
    calls[2]++; observed[0]=(u32)(actor-memory); observed[1]=state;
    observed[2]=word(&scale); observed[3]=word(&x); observed[4]=word(&y); observed[5]=word(&z);
    observed[6]=(u32)mode; store(actor+0x84,state);
}
'''
NATIVE_RUNNER = r'''
static s32 expected(u8 *actor,s32 state,s32 mode,f32 scale) {
    u32 identity=actor[4]; u8 *allocated;
    if(!D_800D1588[identity]) return 0;
    if(!D_800C5A90[identity]) return 0;
    allocated=allocate_memory(992,1,2,0);
    store(actor+720,(u32)allocated);
    if(!allocated) return 1;
    bzero((void*)word(actor+720),64);
    func_1505E650(actor,(u16)((u32)state&65535),scale,0.0f,0.0f,0.0f,mode);
    return 0;
}
static u32 results[3];
static int run(void) {
    const u32 floats[4]={0x80000000,0x3F800000,0x7F812345,1};
    const u32 states[4]={0,65535,65536,0xFEDCBA98};
    const u32 modes[4]={0,1,0xFFFFFFFF,0x80000000};
    unsigned identity,path,bits,alias,form,i,j,cases=0; u32 seen[2][7], called[2][3]; s32 returns[2];
    for(identity=0;identity<256;identity++) for(path=0;path<4;path++)
    for(bits=0;bits<4;bits++) for(alias=0;alias<4;alias++) {
        f32 scale; for(i=0;i<4;i++) ((u8*)&scale)[i]=((const u8*)&floats[bits])[i];
        for(i=0;i<4096;i++) initial[i]=(u8)(i*31+identity);
        initial[0x404]=(u8)identity; store(initial+0x6D0,0xFEDCBA98);
        for(form=0;form<2;form++) {
            for(i=0;i<4096;i++) memory[i]=initial[i];
            for(i=0;i<256;i++) {D_800D1588[i]=path?0x80000000:0; D_800C5A90[i]=(u16)(path==1?0:65535);}
            for(i=0;i<7;i++) observed[i]=0;
            for(i=0;i<3;i++) calls[i]=0;
            result=path==2?NULL:memory+(alias==0?0x900:alias==1?0x400:alias==2?0x6A0:0xA00);
            returns[form]=form?expected(memory+0x400,(s32)states[identity%4],(s32)modes[(identity+bits)%4],scale):
                func_150838EC(memory+0x400,(s32)states[identity%4],(s32)modes[(identity+bits)%4],scale);
            for(i=0;i<7;i++) seen[form][i]=observed[i];
            for(i=0;i<3;i++) called[form][i]=calls[i];
            if(!form) for(i=0;i<4096;i++) saved[i]=memory[i];
        }
        if(failure || returns[0]!=returns[1]) return 1;
        for(j=0;j<7;j++) if(seen[0][j]!=seen[1][j]) return 2;
        for(j=0;j<3;j++) if(called[0][j]!=called[1][j]) return 3;
        for(i=0;i<4096;i++) if(saved[i]!=memory[i]) return 4;
        cases++;
    }
    results[0]=cases; return 0;
}
void _start(void) {
    int code=run();
    __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(results),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");
    __builtin_unreachable();
}
'''


if __name__ == '__main__': unittest.main()
