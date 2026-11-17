"""Qualify a complete ordered diagnostic while leaving byte matching open."""
import json,struct,unittest
from tools.experiments import game_strip_constructor_151acbd4_ordered as m
from tools.tests import game_strip_constructor_151acbd4_private_oracle as g,game_strip_constructor_151acbd4_ordered_native as native
class StripConstructorOrderedTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.raw=m.compile_and_check()
 def tearDown(self):m.check_inputs()
 def test_01_owner_frame_and_all_neighbors(self):
  r=json.loads((m.OUT/'source-report.json').read_text());self.assertEqual((r['raw_words'],r['retail_words'],r['frame'],r['neighbors_unchanged']),(388,360,64,32))
 def test_02_complete_guest_streams(self):
  programs={'retail':list(struct.unpack('>360I',(m.OUT/'retail.bin').read_bytes())),'v35':self.raw,'v35-private-schedule':m.adjusted(self.raw)}
  visits={k:set() for k in programs};count=0
  for case in g.cases():
   for label,words in programs.items():visits[label].update(g.verify(words,case).visits)
   count+=1
  self.assertEqual(count,1016)
  (m.OUT/'guest-report.json').write_text(json.dumps(dict(cases_per_stream=count,streams=list(programs),words_visited={k:len(v)for k,v in visits.items()},all_initialized_public_bytes_compared=True,source_installed=False,c_match_credit=0),indent=2)+'\n')
 def test_03_native_profiles_and_effective_controls(self):
  native.main();r=json.loads((m.OUT/'native-v35/native-report.json').read_text());self.assertEqual(r['cases'],1016);self.assertEqual(len(r['runs']),8);self.assertTrue(r['passes'])
 def test_04_complete_ordered_provider_and_return_relation(self):
  r=m.ordered_proof();self.assertEqual(r['complete_relation']['equal_paths'],10);self.assertEqual(len(r['effective_controls']),2);self.assertFalse(r['source_installed']);self.assertTrue(r['ordered_FP_FCSR_compared'])
if __name__=='__main__':unittest.main()
