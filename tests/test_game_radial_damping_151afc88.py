"""Randomized descriptor: complete owner, FP role proof and bounded execution."""
import json
import unittest
from tools.experiments import game_radial_damping_151afc88_match as source
from tools.tests import game_radial_damping_151afc88_oracle as guest
from tools.tests import game_radial_damping_151afc88_native as native
from tools.tests import game_radial_damping_151afc88_caller as caller
from tools.tests import game_radial_damping_151afc88_proof as proof


class RadialDampingTests(unittest.TestCase):
    def record(self, name, report):
        (source.OUT / name).write_text(json.dumps(report, indent=2) + '\n')

    @classmethod
    def setUpClass(cls):
        cls.state = source.prepare()

    def test_01_objects_role_relation_and_guards(self):
        report = proof.main(self.state['raw_words'], self.state['retail_words'])
        self.assertEqual(report['different_words'], 10)
        self.assertEqual(len(report['negative_controls']), 3)
        self.assertEqual(source.guard_controls(), 60)

    def test_02_guest_reference_and_complete_state(self):
        report = guest.run(self.state)
        self.assertEqual((report['cases'], report['retail_words_visited']), (3072, 135))
        self.record('guest-report.json', report)

    def test_03_native32_and_fourteen_controls(self):
        report = native.run(self.state)
        self.assertEqual(set(report), {'-O0', '-O2', '-O3'})
        self.assertTrue(all(r == dict(cases=4096, negative_controls=14, UBSan=True) for r in report.values()))
        self.record('native-report.json', report)

    def test_04_original_dispatch_and_heading_home(self):
        report = caller.run(self.state)
        self.assertEqual(report['cases'], 80)
        self.assertEqual(guest.home_alias(self.state), [0xFFFF8001] * 3)
        self.record('caller-report.json', report)

    def test_05_connected_factory_and_copy(self):
        report = caller.factory(self.state)
        self.assertEqual(report['cases'], 80)
        self.assertEqual(report['words']['func_15130374'], 18)
        self.assertEqual(report['words']['memcpy'], 11)
        self.record('factory-report.json', report)

    def test_06_actual_Make_and_strict_image(self):
        report = source.qualify_image()
        self.assertEqual(report['image']['strict_exclusions'], 0)
        self.assertEqual(report['whole_image_controls_rejected'], 4)
        self.assertTrue(report['all_other_6050_bodies_and_all_addresses_unchanged'])


if __name__ == '__main__':
    unittest.main()
