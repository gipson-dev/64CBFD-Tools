import unittest
from tools.experiments import game_random_sprite_scatter_15179b14_match as packet,game_random_sprite_scatter_15179b14_make as make,game_random_sprite_scatter_15179b14_image as image
from tools.tests import game_random_sprite_scatter_15179b14_guest as guest,game_random_sprite_scatter_15179b14_native as native,game_random_sprite_scatter_15179b14_callers as callers,game_random_sprite_scatter_15179b14_boundaries as boundaries
class RandomSpriteScatterTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(103,272,0,8));self.assertTrue(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):
  q=guest.main();self.assertEqual((q['cases_per_stream'],q['streams'],q['preserved_words'],q['executed_words'],q['fault_prefix_quintuples']),(608,5,103,95,81));self.assertTrue(q['constant_divisor_guard_proof']['no_direct_loop_write_to_s3'])
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['unguarded_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(206,18,20))
 def test_04_complete_parent_on_idle_and_default_paths(self):
  q=callers.main();self.assertTrue(q['independent_complete_parent_reference_on_qualified_paths']);self.assertEqual((q['parent_words_pinned'],q['parent_words_executed'],q['cases_per_stream'],q['connected_children_per_stream']),(304,52,432,288));self.assertTrue(q['entry_void_s32_count_ABI_parent_ignores_result'])
 def test_05_native_typed_arenas_and_FP(self):
  q=native.main();self.assertEqual(len(q['effective_controls']),10);self.assertEqual(q['initialized_bytes_observed'],109);self.assertTrue(q['initially_unknown59_source_bytes_not_read_before_definition'])
if __name__=='__main__':unittest.main()
