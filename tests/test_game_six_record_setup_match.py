import unittest
from tools.experiments import game_six_record_setup_match as p
from tools.tests import game_six_record_setup_guest as guest, game_six_record_setup_native as native, game_six_record_setup_pad as pad, game_six_record_setup_window as window, game_six_record_setup_boundaries as boundaries
class SixRecordSetupTests(unittest.TestCase):
 report={}
 def test_01_actual_make_and_image(self):type(self).report=p.prepare()
 def test_02_retail_guest(self):guest.main()
 def test_03_padders(self):pad.main()
 def test_04_caller(self):window.main()
 def test_05_native(self):native.main()
 def test_06_boundaries(self):boundaries.main()
