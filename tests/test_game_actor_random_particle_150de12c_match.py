"""Direct C, four emitted streams, real RNG, callback ABI and SDK32."""
import unittest
from tools.experiments import game_actor_random_particle_150de12c_match as packet
from tools.tests import game_actor_random_particle_150de12c_guest as guest
from tools.tests import game_actor_random_particle_150de12c_boundaries as boundaries
from tools.tests import game_actor_random_particle_150de12c_callers as callers
from tools.tests import game_actor_random_particle_150de12c_connected as connected
from tools.tests import game_actor_random_particle_150de12c_native as native
class ActorRandomParticle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=packet.qualify()
    def test_01_direct_owner_Make_and_complete_image(self):
        self.assertTrue(self.report['strict_predicted_ELF_equal'])
        self.assertEqual((self.report['words'],self.report['guards'],self.report['exclusions']),(94,0,0))
    def test_02_guest_and_both_padders_faults_rebases(self):
        guest.main();r=boundaries.main();self.assertEqual(r['GNU_rebased_links'],16)
    def test_03_six_argument_original_callback(self):
        r=callers.main();self.assertTrue(r['six_arguments_checked']and r['current_window_equals_original'])
    def test_04_original_64bit_random_helpers(self):
        r=connected.main();self.assertEqual(r['visited_rng_words'],43)
    def test_05_defined_SDK32_native_and_source_controls(self):native.main()
if __name__=='__main__':unittest.main(verbosity=2)
