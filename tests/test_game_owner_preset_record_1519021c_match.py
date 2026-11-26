import unittest
from tools.experiments import game_owner_preset_record_1519021c_match as packet,game_owner_preset_record_1519021c_make as make,game_owner_preset_record_1519021c_image as image
from tools.tests import game_owner_preset_record_1519021c_guest as guest,game_owner_preset_record_1519021c_native as native,game_owner_preset_record_1519021c_callers as callers,game_owner_preset_record_1519021c_boundaries as boundaries
class OwnerPresetRecordTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(109,144,0,60));self.assertTrue(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['fault_prefix_quintuples'],258)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['all_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(218,24,20))
 def test_04_complete_parent_and_consumed_return(self):self.assertTrue(callers.main()['independent_semantic_leaf_provider_counterpart'])
 def test_05_native_typed_arenas_and_FP(self):self.assertEqual(len(native.main()['effective_controls']),8)
if __name__=='__main__':unittest.main()
