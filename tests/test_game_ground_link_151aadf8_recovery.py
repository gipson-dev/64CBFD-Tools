"""Ground-link semantics, complete original dispatcher, guards and image prerequisites."""
import json,unittest
from tools.experiments import game_ground_link_151aadf8_recovery as m,game_ground_link_151aadf8_match as matching
from tools.tests import game_ground_link_151aadf8_oracle as guest,game_ground_link_151aadf8_native as native,game_ground_link_151aadf8_dispatcher as dispatcher,game_ground_link_151aadf8_proof as proof
class GroundLinkRecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check();matching.main()
 def tearDown(self):m.check_inputs()
 def test_01_complete_owner_guards_and_rebases(self):
  r=json.loads((m.OUT/'object-report.json').read_text());self.assertEqual((r['body_words'],r['retail_words'],r['frame'],r['guard_words'],r['insertions'],r['raw_and_binding_corruptions'],r['stale_CSV_controls']),(165,166,192,50,1,181,200))
 def test_02_complete_private_ordered_relation(self):proof.main()
 def test_03_guest_mutations_and_byte_selectors(self):
  guest.main();r=json.loads((m.OUT/'guest-report.json').read_text());self.assertEqual(r['cases_per_stream'],1094)
 def test_04_native_profiles_and_sequence_control(self):
  native.main();r=json.loads((m.OUT/'native-v42/native-report.json').read_text());self.assertEqual(r['cases'],608);self.assertEqual(len(r['runs']),9)
 def test_05_complete_original_dispatcher(self):
  dispatcher.main();r=json.loads((m.OUT/'dispatcher-report.json').read_text());self.assertTrue(r['complete_original_dispatcher_executed']);self.assertEqual(set(r['cases_per_stream'].values()),{228});self.assertEqual(r['dispatcher_words_visited'],156)
if __name__=='__main__':unittest.main()
