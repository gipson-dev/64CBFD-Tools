import unittest
from tools.experiments import game_actor_colored_dispatch_match as p
from tools.tests import game_actor_colored_dispatch_mixed as mixed, game_actor_colored_dispatch_guest as guest, game_actor_colored_dispatch_native as native, game_actor_colored_dispatch_window as window, game_actor_colored_dispatch_window2 as window2, game_actor_colored_dispatch_boundaries as boundaries, game_actor_colored_dispatch_table_controls as table_controls
class ActorColoredDispatchTests(unittest.TestCase):
 report={}
 def test_01_mixed_padders(self):mixed.main()
 def test_02_actual_make_and_image(self):type(self).report=p.prepare()
 def test_03_guest(self):guest.main()
 def test_04_native(self):native.main()
 def test_05_caller_one(self):window.main()
 def test_06_caller_two(self):window2.main()
 def test_07_boundaries(self):boundaries.main()
 def test_08_table_controls(self):table_controls.main()
