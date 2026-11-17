"""Full source, fit, caller and helper-chain qualification for attached emission."""
import json,unittest
from tools.experiments import game_attached_emission_151a4a38_recovery as m,game_attached_emission_151a4a38_match as matching
from tools.tests import game_attached_emission_151a4a38_proof as proof,game_attached_emission_151a4a38_controls as controls,game_attached_emission_151a4a38_oracle as guest,game_attached_emission_151a4a38_native as native,game_attached_emission_151a4a38_connected as connected,game_attached_emission_151a4a38_callers as callers
class AttachedEmissionRecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check();matching.main()
 def tearDown(self):m.check_inputs()
 def test_guards_padders_rebases(self):
  r=json.loads((m.OUT/'match-report.json').read_text());self.assertEqual((r['raw_and_binding_corruptions'],r['real_CSV_negatives']),(176,2))
 def test_whole_function_and_semantic_controls(self):
  r=proof.prove(*proof.programs());(m.OUT/'proof-report.json').write_text(json.dumps(r,indent=2)+'\n');self.assertEqual(r['paths'],10);self.assertEqual(len(controls.main()['controls']),11)
 def test_complete_guest_model(self):self.assertEqual(guest.main()['cases_per_stream'],1248)
 def test_native32_and_effective_controls(self):self.assertEqual(len(native.main()['runs']),10)
 def test_original_emitter_chain(self):self.assertEqual(connected.main()['cases_per_stream'],480)
 def test_complete_original_dispatcher(self):self.assertEqual(callers.main()['cases_per_stream'],384)
if __name__=='__main__':unittest.main()
