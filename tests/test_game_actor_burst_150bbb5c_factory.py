"""Qualify first-factory progress while retaining the explicit later trail mismatch."""
import itertools,json,unittest
from unittest.mock import patch
from tools.experiments import game_actor_burst_150bbb5c_factory as source
from tools.experiments import game_actor_burst_150bbb5c_recovery as previous
from tools.experiments import game_actor_burst_150bbb5c_ordered as ordered
from tools.tests import game_actor_burst_150bbb5c_oracle as guest
from tools.tests import game_actor_burst_150bbb5c_native as native
from tools.tests import game_actor_burst_150bbb5c_caller as caller
from tools.tests import game_actor_burst_150bbb5c_factory_proof as proof

class FirstFactoryBurstTests(unittest.TestCase):
 def test_01_owner_and_ordered_factory(self):
  row=source.qualify_source()
  self.assertEqual((row['raw_words'],row['frame'],row['strict_factory_paths']),(590,624,5))
  self.assertFalse(row['full_function_relation_proved'])
 def test_02_guest_values_and_early_fault(self):
  with patch.object(previous,'state',source.state):
   self.assertEqual(guest.run()['cases'],274)
   self.assertEqual(guest.faults()['programs'],2)
 def test_03_native_sdk32_with_controls(self):
  with patch.object(previous,'PIN',dict(previous.PIN,body=source.PIN['body'])):
   self.assertEqual(native.run()['cases_per_positive_run'],384)
 def test_04_original_caller_connection(self):
  with patch.object(ordered,'state',source.state):
   self.assertEqual(caller.run()['cases'],3072)
   self.assertEqual(caller.controls()['effective_controls'],6)
 def test_05_factory_controls_and_full_trace_diagnostic(self):
  self.assertEqual(source.factory_controls()['effective_controls'],7)
  # Bounds simplify only non-overflowing signed ranges and real mask results.
  e=proof.e
  for mask in (0,3,255,65535,0x7fffffff):
   value=e.bitop('AND',('X',),mask)
   self.assertEqual(proof.interval(value),(0,mask))
  self.assertIsNone(proof.interval(e.add(e.bitop('AND',('X',),0x7fffffff),1)))
  self.assertIsNone(proof.interval(e.bitop('AND',('X',),0x80000000)))
  rows=[]
  for pair in itertools.product(range(4),repeat=2):
   row=proof.run(label='full-'+''.join(map(str,pair)),target=None,count_pair=pair)
   self.assertFalse(row['strict_factory_equal'])
   self.assertEqual(row['covered_words'],dict(raw=590,retail=587))
   self.assertEqual(row['paths'],5)
   self.assertTrue(row['first_differences'])
   self.assertTrue(all(d['raw_location'][0]==1368 and d['retail_location'][0]==1356 for d in row['first_differences']))
   rows.append(dict(count_pair=pair,**row))
  (source.OUT/'full-trace-diagnostic.json').write_text(json.dumps(dict(
   count_pairs=16,symbolic_paths=80,first_factory_qualified=True,
   full_function_relation_proved=False,source_installed=False,c_match_credit=0,rows=rows),indent=2)+'\n')
 @classmethod
 def tearDownClass(cls):source.check_inputs()
if __name__=='__main__':unittest.main()
