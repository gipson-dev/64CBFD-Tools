import unittest
from tools.experiments import game_state_trajectory_15072f10_match as packet
from tools.tests import game_state_trajectory_15072f10_reference as reference
from tools.tests import game_state_trajectory_15072f10_aliases as aliases
from tools.tests import game_state_trajectory_15072f10_callbacks as callbacks
from tools.tests import game_state_trajectory_15072f10_dispatch as dispatch
from tools.tests import game_state_trajectory_15072f10_connected as connected
from tools.tests import game_state_trajectory_15072f10_faults as faults
from tools.tests import game_state_trajectory_15072f10_native as native
from tools.tests import game_state_trajectory_15072f10_rebase as rebase
class StateTrajectoryMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_reference(self):reference.run()
 def test_aliases(self):aliases.run()
 def test_callback_stub(self):callbacks.run()
 def test_original_dispatch(self):dispatch.run()
 def test_vector_helper(self):connected.run()
 def test_access_cuts(self):faults.run()
 def test_native(self):native.run()
 def test_rebases(self):rebase.run()
if __name__=='__main__':unittest.main()
