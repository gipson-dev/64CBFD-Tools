import unittest
from tools.experiments import game_owner_effect_factory_151c6ea0_match as packet,game_owner_effect_factory_151c6ea0_make as make,game_owner_effect_factory_151c6ea0_image as image
from tools.tests import game_owner_effect_factory_151c6ea0_guest as guest,game_owner_effect_factory_151c6ea0_native as native,game_owner_effect_factory_151c6ea0_callers as callers,game_owner_effect_factory_151c6ea0_boundaries as boundaries
class OwnerEffectFactoryTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(102,176,0,7));self.assertTrue(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['fault_prefix_quintuples'],268)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['all_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(204,8,20))
 def test_04_original_caller_and_unused_return(self):self.assertEqual(callers.main()['child_incidental_V0_poison_checks'],96)
 def test_05_native_defined_fields_and_lifetime(self):self.assertEqual(len(native.main()['effective_controls']),13)
if __name__=='__main__':unittest.main()
