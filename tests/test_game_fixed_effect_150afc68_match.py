import unittest
from tools.experiments import game_fixed_effect_150afc68_match as packet
from tools.tests import game_fixed_effect_150afc68_oracle as oracle
from tools.tests import game_fixed_effect_150afc68_connected as connected
from tools.tests import game_fixed_effect_150afc68_integration as integration
from tools.tests import game_fixed_effect_150afc68_native as native
from tools.tests import game_fixed_effect_150afc68_rebase as rebase
class FixedEffectMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_guest_packets(self):oracle.run()
 def test_fault_prefix(self):oracle.fault_prefixes()
 def test_original_callers(self):connected.run()
 def test_original_factory(self):integration.run()
 def test_native_and_controls(self):native.run()
 def test_rebase(self):rebase.run()
