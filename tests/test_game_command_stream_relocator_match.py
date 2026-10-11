"""Complete Gfx scan, signed opcodes, actual relocation leaf and owner audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_command_stream_relocator_candidates as screen
from tools.experiments import game_command_weight_counter_candidates as counter
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_resource_buffers as buffers
from tools.tests import test_game_resource_extras_match as extras
from tools.tests import test_game_resource_preparation_match as preparation
from tools.tests import test_game_main_resource_loader as main
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools


STACK, STREAM, LEAF = guest.STACK, 0x30000, screen.SYMBOLS['func_1503D438']
VALUES = (0, 1, 0x00FFFFFF, 0x0F000000, 0x80000000, 0x80000001,
    0xF0000000, 0xF1000000, 0xFFFFFFFF)
BASES = (0, 1, 0x10000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)


def fixture(records=((1, 0, 1), (0xDC, 14, 0x80000000)), address=STREAM):
    memory = {STACK+i:0xA5 for i in range(-0x600, 0xC0)}
    for index, (opcode, subtype, value) in enumerate((*records, (0xDF, 0xFF, 0x12345678))):
        start = (address+index*8)&0xFFFFFFFF
        memory.update({(start+i)&0xFFFFFFFF:0xA5 for i in range(8)})
        put(memory, start, opcode, 1)
        put(memory, start+3, subtype, 1)
        put(memory, start+4, value)
    return memory


class CommandOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, commands=STREAM, base=0x10000, phase=0,
            entry=screen.ENTRY, leaf=LEAF, leaf_words=None, actions=None):
        connected = None if leaf_words is None else {leaf+i*4:w for i,w in enumerate(leaf_words)}
        super().__init__(words, memory, arguments=(commands, base), phase=phase, entry=entry, connected=connected)
        self.leaf, self.actions = leaf, actions or {}
        self.loads = 0
    def execute(self, word):
        if word >> 26 == 32:
            buffers.CopyOracle.execute(self, word)
        else:
            super().execute(word)
    def record_call(self, target):
        assert target == self.leaf
        args = tuple(self.r[4:6])
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))
    def hook(self, target):
        assert target == self.leaf
        location, base = self.calls[-1][1:]
        value = self.get(location, 4)
        if value and not value & 0x0F000000:
            self.put(location, (value+base)&0xFFFFFFFF, 4)
        for address, value, width in self.actions.get(self.loads, ()):
            self.put(address, value, width)
        self.loads += 1
        extras.clobber(self, 0xDEADBEEF)


class Reference:
    def __init__(self, memory, leaf=LEAF, actions=None):
        self.memory, self.events, self.calls = memory.copy(), [], []
        self.leaf, self.actions, self.loads = leaf, actions or {}, 0
    def get(self, address, width=1):
        assert all(address+i in self.memory for i in range(width)), ('unmapped reference read', address, width)
        value = read(self.memory, address, width)
        self.events.append(('R', address, width, value))
        return value
    def put(self, address, value, width=4):
        assert all(address+i in self.memory for i in range(width))
        put(self.memory, address, value, width)
        self.events.append(('W', address, width, value&((1 << (width*8))-1)))
    def call(self, address, base):
        self.calls.append((self.leaf, address, base))
        self.events.append(('CALL', self.leaf, (address, base)))
        value = self.get(address, 4)
        if value != 0 and value & 0x0F000000 == 0:
            self.put(address, (value+base)&0xFFFFFFFF)
        for location, value, width in self.actions.get(self.loads, ()):
            self.put(location, value, width)
        self.loads += 1
    def run(self, commands=STREAM, base=0x10000):
        if commands == 0:
            return
        opcode = self.get(commands)
        if opcode == 0xDF:
            return
        opcode = self.get(commands)
        for index in range(128):
            address = (commands+index*8)&0xFFFFFFFF
            if opcode == 1:
                self.call(address+4, base)
            elif opcode == 0xDC and self.get(address+3) == 14:
                self.call(address+4, base)
            opcode = self.get((address+8)&0xFFFFFFFF)
            if opcode == 0xDF:
                return
        raise AssertionError('unterminated bounded reference stream')


class GameCommandStreamRelocatorMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-command-stream-relocator-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt', layout='conker/retail_layout.us.txt')
        manifest = cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == 'f43fa661893aadea680107f8ebe446bdad763489b5558996c8a906802beca058'
        assert cls.baseline['elf'] == '81f7a53fc8dd01e18813f618d7dde988220e76f457a719949052b718be7d501d'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes()
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>52I', cls.rom, screen.ROM))
        cls.leaf_words = list(struct.unpack_from('>9I', cls.before, elf_slot_offset(cls.before, LEAF, 36)))
        assert cls.leaf_words == list(struct.unpack_from('>9I', cls.rom, 0x6A8E8))
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        body = (cls.root/'conker/asm/6A3D0.s').read_text().split('glabel '+screen.FUNCTION, 1)[1].split(
            'endlabel '+screen.FUNCTION, 1)[0]
        cls.slot = cls.out/'slot.s'
        cls.slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', cls.slot, filename='generated_6A3D0'))

    def receipt(self, name, **values):
        (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')
    def link(self, name, entry=screen.ENTRY, leaf=LEAF):
        script = self.out/'rebase.ld'
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            '--defsym=func_1503D438=0x%X'%leaf, '-o', str(elf), str(self.out/(name+'.o'))],
            check=True, capture_output=True)
        return list(struct.unpack_from('>52I', sections(elf)['.text'][1]))
    def compare(self, memory, forms=None, **settings):
        reference = Reference(memory, leaf=settings.get('leaf', LEAF), actions=settings.get('actions'))
        reference.run(settings.get('commands', STREAM), settings.get('base', 0x10000))
        expected = preparation.public(reference.memory), preparation.events(reference.events), reference.calls
        models = [CommandOracle(words, memory, **settings).run() for words in (forms or (self.retail, self.raw, self.padded))]
        for model in models:
            self.assertEqual((preparation.public(model.memory), preparation.events(model.events), model.calls), expected)
        return models
    def test_01_direct_complete_words_and_no_guards(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (52, 0x38, 0))
        self.assertEqual((self.meta['pool_bytes'], self.meta['diagnostics']), (0, ''))
        self.assertEqual(self.raw, self.retail)
        self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(self.link('padded'), self.retail)
        self.receipt('shape', words=52, frame=0x38, direct_differences=0, new_guards=0, original_saved_registers=True)
    @property
    def padded(self):
        if not hasattr(type(self), '_padded_words'):
            type(self)._padded_words = self.link('padded')
        return type(self)._padded_words
    def test_02_all_opcodes_subtypes_and_payload_boundaries(self):
        cases, reached = 0, set()
        for model in self.compare(fixture(records=()), commands=0):
            reached.update(model.visits)
        for model in self.compare(fixture(records=())):
            reached.update(model.visits)
        cases += 2
        for opcode, phase in itertools.product(range(256), (0, 8)):
            for model in self.compare(fixture(((opcode, 14, 1),)), phase=phase):
                reached.update(model.visits)
            cases += 1
        for subtype, phase in itertools.product(range(256), (0, 8)):
            for model in self.compare(fixture(((0xDC, subtype, 1),)), phase=phase):
                reached.update(model.visits)
            cases += 1
        for value, base, opcode, phase in itertools.product(VALUES, BASES, (1, 0xDC, 0x7F), (0, 8)):
            for model in self.compare(fixture(((opcode, 14, value),)), base=base, phase=phase,
                    leaf_words=self.leaf_words):
                reached.update(model.visits)
            cases += 1
        unreachable = {screen.ENTRY+0x78}
        self.assertEqual(reached & set(range(screen.ENTRY, screen.ENTRY+208, 4)),
            set(range(screen.ENTRY, screen.ENTRY+208, 4))-unreachable)
        self.receipt('guest', cases=cases, forms=3, reachable_words=51, unreachable_duplicate_subtype=sorted(unreachable),
            all_256_signed_opcodes_and_unsigned_subtypes=True, actual_9_word_leaf=True, full_public_memory_access_call_reference=True)
    def test_03_live_next_records_and_callee_clobbers(self):
        cases = 0
        for changes, phase in itertools.product(((), ((STREAM+8, 0xDF, 1),), ((STREAM+8, 1, 1),),
                ((STREAM+11, 15, 1),), ((STREAM+16, 1, 1), (STREAM+20, 0x80000000, 4))), (0, 8)):
            self.compare(fixture(((1, 0, 1), (0xDC, 14, 1), (0x7F, 0, 1))), actions={0:changes}, phase=phase)
            cases += 1
        self.receipt('callbacks', cases=cases, argument_and_base_survive_volatile_clobbers=True,
            next_opcode_and_subtype_reloads_preserved=True, hook_mutations_bounded_not_actual_leaf_behavior=True)
    def test_04_independent_rebases(self):
        cases = 0
        for entry, leaf in ((screen.ENTRY, LEAF), (0x15207FF0, 0x152080D0), (0x15308004, 0x15309008)):
            words = [self.link(name, entry, leaf) for name in ('original', 'selected', 'padded')]
            self.assertEqual(words[0], words[1])
            self.assertEqual(words[0], words[2])
            for value, base, phase in itertools.product(VALUES, BASES, (0, 8)):
                self.compare(fixture(((1, 0, value), (0xDC, 14, value))), forms=words,
                    base=base, phase=phase, entry=entry, leaf=leaf, leaf_words=self.leaf_words)
                cases += 1
        self.receipt('rebases', independent_links=9, cases=cases, all_three_forms_word_exact=True)
    def test_05_every_private_and_public_fault_prefix(self):
        pairs = 0
        fitted = self.link('padded')
        for records, phase in itertools.product(((), ((1, 0, 1),), ((0xDC, 14, 0x80000000),),
                ((0xDC, 15, 1), (0xFF, 0, 1)), ((1, 0, 1), (0xDC, 14, 1), (0, 0, 1))), (0, 8)):
            memory = fixture(records)
            complete = CommandOracle(self.retail, memory, phase=phase, leaf_words=self.leaf_words).run()
            for ordinal in range(complete.accesses):
                models = [CommandOracle(words, memory, phase=phase, leaf_words=self.leaf_words)
                    for words in (self.retail, self.raw, fitted)]
                for model in models:
                    model.fault = ordinal
                    with self.assertRaises(guest.AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, ordinal)
                self.assertEqual((models[0].memory, models[0].events, models[0].calls, models[0].r),
                    (models[1].memory, models[1].events, models[1].calls, models[1].r))
                self.assertEqual((models[0].memory, models[0].events, models[0].calls, models[0].r),
                    (models[2].memory, models[2].events, models[2].calls, models[2].r))
                pairs += 1
        self.receipt('faults', fired_original_raw_padded_triples=pairs, every_stack_public_and_actual_leaf_access=True,
            complete_partial_memory_events_calls_registers_exact=True, guest_model_not_hardware=True)
    def test_06_effective_semantic_and_install_controls(self):
        controls = (
            ('terminator', '!= -0x21', '!= -0x20', fixture(((0xE0, 0, 1),))),
            ('vertex', 'case 1:', 'case 2:', fixture(((1, 0, 1),))),
            ('memory', 'case -0x24:', 'case -0x23:', fixture(((0xDC, 14, 1),))),
            ('subtype', '== 0x0E', '== 0x0F', fixture(((0xDC, 14, 1),))),
            ('payload', '.words.w1', '.words.w0', fixture(((1, 0, 1),))),
            ('stride', 'commands[index]', 'commands[index * 2]', fixture(((1, 0, 1), (1, 0, 1)))),
        )
        for name, before, after, memory in controls:
            body = screen.QUALIFIED.replace(before, after)
            self.assertNotEqual(body, screen.QUALIFIED)
            with patch.object(screen, 'ENTRY', 0x15400000):
                _, words = screen.compile_candidate(self.root, self.out, 'negative-'+name, body)
            with self.assertRaises(AssertionError):
                self.compare(memory, forms=(words,), entry=0x15400000)
        before = (self.out/'before-source').read_text()
        for altered in (before.replace(screen.ORIGINAL, ''), before+screen.ORIGINAL,
                before.replace('s32 func_1503D368();', 'void func_1503D368();')):
            with self.assertRaises(ValueError):
                screen.install(altered)
        self.receipt('controls', effective_compiled_controls=6, stale_install_rejections=3)
    def test_07_complete_owner_and_actual_padders(self):
        before = (self.out/'before-source').read_text()
        objects = []
        run = subprocess.run
        def compile_run(command, *args, **kwargs):
            if str(command[0]).endswith('/cc'):
                command = list(command)+['-Wo,-loopunroll,0']
            return run(command, *args, **kwargs)
        for name, body in (('owner-before', before), ('owner-after', screen.install(before))):
            with patch('subprocess.run', side_effect=compile_run):
                obj, diagnostics = compile_owner(self.root, self.out, body, name)
            self.assertEqual(diagnostics, [])
            objects.append(obj)
        def fingerprint(obj, name):
            text, functions, relocations = parse_object(obj)
            info = functions[name]
            start, end = info['value'], info['value']+info['size']
            return info['size'], text[start:end], {o-start:v for o,v in relocations.items() if start <= o < end}
        names = set(parse_object(objects[0])[1])
        self.assertEqual(names, set(parse_object(objects[1])[1]))
        for name in names-{screen.FUNCTION}:
            self.assertEqual(fingerprint(objects[0], name), fingerprint(objects[1], name), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        self.assertEqual(fingerprint(objects[1], screen.FUNCTION), fingerprint(self.out/'selected.o', screen.FUNCTION))
        routes = []
        for route in ('pad_c_object.py', 'pad_generated_object.py'):
            parsed = []
            for i, obj in enumerate(objects):
                asm = self.out/('owner-'+route+'-'+str(i)+'.s')
                args = [str(obj), str(self.out/'before-layout'), 'generated_6A3D0', str(asm)] if route == 'pad_c_object.py' else [
                    str(obj), str(self.root/'conker/asm/6A3D0.s'), str(asm), '--filename', 'generated_6A3D0']
                subprocess.run(['python3', str(self.root/'tools'/route), *args, '--word-patches', str(self.out/'before-guards')],
                    check=True, capture_output=True)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(asm.with_suffix('.o')), str(asm)],
                    check=True, capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            start = parsed[1][1][screen.FUNCTION]['value']
            expected = bytearray(parsed[0][0])
            expected[start:start+208] = parsed[1][0][start:start+208]
            self.assertEqual(bytes(expected), parsed[1][0])
            self.assertEqual({o:v for o,v in parsed[0][2].items() if not start <= o < start+208},
                {o:v for o,v in parsed[1][2].items() if not start <= o < start+208})
            routes.append(parsed[1])
        self.assertEqual(routes[0], routes[1])
        self.receipt('owner', neighbors=len(names)-1, actual_padders=2, diagnostics=0,
            only_target_changes=True, typed_void_Gfx_u32_callers_and_guarded_main_unchanged=True)
    def test_08_immutable_whole_ELF_installation_audit(self):
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
        source = counter.command_source(self.root)
        before_source = (self.out/'before-source').read_text()
        installed_now = source != before_source
        self.assertEqual(source, screen.install(before_source) if installed_now else before_source)
        actual = counter.command_elf(self.root, self.before)
        expected = bytearray(self.before)
        start = elf_slot_offset(self.before, screen.ENTRY, 208)
        extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.before, extent)[0], 12)
        if installed_now:
            struct.pack_into('>52I', expected, start, *self.retail)
            struct.pack_into('>I', expected, extent, 208)
        self.assertEqual(bytes(expected), actual)
        for name, path in self.paths.items():
            if name not in ('source', 'elf'):
                self.assertEqual((self.root/path).read_bytes(), (self.out/('before-'+name)).read_bytes())
        audit = audit_layout(self.root/self.paths['elf'], self.root/'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('linked', installed=installed_now, ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a != b for a,b in zip(self.before, actual)),
            changed_target_bytes=sum(a != b for a,b in zip(self.before[start:start+208], actual[start:start+208])),
            changed_extent_bytes=sum(a != b for a,b in zip(self.before[extent:extent+4], actual[extent:extent+4])),
            every_other_byte_metadata_extent_data_guard_and_CSV_exact_after_counter_projection=True,
            protected_data=audit)

    def test_09_actual_native32_complete_C(self):
        for profile in ('-O2', '-O0'):
            code, detail = self.run_native('native-'+profile[1:], NATIVE+screen.QUALIFIED+NATIVE_MAIN, profile)
            self.assertEqual((code, detail), (0, ''), (profile, code, detail))
        body = screen.QUALIFIED.replace('case 1:', 'case 2:')
        code, _ = self.run_native('native-negative', NATIVE+body+NATIVE_MAIN)
        self.assertNotEqual(code, 0)
        self.receipt('native', cases_per_profile=65754, profiles=['O2', 'O0'], Gfx_size_8_word_offset_4=True,
            full_memory_and_call_arguments_reference=True, all_opcode_subtype_pairs=True,
            effective_vertex_control=True, established_no_strict_aliasing_profile=True)

    def test_10_actual_parent_main_command_extras_relocator_buffer_chain(self):
        original_oracle, original_reference, original_fixture = main.MainOracle, main.Reference, main.fixture
        child_words = self.raw
        reached = set()
        class WithCommands(original_oracle):
            def __init__(model, *args, **kwargs):
                connected = dict(kwargs.get('connected') or {})
                connected.update({screen.ENTRY+i*4:w for i,w in enumerate(child_words)})
                kwargs['connected'] = connected
                super().__init__(*args, **kwargs)
            def run(model):
                result = super().run()
                reached.update(model.visits & set(range(screen.ENTRY, screen.ENTRY+208, 4)))
                return result
        class WithReference(original_reference):
            def call(model, role, *args):
                if role != 'child':
                    return super().call(role, *args)
                target = main.S[main.ROLES[role]]
                model.calls.append((target, *args))
                model.events.append(('CALL', target, args))
                child = Reference(model.memory)
                child.run(commands=args[0], base=args[1])
                model.memory = child.memory
                model.events.extend(child.events)
                model.calls.extend(child.calls)
                return 0
        def with_streams(*args, **kwargs):
            memory = original_fixture(*args, **kwargs)
            for group, table in enumerate((main.PRIMARY, main.SECONDARY, main.NEW_PRIMARY, main.NEW_SECONDARY)):
                for index in range(16):
                    address = 0x60000+(group*16+index)*0x40
                    memory.update(fixture(((1, 0, 1), (0xDC, 14, 0x80000000)), address=address))
                    put(memory, table+index*4, address-main.BLOCK)
            return memory
        saved = self.retail, self.raw
        try:
            self.retail = self.raw = list(struct.unpack_from('>274I', self.rom, main.screen.ROM))
            with patch.object(main, 'MainOracle', WithCommands), patch.object(main, 'Reference', WithReference), \
                    patch.object(main, 'fixture', with_streams):
                main.GameMainResourceLoaderTests.test_10_actual_parent_main_extras_relocator_buffer_chain(self)
        finally:
            self.retail, self.raw = saved
        self.assertTrue(reached)
        self.receipt('command-chain', cases=768, reached_command_words=len(reached),
            actual_104_274_52_56_9_194_word_bodies=True, command_hook_replaced_by_actual_C_body=True,
            deeper_allocator_copy_free_auxiliary_hardware_runtime_still_bounded=True)

    def test_11_exact_child_projection_and_effective_rejections(self):
        before_source = (self.out/'before-source').read_text()
        qualified = screen.install(before_source)
        source_path = self.root/screen.SOURCE
        elf_path = self.root/self.paths['elf']
        read_text, read_bytes = Path.read_text, Path.read_bytes
        start = elf_slot_offset(self.before, screen.ENTRY, 208)
        extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        current = bytearray(self.before)
        struct.pack_into('>52I', current, start, *self.retail)
        struct.pack_into('>I', current, extent, 208)
        def source_patch(body):
            return patch.object(Path, 'read_text', lambda path, *a, **kw:
                body if path == source_path else read_text(path, *a, **kw))
        def elf_patch(data):
            return patch.object(Path, 'read_bytes', lambda path:
                bytes(data) if path == elf_path else read_bytes(path))
        with source_patch(qualified), elf_patch(current):
            self.assertEqual(screen.parent_source(self.root), before_source)
            self.assertEqual(screen.parent_elf(self.root, self.before), self.before)
        for wrong in (qualified.replace('case 1:', 'case 2:'),
                qualified.replace('void func_1503D368(Gfx *, u32);', 'void func_1503D368();'),
                qualified.replace('func_1503D368((Gfx *)*(u32 *)', 'func_1503D368(*(u32 *)', 1),
                qualified+'\n'):
            with source_patch(wrong), self.assertRaises(AssertionError):
                screen.parent_source(self.root)
        for offset in (start+4, extent+3):
            wrong = current.copy()
            wrong[offset] ^= 1
            with source_patch(qualified), elf_patch(wrong), self.assertRaises(AssertionError):
                screen.parent_elf(self.root, self.before)
        wrong = current.copy()
        wrong[start+208] ^= 1
        expected = bytearray(self.before)
        expected[start+208] ^= 1
        with source_patch(qualified), elf_patch(wrong):
            projected = screen.parent_elf(self.root, self.before)
            self.assertEqual(projected, bytes(expected))
            self.assertNotEqual(projected, self.before)
        self.receipt('historical-audits', qualified_source_slot_and_extent_only=True,
            effective_source_rejections=4, effective_word_extent_rejections=2,
            unrelated_ELF_byte_preserved_for_old_whole_ELF_rejection=True,
            historical_baselines_not_refreshed=True)


NATIVE = r'''typedef signed char s8;typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef union {struct {unsigned long w0,w1;} words;unsigned long long align;} Gfx;
#define NULL ((void *)0)
typedef char size_check[sizeof(Gfx)==8?1:-1];
void func_1503D368(Gfx *,u32);
static Gfx data[6],expect[6];static u32 calls[8][2],wanted[8][2];
static int count,referenceCount,mutation,error;
static void change(u8 *p,int index) {
    if(index==0) {
        if(mutation==1) p[8]=0xDF;
        if(mutation==2) p[11]=15;
        if(mutation==3) *(u32 *)(p+12)=0x80000000U;
    }
}
void func_1503D438(u32 *p,u32 base) {
    u32 value=*p;int index=count++;
    if(index>=8) {error=1;return;}
    calls[index][0]=(u32)p-(u32)data;calls[index][1]=base;
    if(value!=0 && (value&0x0F000000U)==0) *p=value+base;
    change((u8 *)data,index);
}
static void referenceCall(u8 *p,u32 base) {
    u32 value=*(u32 *)p;int index=referenceCount++;
    if(index>=8) {error=1;return;}
    wanted[index][0]=(u32)p-(u32)expect;wanted[index][1]=base;
    if(value!=0 && (value&0x0F000000U)==0) *(u32 *)p=value+base;
    change((u8 *)expect,index);
}
static void reference(u8 *p,u32 base) {
    int i;
    if(p==NULL) return;
    for(i=0;i<6;i++) {
        u8 *record=p+i*8;int opcode=record[0];
        if(opcode==0xDF) return;
        if(opcode==1 || (opcode==0xDC && record[3]==14)) referenceCall(record+4,base);
    }
    error=1;
}
static int check(int opcode,int subtype,u32 value,u32 base,int mode,int absent) {
    int i;u8 *p=(u8 *)data,*q=(u8 *)expect;
    count=referenceCount=error=0;mutation=mode;
    for(i=0;i<(int)sizeof(data);i++) p[i]=0xA5;
    p[0]=(u8)opcode;p[3]=(u8)subtype;*(u32 *)(p+4)=value;
    p[8]=0xDC;p[11]=14;*(u32 *)(p+12)=0x80000000U;
    p[16]=1;p[19]=0xFF;*(u32 *)(p+20)=1;
    p[24]=0xDF;
    for(i=0;i<(int)sizeof(data);i++) q[i]=p[i];
    for(i=0;i<16;i++) ((u32 *)calls)[i]=((u32 *)wanted)[i]=0;
    reference(absent?NULL:q,base);
    func_1503D368(absent?NULL:data,base);
    if(error || count!=referenceCount) return 1;
    for(i=0;i<(int)sizeof(data);i++) if(p[i]!=q[i]) return 2;
    for(i=0;i<16;i++) if(((u32 *)calls)[i]!=((u32 *)wanted)[i]) return 3;
    return 0;
}
'''
NATIVE_MAIN = r'''
static int run(void) {
    static u32 values[]={0,1,0x00FFFFFFU,0x0F000000U,0x80000000U,0x80000001U,0xF0000000U,0xF1000000U,0xFFFFFFFFU};
    static u32 bases[]={0,1,0x10000U,0x7FFFFFFFU,0x80000000U,0xFFFFFFFFU};
    int op,sub,i,j,mode,result;
    for(op=0;op<256;op++) for(sub=0;sub<256;sub++) {
        result=check(op,sub,values[(op+sub)%9],bases[(op+sub)%6],(op+sub)%4,0);
        if(result) return result;
    }
    for(i=0;i<9;i++) for(j=0;j<6;j++) for(mode=0;mode<4;mode++) {
        result=check(1,14,values[i],bases[j],mode,0);if(result) return result;
    }
    result=check(1,14,1,1,0,1);if(result) return result;
    return check(0xDF,0,1,1,0,0);
}
void _start(void) {int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


if __name__ == '__main__':
    unittest.main()
