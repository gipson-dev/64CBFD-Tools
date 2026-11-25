import unittest
from tools.experiments import game_buffered_matrix_update_151d6e60_match as packet,game_buffered_matrix_update_151d6e60_make as make,game_buffered_matrix_update_151d6e60_image as image
from tools.tests import game_buffered_matrix_update_151d6e60_guest as guest,game_buffered_matrix_update_151d6e60_native as native,game_buffered_matrix_update_151d6e60_callers as callers,game_buffered_matrix_update_151d6e60_boundaries as boundaries
class BufferedMatrixUpdateTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(104,32,0,6));self.assertTrue(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['fault_prefix_quintuples'],180)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['all_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(208,16,20))
 def test_04_original_indexed_caller_and_return(self):self.assertTrue(callers.main()['two_indexed_sites_and_skip_lifetime_paths'])
 def test_05_native_typed_arenas_and_FP(self):self.assertEqual(len(native.main()['effective_controls']),8)
if __name__=='__main__':unittest.main()
