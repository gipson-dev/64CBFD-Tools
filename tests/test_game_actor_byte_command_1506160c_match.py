"""Focused adoption gates, including all affected shared-ABI callers."""
import json,struct,unittest
from tools.experiments import game_actor_byte_command_1506160c_match as packet
from tools.tests import game_actor_byte_command_1506160c_guest as guest
from tools.tests import game_actor_byte_command_1506160c_native as native
from tools.tests import game_actor_byte_command_1506160c_callers as callers
from tools.tests import game_actor_byte_command_1506160c_packed_caller as packed
from tools.tests import game_actor_byte_command_1506160c_selector_caller as selector
from tools.tests import game_actor_byte_command_1506160c_boundaries as boundaries
from tools.tests import game_actor_byte_command_1506160c_caller_boundaries as caller_boundaries
from tools.tests import game_actor_byte_command_1506160c_symbolic as symbolic
class ActorByteCommand(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_owner_headers_and_literal_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['exclusions'],0)
  self.assertEqual((self.report['words'],self.report['qualified_header_consumers']),(108,214))
 def test_02_guest_access_and_fault_states(self):
  r=guest.main();self.assertEqual(r['cases_per_stream'],21528);self.assertEqual(r['access_fault_pairs'],46)
 def test_03_SDK32_and_source_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),10)
 def test_04_original_forwarding_caller(self):self.assertEqual(callers.main()['cases_per_stream'],4096)
 def test_05_packed_caller_and_symbolic_bits(self):
  self.assertEqual(packed.main()['cases_per_layout'],2048)
  raw=json.loads((packet.OUT/'wrapper-words.json').read_text());truth=list(struct.unpack_from('>17I',(packet.ROOT/'conker/conker.us.bin').read_bytes(),0x9F654))
  self.assertEqual(symbolic.proof(raw),symbolic.proof(truth));raw[9]^=64
  with self.assertRaises(AssertionError):symbolic.proof(raw)
 def test_06_complete_selector_caller(self):self.assertEqual(selector.main()['cases_per_layout'],2560)
 def test_07_both_target_padders_and_rebases(self):self.assertEqual(boundaries.main()['GNU_links'],16)
 def test_08_changed_caller_guards_and_rebases(self):
  r=caller_boundaries.main();self.assertEqual(r['GNU_links'],24);self.assertEqual(r['effective_malformed_controls'],8)
if __name__=='__main__':unittest.main(verbosity=2)
