import unittest
from tools.experiments import game_attachment_vector_effect_150fb324_match as packet,game_attachment_vector_effect_150fb324_make as make,game_attachment_vector_effect_150fb324_image as image
from tools.tests import game_attachment_vector_effect_150fb324_guest as guest,game_attachment_vector_effect_150fb324_native as native,game_attachment_vector_effect_150fb324_callers as callers,game_attachment_vector_effect_150fb324_boundaries as boundaries
class AttachmentVectorEffectTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['normalized_words'],q['frame'],q['guards'],q['raw_neighbors']),(100,101,160,22,17));self.assertTrue(q['both_complete_padders_equal']);self.assertTrue(q['structural_derivation']['independence_includes_GPR_FPR_FCSR_and_byte_memory_footprints']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_ordered_FP_private_relation_and_literal_faults(self):
  q=guest.main();self.assertEqual((q['cases_per_stream'],q['executed_retail_words'],q['literal_full_private_fault_quadruples'],q['raw_ordered_fault_prefixes'],q['extra_owner_read_stutter_boundaries']),(256,101,217,214,3));self.assertEqual(len(q['effective_comparison_controls']),6);self.assertTrue(q['all_original_normalized_faults_retained']);self.assertTrue(q['raw_reordering_not_erased_from_fault_checks'])
 def test_03_words_bindings_carries_and_jump_regions(self):
  q=boundaries.main();self.assertEqual((q['guard_corruptions_rejected'],q['unguarded_word_corruptions_visible'],q['unguarded_binding_corruptions_visible'],q['GNU_links']),(44,156,22,20));self.assertEqual(q['oversized'],['rejected','rejected'])
 def test_04_original_jump_table_caller_and_ignored_result(self):
  q=callers.main();self.assertEqual((q['parent_words_pinned'],q['parent_words_executed'],q['cases_per_stream'],q['connected_children_per_stream']),(3451,32,384,128));self.assertEqual(q['actor_types_reaching_original_target'],[134]);self.assertTrue(q['entry_void_three_argument_ABI_and_ignored_result']);self.assertTrue(q['current_production_parent_is_retained_12_byte_stub'])
 def test_05_native_typed_actors_full_bank_and_FP(self):
  q=native.main();self.assertEqual(len(q['effective_controls']),12);self.assertEqual(q['cases_per_profile'],2048);self.assertTrue(q['actual_C_void_three_argument_ABI']);self.assertTrue(q['no_signal_or_trap_counted_as_control'])
if __name__=='__main__':unittest.main()
