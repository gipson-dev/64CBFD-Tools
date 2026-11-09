"""Behavioral qualification without installing or crediting a frame mismatch."""
import struct,unittest
from tools.experiments import game_resource_maintenance_1510d404_candidates as source
from tools.tests import game_resource_maintenance_1510d404_oracle as guest
from tools.tests import game_resource_maintenance_1510d404_native as native
from tools.tests import game_resource_maintenance_1510d404_controls as controls
ROOT=source.ROOT
class MaintenanceCandidateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_measured_candidates_and_wide_frame_rejection(self):
  self.assertEqual(self.report['matching_credit'],0);self.assertFalse(self.report['installed']);self.assertTrue(self.report['wide_frame_fit_rejected'])
  self.assertEqual(self.report['variants']['counter']['frame'],64);self.assertEqual(self.report['retail_frame'],96)
 def test_02_independent_guest_contract_and_rebases(self):guest.main()
 def test_03_native_contracts_and_effective_controls(self):native.main()
 def test_04_compiled_ido_controls(self):controls.main()
 def test_05_actual_void_caller_interface(self):
  root=ROOT;rom=(root/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>4I',rom,0x46174)
  self.assertEqual(words,(0x0C000000|((source.ENTRY>>2)&0x03FFFFFF),0,0x0C000000|((0x15114A1C>>2)&0x03FFFFFF),0))
  text=(root/'conker/src/game_45B80.c').read_text();self.assertIn('void func_1510D404(void);',text);self.assertIn('func_1510D404();',text)
 def test_06_frozen_production_inputs_unchanged(self):self.assertEqual(source.freeze(ROOT,ROOT/source.BUILD),source.FROZEN)
if __name__=='__main__':unittest.main()
