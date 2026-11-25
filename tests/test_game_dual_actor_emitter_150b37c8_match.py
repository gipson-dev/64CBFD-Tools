import unittest
from tools.experiments import game_dual_actor_emitter_150b37c8_match as packet,game_dual_actor_emitter_150b37c8_make as make,game_dual_actor_emitter_150b37c8_image as image
from tools.tests import game_dual_actor_emitter_150b37c8_guest as guest,game_dual_actor_emitter_150b37c8_boundaries as boundaries,game_dual_actor_emitter_150b37c8_callers as callers,game_dual_actor_emitter_150b37c8_helpers as helpers,game_dual_actor_emitter_150b37c8_native as native
class DualActorEmitterTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(184,85,5));self.assertEqual(make.main()['commands'],3);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertEqual(guest.main()['executed_words'],184)
 def test_03_slot_limits_and_GNU(self):self.assertEqual(boundaries.main()['binding_pins'],10)
 def test_04_original_registry_and_helpers(self):
  self.assertEqual(callers.main()['original_parent_cases'],384);self.assertEqual(helpers.main()['original_rng_words_executed'],43)
 def test_05_native_SDK32_and_effective_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),17)
if __name__=='__main__':unittest.main()
