"""Direct owner action dispatcher; scoped original caller and full classifier ABI."""
import unittest
from tools.experiments import game_owner_action_dispatch_1514d15c_match as packet,game_owner_action_dispatch_1514d15c_make as make,game_owner_action_dispatch_1514d15c_image as image
from tools.tests import game_owner_action_dispatch_1514d15c_guest as guest,game_owner_action_dispatch_1514d15c_native as native,game_owner_action_dispatch_1514d15c_callers as callers,game_owner_action_dispatch_1514d15c_boundaries as boundaries,game_owner_action_dispatch_1514d15c_helpers as helpers
class OwnerActionTests(unittest.TestCase):
 def test_01_direct_C_complete_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors']),(109,72,0,77));self.assertTrue(q['raw_byte_exact']);self.assertTrue(q['both_complete_padders_equal']);self.assertTrue(q['classifier_return_type_ABI_only_raw_body_unchanged']);self.assertEqual(make.main()['commands'],3);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_private_state_faults_and_original_classifier(self):
  q=guest.main();self.assertEqual((q['cases_per_stream'],q['streams'],q['executed_words'],q['fault_prefix_quintuples']),(1972,5,109,77));self.assertEqual(len(q['effective_controls']),6);self.assertTrue(q['all_literal_full_private_states_equal']);h=helpers.main();self.assertEqual(h['dynamic_original_classifier']['executed_words'],439);self.assertEqual(h['dynamic_original_classifier']['cases'],11106);self.assertEqual(h['connected_target']['cases_per_stream'],504);self.assertTrue(h['classifier_ABI']['proof']['all_normal_returns_zero_extend_u8'])
 def test_03_words_bindings_carries_and_jump_regions(self):
  q=boundaries.main();self.assertEqual((q['all_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links'],q['guest_rebase_runs']),(218,44,20,100));self.assertTrue(q['pre_callback_preserves_actual_table23_alias']);self.assertEqual(q['oversized'],['visible overflow','rejected'])
 def test_04_pinned_full_parent_and_actual_call_window(self):
  q=callers.main();self.assertEqual((q['original_parent_words_pinned'],q['original_parent_words_executed'],q['cases_per_stream'],q['streams']),(538,4,144,3));self.assertTrue(q['complete_parent_execution_not_claimed']);self.assertTrue(q['exact_original_call_window']);self.assertEqual(len(q['ignored_target_return_poisons']),2)
 def test_05_actual_native_C_and_effective_controls(self):
  q=native.main();self.assertEqual(len(q['effective_controls']),8);self.assertEqual(q['cases_per_profile'],49152);self.assertTrue(q['typed_812byte_owner_and_both_pointer_field_offsets_asserted']);self.assertTrue(q['pre_callback_aliases_callback_table23']);self.assertTrue(q['strict_aliasing_UBSan_traps_LTO_types']);self.assertTrue(q['no_signal_or_trap_counted_as_control'])
if __name__=='__main__':unittest.main()
