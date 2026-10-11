"""Qualify the full word-loaded opcode scan and halfword publication."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_command_weight_counter_candidates as screen
from tools.experiments import game_record_pair_copy_candidates as pairs
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_command_stream_relocator_match as commands
from tools.tests import test_game_main_resource_loader as main
from tools.tests import test_game_resource_preparation_match as preparation
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools


STACK, TABLE, STREAM, SECOND = guest.STACK, 0x30000, 0x31000, 0x32000
LINKS = ((screen.ENTRY, screen.SYMBOLS),
    (0x15207FF0, dict(D_800C4488=0x80107FFC, D_800C5918=0x80118004)),
    (0x15308004, dict(D_800C4488=0x80218004, D_800C5918=0x80207FF0)))


def slot(symbols, name, identity):
    return (symbols[name]+(identity&0xFFFFFFFF)*(2 if name == 'D_800C5918' else 4))&0xFFFFFFFF


def fixture(opcodes=(5, 6, 0x10, 0x1F, 0xFF), identity=7, symbols=screen.SYMBOLS, pattern=0, output=None):
    memory = {STACK+i:0xA5 for i in range(-0x100, 0x80)}
    table_slot = slot(symbols, 'D_800C4488', identity)
    for start, size in ((table_slot, 4), (TABLE, 8),
            (slot(symbols, 'D_800C5918', identity)-2, 6), (SECOND, 16)):
        memory.update({start+i:0xA5 for i in range(size)})
    put(memory, table_slot, TABLE)
    put(memory, TABLE, STREAM)
    put(memory, TABLE+4, SECOND)
    put(memory, SECOND, 0x06000000)
    put(memory, SECOND+8, 0xDF000000)
    for index, opcode in enumerate((*opcodes, 0xDF)):
        address = STREAM+index*8
        memory.update({address+i:0xA5 for i in range(8)})
        put(memory, address, (opcode << 24)|((index*0x12345+pattern*0x314159)&0xFFFFFF))
        put(memory, address+4, (index*0x98765+pattern*0x13579+0xA180FF01)&0xFFFFFFFF)
    if output is not None:
        symbols = dict(symbols, D_800C5918=(output-(identity&0xFFFFFFFF)*2)&0xFFFFFFFF)
    return memory, symbols


class CounterOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, identity=7, phase=0, entry=screen.ENTRY, unused=(0, 0, 0)):
        super().__init__(words, memory, arguments=(identity&0xFFFFFFFF, *unused), phase=phase, entry=entry)


class Reference:
    def __init__(self, memory, symbols=screen.SYMBOLS):
        self.memory, self.events = memory.copy(), []
        self.symbols = symbols
    def get(self, address):
        assert all(address+i in self.memory for i in range(4)), ('unmapped reference word', address)
        value = read(self.memory, address)
        self.events.append(('R', address, 4, value))
        return value
    def run(self, identity=7):
        table = self.get(slot(self.symbols, 'D_800C4488', identity))
        address = self.get(table)
        count = 0
        for _ in range(1024):
            opcode = self.get(address) >> 24
            if opcode == 0xDF:
                output = slot(self.symbols, 'D_800C5918', identity)
                assert all(output+i in self.memory for i in range(2))
                put(self.memory, output, count, 2)
                self.events.append(('W', output, 2, count&0xFFFF))
                return count
            count += 1 if opcode == 5 else 2 if opcode == 6 else 4 if opcode in range(0x10, 0x20) else 0
            address = (address+8)&0xFFFFFFFF
        raise AssertionError('unterminated bounded reference')


class GameCommandWeightCounterMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-command-weight-counter-match-test'
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
        assert cls.baseline['source'] == screen.COMMAND_SOURCE_SHA
        assert cls.baseline['elf'] == '9bc1f33cba446d25b6852a2962cc5ee7f9309f4af1d9ce3b9e957f300a84f561'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes()
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>46I', cls.rom, screen.ROM))
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
    def link(self, name, entry=screen.ENTRY, symbols=screen.SYMBOLS):
        script = self.out/'rebase.ld'
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()], '-o', str(elf), str(self.out/(name+'.o'))],
            check=True, capture_output=True)
        return list(struct.unpack_from('>46I', sections(elf)['.text'][1]))
    @property
    def padded(self):
        if not hasattr(type(self), '_padded_words'):
            type(self)._padded_words = self.link('padded')
        return type(self)._padded_words
    def compare(self, memory, symbols=screen.SYMBOLS, identity=7, forms=None, **settings):
        reference = Reference(memory, symbols)
        value = reference.run(identity)
        expected = preparation.public(reference.memory), preparation.events(reference.events), value
        models = [CounterOracle(words, memory, identity=identity, **settings).run()
            for words in (forms or (self.retail, self.raw, self.padded))]
        for model in models:
            self.assertEqual((preparation.public(model.memory), preparation.events(model.events), model.r[2]), expected)
            self.assertEqual(model.calls, [])
        return models

    def test_01_direct_complete_leaf_shape(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (46, 0, 0))
        self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes']), ('', 0))
        self.assertEqual(self.raw, self.retail)
        self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(self.padded, self.retail)
        self.receipt('shape', words=46, frame=0, differences=0, new_guards=0, void_identity_contract=True)

    def test_02_all_signed_opcodes_and_word_payloads(self):
        cases, reached = 0, set()
        for opcode, pattern, phase in itertools.product(range(256), range(4), (0, 8)):
            memory, symbols = fixture((opcode,), pattern=pattern)
            for model in self.compare(memory, symbols, phase=phase):
                reached.update(model.visits)
                self.assertTrue(all(event[2] == (2 if event[0] == 'W' else 4) for event in model.events))
            cases += 1
        self.assertEqual(reached & set(range(screen.ENTRY, screen.ENTRY+184, 4)),
            set(range(screen.ENTRY, screen.ENTRY+184, 4)))
        self.receipt('guest', cases=cases, forms=3, reachable_words=46, all_256_signed_opcodes=True,
            opening_and_tail_word_loads_and_halfword_store_exact=True, incidental_full_V0_not_C_return_contract=True)

    def test_03_mixed_lengths_single_table_entry_and_aliases(self):
        cases = 0
        palette = (5, 6, 0x10, 0x1F, 0x7F, 0x80, 0x9F, 0xFF)
        for size, pattern, phase in itertools.product((0, 1, 2, 3, 4, 31, 511), range(4), (0, 8)):
            memory, symbols = fixture(tuple(palette[(i+pattern)%8] for i in range(size)), pattern=pattern)
            models = self.compare(memory, symbols, phase=phase)
            for model in models:
                self.assertNotIn(TABLE+4, [event[1] for event in model.events if event[0] == 'R'])
                self.assertNotIn(SECOND, [event[1] for event in model.events if event[0] == 'R'])
            cases += 1
        for output in (TABLE, TABLE+4, STREAM, STREAM+4, STREAM+5*8):
            memory, symbols = fixture(output=output)
            forms = [self.link(name, symbols=symbols) for name in ('original', 'selected', 'padded')]
            self.compare(memory, symbols, forms=forms)
            cases += 1
        self.receipt('lengths-aliases', cases=cases, empty_DF_and_511_record_streams=True,
            only_first_table_entry=True, publication_aliases_preserve_complete_memory_and_access_order=True)

    def test_04_independent_symbols_identities_and_ignored_registers(self):
        cases = 0
        identities = (0, 1, 7, 186, 187, 255, -1, 0x80000000, 0x7FFFFFFF)
        for entry, symbols in LINKS:
            forms = [self.link(name, entry, symbols) for name in ('original', 'selected', 'padded')]
            self.assertEqual(forms[0], forms[1])
            self.assertEqual(forms[0], forms[2])
            for identity, unused, phase in itertools.product(identities,
                    ((0, 0, 0), (0xDEADBEEF, 0x80000000, 0xFFFFFFFF)), (0, 8)):
                memory, _ = fixture(identity=identity, symbols=symbols)
                self.compare(memory, symbols, identity, forms, entry=entry, phase=phase, unused=unused)
                cases += 1
        self.receipt('rebases', independent_links=9, cases=cases, HI16_LO16_carries=True,
            guest_wrapped_identity_addresses_and_unused_A1_A2_A3_qualified=True,
            not_native_C_out_of_bounds_identity_acceptance=True)

    def test_05_every_word_read_and_halfword_write_fault_prefix(self):
        triples = 0
        for opcodes, phase in itertools.product(((), (5,), (6,), (0x10,), (0xFF,),
                (5, 6, 0x1F, 0x9F, 0xFF)), (0, 8)):
            memory, _ = fixture(opcodes)
            complete = CounterOracle(self.retail, memory, phase=phase).run()
            for ordinal in range(complete.accesses):
                models = [CounterOracle(words, memory, phase=phase) for words in (self.retail, self.raw, self.padded)]
                for model in models:
                    model.fault = ordinal
                    with self.assertRaises(guest.AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, ordinal)
                for model in models[1:]:
                    self.assertEqual((model.memory, model.events, model.calls, model.r),
                        (models[0].memory, models[0].events, models[0].calls, models[0].r))
                triples += 1
        self.receipt('faults', fired_original_raw_padded_triples=triples,
            every_word_read_and_halfword_store=True, no_stack_accesses_in_this_leaf=True,
            complete_partial_memory_events_calls_registers_exact=True, guest_not_hardware=True)

    def test_06_effective_compiled_semantics_and_stale_install_controls(self):
        controls = (('terminator', '!= -0x21', '!= -0x20', (0xE0,)),
            ('one-entry', 'index < 1', 'index < 2', (5,)),
            ('one-weight', 'opcode == 5', 'opcode == 4', (5,)),
            ('two-weight', 'count += 2', 'count += 3', (6,)),
            ('four-class', '(opcode >> 4) == 1', '(opcode >> 4) == 2', (0x1F,)),
            ('four-weight', 'count += 4', 'count += 3', (0x10,)),
            ('stride', 'commandIndex * 2', 'commandIndex * 1', (5, 6)),
            ('publication', 'D_800C5918[identity]', 'D_800C5918[identity + 1]', (5,)))
        for name, before, after, opcodes in controls:
            body = screen.QUALIFIED.replace(before, after)
            self.assertNotEqual(body, screen.QUALIFIED)
            _, words = screen.compile_candidate(self.root, self.out, 'negative-'+name, body)
            memory, symbols = fixture(opcodes)
            if name == 'stride':
                put(memory, STREAM+4, 0xDF000000)
            if name == 'publication':
                memory.update({slot(symbols, 'D_800C5918', 8)+i:0xA5 for i in range(2)})
            with self.assertRaises(AssertionError):
                self.compare(memory, symbols, forms=(words,))
        before = (self.out/'before-source').read_text()
        for wrong in (before.replace(screen.ORIGINAL, ''), before+screen.ORIGINAL,
                before.replace('s32 func_1503D984();', 'void func_1503D984();')):
            with self.assertRaises(ValueError):
                screen.install(wrong)
        self.receipt('controls', effective_compiled_controls=8, stale_install_rejections=3)

    def test_07_complete_owner_and_both_actual_padders(self):
        before = (self.out/'before-source').read_text()
        objects = []
        run = subprocess.run
        def compile_run(command, *args, **kwargs):
            if str(command[0]).endswith('/cc'):
                command = list(command)+['-Wo,-loopunroll,0']
            return run(command, *args, **kwargs)
        for name, source in (('owner-before', before), ('owner-after', screen.install(before))):
            with patch('subprocess.run', side_effect=compile_run):
                obj, diagnostics = compile_owner(self.root, self.out, source, name)
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
            expected[start:start+184] = parsed[1][0][start:start+184]
            self.assertEqual(bytes(expected), parsed[1][0])
            self.assertEqual({o:v for o,v in parsed[0][2].items() if not start <= o < start+184},
                {o:v for o,v in parsed[1][2].items() if not start <= o < start+184})
            routes.append(parsed[1])
        self.assertEqual(routes[0], routes[1])
        self.receipt('owner', neighbors=len(names)-1, actual_padders=2, diagnostics=0,
            only_target_changes=True, typed_identity_caller_and_exact_command_relocator_unchanged=True)

    def test_08_immutable_whole_ELF_installation_audit(self):
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
        source = pairs.counter_source(self.root)
        before_source = (self.out/'before-source').read_text()
        installed_now = source != before_source
        self.assertEqual(source, screen.install(before_source) if installed_now else before_source)
        actual = pairs.counter_elf(self.root, self.before)
        expected = bytearray(self.before)
        start = elf_slot_offset(self.before, screen.ENTRY, 184)
        extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.before, extent)[0], 12)
        if installed_now:
            struct.pack_into('>46I', expected, start, *self.retail)
            struct.pack_into('>I', expected, extent, 184)
        self.assertEqual(bytes(expected), actual)
        for name, path in self.paths.items():
            if name not in ('source', 'elf'):
                data = pairs.counter_guards(self.root) if name == 'guards' else (self.root/path).read_bytes()
                self.assertEqual(data, (self.out/('before-'+name)).read_bytes())
        audit = audit_layout(self.root/self.paths['elf'], self.root/'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('linked', installed=installed_now, ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a != b for a,b in zip(self.before, actual)),
            changed_target_bytes=sum(a != b for a,b in zip(self.before[start:start+184], actual[start:start+184])),
            changed_extent_bytes=sum(a != b for a,b in zip(self.before[extent:extent+4], actual[extent:extent+4])),
            every_other_ELF_byte_metadata_extent_data_guard_and_CSV_exact_after_pair_projection=True, protected_data=audit)

    def test_09_native32_all_opcode_pairs_and_halfword_wrap(self):
        for profile in ('-O2', '-O0'):
            code, detail = self.run_native('native-'+profile[1:], NATIVE+screen.QUALIFIED+NATIVE_MAIN, profile)
            self.assertEqual((code, detail), (0, ''), (profile, code, detail))
        body = screen.QUALIFIED.replace('count += 4;', 'count += 3;')
        code, _ = self.run_native('native-negative', NATIVE+body+NATIVE_MAIN)
        self.assertNotEqual(code, 0)
        self.receipt('native', cases_per_profile=67864, profiles=['O2', 'O0'],
            all_65536_opcode_pairs_and_all_256_valid_identities=True, low_16_bit_wrap_boundaries=True,
            all_output_halves_pointer_slots_and_stream_words_reference=True, effective_four_weight_control=True)

    def test_10_actual_seven_body_loader_chain_with_counter(self):
        old_oracle, old_reference, old_fixture = main.MainOracle, main.Reference, main.fixture
        old_commands_fixture = commands.fixture
        counter_words, reached = self.raw, set()
        class WithCounter(old_oracle):
            def __init__(model, *args, **kwargs):
                connected = dict(kwargs.get('connected') or {})
                connected.update({screen.ENTRY+i*4:w for i,w in enumerate(counter_words)})
                kwargs['connected'] = connected
                super().__init__(*args, **kwargs)
            def run(model):
                result = super().run()
                reached.update(model.visits & set(range(screen.ENTRY, screen.ENTRY+184, 4)))
                return result
        class WithReference(old_reference):
            def call(model, role, *args):
                if role != 'prepare':
                    return super().call(role, *args)
                target = main.S[main.ROLES[role]]
                model.calls.append((target, *args))
                model.events.append(('CALL', target, args))
                child = Reference(model.memory)
                value = child.run(args[0])
                model.memory = child.memory
                model.events.extend(child.events)
                return value
        def with_output(*args, **kwargs):
            memory = old_fixture(*args, **kwargs)
            identity = kwargs.get('identity', args[0] if args else 7)
            output = slot(screen.SYMBOLS, 'D_800C5918', identity)
            memory.update({output+i:0xA5 for i in range(2)})
            return memory
        def with_weights(records=((1, 0, 1), (0xDC, 14, 0x80000000)), **kwargs):
            if records == ((1, 0, 1), (0xDC, 14, 0x80000000)):
                records += ((5, 0, 1), (6, 0, 1), (0x1F, 0, 1))
            return old_commands_fixture(records, **kwargs)
        saved = self.retail, self.raw
        try:
            self.retail = self.raw = list(struct.unpack_from('>52I', self.rom, commands.screen.ROM))
            with patch.object(main, 'MainOracle', WithCounter), patch.object(main, 'Reference', WithReference), \
                    patch.object(main, 'fixture', with_output), patch.object(commands, 'fixture', with_weights):
                commands.GameCommandStreamRelocatorMatchTests.test_10_actual_parent_main_command_extras_relocator_buffer_chain(self)
        finally:
            self.retail, self.raw = saved
        self.assertTrue(reached)
        self.receipt('counter-chain', cases=768, reached_counter_words=len(reached),
            actual_104_274_52_46_56_9_194_word_bodies=True,
            counter_hook_replaced_with_actual_body=True,
            deeper_allocator_copy_free_auxiliary_hardware_runtime_still_bounded=True)

    def test_11_exact_historical_projection_and_effective_rejections(self):
        before_source = (self.out/'before-source').read_text()
        qualified = screen.install(before_source)
        source_path, elf_path = self.root/screen.SOURCE, self.root/self.paths['elf']
        read_text, read_bytes = Path.read_text, Path.read_bytes
        start = elf_slot_offset(self.before, screen.ENTRY, 184)
        extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        current = bytearray(self.before)
        struct.pack_into('>46I', current, start, *self.retail)
        struct.pack_into('>I', current, extent, 184)
        def source_patch(body):
            return patch.object(Path, 'read_text', lambda path, *a, **kw:
                body if path == source_path else read_text(path, *a, **kw))
        def elf_patch(data):
            return patch.object(Path, 'read_bytes', lambda path:
                bytes(data) if path == elf_path else read_bytes(path))
        with source_patch(qualified), elf_patch(current):
            self.assertEqual(screen.command_source(self.root), before_source)
            self.assertEqual(screen.command_elf(self.root, self.before), self.before)
        for wrong in (qualified.replace('count += 4;', 'count += 3;'),
                qualified.replace('void func_1503D984(s32);', 'void func_1503D984();'),
                qualified.replace('extern s16 D_800C5918[];', 'extern u16 D_800C5918[];'), qualified+'\n'):
            with source_patch(wrong), self.assertRaises(AssertionError):
                screen.command_source(self.root)
        for offset in (start+4, extent+3):
            wrong = current.copy()
            wrong[offset] ^= 1
            with source_patch(qualified), elf_patch(wrong), self.assertRaises(AssertionError):
                screen.command_elf(self.root, self.before)
        wrong, expected = current.copy(), bytearray(self.before)
        wrong[start+184] ^= 1
        expected[start+184] ^= 1
        with source_patch(qualified), elf_patch(wrong):
            self.assertEqual(screen.command_elf(self.root, self.before), bytes(expected))
            self.assertNotEqual(screen.command_elf(self.root, self.before), self.before)
        self.receipt('historical-audits', qualified_source_slot_extent_only=True,
            effective_source_rejections=4, effective_word_extent_rejections=2,
            unrelated_byte_preserved_for_whole_ELF_rejection=True, historical_baselines_not_refreshed=True)


NATIVE = r'''typedef signed char s8;typedef short s16;typedef unsigned int u32;typedef int s32;
u32 *D_800C4488[256];s16 D_800C5918[256];
void func_1503D984(s32);
static u32 data[34004],copy[34004],table[2],second[4];
static u32 randomWord(u32 index,u32 pattern) {return (index*0x12345U+pattern*0x314159U)&0xFFFFFFU;}
static int check(int first,int secondOp,int size,int identity,int pattern) {
    int i,op;u32 count=0;int length=size+1;
    second[0]=0x06000000U;second[1]=0xA5;second[2]=0xDF000000U;second[3]=0xA5;
    for(i=0;i<256;i++) {D_800C5918[i]=(s16)0xA180;D_800C4488[i]=table;}
    table[0]=(u32)data;table[1]=(u32)second;
    for(i=0;i<size;i++) {
        op=first>=0?(i==0?first:secondOp):((i+pattern)%8==0?5:(i+pattern)%8==1?6:(i+pattern)%8==2?0x10:
            (i+pattern)%8==3?0x1F:(i+pattern)%8==4?0x80:(i+pattern)%8==5?0x9F:(i+pattern)%8==6?0xFF:0);
        data[i*2]=((u32)op<<24)|randomWord((u32)i,(u32)pattern);
        data[i*2+1]=(u32)i*0x98765U+(u32)pattern*0x13579U+0xA180FF01U;
    }
    data[size*2]=0xDF000000U|randomWord((u32)size,(u32)pattern);data[size*2+1]=0xDEADBEEF;
    for(i=0;i<length*2;i++) copy[i]=data[i];
    for(i=0;i<size;i++) {
        op=(int)(copy[i*2]>>24);if(op==0xDF) break;
        count+=op==5?1U:op==6?2U:op>=0x10 && op<0x20?4U:0U;
    }
    func_1503D984(identity);
    for(i=0;i<256;i++) if((unsigned short)D_800C5918[i]!=(i==identity?(count&65535U):0xA180U) ||
        D_800C4488[i]!=table) return 1;
    for(i=0;i<length*2;i++) if(copy[i]!=data[i]) return 2;
    if(table[0]!=(u32)data || table[1]!=(u32)second || second[0]!=0x06000000U || second[2]!=0xDF000000U) return 3;
    return 0;
}
'''
NATIVE_MAIN = r'''
static int run(void) {
    static int lengths[]={8191,8192,8193,16383,16384,16385,16999,17000};
    int a,b,id,n,pattern,result;
    for(a=0;a<256;a++) for(b=0;b<256;b++) {
        result=check(a,b,2,7,(a+b)%16);if(result) return result;
    }
    for(id=0;id<256;id++) {result=check(5,0x1F,3,id,id);if(result) return result;}
    for(n=0;n<=128;n++) for(pattern=0;pattern<16;pattern++) {
        result=check(-1,0,n,7,pattern);if(result) return result;
    }
    for(n=0;n<8;n++) {result=check(0x1F,0x1F,lengths[n],7,0);if(result) return result;}
    return 0;
}
void _start(void) {int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


if __name__ == '__main__':
    unittest.main()
