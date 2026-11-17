"""Bounded private progress: full prefix, snapshot induction and public checks."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,struct,unittest
from tools.experiments import game_strip_update_151ad174_lifetime as m
from tools.tests import game_strip_update_151ad174_private_oracle as guest
from tools.tests import game_strip_update_151ad174_private_native as native
from tools.tests import game_strip_update_151ad174_private_caller as caller
from tools.tests import game_strip_update_151ad174_lifetime_relation as relation
class StripUpdateLifetimeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=m.compile_and_check();raw,refs=guest.payload(m.OUT/'owner.o',m.NAME);cls.raw=guest.bound_blob(raw,refs,guest.SYMS);cls.truth=list(struct.unpack('>494I',(m.OUT/'retail.bin').read_bytes()))
 @classmethod
 def tearDownClass(cls):m.check_inputs()
 def test_01_public_guest_and_preserved_registers(self):
  coverage={'retail':set(),'raw':set()};n=0
  for case in guest.cases():
   for name,words in [('retail',self.truth),('raw',self.raw)]:coverage[name].update(guest.verify(words,case).visits)
   n+=1
  self.assertEqual(n,544);self.assertEqual({k:len(v)for k,v in coverage.items()},{'retail':489,'raw':485})
  (m.OUT/'guest-report.json').write_text(json.dumps(dict(cases=n,words_visited={k:len(v)for k,v in coverage.items()},public_bytes_and_calls_equal=True,full_preserved_registers=True,source_installed=False,c_match_credit=0),indent=2)+'\n')
 def test_02_symbolic_prefix_and_inductive_snapshot(self):
  prefix=relation.prefix_controls(self.truth,self.raw);snapshot=relation.snapshot_controls(self.truth,self.raw)
  self.assertEqual((prefix['paths'],prefix['visited_words'],prefix['call_boundaries']),(18,142,30));self.assertTrue(prefix['all_floating_registers_at_every_call_and_join']);self.assertTrue(snapshot['loop_live_relation_reestablished'])
  for name,row in [('prefix-relation.json',prefix),('snapshot-relation.json',snapshot)]:(m.OUT/name).write_text(json.dumps(row,indent=2)+'\n')
 def test_03_native_three_profiles_and_four_controls(self):
  adapter=SimpleNamespace(ROOT=m.ROOT,PACKET=m.PACKET,OUT=m.OUT,FROZEN=m.source.FROZEN,SOURCE=m.source.SOURCE,PIN=dict(m.source.PIN,body=m.PIN['body']),check_inputs=m.check_inputs)
  with patch.object(native,'source',adapter):native.main()
  row=json.loads((m.OUT/'native/native-report.json').read_text());self.assertTrue(row['passes']);self.assertEqual((row['cases'],len(row['runs'])),(544,7))
 def test_04_complete_registered_caller(self):
  with patch.object(caller,'p',m.OUT):caller.main()
  row=json.loads((m.OUT/'caller-report.json').read_text());self.assertEqual(row['cases_per_stream'],64);self.assertEqual(row['caller_words_visited'],{'retail':73,'raw':73});self.assertTrue(row['effective_controls'])
 def test_05_normal_allocation_capture_and_scoped_identity(self):
  row=m.capture_allocation();self.assertTrue(row['all_33_bodies_bindings_pools_identical']);self.assertTrue(row['function_scoped_identity']);self.assertEqual(row['amplitude_allocation']['color'],30)
if __name__=='__main__':unittest.main()
