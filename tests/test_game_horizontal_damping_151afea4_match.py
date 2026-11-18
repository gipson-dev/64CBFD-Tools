"""Complete direct-C horizontal damping qualification and linked prediction."""
import unittest
from tools.experiments import game_horizontal_damping_151afea4_match as source
from tools.tests import game_horizontal_damping_151afea4_guest as guest
from tools.tests import game_horizontal_damping_151afea4_native as native


class HorizontalDampingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = source.qualify_source()

    def test_01_owner_padders_and_rebases(self):
        report = source.padders()
        self.assertEqual(report['gnu_links'], 12)
        self.assertEqual(report['source_binding_corruptions_rejected'], 108)
        self.assertEqual(self.source['neighbors_unchanged'], 6)
        self.assertEqual((self.source['guards'], self.source['insertions'], self.source['omissions']), (0, 0, 0))
        guest.prepare()

    def test_02_guest_and_access_boundaries(self):
        self.assertEqual(guest.guest()['retail_words_visited'], 106)
        self.assertEqual(guest.boundaries()['high_tick_prefix_cuts'], 240)

    def test_03_native32_with_controls(self):
        report = native.main()
        self.assertEqual(set(report['profiles']), {'-O0', '-O2', '-O3'})
        self.assertTrue(all(r == dict(cases=440, rejected_controls=6, UBSan=True) for r in report['profiles'].values()))

    def test_04_complete_caller_selected_paths(self):
        report = guest.caller()
        self.assertEqual(report['cases_per_stream'], 80)
        self.assertEqual(report['callback_index'], 6)
        self.assertTrue(report['return_zero_control_reaches_release'])

    def test_05_actual_Make_and_strict_full_image(self):
        report = source.qualify_image()
        self.assertEqual(report['image']['strict_exclusions'], 0)
        self.assertEqual(report['whole_image_controls_rejected'], 4)
        self.assertTrue(report['all_other_6050_bodies_and_all_addresses_unchanged'])


if __name__ == '__main__':
    unittest.main()
