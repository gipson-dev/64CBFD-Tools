import unittest
from tools.experiments import game_optional_emitter_150d728c_match as packet,game_optional_emitter_150d728c_make as make,game_optional_emitter_150d728c_image as image
from tools.tests import game_optional_emitter_150d728c_guest as guest,game_optional_emitter_150d728c_native as native,game_optional_emitter_150d728c_callers as callers,game_optional_emitter_150d728c_boundaries as boundaries
class OptionalEmitterTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['retail_slot_words'],q['frame'],q['guards'],q['neighbors']),(98,101,264,0,1));self.assertTrue(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_packets_and_faults(self):
  q=guest.main();self.assertEqual((q['cases_per_stream'],q['retail_body_words'],q['executed_body_words'],q['fault_prefix_quintuples']),(288,98,97,156));self.assertTrue(q['full_private_states_equal']);self.assertTrue(q['actual88word_setup_helper_connected'])
 def test_03_words_bindings_and_jump_regions(self):
  q=boundaries.main();self.assertEqual((q['guards'],q['guard_corruptions_rejected'],q['unguarded_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(0,0,196,14,20))
 def test_04_complete_parent_on_selected_event_paths(self):
  q=callers.main();self.assertTrue(q['independent_complete_parent_reference_on_qualified_paths']);self.assertEqual((q['parent_words_pinned'],q['parent_words_executed'],q['cases_per_stream'],q['connected_children_per_stream']),(466,52,128,64));self.assertTrue(q['entry_void_five_word_ABI_and_ignored_result'])
 def test_05_native_defined_packet_bytes(self):
  q=native.main();self.assertEqual(len(q['effective_controls']),9);self.assertEqual(q['cases_per_profile'],4096);self.assertTrue(q['actual_C_void_optional_matrix_position_direction_u8_slot_s32_context']);self.assertTrue(q['unknown_small3_large5_bytes_never_read'])
if __name__=='__main__':unittest.main()
