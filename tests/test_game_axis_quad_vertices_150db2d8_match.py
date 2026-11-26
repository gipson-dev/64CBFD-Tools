import unittest
from tools.experiments import game_axis_quad_vertices_150db2d8_match as packet,game_axis_quad_vertices_150db2d8_make as make,game_axis_quad_vertices_150db2d8_image as image
from tools.tests import game_axis_quad_vertices_150db2d8_guest as guest,game_axis_quad_vertices_150db2d8_native as native,game_axis_quad_vertices_150db2d8_callers as callers,game_axis_quad_vertices_150db2d8_boundaries as boundaries
class AxisQuadVertexTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(144,72,0,5));self.assertTrue(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['fault_prefix_quintuples'],558)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['all_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(288,6,20))
 def test_04_original_indexed_caller_and_return(self):self.assertTrue(callers.main()['independent_semantic_leaf_provider_counterpart'])
 def test_05_native_typed_arenas_and_FP(self):self.assertEqual(len(native.main()['effective_controls']),7)
if __name__=='__main__':unittest.main()
