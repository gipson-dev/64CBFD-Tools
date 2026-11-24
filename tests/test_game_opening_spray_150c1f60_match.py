"""Focused complete constructor qualification, never helper matching credit."""
import unittest
from tools.experiments import game_opening_spray_150c1f60_match as p
from tools.experiments import game_opening_spray_150c1f60_make as make
from tools.experiments import game_opening_spray_150c1f60_image as image
from tools.experiments import game_opening_spray_150c1f60_qualification as qualification
from tools.tests import game_opening_spray_150c1f60_guest as guest
from tools.tests import game_opening_spray_150c1f60_native as native
class OpeningSprayTests(unittest.TestCase):
 def test_01_objects(self):p.objects()
 def test_02_guest(self):guest.main();guest.faults();guest.callers()
 def test_03_native(self):native.main()
 def test_04_boundaries(self):qualification.main()
 def test_05_make_and_image(self):make.main();image.main()
if __name__=='__main__':unittest.main()
