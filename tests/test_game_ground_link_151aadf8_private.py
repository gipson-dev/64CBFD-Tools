"""Three private gates; production C, guards, ELF and counts remain frozen."""
import unittest
from tools.experiments import game_ground_link_151aadf8_private as m
from tools.tests import game_ground_link_151aadf8_private_oracle as g
from tools.tests import game_ground_link_151aadf8_private_native as n
class GroundLinkPrivateTests(unittest.TestCase):
 def test_01_complete_owners_and_both_padders(self):m.prepare()
 def test_02_retail_and_three_guest_streams(self):g.main()
 def test_03_native_sdk32_profiles_and_controls(self):n.main()
if __name__=='__main__':unittest.main()
