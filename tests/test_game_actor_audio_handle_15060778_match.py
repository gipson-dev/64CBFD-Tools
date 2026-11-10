"""Actor audio source/ABI, guarded emission and strict linked-image gates."""
import json
import unittest
from tools.experiments import game_actor_audio_handle_15060778_match as source
from tools.tests import game_actor_audio_handle_15060778_oracle as game
from tools.tests import game_sound_slot_10010be8_oracle as alloc
from tools.tests import game_object_audio_10010ffc_oracle as caller
from tools.tests import game_actor_audio_handle_15060778_native as native
from tools.tests import game_actor_audio_handle_15060778_controls as controls
from tools.tests import game_actor_audio_handle_15060778_boundaries as boundaries
from tools.tests import game_actor_audio_handle_15060778_callers as parents

ROOT = source.ROOT


class ActorAudioMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = source.prepare(ROOT)

    def test_01_complete_owners_actual_Make_and_strict_image(self):
        self.assertTrue(self.report['Init_object_byte_identical'])
        self.assertEqual(self.report['raw_game_neighbors'], 88)
        self.assertEqual(self.report['raw_init_equal_neighbors'], 52)
        self.assertEqual(self.report['image_changed_bytes'], 590)
        self.assertEqual(self.report['strict_unexplained_bytes'], 0)
        self.assertEqual(self.report['Make_commands'], 9)
        self.assertEqual(self.report['guards'], {'func_15060778': 8, 'func_10010BE8': 73, 'func_10010FFC': 104})

    def test_02_actor_audio_guest_widths_callbacks_and_homes(self):
        r = game.main()
        self.assertEqual(r['cases_per_body'], 1447)
        self.assertEqual(r['coverage'], {'raw': 174, 'retail': 174})

    def test_03_allocator_guest_selection_wrap_and_mutations(self):
        r = alloc.main()
        self.assertEqual(r['cases_per_body'], 2160)
        self.assertEqual(set(r['coverage'].values()), {162})
        self.assertTrue(all(v == [33, 83] for v in r['missing'].values()))

    def test_04_affected_caller_guest_scale_and_narrowing(self):
        r = caller.main()
        self.assertEqual(r['cases_per_body'], 776)
        self.assertEqual(r['native_defined_cases'], 772)
        self.assertEqual(set(r['coverage'].values()), {109})

    def test_05_SDK32_native_O0_O2_O3_UBSan_exact_public_bytes(self):
        r = native.main()
        self.assertEqual(set(r['profiles']), {'-O0', '-O2', '-O3'})
        self.assertTrue(all(v['UBSan'] and v['exact_output_bytes'] == 12668068 for v in r['profiles'].values()))

    def test_06_twenty_nine_effective_compiled_controls(self):
        r = controls.main()
        self.assertEqual(sum(map(len, r.values())), 29)
        self.assertTrue(all(v['normal_completion'] and v['skipped_execution_errors'] == 0 for group in r.values() for v in group.values()))

    def test_07_input_corruptions_stale_guards_and_symbol_rebases(self):
        r = boundaries.main()
        self.assertEqual(r['guards']['word_and_binding_corruptions'], 488)
        self.assertEqual(r['guards']['stale_guard_rejections'], 370)
        self.assertEqual(r['rebases']['executions'], 132)

    def test_08_five_original_sites_and_void_result_liveness(self):
        r = parents.main()
        self.assertEqual(r['full_parent_runs'], 888)
        self.assertEqual(r['window_runs'], 36)
        self.assertEqual(r['connected_target_calls'], 864)
        self.assertEqual(len(r['V0_liveness']), 5)
        self.assertTrue(all(not row['read_before_kill'] for row in r['V0_liveness']))

    def test_09_eight_strict_image_corruptions(self):
        before = (source.out / 'frozen/conker/build/conker.us.elf').read_bytes()
        actual = (source.out / 'qualified-image.elf').read_bytes()
        truth = (ROOT / 'conker/conker.us.bin').read_bytes()[0x8DC28:0x8DEE0]
        target = next(r for r in source.symbol_rows(before) if r[1] == 'func_15060778')
        locations = [source.elf_slot_offset(before, 0x15060778, 696), source.elf_slot_offset(before, 0x10010BE8, 656), source.elf_slot_offset(before, 0x1505A3A8, 548), source.elf_slot_offset(before, self.report['protected_data']['address'], 1), target[0] + 4, target[0] + 8, target[3], 24]
        for at in locations:
            wrong = bytearray(actual)
            wrong[at] ^= 1
            with self.assertRaises(ValueError):
                source.strict_image(before, bytes(wrong), truth)

    def test_10_live_inputs_and_protected_data_stay_closed(self):
        source.live_inputs(self.report['source_installed'])
        self.assertTrue(self.report['all_addresses_fixed'])
        self.assertEqual(self.report['functions'], 6050)
        self.assertTrue(self.report['protected_data']['exact'])
        self.assertEqual(self.report['protected_data']['different_bytes'], 0)


if __name__ == '__main__':
    unittest.main()
