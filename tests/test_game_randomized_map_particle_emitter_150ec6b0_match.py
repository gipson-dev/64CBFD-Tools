"""Complete randomized emitter qualification with explicit normalization limits."""
import unittest
from tools.experiments import game_randomized_map_particle_emitter_150ec6b0_match as packet
from tools.tests import game_randomized_map_particle_emitter_150ec6b0_guest as guest
from tools.tests import game_randomized_map_particle_emitter_150ec6b0_faults as faults
from tools.tests import game_randomized_map_particle_emitter_150ec6b0_callers as callers
from tools.tests import game_randomized_map_particle_emitter_150ec6b0_connected as connected
from tools.tests import game_randomized_map_particle_emitter_150ec6b0_native as native
class RandomizedMapParticleEmitter(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_owner_and_literal_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal'])
  self.assertEqual((self.report['raw_words'],self.report['normalized_words'],self.report['guards'],self.report['exclusions']),(237,238,19,0))
 def test_02_ordered_guest_packets(self):self.assertEqual(guest.main()['cases_per_stream'],979)
 def test_03_both_padders_and_GNU_links(self):
  report=packet.normalize();self.assertTrue(report['both_padders_equal']);self.assertEqual(report['GNU_links'],8)
 def test_04_access_fault_prefixes(self):self.assertEqual(faults.main()['access_fault_pairs'],424)
 def test_05_callback_ABI(self):self.assertEqual(callers.main()['cases_per_stream'],192)
 def test_06_original_providers(self):self.assertEqual(connected.main()['cases_per_stream'],1728)
 def test_07_SDK32_and_source_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),8)
if __name__=='__main__':unittest.main(verbosity=2)
