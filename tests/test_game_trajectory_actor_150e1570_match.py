import unittest
from tools.experiments import game_trajectory_actor_150e1570_match as packet
from tools.tests import game_trajectory_actor_150e1570_reference as reference
from tools.tests import game_trajectory_actor_150e1570_source_aliases as aliases
from tools.tests import game_trajectory_actor_150e1570_faults as faults
from tools.tests import game_trajectory_actor_150e1570_connected as connected
from tools.tests import game_trajectory_actor_150e1570_native as native
from tools.tests import game_trajectory_actor_150e1570_rebase as rebase
from tools.tests import game_trajectory_actor_150e1570_home_mutation as home_mutation
from tools.tests import game_trajectory_actor_150e1570_second_caller as second_caller
class TrajectoryActorMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_reference(self):reference.run()
 def test_aliases(self):aliases.run()
 def test_faults(self):faults.run()
 def test_connected_callback(self):connected.run()
 def test_native(self):native.run()
 def test_rebase(self):rebase.run()
 def test_home_mutation(self):home_mutation.run()
 def test_second_caller(self):second_caller.run()
