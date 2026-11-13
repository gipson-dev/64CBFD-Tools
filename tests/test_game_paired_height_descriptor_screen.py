"""Private screening: guarded bytes, normal cases, and explicit alias limits."""
import unittest
from tools.experiments import game_paired_height_descriptor_screen as packet
from tools.tests import game_paired_height_descriptor_oracle as oracle
from tools.tests import game_paired_height_descriptor_connected as connected
from tools.tests import game_paired_height_descriptor_native as native
from tools.tests import game_paired_height_descriptor_rebase as rebase

class HeightDescriptorScreen(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_ordinary(self):
  self.assertEqual(oracle.ordinary(self.state), {"func_150C5F94":96,"func_150C68C4":96})
 def test_connected_factory_and_copy(self):
  report=connected.run(self.state,(packet.ROOT/"conker/conker.us.bin").read_bytes())
  self.assertEqual({k:v["cases"] for k,v in report.items()}, {n:80 for n in self.state})
  self.assertTrue(all(v["copy_words_visited"]==11 for v in report.values()))
  print("connected",report,flush=True)
 def test_fault_prefixes(self):
  report=connected.fault_prefixes(self.state)
  self.assertTrue(all(v["access_cuts"]>0 for v in report.values()))
  print("faults",report,flush=True)
 def test_rebases(self):
  self.assertEqual(rebase.run(self.state),{n:{"symbol_bases":3,"actual_gnu_links":12} for n in self.state})
 def test_native(self):
  report=native.run()
  self.assertTrue(all(len(v)==3 for v in report.values()))
  print("native",report,flush=True)
 def test_original_callers(self):
  self.assertEqual(connected.callers(self.state,(packet.ROOT/"conker/conker.us.bin").read_bytes()), {n:80 for n in self.state})
 def test_aliases(self):
  self.assertEqual(oracle.aliases(self.state), {n:{"ok":638,"incomplete-alias-cases":10} for n in self.state})

if __name__=="__main__":unittest.main()
