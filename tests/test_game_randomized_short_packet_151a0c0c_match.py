"""Complete source, instruction, caller, native and symbolic qualification."""
import unittest
from tools.experiments import game_randomized_short_packet_151a0c0c_match as m
class RandomizedShortPacketTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.main()
 def test_guest_packet_and_provider_order(self):
  from tools.tests import game_randomized_short_packet_151a0c0c_oracle as g
  g.main();m.check_inputs()
 def test_native32_defined_fields_and_controls(self):
  from tools.tests import game_randomized_short_packet_151a0c0c_native as native
  native.main();m.check_inputs()
 def test_original_indirect_parents(self):
  from tools.tests import game_randomized_short_packet_151a0c0c_callers as callers
  callers.main();m.check_inputs()
 def test_whole_function_ordered_FP_and_storage(self):
  from tools.tests import game_randomized_short_packet_151a0c0c_proof as proof
  proof.main();m.check_inputs()
if __name__=='__main__':unittest.main()
