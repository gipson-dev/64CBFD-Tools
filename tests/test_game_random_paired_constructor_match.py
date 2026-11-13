"""Qualification tests for paired randomized effect constructors."""
import unittest
from tools.experiments import game_random_paired_constructor_match as packet
from tools.tests import game_random_paired_constructor_match_oracle as guest
from tools.tests import game_random_paired_constructor_match_connected as connected
from tools.tests import game_random_paired_constructor_match_native as native
from tools.tests import game_random_paired_constructor_match_rebase as rebase
class RandomPairedConstructorMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_semantic_model(self):self.assertEqual(guest.ordinary(self.state),{n:20 for n in self.state})
 def test_original_rng(self):
  report=connected.run(self.state)
  self.assertTrue(all(v["rng_words_visited"]==43 for v in report.values()))
  print("connected",report,flush=True)
 def test_original_factory_chain(self):
  report=connected.full_helpers(self.state)
  self.assertTrue(all(v["cases"]==48 for v in report.values()))
  print("full helpers",report,flush=True)
 def test_original_dispatch_window(self):
  self.assertEqual(connected.callers(self.state),{n:48 for n in self.state})
 def test_fault_prefixes(self):
  report=connected.fault_prefixes(self.state)
  self.assertTrue(all(v["access_cuts"]>0 for v in report.values()))
  print("fault prefixes",report,flush=True)
 def test_native(self):
  report=native.run()
  self.assertTrue(all(len(v)==3 for v in report.values()))
  print("native",report,flush=True)
 def test_rebases(self):
  self.assertEqual(rebase.run(self.state),{n:{"symbol_bases":3,"actual_gnu_links":12} for n in self.state})
 def test_aliases(self):self.assertEqual(guest.aliases(self.state),{n:452 for n in self.state})
if __name__=='__main__':unittest.main()
