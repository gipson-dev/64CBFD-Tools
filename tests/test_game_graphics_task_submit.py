"""Exact SDK task emission, ordered guest state, original caller and fault cuts."""
import itertools
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_graphics_task_submit as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import game_graphics_task_submit_oracle as model
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as tracking
from tools.tests.test_game_record_constructor_match import elf_slot_offset


def state(m):
    return (m.memory, m.r, m.f, m.events, m.calls, m.current_pc, m.delay_of,
        m.all_accesses, m.root_accesses, m.fired)


class GraphicsTaskSubmitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>239I', cls.rom, source.ROM))
        data, functions = source.build.link_owner(cls.root, cls.out, cls.padded, source.OWNER)
        cls.emitted = list(struct.unpack_from('>239I', data, functions[source.FUNCTION]['value']))
        cls.helper = dict(zip(range(model.INIT, model.INIT + 244, 4), struct.unpack_from('>61I', cls.rom, 0x4784C)))

    def receipt(self, name, **row):
        (self.out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')

    def test_01_direct239_original_frame_and_complete_owner_neighbors(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (239, 40, 0))
        self.assertEqual(self.row['diagnostics'], ''); self.assertFalse(self.row['pools'])
        self.assertEqual(self.raw, self.truth); self.assertEqual(self.emitted, self.truth)
        self.assertEqual(len(source.RELOCATIONS), 64)
        original = assembly.ViewListSetupTests.original.__func__(type(self), 'original-task-submit',
            (self.out / 'before-view_list_caller_original').read_text(), source.FUNCTION)
        data, functions = source.build.link_owner(self.root, self.out, original, source.OWNER)
        f = functions[source.FUNCTION]; self.assertEqual(f['size'], 956)
        self.assertEqual(data[f['value']:f['value'] + 956], self.rom[source.ROM:source.ROM + 956])
        before = (self.out / 'before-elf').read_bytes(); at = elf_slot_offset(before, model.INIT, 244)
        self.assertEqual(before[at:at + 244], self.rom[0x4784C:0x47940])
        self.receipt('emission', direct_words=239, frame=40, capacity_home='SP+0x24', new_guards=0,
            original_GNU_words=239, existing_no_unroll_profile=True,
            unchanged_neighbors=self.row['unchanged_no_unroll_neighbors'], unchanged_caller_functions=self.row['unchanged_caller_functions'])

    def test_02_three_way_reference_all_words_and_literal_private_state(self):
        cases = 0; seen = set()
        for memory, args in model.corpus():
            expected, calls, fired = model.reference(memory, args)
            wanted = model.public(expected)
            for phase in (0, 8):
                machines = []
                for words in (self.truth, self.raw, self.emitted):
                    m = model.SubmitOracle(words, memory, args, phase=phase).run()
                    self.assertTrue(model.public(m.memory) == wanted, args)
                    self.assertEqual(m.calls, calls); self.assertEqual(m.fired, fired)
                    seen.update(m.visits); machines.append(m)
                for m in machines[1:]: self.assertEqual(state(m), state(machines[0]))
                cases += 1
        self.assertEqual(seen & set(range(source.ENTRY, source.ENTRY + 956, 4)), set(range(source.ENTRY, source.ENTRY + 956, 4)))
        self.receipt('guest', three_way_cases=cases, all239_root_words_visited=True,
            full_literal_memory_GPR_FPR_ordered_events_accesses_and_delay_state=True,
            bounded_ucode_cache_and_blocking_queue_contracts=True, hardware_scheduling_not_emulated=True)

    def test_03_positive_callbacks_cached_capacity_and_live_task_page_fields(self):
        cases = 0
        for page, swap, phase, mode in itertools.product((0, 1), (0, 1, 0x10000), (0, 8), range(1, 7)):
            memory, args = model.fixture(used=1001 if mode in (1, 6) else 20, page=page, swap=swap)
            expected, calls, fired = model.reference(memory, args, mode); self.assertEqual(len(fired), 1)
            machines = []
            for words in (self.truth, self.raw, self.emitted):
                m = model.SubmitOracle(words, memory, args, phase=phase, mode=mode).run()
                self.assertTrue(model.public(m.memory) == model.public(expected), (page, swap, phase, mode))
                self.assertEqual(m.calls, calls); self.assertEqual(m.fired, fired); machines.append(m)
            for m in machines[1:]: self.assertEqual(state(m), state(machines[0]))
            cases += 1
        self.receipt('callbacks', three_way_cases=cases, all_positive_gates_fired=True,
            live_task_program_fields_page_count_and_halfword_wrap=True, synthetic_provider_mutations_not_runtime_evidence=True)

    def test_04_all_words_bindings_pools_and_source_anchors_fail_closed(self):
        text, functions, relocations = parse_object(self.obj); f = functions[source.FUNCTION]
        for i in range(239):
            bad = bytearray(text); bad[f['value'] + i * 4] ^= 1
            with patch.object(source, 'parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaises(ValueError): source.checked_object(self.obj)
        for at in (*source.RELOCATIONS, 0):
            bad = dict(relocations); bad[f['value'] + at] = [('R_MIPS_26', 'wrong')]
            with patch.object(source, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaises(ValueError): source.checked_object(self.obj)
        with patch.object(source, 'sections', return_value={'.rodata':(0, b'bad')}):
            with self.assertRaises(ValueError): source.checked_object(self.obj)
        for recover, key in ((source.recovered_owner, 'view_list_caller_owner'), (source.recovered_caller, 'dispatch_owner')):
            with self.assertRaises(ValueError): recover(recover((self.out / ('before-' + key)).read_text()))
        before = (self.out / 'before-guards').read_bytes(); reader = csv.DictReader(io.StringIO(before.decode()))
        fields = reader.fieldnames; rows = list(reader)
        retired = {0x558, 0x55C, 0x568, 0x588, 0x58C, 0x590, 0x598, 0x59C, 0x5B0}; tested = 0
        for row in rows:
            if row['filename'] != 'game_45B80' or row['function'] != 'func_1501878C' or int(row['offset'], 16) not in retired: continue
            for field in ('filename', 'function', 'offset', 'expected', 'replacement', 'expected_relocations', 'replacement_relocations', 'insert_after', 'omit'):
                prior = row[field]; row[field] = 'bad'; value = io.StringIO(newline='')
                writer = csv.DictWriter(value, fieldnames=fields, lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
                with self.assertRaises(ValueError): source.recovered_guards(value.getvalue().encode(), self.out / 'caller-before.o', self.out / 'caller-after.o')
                row[field] = prior; tested += 1
        self.assertEqual(tested, 81)
        self.receipt('fail-closed', words=239, bindings=64, extra_binding=1, private_pool=1,
            source_and_caller_anchors=True, retired_guard_field_corruptions=81)

    def test_05_three_independent_original_and_C_rebases_with_carries(self):
        original = assembly.ViewListSetupTests.original.__func__(type(self), 'original-rebase-task',
            (self.out / 'before-view_list_caller_original').read_text(), source.FUNCTION)
        text, functions, relocations = parse_object(self.padded)
        names = sorted({name for rows in source.RELOCATIONS.values() for _, name in rows})
        for index in range(3):
            entry = 0x15207FF0 + index * 0x100000
            symbols = {name:(entry + 0x10000 + n * 0x100 if name.startswith(('func_', 'os')) else
                0x80100000 + n * 0x10000 + (0x7FFC, 0x8004, 0x7FD0)[index]) for n, name in enumerate(names)}
            emitted, unresolved = emit_function(text, functions[source.FUNCTION], relocations, source.FUNCTION, symbols)
            self.assertFalse(unresolved)
            asm = self.out / ('direct-rebase-%d.s' % index); asm.write_text(emitted); obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], capture_output=True, check=True)
            images = []
            for label, path in (('original', original), ('direct', obj)):
                script = self.out / ('rebase-%s-%d.ld' % (label, index)); elf = script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)], capture_output=True, check=True)
                images.append(sections(elf)['.text'][1][:956])
            self.assertEqual(images[0], images[1])
        self.receipt('rebases', independent_original_links=3, independent_C_links=3, all239_words=True, HI_LO_carries=True)

    def test_06_complete_original_caller_and_real_argument_post_call_cut(self):
        original = assembly.ViewListSetupTests.original.__func__(type(self), 'original-task-caller',
            (self.out / 'before-task_original_caller').read_text(), 'func_1501878C')
        data, functions = source.build.link_owner(self.root, self.out, original, 'game_45B80')
        f = functions['func_1501878C']; full = data[f['value']:f['value'] + f['size']]
        self.assertEqual(len(full), 412 * 4); self.assertEqual(full, self.rom[0x45C3C:0x462AC])
        entry, join = 0x15018CDC, 0x15018CF8
        cut = list(struct.unpack_from('>7I', full, entry - 0x1501878C))
        class Join(Exception): pass
        class Code(tracking.TrackedCode):
            def __getitem__(self, pc):
                if pc == join: raise Join
                return super().__getitem__(pc)
        cases = 0
        for used, page, phase in itertools.product((-1, 20, 601, 1001), (0, 1), (0, 8)):
            memory, _ = model.fixture(used=used, page=page); args = (0, 1)
            expected, calls, _ = model.reference(memory, args); expected[0x800BE9B4] = 0
            machines = []
            for words in (self.truth, self.raw, self.emitted):
                connected = dict(zip(range(source.ENTRY, source.ENTRY + 956, 4), words)); connected[join] = 0
                m = model.SubmitOracle(cut, memory, args, connected, phase=phase, entry=entry)
                record = m.record_call
                def caller(target):
                    if target == source.ENTRY:
                        m.calls.append((target, m.arguments(2))); m.events.append(('CALL', target, m.arguments(2)))
                    else: record(target)
                m.record_call = caller; m.code = Code(m.code, m)
                with self.assertRaises(Join): m.run()
                self.assertEqual(m.calls, [(source.ENTRY, args), *calls])
                self.assertTrue(model.public(m.memory) == model.public(expected))
                self.assertEqual(m.r[2], memory[0x800BEAC0]); self.assertEqual(m.r[29], model.STACK + phase)
                machines.append(m)
            for m in machines[1:]: self.assertEqual(state(m), state(machines[0]))
            cases += 1
        self.receipt('callers', full_original_words=412, actual_cut_cases=cases, real_delay_slot_swap_one=True,
            post_call_flag_read_and_byte_clear=True, full_frame_loop_or_gameplay_not_claimed=True)

    def test_07_connected_real61_word_setup_and_all_memory_fault_prefixes(self):
        cases = faults = 0; visited = set()
        for used, page, phase in itertools.product((-1, 20, 601, 1001), (0, 1), (0, 8)):
            memory, args = model.fixture(used=used, page=page)
            expected, calls, _ = model.reference(memory, args); machines = []
            for words in (self.truth, self.raw, self.emitted):
                m = model.SubmitOracle(words, memory, args, self.helper, phase).run()
                self.assertTrue(model.public(m.memory) == model.public(expected)); self.assertEqual(m.calls, calls)
                visited.update(m.visits); machines.append(m)
            for m in machines[1:]: self.assertEqual(state(m), state(machines[0]))
            cases += 1
            if used not in (-1, 20, 601): continue
            for fault in range(machines[0].all_accesses):
                partial = []
                for words in (self.truth, self.raw, self.emitted):
                    m = model.SubmitOracle(words, memory, args, self.helper, phase); m.access_fault = fault
                    with self.assertRaises(tracking.AccessBoundary): m.run()
                    self.assertEqual(m.all_accesses, fault); partial.append(m)
                for m in partial[1:]: self.assertEqual(state(m), state(partial[0]))
                faults += 1
        self.assertEqual(visited & set(self.helper), set(self.helper))
        self.receipt('connected-faults', three_way_completed_cases=cases, real_setup_words=61,
            all61_setup_words_visited=True, fired_three_way_fault_prefixes=faults,
            root_and_real_setup_accesses=True, hardware_cache_queue_ucode_not_emulated=True)

    def test_08_guest_only_high_pages_and_wrapping_command_addresses(self):
        fixtures = []
        for page, used in itertools.product((128, 255), (20, 1001)):
            memory, args = model.fixture(page=0, used=used)
            for p in range(0x1000, 0x7000): memory.setdefault(0x800BE600 + p, 0xA5)
            memory[model.PAGE] = page
            first = model.BUFFERS + 0x4000
            model.put(memory, model.ROWS + page * 4, first); model.put(memory, model.ENDS + page * 4, first + 40)
            fixtures.append((memory, args))
        for used in (0, 7):
            memory, args = model.fixture()
            memory.update({a:0xA5 for a in range(0xFFFFF000, 0x100000000)})
            memory.update({a:0xA5 for a in range(0x200)})
            for address, value in ((model.ROWS, 0xFFFFFFF0), (model.ROWS + 4, 0x20),
                    (model.CURSOR, (0xFFFFFFF0 + used * 8) & 0xFFFFFFFF),
                    (model.ENDS, 0x18), (model.ENDS + 4, 0x48)):
                model.put(memory, address, value)
            fixtures.append((memory, args))
        cases = 0
        for memory, args in fixtures:
            expected, calls, _ = model.reference(memory, args)
            for phase in (0, 8):
                machines = []
                for words in (self.truth, self.raw, self.emitted):
                    m = model.SubmitOracle(words, memory, args, self.helper, phase).run()
                    self.assertTrue(model.public(m.memory) == model.public(expected)); self.assertEqual(m.calls, calls)
                    machines.append(m)
                for m in machines[1:]: self.assertEqual(state(m), state(machines[0]))
                cases += 1
        self.receipt('word-addresses', three_way_cases=cases, high_unsigned_page_bytes=[128, 255],
            wrapping_row_difference_and_command_end_stores=True, guest_only_not_portable_native_pointers=True)


if __name__ == '__main__': unittest.main()
