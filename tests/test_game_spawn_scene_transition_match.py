import unittest
from tools.experiments import game_spawn_scene_transition_match as p
from tools.tests import game_spawn_scene_transition_guest as guest, game_spawn_scene_transition_native as native, game_spawn_scene_transition_pad as pad, game_spawn_scene_transition_window as window, game_spawn_scene_transition_boundaries as boundaries
class SpawnSceneTransitionTests(unittest.TestCase):
 report={}
 def test_01_actual_make_and_image(self):type(self).report=p.prepare()
 def test_02_retail_guest(self):guest.main()
 def test_03_padders(self):pad.main()
 def test_04_caller(self):window.main()
 def test_05_native(self):native.main()
 def test_06_boundaries(self):boundaries.main()
