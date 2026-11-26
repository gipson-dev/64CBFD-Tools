import unittest
from tools.experiments import game_seed_sprite_tick_151934b4_match as packet,game_seed_sprite_tick_151934b4_make as make,game_seed_sprite_tick_151934b4_image as image
from tools.tests import game_seed_sprite_tick_151934b4_guest as guest,game_seed_sprite_tick_151934b4_native as native,game_seed_sprite_tick_151934b4_callers as callers,game_seed_sprite_tick_151934b4_boundaries as boundaries
class SeedSpriteTickTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(106,72,0,1));self.assertTrue(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['fault_prefix_quintuples'],81)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['all_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(212,10,20))
 def test_04_original_indexed_caller_and_return(self):self.assertTrue(callers.main()['void_return_register_ignored_and_phase_expiration_qualified'])
 def test_05_native_typed_arenas_and_FP(self):self.assertEqual(len(native.main()['effective_controls']),7)
if __name__=='__main__':unittest.main()
