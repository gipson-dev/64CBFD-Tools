"""Direct body, complete guest/native semantics and authentic caller ABI."""
import json,unittest
from tools.experiments import game_effect_chain_151a6c90_recovery as m
from tools.tests import game_effect_chain_151a6c90_oracle as guest,game_effect_chain_151a6c90_native as native,game_effect_chain_151a6c90_callers as callers
class EffectChainRecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check();m.qualify_objects()
 def tearDown(self):m.check_inputs()
 def test_01_literal_body_bindings_and_both_padders(self):
  r=json.loads((m.OUT/'object-qualification.json').read_text());self.assertTrue(r['raw_literal']);self.assertEqual((r['raw_instruction_words'],r['slot_words'],r['frame'],r['guards'],r['corruption_controls']),(154,156,168,0,165))
 def test_02_guest_semantics(self):
  guest.main();r=json.loads((m.OUT/'guest-report.json').read_text());self.assertEqual(r['cases_per_stream'],560);self.assertEqual(set(r['target_words_visited'].values()),{150})
 def test_03_native_three_profiles_and_effective_controls(self):
  native.main();r=json.loads((m.OUT/'native-v2/native-report.json').read_text());self.assertEqual(r['cases_per_profile'],560);self.assertEqual(len(r['runs']),9)
 def test_04_rebases_and_actual_caller_window(self):
  callers.main();r=json.loads((m.OUT/'rebase-caller-report.json').read_text());self.assertEqual(len(r['rebases']),4);self.assertEqual(set(r['callers']['cases_per_stream'].values()),{128})
if __name__=='__main__':unittest.main()
