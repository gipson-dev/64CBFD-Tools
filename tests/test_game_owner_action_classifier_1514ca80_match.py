"""Classifier qualification including the complete accepted dispatcher caller."""
import unittest
from tools.experiments import game_owner_action_classifier_1514ca80_match as packet,game_owner_action_classifier_1514ca80_make as make,game_owner_action_classifier_1514ca80_image as image
from tools.tests import game_owner_action_classifier_1514ca80_guest as guest,game_owner_action_classifier_1514ca80_native as native,game_owner_action_classifier_1514ca80_callers as callers,game_owner_action_classifier_1514ca80_boundaries as boundaries
class ClassifierTests(unittest.TestCase):
 def test_01_complete_owner_tables_padders_Make_and_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors_unchanged'],q['normalized_neighbors_unchanged']),(439,0,9,76,77));self.assertTrue(q['all_raw_pool_bytes_and_ownership_accounted']);self.assertTrue(q['both_complete_padders_equal']);self.assertEqual(make.main()['commands'],3);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_states_aliases_fault_prefixes(self):
  q=guest.main();self.assertEqual((q['cases_per_stream'],q['streams'],q['executed_words'],q['fault_prefix_quintuples']),(14130,5,439,40));self.assertTrue(q['independent_ordered_reference_memory_and_return_equal']);self.assertEqual(len(q['effective_controls']),3)
 def test_03_all_guards_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['all_word_mutations_visible_or_rejected'],q['all_binding_mutations_visible_or_rejected'],q['ninth_guard_word_and_binding_rejections'],q['GNU_links'],q['guest_rebase_runs']),(878,20,4,20,120));self.assertTrue(q['five_independent_construction_routes']);self.assertTrue(q['four_tables_and_level_independently_rebased']);self.assertEqual(q['oversized'],['rejected','rejected'])
 def test_04_complete_109_word_dispatcher_caller(self):
  q=callers.main();self.assertEqual((q['original_parent_words_pinned'],q['original_parent_words_executed'],q['cases_per_stream'],q['connected_runs']),(109,109,761,3044));self.assertTrue(q['complete_parent_execution']);self.assertTrue(q['independent_classifier_and_dispatch_references_equal']);self.assertEqual(len(q['effective_controls']),2)
 def test_05_actual_native_C_and_live_alias_controls(self):
  q=native.main();self.assertEqual(q['cases_per_profile'],207314);self.assertEqual(len(q['profiles']),3);self.assertEqual(len(q['effective_controls']),8);self.assertTrue(q['actual_C_u8_four_argument_ABI']);self.assertTrue(q['strict_aliasing_UBSan_traps_LTO_types']);self.assertTrue(q['no_signal_or_trap_counted_as_control'])
if __name__=='__main__':unittest.main()
