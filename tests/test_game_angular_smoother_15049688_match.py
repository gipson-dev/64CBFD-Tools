import unittest
from tools.experiments import game_angular_smoother_15049688_match as packet
from tools.tests import game_angular_smoother_15049688_reference as reference
from tools.tests import game_angular_smoother_15049688_aliases as aliases
from tools.tests import game_angular_smoother_15049688_edge as edge
from tools.tests import game_angular_smoother_15049688_caller as caller
from tools.tests import game_angular_smoother_15049688_native as native
from tools.tests import game_angular_smoother_15049688_rebase as rebase
class AngularSmootherMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_reference(self):reference.run()
 def test_stack_aliases(self):aliases.run()
 def test_float_edges(self):edge.edges()
 def test_access_cuts(self):edge.faults()
 def test_original_caller(self):caller.run()
 def test_native(self):native.run()
 def test_rebases(self):rebase.run()
if __name__=='__main__':unittest.main()
