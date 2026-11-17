"""Complete emitter, mutable providers, original caller and both real padders."""
import json,unittest
from tools.experiments import game_actor_accumulator_151ab9c8_recovery as m,game_actor_accumulator_151ab9c8_match as matching
from tools.tests import game_actor_accumulator_151ab9c8_oracle as guest,game_actor_accumulator_151ab9c8_native as native,game_actor_accumulator_151ab9c8_caller as caller,game_actor_accumulator_151ab9c8_proof as proof
class ActorAccumulatorRecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check();matching.main()
 def tearDown(self):m.check_inputs()
 def test_01_complete_owner_guards_and_rebases(self):
  r=json.loads((m.OUT/'object-report.json').read_text());self.assertEqual((r['body_words'],r['retail_words'],r['frame'],r['guard_words'],r['insertions'],r['omissions']),(227,227,280,150,0,0))
 def test_02_entry_and_inductive_loop_relation(self):proof.main()
 def test_03_guest_mutations_boundaries_and_prefixes(self):
  guest.main();r=json.loads((m.OUT/'guest-report.json').read_text());self.assertEqual(r['cases_per_stream'],1472);self.assertEqual(r['bounded_nontermination_prefixes_per_stream'],64);self.assertTrue(r['public_actor_buffers_disjoint_from_private_stack'])
 def test_04_native_profiles_and_effective_controls(self):
  native.main();r=json.loads((m.OUT/'native-v28/native-report.json').read_text());self.assertEqual(r['cases'],1408);self.assertEqual(len(r['runs']),8)
 def test_05_complete_original_record_tick(self):
  caller.main();r=json.loads((m.OUT/'caller-report.json').read_text());self.assertTrue(r['complete_original_caller_executed']);self.assertEqual(set(r['cases_per_stream'].values()),{192});self.assertEqual(r['caller_words_visited'],45)
if __name__=='__main__':unittest.main()
