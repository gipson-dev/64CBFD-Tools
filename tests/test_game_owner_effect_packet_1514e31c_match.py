"""Packet source, independent initialization schedule, native/guest/caller and full ELF."""
import unittest
from tools.experiments import game_owner_effect_packet_1514e31c_match as objects,game_owner_effect_packet_1514e31c_make as make,game_owner_effect_packet_1514e31c_image as image
from tools.tests import game_owner_effect_packet_1514e31c_native as native,game_owner_effect_packet_1514e31c_guest as guest,game_owner_effect_packet_1514e31c_callers as callers,game_owner_effect_packet_1514e31c_boundaries as boundaries
class PacketTests(unittest.TestCase):
 def test_01_whole_owner_padders_actual_Make_independent_image(self):
  q=objects.main();self.assertEqual((q['words'],q['guards'],q['raw_neighbors'],q['normalized_neighbors']),(123,32,77,77));self.assertTrue(q['all_words_accounted']);self.assertTrue(q['all_bindings_unchanged']);self.assertTrue(q['no_register_frame_FP_or_value_rewrite']);self.assertTrue(q['both_complete_padders_equal']);self.assertEqual(make.main()['commands'],3);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_native_separate_storage_live_mutations_FP_bits_and_controls(self):
  q=native.main();self.assertEqual(q['cases_per_profile'],28672);self.assertEqual(len(q['profiles']),3);self.assertEqual(len(q['effective_controls']),10);self.assertTrue(q['CSR_unchanged']);self.assertTrue(q['separate_vector_and_live_packet_storage']);self.assertFalse(q['native_incoming_home_mutation_claimed'])
 def test_03_guest_actual_helpers_home_reloads_and_normalized_fault_prefixes(self):
  q=guest.main();self.assertEqual((q['guest_runs'],q['executed_words'],q['actual_packet_wrapper_words'],q['actual_memcpy_words'],q['normalized_fault_triples']),(10240,123,41,11,392));self.assertTrue(q['independent_packets_public_effects_and_owners_equal']);self.assertTrue(q['all_raw_and_normalized_complete_post_states_equal']);self.assertFalse(q['raw_literal_fault_prefix_parity_claimed']);self.assertEqual(len(q['effective_controls']),3)
 def test_04_complete_dispatcher_and_ignored_callback_return(self):
  q=callers.main();self.assertEqual((q['original_parent_words_executed'],q['target_words_executed'],q['connected_runs'],q['target_callback_entries'],q['actual_callback_slot']),(109,123,11632,7680,3));self.assertTrue(q['all_three_selected_routes']);self.assertTrue(q['three_child_return_poisons_ignored']);self.assertEqual(len(q['effective_controls']),2)
 def test_05_all_words_bindings_guards_and_independent_rebases(self):
  q=boundaries.main();self.assertEqual((q['all_word_mutations_visible_or_rejected'],q['all_binding_mutations_visible_or_rejected'],q['all_32_guard_unexpected_binding_rejections'],q['all_32_guard_removals_visible'],q['GNU_links']),(246,14,64,64,20));self.assertTrue(all(v['result']=='rejected'for v in q['overflow']))
if __name__=='__main__':unittest.main()
