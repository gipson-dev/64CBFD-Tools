import unittest
from tools.experiments import game_scene_transition_dispatch_match as p
from tools.tests import game_scene_transition_dispatch_guest as guest, game_scene_transition_dispatch_native as native, game_scene_transition_dispatch_pad as pad, game_scene_transition_dispatch_connected as connected, game_scene_transition_dispatch_window as window, game_scene_transition_dispatch_boundaries as boundaries
class SceneTransitionDispatchTests(unittest.TestCase):
 report={}
 def test_01_actual_make_and_image(self):type(self).report=p.prepare()
 def test_02_padders_and_table(self):pad.main()
 def test_03_retail_guest(self):guest.main()
 def test_04_native(self):native.main()
 def test_05_connected_helpers(self):connected.main()
 def test_06_caller(self):window.main()
 def test_07_boundaries(self):boundaries.main()
