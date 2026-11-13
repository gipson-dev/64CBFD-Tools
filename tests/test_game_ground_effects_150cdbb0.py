"""Qualification packet for the ground-height effect dispatcher."""
import json
import unittest

from tools.experiments import game_ground_effects_150cdbb0_match as match
from tools.tests import game_ground_effects_150cdbb0_connected as connected
from tools.tests import game_ground_effects_150cdbb0_native as native
from tools.tests import game_ground_effects_150cdbb0_oracle as guest
from tools.tests import game_ground_effects_150cdbb0_rebase as rebase


class GroundEffectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state=match.prepare()

    def receipt(self,name,result):
        (match.OUT/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')

    def test_owner_and_independent_padders(self):
        rows=match.MANIFEST['guard_rows']
        self.assertEqual(match.OUT.name,'game-ground-effects-150cdbb0-match')
        self.assertEqual((len(rows),sum(bool(row['insert_after']) for row in rows)),(4,1))
        self.assertEqual(match.payload(self.state['retail']),match.payload(self.state['generated']))
        self.assertEqual(match.payload(self.state['retail']),match.payload(self.state['generic']))

    def test_guest_model(self):self.receipt('guest',guest.run(self.state))
    def test_actual_rng(self):self.receipt('rng',connected.connected_rng(self.state))
    def test_original_caller(self):self.receipt('caller',connected.caller(self.state))
    def test_access_fault_prefixes(self):self.receipt('faults',connected.faults(self.state))
    def test_native_32bit(self):self.receipt('native',native.run(self.state))
    def test_independent_rebases(self):self.receipt('rebase',rebase.run(self.state))


if __name__=='__main__':unittest.main(verbosity=2)
