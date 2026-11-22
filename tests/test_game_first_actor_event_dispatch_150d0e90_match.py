"""Direct words, ordered guest events, callback ABI, padding and SDK32."""
import unittest
from tools.experiments import game_first_actor_event_dispatch_150d0e90_match as packet
from tools.tests import game_first_actor_event_dispatch_150d0e90_guest as guest
from tools.tests import game_first_actor_event_dispatch_150d0e90_boundaries as boundaries
from tools.tests import game_first_actor_event_dispatch_150d0e90_callers as callers
from tools.tests import game_first_actor_event_dispatch_150d0e90_native as native
class FirstActorEventDispatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_direct_owner_and_literal_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal'])
  self.assertEqual((self.report['words'],self.report['guards'],self.report['exclusions']),(149,0,0))
  self.assertEqual(self.report['unchanged_owner_functions'],4)
 def test_02_ordered_guest_lookup_and_faults(self):self.assertEqual(guest.main()['lookup_words_executed'],28)
 def test_03_both_padders_and_GNU_links(self):self.assertEqual(boundaries.main()['GNU_rebased_links'],16)
 def test_04_current_frame_dispatcher_and_callback_ABI(self):self.assertEqual(callers.main()['dispatcher_words_executed'],43)
 def test_05_SDK32_and_effective_source_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),10)
if __name__=='__main__':unittest.main(verbosity=2)
