import unittest
from tools.experiments import game_local_vector_transform_15117da4_match as packet,game_local_vector_transform_15117da4_make as make,game_local_vector_transform_15117da4_image as image
from tools.tests import game_local_vector_transform_15117da4_guest as guest,game_local_vector_transform_15117da4_symbolic as symbolic,game_local_vector_transform_15117da4_boundaries as boundaries,game_local_vector_transform_15117da4_callers as callers,game_local_vector_transform_15117da4_native as native
class LocalVectorTransformTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(102,15,83));self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertGreater(guest.main()['access_fault_quads'],0)
 def test_03_guards_and_GNU(self):
  q=boundaries.main();self.assertEqual((q['guarded_corruptions_rejected'],q['unguarded_corruptions_visible'],q['binding_pins'],q['GNU_links']),(30,174,14,20))
 def test_04_ordered_FP_proof_and_bounded_callers(self):
  self.assertEqual(symbolic.main()['structural_cases'],147);self.assertEqual(callers.main()['bounded_parent_words_visited'],127)
 def test_05_native_ABI_and_controls(self):self.assertEqual(len(native.main()['effective_controls']),7)
if __name__=='__main__':unittest.main()
