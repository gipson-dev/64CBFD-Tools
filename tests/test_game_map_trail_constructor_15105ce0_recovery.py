"""Private constructor screen and bounded guest semantics, without adoption."""
import json
import struct
import unittest
from tools.experiments import game_map_trail_constructor_15105ce0_recovery as source
from tools.tests import game_map_trail_constructor_15105ce0_oracle as guest
from tools.tests.game_map_trail_constructor_15105ce0_native import run as native

class ConstructorRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=source.screen()
        raw,refs=source.payload(source.OUT/'screen/candidate.o',source.FUNCTION)
        symbols={'memcpy':guest.COPY,'bzero':guest.ZERO}
        for rows in refs.values():
            for _,name in rows:
                if name not in symbols:symbols[name]=int(name.split('_')[1],16)
        cls.words=source.bound_blob(raw,refs,symbols)
        cls.retail=struct.unpack_from('>235I',(source.ROOT/'conker/conker.us.bin').read_bytes(),source.ROM)
    def test_01_private_shape_and_all_owner_neighbors(self):
        self.assertEqual((self.receipt['words'],self.receipt['frame'],self.receipt['unchanged_neighbors']), (233,216,36))
        self.assertTrue(self.receipt['pools_unchanged'])
        self.assertEqual(self.receipt['credit'],0)
        self.assertIn(source.STUB,(source.ROOT/source.SOURCE).read_text())
    def test_02_guest_packets_reload_boundaries_and_callee_lifetimes(self):
        result=guest.run(self.words,self.retail)
        (source.OUT/'guest-report.json').write_text(json.dumps(result,indent=2)+'\n')
        self.assertEqual(result['cases'],512)
    def test_03_native_SDK32_and_effective_semantic_controls(self):
        result=native(source,guest)
        self.assertEqual((result['cases_each_profile'],result['profiles'],result['controls']),(512,3,8))
    def test_04_literal_ROM_caller_census(self):
        result=source.caller_census()
        self.assertEqual(len(result['direct_JALs']),4)
        (source.OUT/'caller-census.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':unittest.main()
