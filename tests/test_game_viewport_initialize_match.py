"""Direct initializer words, literal private state, original calls and fault cuts."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_viewport_initialize_lifetimes as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import game_viewport_initialize_oracle as model
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as tracking
from tools.tests.test_game_record_constructor_match import elf_slot_offset


def state(m):
    return (m.memory, m.r, m.f, m.events, m.calls, m.current_pc, m.delay_of,
        m.all_accesses, m.root_accesses, m.observations, m.fired)


class ViewportInitializeMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)
        cls.obj, cls.padded, cls.raw, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>373I', cls.rom, source.ROM))
        cls.helpers = {}
        for va, rom, count in ((model.BOUNDS, 0x48344, 44), (model.CLAMP, 0x483F4, 87)):
            cls.helpers.update(zip(range(va, va + count * 4, 4), struct.unpack_from('>%dI' % count, cls.rom, rom)))
        data, functions = source.build.link_owner(cls.root, cls.out, cls.padded, source.OWNER)
        cls.emitted = list(struct.unpack_from('>373I', data, functions[source.FUNCTION]['value']))

    def receipt(self, name, **row):
        (self.out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')

    def test_01_direct373_frame_homes_original_and_ten_neighbors(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (373, 72, 0))
        self.assertEqual(self.row['unchanged_neighbors'], 10)
        self.assertEqual(self.row['diagnostics'], ''); self.assertFalse(self.row['pools'])
        self.assertEqual(self.raw, self.truth); self.assertEqual(self.emitted, self.truth)
        self.assertEqual(len(source.RELOCATIONS), 34)
        original = assembly.ViewListSetupTests.original.__func__(type(self), 'original-direct-viewport',
            (self.out / 'before-viewport_original').read_text(), source.FUNCTION)
        data, functions = source.build.link_owner(self.root, self.out, original, source.OWNER)
        f = functions[source.FUNCTION]; self.assertEqual(f['size'], 1492)
        self.assertEqual(data[f['value']:f['value'] + 1492], self.rom[source.ROM:source.ROM + 1492])
        before = (self.out / 'before-elf').read_bytes(); at = elf_slot_offset(before, model.BOUNDS, 524)
        self.assertEqual(before[at:at + 524], self.rom[0x48344:0x48550])
        self.receipt('emission', direct_words=373, frame=72, original_GNU_words=373, sine_home='SP+0x34',
            new_guards=0, unchanged_normal_neighbors=10, existing_A39C_no_unroll_override_verified=True)

    def test_02_three_way_independent_reference_and_literal_private_state(self):
        cases = invalid = 0; seen = set()
        fixtures = itertools.chain(model.corpus(), (model.fixture(layout=1, pattern=p) for p in (1, 2, 3)),
            (model.fixture(depth=p) for p in (0xFFFF, 0x10000)))
        for memory, args in fixtures:
            expected, calls, complete = model.reference(memory, args)
            for phase in (0, 8):
                machines = []
                for words in (self.truth, self.raw, self.emitted):
                    m = model.InitializeOracle(words, memory, args, self.helpers, phase)
                    if complete: m.run()
                    else:
                        with self.assertRaises(model.ConversionBoundary): m.run()
                    self.assertTrue(model.public(m.memory) == model.public(expected), (args, phase))
                    self.assertEqual(m.calls, calls); seen.update(m.visits); machines.append(m)
                for m in machines[1:]: self.assertEqual(state(m), state(machines[0]))
                cases += 1; invalid += not complete
        wanted = set(range(source.ENTRY, source.ENTRY + 1492, 4))
        self.assertEqual(seen & wanted, wanted)
        self.receipt('guest', three_way_cases=cases, conversion_prefix_cases=invalid, all373_words_visited=True,
            real_bounds_clamp_words=131, full_private_memory_GPR_FPR_ordered_events_and_accesses=True,
            other_helpers_bounded_here=True, hardware_FCSR_not_emulated=True)

    def test_03_callbacks_fire_and_preserve_all_literal_lifetimes(self):
        cases = 0
        for index, layout, transfer, mode, phase in itertools.product((0, 1, 3), (0, 1, 3), (0, 1), range(6), (0, 8)):
            memory, args = model.fixture(index, layout, transfer=transfer)
            expected, calls, complete = model.reference(memory, args, 2, mode)
            self.assertTrue(complete); machines = []
            for words in (self.truth, self.raw, self.emitted):
                m = model.InitializeOracle(words, memory, args, self.helpers, phase, 2, mode).run()
                self.assertTrue(model.public(m.memory) == model.public(expected), (index, layout, transfer, mode))
                self.assertEqual(len(m.fired), int(mode in (1, 2, 3, 4) or mode == 5 and bool(transfer)))
                self.assertEqual(m.calls, calls); machines.append(m)
            for m in machines[1:]: self.assertEqual(state(m), state(machines[0]))
            cases += 1
        self.receipt('callbacks', three_way_cases=cases, positive_provider_gates=True,
            live_base_page_FOV_cached_angle_and_full_private_state=True)

    def test_04_all_words_bindings_pool_and_stale_source_fail_closed(self):
        text, functions, relocations = parse_object(self.obj); f = functions[source.FUNCTION]
        for i in range(373):
            bad = bytearray(text); bad[f['value'] + i * 4] ^= 1
            with patch.object(source, 'parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaises(ValueError): source.checked_object(self.obj)
        for at in (*source.RELOCATIONS, 0):
            bad = dict(relocations); bad[f['value'] + at] = [('R_MIPS_26', 'wrong')]
            with patch.object(source, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaises(ValueError): source.checked_object(self.obj)
        with patch.object(source.previous, 'sections', return_value={'.rodata':(0, b'bad')}):
            with self.assertRaises(ValueError): source.checked_object(self.obj)
        with self.assertRaises(ValueError): source.recovered_owner(source.recovered_owner((self.out / 'before-frustum_owner').read_text()))
        self.receipt('fail-closed', word_corruptions=373, bindings=34, extra_binding=1, private_pool=1, stale_source=True)

    def test_05_independent_GNU_and_direct_C_rebases_with_carries(self):
        original = assembly.ViewListSetupTests.original.__func__(type(self), 'original-viewport-rebase',
            (self.out / 'before-viewport_original').read_text(), source.FUNCTION)
        text, functions, relocations = parse_object(self.padded)
        names = sorted({name for rows in source.RELOCATIONS.values() for _, name in rows})
        for index in range(3):
            entry = 0x15207FF0 + index * 0x100000
            symbols = {name:(entry + 0x10000 + n * 0x100 if name.startswith('func_') or name in ('sinf', 'cosf') else
                0x80100000 + n * 0x10000 + (0x7FFC, 0x8004, 0x7FD0)[index]) for n, name in enumerate(names)}
            emitted, unresolved = emit_function(text, functions[source.FUNCTION], relocations, source.FUNCTION, symbols)
            self.assertFalse(unresolved)
            asm = self.out / ('direct-rebase-%d.s' % index); asm.write_text(emitted); obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], capture_output=True, check=True)
            images = []
            for label, path in (('original', original), ('direct', obj)):
                script = self.out / ('rebase-%s-%d.ld' % (label, index))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry); elf = script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)], capture_output=True, check=True)
                images.append(sections(elf)['.text'][1][:1492])
            self.assertEqual(images[0], images[1])
        self.receipt('rebases', independent_original_links=3, direct_C_links=3, all373_words=True, HI_LO_carries=True)

    def test_06_actual_original_caller_cuts_delay_args_and_post_call_use(self):
        original = assembly.ViewListSetupTests.original.__func__(type(self), 'original-viewport-caller',
            (self.out / 'before-view_init_original').read_text(), 'func_1501A220')
        data, functions = source.build.link_owner(self.root, self.out, original, source.OWNER)
        f = functions['func_1501A220']; full = data[f['value']:f['value'] + f['size']]
        self.assertEqual(len(full), 380); self.assertEqual(full, self.rom[0x476D0:0x4784C])
        cases = 0
        for entry, length, looping in ((0x1501A320, 10, True), (0x1501A34C, 5, False)):
            cut = list(struct.unpack_from('>%dI' % length, full, entry - 0x1501A220)); join = entry + length * 4
            class Join(Exception): pass
            class Code(tracking.TrackedCode):
                def __getitem__(self, pc):
                    if pc == join: raise Join
                    return super().__getitem__(pc)
            for index, phase in itertools.product((0, 1, 3), (0, 8)):
                memory, args = model.fixture(index, 1 if looping else 0)
                model.put(memory, 0x80082FA0, index)
                expected, calls, complete = model.reference(memory, args); self.assertTrue(complete)
                machines = []
                for words in (self.truth, self.raw, self.emitted):
                    connected = dict(self.helpers); connected.update(zip(range(source.ENTRY, source.ENTRY + 1492, 4), words))
                    connected[join] = 0
                    m = model.InitializeOracle(cut, memory, args, connected, phase, entry=entry)
                    m.r[16] = m.before[16] = index; m.r[17] = m.before[17] = 1 if looping else 0
                    m.r[18] = m.before[18] = 0x80082FA0
                    base_record = m.record_call
                    def record(target):
                        if target == source.ENTRY:
                            m.calls.append((target, m.arguments(4))); m.events.append(('CALL', target, m.arguments(4)))
                        else: base_record(target)
                    m.record_call = record; m.code = Code(m.code, m)
                    with self.assertRaises(Join): m.run()
                    self.assertEqual(m.calls, [(source.ENTRY, args), *calls])
                    self.assertTrue(model.public(m.memory) == model.public(expected))
                    self.assertEqual(m.r[16], index + int(looping))
                    if looping: self.assertEqual(m.r[17], index)
                    self.assertEqual(m.r[29], model.STACK + phase); machines.append(m)
                for m in machines[1:]: self.assertEqual(state(m), state(machines[0]))
                cases += 1
        self.receipt('callers', full_original_words=95, actual_cut_cases=cases, real_delay_slot_a3=True,
            live_count_reload_and_post_call_index_increment=True, full_startup_gameplay_not_claimed=True)

    def test_07_all_executed_memory_fault_prefixes(self):
        cases = 0
        for memory, args in [model.fixture(), model.fixture(1, 1, transfer=1), model.fixture(3, 3),
                model.fixture(alias=1), model.fixture(alias=2), model.fixture(alias=3)]:
            for phase in (0, 8):
                full = model.InitializeOracle(self.truth, memory, args, self.helpers, phase).run()
                for fault in range(full.all_accesses):
                    machines = []
                    for words in (self.truth, self.raw, self.emitted):
                        m = model.InitializeOracle(words, memory, args, self.helpers, phase); m.access_fault = fault
                        with self.assertRaises(tracking.AccessBoundary): m.run()
                        self.assertEqual(m.all_accesses, fault); machines.append(m)
                    for m in machines[1:]: self.assertEqual(state(m), state(machines[0]))
                    cases += 1
        self.receipt('faults', fired_three_way_prefixes=cases, root_and_real_bounds_clamp_accesses=True,
            all_memory_GPR_FPR_events_and_delay_state=True, hardware_exceptions_not_emulated=True)


if __name__ == '__main__': unittest.main()
