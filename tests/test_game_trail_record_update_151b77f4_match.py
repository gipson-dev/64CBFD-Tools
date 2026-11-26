import unittest
from tools.experiments import game_trail_record_update_151b77f4_match as packet,game_trail_record_update_151b77f4_make as make,game_trail_record_update_151b77f4_image as image
from tools.tests import game_trail_record_update_151b77f4_guest as guest,game_trail_record_update_151b77f4_native as native,game_trail_record_update_151b77f4_callers as callers,game_trail_record_update_151b77f4_boundaries as boundaries,game_trail_record_update_151b77f4_symbolic as symbolic
class TrailRecordUpdateTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(105,72,11,16));self.assertTrue(q['normalized_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['literal_fault_prefix_quadruples'],192)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['unguarded_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links'],q['guard_corruptions_rejected']),(188,10,20,22))
 def test_04_original_indexed_caller_and_return(self):self.assertTrue(callers.main()['actual_unsigned_selector14_table_JALR_and_zero_result_consumer'])
 def test_05_native_typed_arenas_and_FP(self):self.assertEqual(len(native.main()['effective_controls']),7)
 def test_06_closed_schedule_symbolic_identity(self):self.assertTrue(symbolic.main()['all32_GPRs_and_entire_functional_memory_identical'])
if __name__=='__main__':unittest.main()
