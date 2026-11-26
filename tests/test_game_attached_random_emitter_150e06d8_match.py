import unittest
from tools.experiments import game_attached_random_emitter_150e06d8_match as packet,game_attached_random_emitter_150e06d8_make as make,game_attached_random_emitter_150e06d8_image as image
from tools.tests import game_attached_random_emitter_150e06d8_guest as guest,game_attached_random_emitter_150e06d8_native as native,game_attached_random_emitter_150e06d8_callers as callers,game_attached_random_emitter_150e06d8_boundaries as boundaries
class AttachedRandomEmitterTests(unittest.TestCase):
 def test_01_mixed_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['normalized_words'],q['frame'],q['guards'],q['raw_and_both_profile_neighbors']),(100,101,112,24,12));self.assertTrue(q['both_complete_mixed_owner_padders_equal']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_ordered_calls_FP_private_relation_and_faults(self):
  q=guest.main();self.assertEqual((q['cases_per_stream'],q['executed_retail_words'],q['literal_full_private_fault_quadruples'],q['raw_common_fault_frame_access_and_used_operand_pairs'],q['extra_owner_read_stutter_boundaries']),(256,101,114,111,3));self.assertTrue(q['raw_fault_identity_not_claimed']);self.assertEqual(len(q['effective_comparison_controls']),5)
 def test_03_words_bindings_carries_and_jump_regions(self):
  q=boundaries.main();self.assertEqual((q['guards'],q['guard_corruptions_rejected'],q['unguarded_word_corruptions_visible'],q['unguarded_binding_corruptions_visible'],q['guard_binding_corruptions_rejected'],q['GNU_links']),(24,48,152,30,4,20));self.assertEqual(q['oversized'],['rejected','rejected'])
 def test_04_original_bounded_caller_and_complete_epilogue(self):
  q=callers.main();self.assertEqual((q['parent_words_pinned'],q['parent_words_executed'],q['cases_per_stream'],q['connected_children_per_stream']),(3451,24,96,32));self.assertTrue(q['entry_void_four_word_ABI_and_ignored_result']);self.assertTrue(q['only_variant0_1_table_domain_qualified'])
 def test_05_native_canonical_layout_and_defined_packets(self):
  q=native.main();self.assertEqual(len(q['effective_controls']),11);self.assertEqual(q['cases_per_profile'],4096);self.assertTrue(q['canonical_actor_prefix_copied_from_frozen_header']);self.assertTrue(q['no_signal_or_trap_counted_as_control'])
if __name__=='__main__':unittest.main()
