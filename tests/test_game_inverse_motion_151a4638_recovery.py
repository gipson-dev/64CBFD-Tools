"""Complete source, literal fitting, semantic, native and original-caller gates."""
import json,unittest
from tools.experiments import game_inverse_motion_151a4638_recovery as m,game_inverse_motion_151a4638_match as matching
from tools.tests import game_inverse_motion_151a4638_proof as proof,game_inverse_motion_151a4638_controls as controls,game_inverse_motion_151a4638_oracle as guest,game_inverse_motion_151a4638_native as native,game_inverse_motion_151a4638_connected as connected,game_inverse_motion_151a4638_callers as callers
class InverseMotionRecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check();matching.main()
 def tearDown(self):m.check_inputs()
 def test_guards_padders_rebases(self):
  r=json.loads((m.OUT/'match-report.json').read_text());self.assertEqual((r['raw_and_binding_corruptions'],r['real_CSV_negatives']),(140,2))
 def test_whole_function_and_semantic_controls(self):
  r=proof.prove(*proof.programs());(m.OUT/'proof-report.json').write_text(json.dumps(r,indent=2)+'\n');c=controls.main();self.assertEqual(len(c['controls']),11)
 def test_complete_guest_model(self):
  r=guest.main();self.assertEqual(r['cases_per_stream'],2112);self.assertTrue(all(n==0 for n in r['FP_order_disagreements'].values()))
 def test_native32_and_effective_controls(self):self.assertEqual(len(native.main()['runs']),10)
 def test_original_factory_and_copy_chain(self):self.assertEqual(connected.main()['cases_per_stream'],192)
 def test_original_caller_window(self):self.assertEqual(callers.main()['cases_per_stream'],576)
if __name__=='__main__':unittest.main()
