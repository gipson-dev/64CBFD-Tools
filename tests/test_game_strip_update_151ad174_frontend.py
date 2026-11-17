"""Normal compiler provenance and a shape match that remains uncredited."""
from pathlib import Path
import json,struct,unittest
from tools.experiments import game_strip_update_151ad174_frontend as m
from tools.tests import game_strip_update_151ad174_private_oracle as guest,game_strip_update_151ad174_private_observation as observation
class StripUpdateFrontendTests(unittest.TestCase):
 def tearDown(self):m.check_inputs()
 def test_01_selected_normal_streams(self):
  row=m.capture('v20');layout=m.layout('v20');self.assertTrue(row['producer_and_driver_completed']);self.assertTrue(row['all_33_owner_bodies_bindings_and_pools_identical']);self.assertEqual((layout['frontend']['M_bytes'],layout['optimizer']['M_bytes']),(620,656))
 def test_02_gravity_normal_streams(self):
  row=m.capture('v22');layout=m.layout('v22');self.assertTrue(row['producer_and_driver_completed']);self.assertEqual((layout['frontend']['M_bytes'],layout['optimizer']['M_bytes']),(616,660))
 def test_03_retail_shape_still_has_a_private_and_FP_gap(self):
  m.capture('v27');m.layout('v27');work=m.OUT/'v27';raw,refs=guest.payload(work/'baseline.o','func_151AD174');words=guest.bound_blob(raw,refs,guest.SYMS);self.assertEqual((len(words),65536-(words[0]&65535)),(494,776))
  coverage=set();n=0
  for case in guest.cases():coverage.update(guest.verify(words,case).visits);n+=1
  case=guest.Case(seed=7,owner=1,impulse=1,pattern=1);initial=guest.fixture(case);truth_blob=(m.source.FROZEN/'conker/conker.us.bin').read_bytes()[m.source.ROM:m.source.ROM+m.source.SIZE]
  self.assertEqual(__import__('hashlib').sha256(truth_blob).hexdigest(),m.source.PIN['retail_sha256']);truth=list(struct.unpack('>494I',truth_blob));retail=observation.Observe(truth,initial,case).run();candidate=observation.Observe(words,initial,case).run()
  differences=[i for i in range(-776,16)if retail.memory[guest.STACK+i]!=candidate.memory[guest.STACK+i]];different_words=sorted(set(i&~3 for i in differences));self.assertEqual(different_words,[-652,-644,-620,-604,-600,-528]);self.assertEqual((len(retail.fp),len(candidate.fp)),(1671,1670));self.assertNotEqual(retail.fp,candidate.fp);self.assertEqual(n,544)
  report=dict(guest_cases=544,words=494,frame=776,words_visited=len(coverage),private_different_words=different_words,FP_operations=[len(retail.fp),len(candidate.fp)],source_installed=False,c_match_credit=0)
  (work/'shape-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':unittest.main()
