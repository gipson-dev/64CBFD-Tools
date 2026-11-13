"""Private screening: guarded bytes, normal cases, and explicit alias limits."""
import unittest
from tools.experiments import game_paired_height_descriptor_screen as packet
from tools.tests import game_paired_height_descriptor_oracle as oracle

class HeightDescriptorScreen(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_ordinary(self):
  self.assertEqual(oracle.ordinary(self.state), {"func_150C5F94":96,"func_150C68C4":96})
 def test_aliases(self):
  self.assertEqual(oracle.aliases(self.state), {n:{"ok":638,"incomplete-alias-cases":10} for n in self.state})

if __name__=="__main__":unittest.main()
