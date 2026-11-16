"""Whole-body semantic, object, native and original-parent qualification."""
import json,unittest
from tools.experiments import game_ring_emitter_151a37c0_recovery as m
from tools.experiments import game_ring_emitter_151a37c0_match as matching
from tools.tests import game_ring_emitter_151a37c0_proof as proof
from tools.tests import game_ring_emitter_151a37c0_oracle as guest
from tools.tests import game_ring_emitter_151a37c0_native as native
from tools.tests import game_ring_emitter_151a37c0_callers as callers

class RingEmitterRecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check();matching.main()
 def tearDown(self):m.check_inputs()
 def test_words_guards_padders_and_rebases(self):
  report=json.loads((m.OUT/'match-report.json').read_text())
  self.assertEqual((report['raw_and_binding_corruptions'],report['real_CSV_negatives']),(277,2))
 def test_symbolic_whole_function_and_effective_controls(self):
  raw=m.programs()['raw'];retail=m.retail();report=proof.prove(raw,retail);controls=proof.controls(raw,retail)
  (m.OUT/'whole-proof-report.json').write_text(json.dumps(report,indent=2)+'\n')
  (m.OUT/'whole-proof-controls.json').write_text(json.dumps(controls,indent=2)+'\n')
  self.assertEqual(len(controls['negatives']),17)
 def test_guest_and_original_providers(self):self.assertEqual(guest.main()['cases_per_stream'],1828)
 def test_native32_and_effective_controls(self):self.assertEqual(len(native.main()['runs']),14)
 def test_original_second_table_parent(self):self.assertEqual(callers.main()['cases_per_stream'],618)

if __name__=='__main__':unittest.main()
