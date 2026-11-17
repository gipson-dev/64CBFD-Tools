"""Full semantic, guarded-object, native and original-parent region checks."""
import json,unittest
from tools.experiments import game_region_emitter_151a5660_recovery as m,game_region_emitter_151a5660_match as matching
from tools.tests import game_region_emitter_151a5660_oracle as guest,game_region_emitter_151a5660_native as native,game_region_emitter_151a5660_prefix_proof as prefix,game_region_emitter_151a5660_proof as proof,game_region_emitter_151a5660_return_range as ranges,game_region_emitter_151a5660_callers as callers,game_region_emitter_151a5660_producer as producer
class RegionEmitterRecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check();matching.main();ranges.main()
 def tearDown(self):m.check_inputs()
 def test_01_source_and_guards(self):
  r=json.loads((m.OUT/'guard-qualification.json').read_text());self.assertEqual((r['guard_words'],r['raw_and_binding_corruptions'],r['stale_CSV_controls']),(47,439,94))
 def test_02_opening_transfer(self):
  prefix.main();self.assertEqual(json.loads((m.OUT/'prefix-proof-qualified.json').read_text())['paths'],7)
 def test_03_inductive_iteration(self):
  proof.main();r=json.loads((m.OUT/'iteration-proof-qualified-inductive.json').read_text());self.assertEqual(r['paths'],42);self.assertEqual(len(r['effective_controls']),5)
 def test_04_guest_and_unsigned_conversion(self):
  guest.main();r=json.loads((m.OUT/'finite-guest-v39-rev2.json').read_text());self.assertEqual(r['cases'],793);self.assertEqual(set(r['target_words_visited'].values()),{398,399})
 def test_05_native_three_profiles(self):
  native.main();r=json.loads((m.OUT/'native-qualification-selected-rev2/native-report.json').read_text());self.assertEqual(r['cases_per_profile'],764);self.assertEqual(len(r['runs']),11)
 def test_06_original_dispatcher(self):
  callers.main();self.assertEqual(json.loads((m.OUT/'connected-parent.json').read_text())['cases_per_stream'],384)
 def test_07_actual_producer(self):
  producer.main();self.assertEqual(json.loads((m.OUT/'producer-audit.json').read_text())['payload_copy_bytes'],112)
if __name__=='__main__':unittest.main()
