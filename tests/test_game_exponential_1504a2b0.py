"""Qualification packet for the retail exponential approximation."""
import json
import unittest

from tools.experiments import game_exponential_1504a2b0_match as match
from tools.tests import game_exponential_1504a2b0_boundaries as boundaries
from tools.tests import game_exponential_1504a2b0_caller as caller
from tools.tests import game_exponential_1504a2b0_native as native
from tools.tests import game_exponential_1504a2b0_oracle as guest


class ExponentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = match.prepare()

    def receipt(self, name, result):
        (match.OUT/(name+'.json')).write_text(json.dumps(result, indent=2)+'\n')

    def test_owner_and_independent_padders(self):
        rows = match.MANIFEST['guard_rows']
        self.assertEqual(match.OUT.name, 'game-exponential-1504a2b0-match')
        self.assertEqual((len(rows), sum(bool(row['insert_after']) for row in rows)), (29,2))
        self.assertEqual(match.payload(self.state['retail']), match.payload(self.state['generated']))
        self.assertEqual(match.payload(self.state['retail']), match.payload(self.state['generic']))

    def test_finite_guest_model(self):
        self.receipt('guest', guest.run(self.state))

    def test_original_caller(self):
        self.receipt('caller', caller.run(self.state))

    def test_read_fault_prefixes(self):
        self.receipt('faults', boundaries.access_prefixes(self.state))

    def test_exceptional_instruction_prefixes(self):
        self.receipt('exceptional', boundaries.exceptional_prefixes(self.state))

    def test_relocations_and_independent_rebases(self):
        self.receipt('rebase', boundaries.rebase(self.state))

    def test_native_32bit(self):
        self.receipt('native', native.run(self.state))


if __name__ == '__main__':
    unittest.main(verbosity=2)
