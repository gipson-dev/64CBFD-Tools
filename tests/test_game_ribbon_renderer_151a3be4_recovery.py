"""Complete ribbon-source, proof, guest, native and actual-caller gates."""
import json,unittest
from tools.experiments import game_ribbon_renderer_151a3be4_recovery as m,game_ribbon_renderer_151a3be4_match as matching
from tools.tests import game_ribbon_renderer_151a3be4_proof as p,game_ribbon_renderer_151a3be4_composition as composition,game_ribbon_renderer_151a3be4_controls as controls,game_ribbon_renderer_151a3be4_oracle as guest,game_ribbon_renderer_151a3be4_native as native,game_ribbon_renderer_151a3be4_callers as callers
class RibbonRendererTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check();matching.main()
 def tearDown(self):m.check_inputs()
 def test_words_guards_padders_and_rebases(self):
  r=json.loads((m.OUT/'match-report.json').read_text());self.assertEqual((r['raw_and_binding_corruptions'],r['real_CSV_negatives']),(633,2))
 def test_composed_symbolic_proof_and_controls(self):
  raw,retail=p.programs()
  for check in(p.opening_proof,p.setup_proof,p.seed_proof,p.first_pair_proof,p.loop_geometry_proof,p.second_pair_proof,p.seam_proof,p.tail_proof,p.epilogue_proof):check(raw,retail)
  r=composition.prove(raw,retail);(m.OUT/'whole-proof-report.json').write_text(json.dumps(r,indent=2)+'\n');c=controls.main();self.assertEqual((len(c['word_controls']),len(c['cut_controls'])),(15,9))
 def test_guest_all_streams_and_aliases(self):self.assertEqual(guest.main()['cases_per_stream'],1052)
 def test_native32_and_effective_controls(self):self.assertEqual(len(native.main()['runs']),15)
 def test_actual_dispatcher_allocator_and_memcpy(self):self.assertEqual(callers.main()['cases_per_stream'],2048)
if __name__=='__main__':unittest.main()
