"""Complete bone-hit semantics, original callers, guards and independent links."""
import json,unittest
from tools.experiments import game_bone_hit_151aabc4_recovery as m,game_bone_hit_151aabc4_match as matching
from tools.tests import game_bone_hit_151aabc4_oracle as guest,game_bone_hit_151aabc4_native as native,game_bone_hit_151aabc4_callers as callers,game_bone_hit_151aabc4_proof as proof
class BoneHitRecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check();matching.main()
 def tearDown(self):m.check_inputs()
 def test_01_complete_owner_guards_and_rebases(self):
  r=json.loads((m.OUT/'object-report.json').read_text());self.assertEqual((r['body_words'],r['frame'],r['guard_words'],r['raw_and_binding_corruptions'],r['stale_CSV_controls']),(126,200,30,144,120))
 def test_02_whole_function_ordered_proof(self):
  proof.main();r=json.loads((m.OUT/'proof-report.json').read_text());self.assertTrue(r['whole_function']);self.assertEqual(r['paths'],4);self.assertEqual(set(r['reachable_words'].values()),{126})
 def test_03_guest_mutations_and_byte_arguments(self):
  guest.main();r=json.loads((m.OUT/'guest-report.json').read_text());self.assertEqual(r['cases_per_stream'],858);self.assertEqual(set(r['target_words_visited'].values()),{126})
 def test_04_native_three_profiles_and_controls(self):
  native.main();r=json.loads((m.OUT/'native-v13/native-report.json').read_text());self.assertEqual(r['cases_per_profile'],848);self.assertEqual(len(r['runs']),9)
 def test_05_six_complete_original_callers(self):
  callers.main();r=json.loads((m.OUT/'callers-report.json').read_text());self.assertEqual(len(r['callers']),6);self.assertTrue(all(v['production_literal']for v in r['helpers']));self.assertTrue(all(set(v['cases_per_stream'].values())=={168}for v in r['callers']))
if __name__=='__main__':unittest.main()
