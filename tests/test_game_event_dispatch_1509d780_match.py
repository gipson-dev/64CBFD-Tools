"""Semantic switch, exact pool, VM callback and strict complete-image gates."""
import unittest
from tools.experiments import game_event_dispatch_1509d780_match as source
from tools.tests import game_event_dispatch_1509d780_oracle as guest
from tools.tests import game_event_dispatch_1509d780_native as native
from tools.tests import game_event_dispatch_1509d780_controls as controls
from tools.tests import game_event_dispatch_1509d780_boundaries as boundaries
from tools.tests import game_event_dispatch_1509d780_callers as callers
ROOT=source.ROOT
class EventDispatchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_direct_target_pool_and_complete_image(self):
  self.assertEqual(self.report['image'],dict(changed_bytes=271,metadata_groups=[],strict_exclusions=0));self.assertEqual(self.report['actual_Make_commands'],3);self.assertEqual(self.report['non_target_neighbors'],18);self.assertEqual(self.report['guards'],0);self.assertEqual(self.report['switch_pool']['entries'],40)
 def test_02_guest_actions_aliases_and_complete_machine(self):
  r=guest.main();self.assertEqual(r['cases'],704);self.assertEqual(r['coverage'],95);self.assertEqual(r['missing'],[]);self.assertEqual(r['complete_machine_and_trace_pairs'],704);self.assertFalse(r['portable_C_fallthrough_results_qualified'])
 def test_03_native_SDK32_O0_O2_O3_UBSan_and_discarded_results(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==680 and v['exact_public_and_call_bytes']==80364 and v['UBSan']and not v['strict_aliasing']and v['fallthrough_results_discarded']for v in r['profiles'].values()))
 def test_04_seventeen_effective_compiled_controls(self):
  r=controls.main();self.assertEqual(r['controls'],17);self.assertTrue(all(v['normal_completion']and v['execution_errors_before_witness']==0 for v in r['effective_compiled_controls'].values()))
 def test_05_padders_all_pool_destinations_rebases_and_fault_cuts(self):
  r=boundaries.main();self.assertEqual(r['padders']['word_and_binding_corruptions'],115);self.assertEqual(r['padders']['pool_entry_corruptions'],40);self.assertEqual(r['padders']['guards'],0);self.assertEqual(r['rebases']['executions'],80);self.assertEqual(r['rebases']['GNU_linker_comparisons'],16);self.assertEqual(r['faults']['exact_access_cut_pairs'],25)
 def test_06_original_VM_publication_and_real_lookup(self):
  r=callers.main();self.assertEqual(r['VM_pairs'],368);self.assertEqual(r['VM_window_covered_words'],42);self.assertEqual(r['real_lookup_pairs'],624);self.assertEqual(r['real_lookup_covered_words'],52);self.assertTrue(r['VM_result_publication_checked']);self.assertFalse(r['ABI']['original_C_return_type_proven']);self.assertFalse(r['full_VM_or_effect_helpers_qualified'])
 def test_07_eight_complete_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.symbol_rows(before)if v[1]==source.NAME)
  for at in[24,source.elf_slot_offset(before,source.ENTRY,380),source.elf_slot_offset(before,source.ENTRY+24*4,4),source.elf_slot_offset(before,0x1509D8FC,4),source.elf_slot_offset(before,0x8009F1AC,1),symbol[0]+4,symbol[0]+8,symbol[3]]:
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth})
 def test_08_closed_live_inputs_addresses_guards_and_binding(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes());old=(source.out/'frozen/conker/Makefile').read_text();new=(source.out/'proposed-Makefile').read_text();line='$(BUILD_DIR)/$(SRC_DIR)/game/generated_C9EC0.c.o: RETAIL_RODATA_SYMBOL := jtbl_8009F1AC_game'+chr(10);self.assertEqual(new.replace(line,''),old)
if __name__=='__main__':unittest.main()
