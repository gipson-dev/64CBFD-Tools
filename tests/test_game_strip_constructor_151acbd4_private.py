"""Private complete behavior, exact opening and explicitly open FP frontier."""
import json,unittest
from tools.experiments import game_strip_constructor_151acbd4_private_recovery as m
from tools.tests import game_strip_constructor_151acbd4_private_oracle as guest,game_strip_constructor_151acbd4_private_native as native,game_strip_constructor_151acbd4_private_proof as proof
class StripConstructorPrivateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check()
 def tearDown(self):m.check_inputs()
 def test_01_complete_owner_frame_and_neighbors(self):
  r=json.loads((m.OUT/'source-report.json').read_text());self.assertEqual((r['raw_words'],r['retail_words'],r['frame'],r['neighbors_unchanged']),(386,360,64,32));self.assertFalse(r['source_installed'])
 def test_02_full_guest_constructor_outputs(self):
  guest.main();r=json.loads((m.OUT/'guest-report.json').read_text());self.assertEqual(r['cases_per_stream'],1016);self.assertTrue(r['all_initialized_public_bytes_compared'])
 def test_03_native_profiles_and_wrapping_control(self):
  native.main();r=json.loads((m.OUT/'native-v7/native-report.json').read_text());self.assertEqual(r['cases'],1016);self.assertEqual(len(r['runs']),8);self.assertTrue(r['passes'])
 def test_04_exact_opening_and_recorded_FP_frontier(self):
  proof.main();r=json.loads((m.OUT/'prefix-report.json').read_text());self.assertEqual(r['opening']['equal_paths'],4);self.assertFalse(r['whole_function_proved']);self.assertTrue(r['FP_status_boundary_open'])
if __name__=='__main__':unittest.main()
