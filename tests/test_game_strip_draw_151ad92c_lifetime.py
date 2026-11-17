"""Renderer lifetimes and partial opening relation; no matching credit."""
import json,struct,unittest
from tools.experiments import game_strip_draw_151ad92c_lifetime as source

class StripDrawLifetimeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  source.check_inputs();cls.guest,cls.caller,cls.native=source.bind_engines()
 @classmethod
 def tearDownClass(cls):
  try:source.check_inputs()
  finally:source.restore_engines()
 @classmethod
 def programs(cls):
  from tools.tests import game_strip_draw_151ad92c_entry_proof as proof
  data,refs=cls.guest.o.payload(source.OUT/'owner.o',source.NAME)
  raw=cls.guest.o.bound_blob(data,refs,cls.guest.SYMS)
  normalized,edits=proof.derive(raw);assert edits==source.PIN['home_edits']
  return {'retail':list(struct.unpack('>464I',(source.OUT/'retail.bin').read_bytes())),'raw':raw,'homes':normalized}
 def test_01_complete_owner_and_original_frame(self):
  report=source.compile_and_check();self.assertEqual((report['raw_words'],report['retail_words'],report['frame']),(469,464,304))
 def test_02_symbolic_opening_and_effective_controls(self):
  from tools.tests import game_strip_draw_151ad92c_entry_proof as proof
  proof.main()
 def test_03_finite_public_matrix_and_remaining_frontier(self):
  g=self.guest;programs=self.programs();coverage={name:set()for name in programs};n=fp=equal_fp=equal_frame=0
  for case in g.cases():
   runs={name:g.verify(code,case)for name,code in programs.items()};retail=runs['retail'];raw=runs['raw'];homes=runs['homes']
   for name,m in runs.items():coverage[name].update(m.visits)
   self.assertEqual(raw.fp,homes.fp);fp+=len(retail.fp);equal_fp+=raw.fp==retail.fp;equal_frame+=homes.boundaries==retail.boundaries;n+=1
  self.assertEqual(n,544);self.assertLess(equal_fp,n);self.assertLess(equal_frame,n)
  report=dict(cases_per_stream=n,streams=list(programs),words_visited={k:len(v)for k,v in coverage.items()},retail_FP_observations=fp,ordered_FP_equal_cases=equal_fp,normalized_provider_frame_equal_cases=equal_frame,public_bytes_calls_return_and_saved_regs_equal=True,home_relocation_preserves_full_raw_FP_trace=True,source_installed=False,c_match_credit=0)
  (source.OUT/'guest-lifetime-report.json').write_text(json.dumps(report,indent=2)+'\n')
 def test_04_complete_original_caller_and_selector(self):self.caller.main()
 def test_05_native_sdk_c_and_semantic_controls(self):self.native.main()
 def test_06_late_home_load_controls(self):
  from tools.tests import game_strip_draw_151ad92c_entry_proof as proof
  programs=self.programs();limit=max(proof.cuts(programs['homes']));controls=[]
  case=self.guest.Case(seed=7,count=3,width=1,height=32,texture=54,mutation=15)
  for row in source.PIN['home_edits']:
   if row['index']*4<limit:continue
   bad=programs['homes'][:];bad[row['index']]=row['expected_word']
   with self.assertRaises(AssertionError):self.guest.verify(bad,case)
   controls.append(row['index'])
  self.assertEqual(len(controls),3)
  (source.OUT/'late-home-controls.json').write_text(json.dumps(dict(rejected_stale_load_indices=controls,source_installed=False,c_match_credit=0),indent=2)+'\n')
if __name__=='__main__':unittest.main()
