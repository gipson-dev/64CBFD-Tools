"""Direct particle accumulation, packets, callback ABI, padding and SDK32."""
import unittest
from tools.experiments import game_particle_emission_accumulator_150ec520_match as packet
from tools.tests import game_particle_emission_accumulator_150ec520_guest as guest
from tools.tests import game_particle_emission_accumulator_150ec520_boundaries as boundaries
from tools.tests import game_particle_emission_accumulator_150ec520_callers as callers
from tools.tests import game_particle_emission_accumulator_150ec520_connected as connected
from tools.tests import game_particle_emission_accumulator_150ec520_native as native
class ParticleEmissionAccumulator(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_direct_owner_and_literal_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal'])
  self.assertEqual((self.report['words'],self.report['guards'],self.report['exclusions']),(100,0,0))
  self.assertEqual(self.report['unchanged_owner_functions'],6)
 def test_02_ordered_guest_packets_and_faults(self):self.assertEqual(guest.main()['target_executed_words'],99)
 def test_03_both_padders_and_GNU_links(self):self.assertEqual(boundaries.main()['GNU_rebased_links'],16)
 def test_04_callback_ABI_and_original_providers(self):
  self.assertEqual(callers.main()['original_call_window_words'],45)
  self.assertEqual(connected.main()['provider_executed_words']['0x151464b8'],20)
 def test_05_SDK32_and_effective_source_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),10)
if __name__=='__main__':unittest.main(verbosity=2)
