import unittest
from tools.experiments import game_owner_lifecycle_151d2f90_match as packet,game_owner_lifecycle_151d2f90_make as make,game_owner_lifecycle_151d2f90_image as image
from tools.tests import game_owner_lifecycle_151d2f90_guest as guest,game_owner_lifecycle_151d2f90_native as native,game_owner_lifecycle_151d2f90_callers as callers,game_owner_lifecycle_151d2f90_boundaries as boundaries
class OwnerLifecycleTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(104,24,0,18));self.assertTrue(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['fault_prefix_quintuples'],87)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['unguarded_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(208,26,20))
 def test_04_complete_list_walker_and_ignored_return(self):self.assertTrue(callers.main()['independent_complete_parent_reference'])
 def test_05_native_typed_arenas_and_callbacks(self):self.assertEqual(len(native.main()['effective_controls']),10)
if __name__=='__main__':unittest.main()
