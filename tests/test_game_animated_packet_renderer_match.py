import unittest
from tools.experiments import game_animated_packet_renderer_match as p
from tools.tests import game_animated_packet_renderer_guest as guest, game_animated_packet_renderer_native as native, game_animated_packet_renderer_pad as pad, game_animated_packet_renderer_guards as guards, game_animated_packet_renderer_window as window, game_animated_packet_renderer_boundaries as boundaries
class AnimatedPacketTests(unittest.TestCase):
 report={}
 def test_01_actual_make_and_image(self):type(self).report=p.prepare()
 def test_02_retail_guest(self):guest.main()
 def test_03_padders(self):pad.main()
 def test_04_guards(self):guards.main()
 def test_05_caller(self):window.main()
 def test_06_native(self):native.main()
 def test_07_boundaries(self):boundaries.main()
