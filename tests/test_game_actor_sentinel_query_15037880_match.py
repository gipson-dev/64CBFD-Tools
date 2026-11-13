import unittest
from tools.experiments import game_actor_sentinel_query_15037880_match as packet
from tools.tests import game_actor_sentinel_query_15037880_reference as reference
from tools.tests import game_actor_sentinel_query_15037880_faults as faults
from tools.tests import game_actor_sentinel_query_15037880_connected as connected
from tools.tests import game_actor_sentinel_query_15037880_second_caller as second_caller
from tools.tests import game_actor_sentinel_query_15037880_native as native
from tools.tests import game_actor_sentinel_query_15037880_rebase as rebase
class ActorSentinelQueryMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_reference(self):reference.run()
 def test_faults(self):faults.run()
 def test_connected_caller(self):connected.run()
 def test_second_caller(self):second_caller.run()
 def test_native(self):native.run()
 def test_rebase(self):rebase.run()
