"""Direct paired-float recovery, aliases, callers and full-image gates."""
import struct,unittest
from tools.experiments import game_paired_float_approach_1505a250_match as source
from tools.tests import game_paired_float_approach_1505a250_oracle as guest
from tools.tests import game_paired_float_approach_1505a250_native as native
from tools.tests import game_paired_float_approach_1505a250_controls as controls
from tools.tests import game_paired_float_approach_1505a250_boundaries as boundaries
from tools.tests import game_paired_float_approach_1505a250_callers as callers
ROOT=source.ROOT
class FloatPairApproachTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_direct_target_and_complete_image(self):
  self.assertEqual(self.report['image']['changed_bytes'],211);self.assertEqual(self.report['image']['strict_exclusions'],0);self.assertEqual(self.report['actual_Make_commands'],5);self.assertEqual(self.report['non_target_neighbors'],88);self.assertEqual(self.report['guards'],0)
 def test_02_guest_float_edges_aliases_and_complete_machine_state(self):
  r=guest.main();self.assertEqual(r['cases'],1479);self.assertEqual(r['coverage'],85);self.assertEqual(r['missing'],[75]);self.assertEqual(r['complete_machine_and_trace_pairs'],1479)
 def test_03_native_SDK32_strict_aliasing_O0_O2_O3_UBSan(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==1443 and v['exact_canonical_output_bytes']==63492 and v['UBSan']and v['strict_aliasing']for v in r['profiles'].values()))
 def test_04_seventeen_effective_compiled_controls(self):
  r=controls.main();self.assertEqual(r['controls'],17);self.assertTrue(all(v['normal_completion']and v['execution_errors']==0 for v in r['effective_compiled_controls'].values()))
 def test_05_padders_dead_word_rebases_and_fault_cuts(self):
  r=boundaries.main();self.assertEqual(r['CFG']['unreachable'],[75]);self.assertEqual(r['padders']['word_and_binding_corruptions'],88);self.assertEqual(r['padders']['guards'],0);self.assertEqual(r['rebases']['executions'],48);self.assertEqual(r['faults']['exact_access_cut_pairs'],89)
 def test_06_all_nine_original_argument_setup_windows(self):
  r=callers.main();self.assertEqual(r['executions'],2916);self.assertEqual(r['full_state_and_trace_pairs'],1458);self.assertEqual(r['total_window_words'],155);self.assertEqual(len(r['window_coverage']),9)
 def test_07_eight_complete_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[0x87700:0x87858];symbol=next(r for r in source.symbol_rows(before)if r[1]=='func_1505A250')
  for at in [24,source.elf_slot_offset(before,0x1505A250,344),source.elf_slot_offset(before,0x1505A250+75*4,4),source.elf_slot_offset(before,0x1505A3A8,548),source.elf_slot_offset(before,self.report['protected_data']['address'],1),symbol[0]+4,symbol[0]+8,symbol[3]]:
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{'func_1505A250':truth})
 def test_08_closed_live_inputs_addresses_guards_and_data(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
if __name__=='__main__':unittest.main()
