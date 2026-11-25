import unittest
from tools.experiments import game_random_particle_150b5e34_match as packet,game_random_particle_150b5e34_make as make,game_random_particle_150b5e34_image as image
from tools.tests import game_random_particle_150b5e34_guest as guest,game_random_particle_150b5e34_boundaries as boundaries,game_random_particle_150b5e34_callers as callers,game_random_particle_150b5e34_helpers as helpers,game_random_particle_150b5e34_native as native
class RandomParticleTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(115,21,11));self.assertEqual(make.main()['commands'],3);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertTrue(guest.main()['all115_words_visited'])
 def test_03_slot_limits_and_GNU(self):self.assertEqual(boundaries.main()['binding_pins'],5)
 def test_04_original_callers_and_factory(self):
  self.assertEqual(callers.main()['cases_per_stream'],392);self.assertEqual(helpers.main()['cases'],128)
 def test_05_native_SDK32_and_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),11)
if __name__=='__main__':unittest.main()
