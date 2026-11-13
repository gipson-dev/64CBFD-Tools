"""Qualification checks for the paired random-effect wrapper conversions."""
import json
import unittest

from tools.experiments import game_random_effect_pair_150d6388_match as match
from tools.tests import game_random_effect_pair_150d6388_boundaries as boundaries
from tools.tests import game_random_effect_pair_150d6388_connected as connected
from tools.tests import game_random_effect_pair_150d6388_native as native
from tools.tests import game_random_effect_pair_150d6388_oracle as guest


class RandomEffectPairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = match.prepare()

    def receipt(self, name, result):
        (match.OUT / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n')

    def test_owner_and_independent_padders(self):
        self.assertEqual(match.OUT.name, 'game-random-effect-pair-150d6388-match')
        for name in match.NAMES:
            self.assertEqual(match.payload(self.state['generated'], name),
                             match.payload(self.state['generic'], name))
            self.assertEqual(match.payload(self.state['generated'], name),
                             match.payload(self.state['retail'][name], name))

    def test_guest_with_modeled_helpers(self):
        self.receipt('guest', guest.run(self.state))

    def test_nonfinite_model(self):
        self.receipt('nonfinite', boundaries.nonfinite(self.state))

    def test_access_fault_prefixes(self):
        self.receipt('faults', boundaries.faults(self.state))

    def test_original_rng(self):
        self.receipt('rng', connected.real_rng(self.state))

    def test_original_caller(self):
        self.receipt('caller', connected.caller(self.state))

    def test_native_32bit(self):
        self.receipt('native', native.run(self.state))


if __name__ == '__main__':
    unittest.main(verbosity=2)
