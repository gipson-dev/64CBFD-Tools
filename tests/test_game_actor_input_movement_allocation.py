"""Qualify complete movement allocation recovery without installing a partial match."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_allocation as allocation
from tools.tests import test_game_actor_input_movement_recovery as previous
from tools.tests import game_actor_input_movement_oracle as model
from tools.tests import game_actor_input_movement_native as native

source = allocation.source


class MovementAllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / allocation.BUILD
        cls.body = allocation.selected_body()
        cls.obj, cls.words, cls.row = allocation.measure(cls.root, cls.out, allocation.SELECTED_NAME, cls.body)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>959I', cls.rom, source.ROM))
        cls.connected = {0x150F34A0 + i * 4: w for i, w in enumerate(struct.unpack_from('>21I', cls.rom, 0x120950))}
        cls.harness = previous.MovementRecoveryTests('test_02_all_three_paths_and_numeric_boundaries')
        for name in ('root', 'out', 'rom', 'obj', 'words', 'truth', 'connected'):
            setattr(cls.harness, name, getattr(cls, name))
        cls.harness.coverage = set()
        cls.harness.providers = set()

    def receipt(self, filename, **data):
        (self.out / (filename + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def test_01_complete_extent_prefix_and_preserved_owner(self):
        self.assertEqual(tuple(self.row[k] for k in ('words', 'frame', 'differences')), (959, 128, 721))
        self.assertEqual(self.row['raw_sha'], allocation.SELECTED_SHA)
        self.assertEqual((self.row['first_unequal_word'], self.row['initial_controller_register']), (66, 10))
        self.assertEqual(self.words[:66], self.truth[:66])
        self.assertEqual((self.words[66], self.truth[66]), (0x51A0002A, 0x51A0002B))
        self.assertEqual((self.row['raw_neighbors'], self.row['padded_neighbors']), (11, 11))
        self.assertEqual((self.row['new_guards'], self.row['matching_credit']), (0, 0))
        self.assertEqual(self.row['padded_differences'], 721)
        self.assertIn('(u32)angle + (u32)D_800CC280', self.body)
        self.receipt('shape', **{k: v for k, v in self.row.items() if k != 'bindings'})

    def test_02_two_completed_owned_captures_revalidated_with_live_inputs(self):
        rows = []
        for name, body, kind in ((allocation.SELECTED_NAME, self.body, 'selected'),
                                 ('global-controller', allocation.frame.global_controller_body(), 'global-controller')):
            record, words, facts = allocation.revalidate_capture(self.root, self.out, name, body, kind)
            self.assertTrue(record['code_unchanged'])
            rows.append(dict(name=name, facts=facts, source_sha=record['source_sha']))
            if kind == 'selected':
                self.assertEqual(words, self.words)
                markers = dict(allocation.frame.MARKERS)
                markers['distanceCall'] = 'nearestDistance = func_1505A6F8(D_800D154C, record);'
                markers['turn'] = 'func_150599C8(actor, 8, (u16)heading);'
                result = allocation.frame.summary(record, allocation.frame.isolated(body), markers)
                result.update(code_unchanged=True, whole_owner_target_identical=True)
                layout = allocation.frame.check_layout(result, words, allocation.frame.FITTED_NAME)
                self.assertEqual((layout['frontend_local_bytes'], layout['optimizer_local_bytes']), (84, 76))
        self.receipt('captures', completed_captures_revalidated=2, rows=rows, selected_layout=layout,
                     whole_owner_normal_traced_functions_relocations_pools_and_sources_identical=True)

    def test_03_effective_reservation_operand_and_machine_controls(self):
        work = self.out / 'traces' / allocation.SELECTED_NAME
        record = json.loads((work / 'allocation-summary.json').read_text())
        allocation.check_allocation(record, self.words, 'selected')
        count = 0
        for key in ('code_unchanged', 'whole_owner_target_identical'):
            bad = copy.deepcopy(record)
            bad[key] = False
            with self.assertRaises(ValueError):
                allocation.check_allocation(bad, self.words, 'selected')
            count += 1
        bad = copy.deepcopy(record)
        bad['compiler_sha256']['uopt'] = '0' * 64
        with self.assertRaises(ValueError):
            allocation.check_allocation(bad, self.words, 'selected')
        count += 1
        rows = record['records']['optimizer']
        register = next(i for i, r in enumerate(rows) if r['name'] == 'regs' and r['words'][1] == 1)
        for operand in (1, 2, 3):
            bad = copy.deepcopy(record)
            bad['records']['optimizer'][register]['words'][operand] += 1
            with self.assertRaises(ValueError):
                allocation.check_allocation(bad, self.words, 'selected')
            count += 1
        indirect = next(i for i, r in enumerate(rows) if r['name'] == 'ilod')
        for key, value in (('dtype', 'J'), ('storage', 'R'), ('offset', 4), ('block', 754), ('length', 8)):
            bad = copy.deepcopy(record)
            bad['records']['optimizer'][indirect + 1][key] = value
            with self.assertRaises(ValueError):
                allocation.check_allocation(bad, self.words, 'selected')
            count += 1
        constant = next(i for i, r in enumerate(rows) if r['name'] == 'rldc' and r['dtype'] == 'J')
        bad = copy.deepcopy(record)
        bad['records']['optimizer'][constant]['constants'][0] += 1
        with self.assertRaises(ValueError):
            allocation.check_allocation(bad, self.words, 'selected')
        count += 1
        for index in (0, 17, 23, 47):
            bad = list(self.words)
            bad[index] ^= 1 << 16
            with self.assertRaises(ValueError):
                allocation.check_allocation(record, bad, 'selected')
            count += 1
        self.receipt('allocation-controls', effective_controls=count, actual_wire_and_machine_operands=True)

    def test_04_complete_public_width_filter_mutation_and_FP_corpus(self):
        for name in ('test_02_all_three_paths_and_numeric_boundaries', 'test_03_every_signed_stick_byte_and_cooldown',
                     'test_04_record_filters_nearest_ties_and_mutating_providers', 'test_10_modeled_float_edges_not_hardware_FCSR'):
            getattr(self.harness, name)()
        self.assertEqual(len(self.harness.coverage & set(range(source.ENTRY, source.ENTRY + source.SIZE, 4))), 947)
        self.receipt('complete-public', complete_cases=2496, additional_FP_cases=20, reachable_retail_words=947,
                     original_unreachable_duplicate_words_retained=12, full_hardware_FCSR_not_claimed=True)

    def test_05_all_five_gate_prefixes_and_effective_old_controller_rejection(self):
        cuts = (21, 29, 20, 22, 23)
        equal = 0
        failures = []
        for phase, pattern, gate in itertools.product((0, 8), (0, 1), range(5)):
            memory, case = model.fixture(self.rom, held=101, phase=phase, pattern=pattern, gate=gate)
            for cut in range(cuts[gate] + 1):
                pair = [model.Oracle(words, memory, case, self.connected) for words in (self.truth, self.words)]
                for machine in pair:
                    machine.access_fault = cut
                    with self.assertRaises(model.point.faults.AccessBoundary):
                        machine.run()
                same = model.point.state(pair[0]) == model.point.state(pair[1])
                self.assertEqual(same, cut < cuts[gate])
                self.assertEqual(pair[0].lo, pair[1].lo)
                self.assertEqual(pair[0].condition, pair[1].condition)
                if same:
                    equal += 1
                else:
                    self.assertEqual(pair[0].memory, pair[1].memory)
                    self.assertEqual(pair[0].r, pair[1].r)
                    self.assertEqual(pair[0].f, pair[1].f)
                    self.assertEqual([m.current_pc for m in pair], [0x150F36B4, 0x150F36B0])
                    failures.append(dict(phase=phase, pattern=pattern, gate=gate, cut=cut))
        self.assertEqual((equal, len(failures)), (460, 20))
        memory, case = model.fixture(self.rom, held=101, pattern=1)
        wrong = list(self.words)
        wrong[17] = (wrong[17] & ~0x1F0000) | 3 << 16
        pair = [model.Oracle(words, memory, case, self.connected) for words in (self.truth, wrong)]
        for machine in pair:
            machine.access_fault = 10
            with self.assertRaises(model.point.faults.AccessBoundary):
                machine.run()
        self.assertNotEqual(model.point.state(pair[0]), model.point.state(pair[1]))
        self.receipt('prefixes', initial_states=20, equal_complete_prefix_states=equal, remaining_rejections=failures,
                     former_controller_gap_closed=True, effective_controller_word_control=1,
                     same_memory_GPR_FPR_LO_condition_at_first_gap=True, no_full_private_or_fault_matching=True)

    def test_06_text_rebases_native32_and_unsigned_heading_extremes(self):
        self.harness.test_05_two_independent_text_rebases()
        specs = [*list(previous.core_specs())[::7], *list(previous.mutation_specs())[::5], *previous.targeted_specs()]
        original_fixture = model.fixture

        def fixture(rom, **spec):
            memory, case = original_fixture(rom, **spec)
            if 'headingOffset' in spec:
                model.put(memory, 0x800CC280, spec['headingOffset'])
            return memory, case

        for angle, offset in itertools.product((0, 1, 65535), (0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)):
            specs.append(dict(mode=0, angle=angle, magnitude=2., headingOffset=offset))
        with patch.object(model, 'fixture', fixture), patch.object(source, 'SELECTED', self.body):
            row = native.qualify(self.root, self.out, self.rom, specs)
            for spec in specs[-9:]:
                self.harness.compare(spec)
        self.assertEqual((row['cases_per_profile'], row['effective_controls']), (139, 8))
        self.receipt('native-rebases', native_cases_per_profile=139, profiles=['O2', 'O0'], UBSan=True,
                     additional_guest_unsigned_heading_cases=9, independent_text_rebases=2, cases_per_rebase=6)

    def test_07_guest_controller_aliases_after_global_source_recovery(self):
        count = 0
        for alias, gate, mode in itertools.product((0x800CC284, 0x800CC288, model.SLOT), (0, 1), (0, 1)):
            memory, case = model.fixture(self.rom, gate=gate, mode=mode, pattern=1, pressed=0x8000)
            model.put(memory, model.SLOT, alias)
            memory.update({0x800C0080 + i: 0xA5 for i in range(32)})
            expected = model.reference(memory, case)
            for words in (self.truth, self.words):
                actual = model.Oracle(words, memory, case, self.connected).run()
                self.assertEqual(model.public(actual.memory), model.public(expected[0]))
                self.assertEqual(actual.calls, expected[1])
                self.assertEqual(actual.observations, expected[2])
            count += 1
        self.receipt('aliases', complete_guest_alias_cases=count, native_pointer_alias_acceptance_not_claimed=True)

    def test_08_production_layout_and_immutable_checkpoints_unchanged(self):
        allocation.freeze(self.root, self.out)
        for key, path in allocation.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes())
        self.harness.test_07_production_baseline_and_callback_preserved()
        source.checkpoint.freeze_after(self.root)
        self.receipt('protected', entries=len(allocation.PATHS), distinct_paths=len(set(allocation.PATHS.values())),
                     ELF_sha=hashlib.sha256((self.root / 'conker/build/conker.us.elf').read_bytes()).hexdigest(),
                     all_ten_first_image_members_preserved=True, installed=False, matching_credit=0, new_guards=0)


if __name__ == '__main__':
    unittest.main()
