"""Focused private recovery, deliberately no matching-credit gate."""
import unittest
from tools.experiments import game_scaled_argument_packet_151a1010_recovery as m
from tools.tests import game_scaled_argument_packet_151a1010_oracle as g
from tools.tests import game_scaled_argument_packet_151a1010_native as n
from tools.tests import game_scaled_argument_packet_151a1010_proof as p
class ScaledPacketRecovery(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check()
 def test_01_complete_guest_packet(self):g.main()
 def test_02_ordered_transfer(self):
  p.main()
  streams=m.programs()
  with self.assertRaisesRegex(AssertionError,'ordered transfer mismatch'):p.prove(streams['original-frame'],streams['retail'])
 def test_03_defined_native32(self):n.main()
 def test_04_static_reference_scope(self):
  self.assertFalse(any(m.caller_census().values()));self.assertEqual(m.check_inputs(),887)
if __name__=='__main__':unittest.main()
