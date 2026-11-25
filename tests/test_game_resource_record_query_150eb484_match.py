import unittest
from tools.experiments import game_resource_record_query_150eb484_match as p,game_resource_record_query_150eb484_make as make,game_resource_record_query_150eb484_image as image
from tools.tests import game_resource_record_query_150eb484_guest as guest,game_resource_record_query_150eb484_native as native,game_resource_record_query_150eb484_callers as callers,game_resource_record_query_150eb484_boundaries as boundaries,game_resource_record_query_150eb484_symbolic as proof
class ResourceRecordQueryTests(unittest.TestCase):
 def test_01_both_owners_Make_and_strict_image(self):
  q=p.objects();self.assertEqual((q['words'],q['guards'],q['retired_wrapper_guards']),(100,23,4));self.assertEqual(len(make.main()['owners']),2);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertEqual(guest.main()['fault_prefix_quads'],225)
 def test_03_all_guards_and_GNU_rebases(self):
  q=boundaries.main();self.assertEqual((q['guarded_word_corruptions_rejected'],q['unguarded_word_corruptions_visible'],q['GNU_links']),(46,154,20))
 def test_04_forwarding_and_original_parent(self):self.assertEqual(callers.main()['parent_cases_per_stream'],160)
 def test_05_changed_region_and_private_frame_proof(self):self.assertEqual(proof.main()['exact_changed_region_cases'],8)
 def test_06_native_ABI_and_effective_controls(self):self.assertEqual(len(native.main()['effective_controls']),8)
if __name__=='__main__':unittest.main()
