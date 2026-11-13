import unittest
from tools.experiments import game_impact_random_151ac408_match as packet
from tools.tests import game_impact_random_151ac408_oracle as oracle
from tools.tests import game_impact_random_151ac408_connected as connected
from tools.tests import game_impact_random_151ac408_faults as faults
from tools.tests import game_impact_random_151ac408_native as native
from tools.tests import game_impact_random_151ac408_rebase as rebase
class RandomImpactMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_guest_model(self):oracle.run()
 def test_fault_prefix(self):faults.run()
 def test_original_caller(self):connected.run()
 def test_native_and_controls(self):native.run()
 def test_rebase(self):rebase.run()
