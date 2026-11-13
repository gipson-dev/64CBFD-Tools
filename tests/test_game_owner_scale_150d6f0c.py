"""Qualification checks for func_150D6F0C's private or installed C body."""
import json,unittest
from tools.experiments import game_owner_scale_150d6f0c_match as match
from tools.tests import game_owner_scale_150d6f0c_oracle as guest
from tools.tests import game_owner_scale_150d6f0c_alias as alias
from tools.tests import game_owner_scale_150d6f0c_connected as connected
from tools.tests import game_owner_scale_150d6f0c_faults as faults
from tools.tests import game_owner_scale_150d6f0c_native as native

class OwnerScaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.state=match.prepare()
    def receipt(self,name,result):(match.OUT/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    def test_owner_and_independent_padders(self):
        rows=match.MANIFEST['guard_rows']
        self.assertEqual((len(rows),sum(bool(row['insert_after']) for row in rows)),(10,0))
        self.assertEqual(match.payload(self.state['generated']),match.payload(self.state['generic']))
    def test_guest_with_modeled_helper(self):self.receipt('guest',guest.run(self.state))
    def test_owner_target_aliases(self):self.receipt('alias',alias.run(self.state))
    def test_original_helper(self):self.receipt('helper',connected.real_helper(self.state))
    def test_callback_table_caller(self):self.receipt('caller',connected.caller(self.state))
    def test_access_fault_prefixes(self):self.receipt('faults',faults.run(self.state))
    def test_native_32bit(self):self.receipt('native',native.run(self.state))

if __name__=='__main__':unittest.main(verbosity=2)
