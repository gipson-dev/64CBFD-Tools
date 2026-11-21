"""Audio command dispatcher: complete semantics, closed schedule and full image."""
import unittest
from tools.experiments import game_audio_command_dispatch_1509e730_recovery as s,game_audio_command_dispatch_1509e730_match as match
from tools.tests import game_audio_command_dispatch_1509e730_validate as validate,game_audio_command_dispatch_1509e730_proof as proof,game_audio_command_dispatch_1509e730_guest as guest
from tools.tests import game_audio_command_dispatch_1509e730_native as native,game_audio_command_dispatch_1509e730_callers as callers,game_audio_command_dispatch_1509e730_caller_controls as controls
from tools.tests import game_audio_command_dispatch_1509e730_links as links,game_audio_command_dispatch_1509e730_census as census
class AudioCommandDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.source=s.screen()
    def test_01_source_owner_shape_and_exact_command_table(self):
        self.assertEqual((self.source['words'],self.source['frame'],self.source['neighbors'],self.source['table_entries']),(92,32,3,7))
    def test_02_closed_permutation_branches_and_relocations(self):
        r=validate.run();self.assertEqual((r['normalized_differences'],r['insertions'],r['omissions'],r['relocation_sites']),(0,0,0,17))
        self.assertEqual(len(r['checked_negative_controls']),3)
    def test_03_complete_control_path_instruction_proof(self):
        r=proof.run();self.assertTrue(r['passes']);self.assertEqual((r['unique_control_paths'],r['covered_words']),(11,92));self.assertEqual(len(r['effective_controls']),4)
    def test_04_guest_ordered_effects_complete_frames_and_defects(self):
        r=guest.run();self.assertEqual((r['cases_per_stream'],r['streams']),(7446,3));self.assertTrue(r['all_private_call_and_return_bytes_equal']);self.assertEqual(len(r['checked_negative_controls']),5)
    def test_05_native_complete_owner_defined_aliases_and_source_defects(self):
        r=native.run();self.assertEqual([v['cases']for v in r['valid']],[13440]*3);self.assertEqual(len(r['rejected']),6)
    def test_06_original_registry_and_both_connected_callers(self):
        c=census.run();self.assertEqual(c['direct_original_code_references'],[]);self.assertEqual([v['address']for v in c['loaded_pointer_references']],['0x800884f8'])
        r=callers.run();self.assertEqual([v['cases_per_stream']for v in r['windows'].values()],[432,432]);self.assertEqual(r['helper_calls_per_stream'],672)
    def test_07_effective_original_caller_delay_controls(self):
        r=controls.run();self.assertTrue(r['passes']);self.assertEqual(len(r['controls']),4)
    def test_08_independent_original_and_compiled_GNU_carry_links(self):
        r=links.run();self.assertTrue(r['passes']);self.assertEqual(len(r['links']),2);self.assertTrue(r['links'][1]['data_HI16_LO16_carry_exercised'])
    def test_09_both_padders_natural_Make_and_strict_entire_image(self):
        r=match.qualify();self.assertEqual((r['guard_rows'],r['insertions'],r['omissions']),(80,0,0));self.assertTrue(r['namespace_augmented_layout_object_equal'])
        self.assertEqual((r['changed_bytes'],r['exclusions'],r['function_slots']),(321,0,6051));self.assertTrue(r['strict_predicted_ELF_equal']);self.assertTrue(r['protected_data_audit']['exact'])
        self.assertEqual(r['actual_Make']['commands'],3);self.assertEqual(r['original_jump_labels_preserved'],7)
