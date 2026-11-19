"""Focused allocation diagnostics; previous semantic suites are explicitly reused."""
import unittest
from tools.experiments import game_actor_burst_150bbb5c_allocation as s

class ActorBurstAllocationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=s.qualify()
 def test_01_uopt_scoped_constant_and_code_identity(self):
  self.assertTrue(self.report['all_objects_unchanged'])
  self.assertEqual((self.report['descriptor_constant']['expression'],self.report['descriptor_constant']['color']),(499,18))
  self.assertFalse(self.report['timing_cost_numbers_valid'])
 def test_02_ugen_already_assigned_s4_and_stub_control(self):
  self.assertEqual(self.report['s4_register_nodes'],dict(ugen_full=3,ugen_stub=0))
  self.assertEqual(self.report['ugen_event_counts'],dict(ugen_full=296,ugen_stub=121))
  self.assertFalse(self.report['source_installed'])
 def test_03_diagnostic_fail_closed_controls(self):
  self.assertEqual(s.rejection_controls()['effective_controls'],3)
 def test_04_exact_unchanged_semantic_receipt_reuse(self):
  rows=s.reused_semantic_receipts()
  self.assertEqual(set(rows),{'primary','sibling'})
  self.assertTrue(all(not row['freshly_rerun']and row['tests']==5 for row in rows.values()))
 @classmethod
 def tearDownClass(cls):s.check_inputs()
if __name__=='__main__':unittest.main()
