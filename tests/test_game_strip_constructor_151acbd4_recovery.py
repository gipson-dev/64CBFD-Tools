"""Complete strip C recovery, both padders/rebases, native and actual callers."""
import json,unittest
from tools.experiments import game_strip_constructor_151acbd4_recovery as m,game_strip_constructor_151acbd4_match as matching
from tools.tests import game_strip_constructor_151acbd4_oracle as guest,game_strip_constructor_151acbd4_native as native,game_strip_constructor_151acbd4_caller as callers,game_strip_constructor_151acbd4_proof as proof
class StripConstructorRecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check();matching.main()
 def tearDown(self):m.check_inputs()
 def test_01_guards_both_padders_and_independent_rebases(self):
  r=json.loads((m.OUT/'object-report.json').read_text());self.assertEqual((r['body_words'],r['retail_words'],r['frame'],r['guard_words'],r['insertions'],r['omissions'],r['gnu_links']),(359,360,64,307,1,0,12));self.assertEqual(r['stale_CSV_controls'],1228);self.assertEqual((r['owner_functions'],r['neighbors_preserved']),(33,32))
 def test_02_complete_ordered_provider_and_return_relation(self):proof.main()
 def test_03_guest_complete_public_outputs(self):
  guest.main();r=json.loads((m.OUT/'guest-report.json').read_text());self.assertEqual(r['cases_per_stream'],1016);self.assertTrue(r['all_initialized_public_bytes_compared'])
 def test_04_native_profiles_and_negative_controls(self):
  native.main();r=json.loads((m.OUT/'native-v63/native-report.json').read_text());self.assertEqual(r['cases'],1016);self.assertEqual(len(r['runs']),8);self.assertTrue(r['passes'])
 def test_05_all_complete_scene_callers(self):
  callers.main();controls=callers.controls();r=json.loads((m.OUT/'caller-report.json').read_text());self.assertEqual(r['complete_original_callers'],3);self.assertEqual(r['static_call_sites'],6);self.assertEqual(set(r['cases_per_stream'].values()),{384});self.assertTrue(r['complete_mapped_RAM_and_private_stack_compared']);self.assertEqual(len(controls),8)
if __name__=='__main__':unittest.main()
