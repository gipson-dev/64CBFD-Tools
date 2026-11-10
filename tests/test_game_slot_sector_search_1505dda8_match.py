"""Direct slot-sector recovery, typed helpers, callers and full-image gates."""
import unittest
from tools.experiments import game_slot_sector_search_1505dda8_match as source
from tools.tests import game_slot_sector_search_1505dda8_oracle as guest
from tools.tests import game_slot_sector_search_1505dda8_native as native
from tools.tests import game_slot_sector_search_1505dda8_controls as controls
from tools.tests import game_slot_sector_search_1505dda8_boundaries as boundaries
from tools.tests import game_slot_sector_search_1505dda8_callers as callers
ROOT=source.ROOT
class SlotSectorSearchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_direct_target_and_complete_image(self):
  self.assertEqual(self.report['image']['changed_bytes'],282);self.assertEqual(self.report['image']['strict_exclusions'],0);self.assertEqual(self.report['actual_Make_commands'],5);self.assertEqual(self.report['non_target_neighbors'],88);self.assertEqual(self.report['guards'],0)
 def test_02_guest_float_edges_aliases_and_complete_machine_state(self):
  r=guest.main();self.assertEqual(r['cases'],886);self.assertEqual(r['coverage'],88);self.assertEqual(r['missing'],[58,59]);self.assertEqual(r['complete_machine_and_trace_pairs'],886)
 def test_03_native_SDK32_strict_aliasing_O0_O2_O3_UBSan(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==846 and v['exact_public_and_call_bytes']==817492 and v['UBSan']and v['strict_aliasing']for v in r['profiles'].values()))
 def test_04_seventeen_effective_compiled_controls(self):
  r=controls.main();self.assertEqual(r['controls'],17);self.assertTrue(all(v['normal_completion']and v['execution_errors']==0 for v in r['effective_compiled_controls'].values()))
 def test_05_padders_dead_words_rebases_and_fault_cuts(self):
  r=boundaries.main();self.assertEqual(r['CFG']['unreachable'],[58,59]);self.assertEqual(r['padders']['word_and_binding_corruptions'],97);self.assertEqual(r['padders']['guards'],0);self.assertEqual(r['rebases']['executions'],48);self.assertEqual(r['faults']['exact_access_cut_pairs'],216)
 def test_06_real_float_helper_and_all_three_call_sites(self):
  r=callers.main();self.assertEqual(r['connected_target_and_parent_executions'],2592);self.assertEqual(r['complete_machine_and_trace_pairs'],1296);self.assertEqual(r['real_helper_words'],51);self.assertEqual(r['parent_window_words'],8);self.assertEqual(r['helper_caller_executions'],216);self.assertEqual(sum(r['helper_caller_window_words'].values()),29)
 def test_07_eight_complete_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(r for r in source.symbol_rows(before)if r[1]==source.NAME)
  for at in [24,source.elf_slot_offset(before,source.ENTRY,360),source.elf_slot_offset(before,source.ENTRY+58*4,4),source.elf_slot_offset(before,0x1505DF10,204),source.elf_slot_offset(before,self.report['protected_data']['address'],1),symbol[0]+4,symbol[0]+8,symbol[3]]:
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth})
 def test_08_closed_live_inputs_addresses_guards_and_data(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
if __name__=='__main__':unittest.main()
