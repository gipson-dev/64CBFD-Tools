import unittest
from tools.experiments import game_oriented_quad_constructor_15165f80_match as packet,game_oriented_quad_constructor_15165f80_make as make,game_oriented_quad_constructor_15165f80_image as image
from tools.tests import game_oriented_quad_constructor_15165f80_guest as guest,game_oriented_quad_constructor_15165f80_native as native,game_oriented_quad_constructor_15165f80_callers as callers,game_oriented_quad_constructor_15165f80_boundaries as boundaries
class OrientedQuadConstructorTests(unittest.TestCase):
 def test_01_owner_prototypes_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors']),(102,56,15,4));self.assertTrue(q['both_complete_padders_equal']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_ordered_FP_effects_raw_roles_and_faults(self):
  q=guest.main();self.assertEqual((q['cases_per_stream'],q['executed_retail_words'],q['literal_full_private_fault_quadruples']),(768,102,187));self.assertEqual(len(q['effective_comparison_controls']),7);self.assertTrue(q['raw_full_fault_register_identity_not_claimed'])
 def test_03_words_bindings_carries_and_jump_regions(self):
  q=boundaries.main();self.assertEqual((q['guard_corruptions_rejected'],q['unguarded_word_corruptions_visible'],q['unguarded_binding_corruptions_visible'],q['GNU_links']),(30,174,12,20));self.assertEqual(q['oversized'],['rejected','rejected'])
 def test_04_complete_original_parent_and_origin(self):
  q=callers.main();self.assertEqual((q['parent_words'],q['parent_words_executed'],q['cases_per_stream'],q['connected_children_per_stream']),(54,54,144,72));self.assertEqual(len(q['static_ignored_result_routes']),7);self.assertTrue(q['void_nine_argument_ABI_qualified'])
 def test_05_native_typed_storage_and_FP(self):
  q=native.main();self.assertEqual(len(q['effective_controls']),12);self.assertEqual(q['cases_per_profile'],4096);self.assertTrue(q['actual_nine_argument_C_void_entry']);self.assertTrue(q['no_signal_or_trap_counted_as_control'])
if __name__=='__main__':unittest.main()
