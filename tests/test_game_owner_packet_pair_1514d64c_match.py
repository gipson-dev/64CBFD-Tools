"""Packet source, closed compiler normalization, native/guest/caller and whole image."""
import unittest
from tools.experiments import game_owner_packet_pair_1514d64c_match as objects,game_owner_packet_pair_1514d64c_make as make,game_owner_packet_pair_1514d64c_image as image
from tools.tests import game_owner_packet_pair_1514d64c_native as native,game_owner_packet_pair_1514d64c_guest as guest,game_owner_packet_pair_1514d64c_callers as callers,game_owner_packet_pair_1514d64c_boundaries as boundaries
class PacketPairTests(unittest.TestCase):
 def test_01_whole_owner_padders_actual_Make_independent_image(self):
  q=objects.main();self.assertEqual((q['words'],q['guards'],q['raw_neighbors'],q['normalized_neighbors']),(200,44,77,77));self.assertTrue(q['all_200_words_accounted']);self.assertTrue(q['all_13_bindings_unchanged']);self.assertTrue(q['both_complete_padders_equal']);self.assertEqual(make.main()['commands'],3);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_native_source_live_mutations_FP_bits_and_controls(self):
  q=native.main();self.assertEqual(q['cases_per_profile'],229376);self.assertEqual(len(q['profiles']),3);self.assertEqual(len(q['effective_controls']),8);self.assertTrue(q['CSR_unchanged']);self.assertTrue(q['unwritten_bytes_checked_only_after_defined_provider_poison'])
 def test_03_guest_original_helpers_and_normalized_fault_prefixes(self):
  q=guest.main();self.assertEqual((q['guest_runs'],q['target_words_executed'],q['actual_factory_wrapper_words_executed'],q['actual_memcpy_words_executed'],q['normalized_literal_fault_triples']),(20480,200,41,11,633));self.assertTrue(q['independent_packets_and_public_effects_equal']);self.assertFalse(q['raw_literal_private_fault_parity_claimed'])
 def test_04_complete_dispatcher_and_callback_return_poisons(self):
  q=callers.main();self.assertEqual((q['original_parent_words_executed'],q['target_words_executed'],q['connected_runs'],q['target_callback_entries']),(109,200,5872,3840));self.assertTrue(q['all_three_selected_routes']);self.assertTrue(q['three_child_return_poisons_ignored']);self.assertEqual(len(q['effective_controls']),2)
 def test_05_every_word_binding_guard_and_independent_rebases(self):
  q=boundaries.main();self.assertEqual((q['all_word_mutations_visible_or_rejected'],q['all_binding_mutations_visible_or_rejected'],q['all_44_guard_unexpected_binding_rejections'],q['all_44_guard_removals_visible'],q['GNU_links']),(400,26,88,88,20));self.assertTrue(all(v['result']=='rejected'for v in q['overflow']))
if __name__=='__main__':unittest.main()
