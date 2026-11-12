import unittest
from tools.experiments import game_paired_packet_constructors_match as p
from tools.tests import game_paired_packet_constructors_guest as guest, game_paired_packet_constructors_native as native, game_paired_packet_constructors_pad as pad, game_paired_packet_constructors_guards as guards, game_paired_packet_constructors_window as window, game_paired_packet_constructors_boundaries as boundaries
class PairedPacketTests(unittest.TestCase):
 report={}
 def test_01_actual_make_and_image(self):type(self).report=p.prepare()
 def test_02_retail_guest(self):guest.main()
 def test_03_padders(self):pad.main()
 def test_04_guards(self):guards.main()
 def test_05_caller(self):window.main()
 def test_06_native(self):native.main()
 def test_07_boundaries(self):boundaries.main()
