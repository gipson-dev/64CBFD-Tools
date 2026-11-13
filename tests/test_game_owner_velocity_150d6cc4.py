"""Qualification checks for func_150D6CC4's private or installed C body."""
import json,unittest
from tools.experiments import game_owner_velocity_150d6cc4_match as match
from tools.tests import game_owner_velocity_150d6cc4_oracle as guest
from tools.tests import game_owner_velocity_150d6cc4_alias as alias
from tools.tests import game_owner_velocity_150d6cc4_connected as connected
from tools.tests import game_owner_velocity_150d6cc4_faults as faults
from tools.tests import game_owner_velocity_150d6cc4_native as native

class OwnerVelocityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.state=match.prepare()
    def receipt(self,name,result):(match.OUT/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    def test_owner_and_independent_padders(self):
        self.assertEqual(match.OUT.name, 'game-owner-velocity-150d6cc4-match')
        rows=match.MANIFEST['guard_rows']
        self.assertEqual((len(rows),sum(bool(row['insert_after']) for row in rows)),(7,0))
        self.assertEqual(match.payload(self.state['generated']),match.payload(self.state['generic']))
    def test_guest_with_modeled_helpers(self):self.receipt('guest',guest.run(self.state))
    def test_owner_target_aliases(self):self.receipt('alias',alias.run(self.state))
    def test_original_helpers(self):self.receipt('helpers',connected.real_helpers(self.state))
    def test_callback_table_caller(self):self.receipt('caller',connected.caller(self.state))
    def test_access_fault_prefixes(self):self.receipt('faults',faults.run(self.state))
    def test_native_32bit(self):self.receipt('native',native.run(self.state))

if __name__=='__main__':unittest.main(verbosity=2)
