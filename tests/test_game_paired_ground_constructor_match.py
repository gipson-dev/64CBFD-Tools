import unittest
from tools.experiments import game_paired_ground_constructor_match as packet
from tools.tests import game_paired_ground_constructor_oracle as guest
from tools.tests import game_paired_ground_constructor_connected as connected
from tools.tests import game_paired_ground_constructor_native as native
from tools.tests import game_paired_ground_constructor_rebase as rebase
class GroundConstructorMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_ordinary(self):self.assertEqual(guest.ordinary(self.state),{n:80 for n in self.state})
 def test_original_rng(self):
  report=connected.run(self.state)
  self.assertTrue(all(x["visited"]==43 for x in report.values()))
  print("rng",report,flush=True)
 def test_original_factory_wrapper(self):
  report=connected.run(self.state,True)
  self.assertTrue(all(x["cases"]==96 for x in report.values()))
  print("factory",report,flush=True)
 def test_original_callers(self):self.assertEqual(connected.callers(self.state),{n:16 for n in self.state})
 def test_faults(self):
  report=connected.faults(self.state)
  self.assertTrue(all(v["cuts"]>0 for v in report.values()))
  print("faults",report,flush=True)
 def test_native(self):
  report=native.run()
  self.assertTrue(all(len(v)==3 for v in report.values()))
  print("native",report,flush=True)
 def test_aliases(self):self.assertEqual(guest.aliases(self.state),{n:{'cases':1808,'incomplete':40}for n in self.state})
 def test_rebases(self):
  report=rebase.run(self.state)
  self.assertTrue(all(v['actual_gnu_links']==12 for v in report.values()))
  print('rebases',report,flush=True)
if __name__=='__main__':unittest.main()
