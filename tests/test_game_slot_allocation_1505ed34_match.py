"""Direct allocation source, all five consumers, real helper paths and strict image."""
import unittest
from tools.experiments import game_slot_allocation_1505ed34_match as source
from tools.tests import game_slot_allocation_1505ed34_oracle as guest
from tools.tests import game_slot_allocation_1505ed34_native as native
from tools.tests import game_slot_allocation_1505ed34_controls as controls
from tools.tests import game_slot_allocation_1505ed34_boundaries as boundaries
from tools.tests import game_slot_allocation_1505ed34_callers as callers
ROOT=source.ROOT
class SlotAllocationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_direct_target_and_complete_image(self):
  self.assertEqual(self.report['image'],dict(changed_bytes=267,metadata_groups=[],strict_exclusions=0));self.assertEqual(self.report['actual_Make_commands'],5);self.assertEqual(self.report['non_target_neighbors'],88);self.assertEqual(self.report['guards'],0)
 def test_02_guest_priorities_effects_and_complete_machine(self):
  r=guest.main();self.assertEqual(r['cases'],348);self.assertEqual(r['coverage'],95);self.assertEqual(r['missing'],[]);self.assertEqual(r['complete_machine_and_trace_pairs'],348);self.assertEqual(r['sparse_short_circuit_cases'],8)
 def test_03_native_SDK32_strict_aliasing_O0_O2_O3_UBSan(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==340 and v['exact_public_and_call_bytes']==7194224 and v['UBSan']and v['strict_aliasing']for v in r['profiles'].values()))
 def test_04_fourteen_effective_compiled_controls(self):
  r=controls.main();self.assertEqual(r['controls'],14);self.assertTrue(all(v['normal_completion']and v['execution_errors_before_witness']==0 for v in r['effective_compiled_controls'].values()))
 def test_05_padders_field_alias_rebases_and_fault_cuts(self):
  r=boundaries.main();self.assertEqual(r['padders']['word_and_binding_corruptions'],109);self.assertEqual(r['padders']['guards'],0);self.assertEqual(r['rebases']['executions'],64);self.assertEqual(r['rebases']['GNU_linker_comparisons'],16);self.assertEqual(r['faults']['exact_access_cut_pairs'],341)
 def test_06_all_five_original_consumers_and_real_helper_paths(self):
  r=callers.main();self.assertEqual(r['caller_pairs'],150);self.assertEqual(sum(r['caller_window_words'].values()),73);self.assertEqual(r['real_helper_pairs'],80);self.assertEqual(r['real_helper_covered_words'],152);self.assertTrue(r['initializer_called_twice_after_real_cleanup']);self.assertFalse(r['full_parent_or_callee_algorithms_qualified'])
 def test_07_eight_complete_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.symbol_rows(before)if v[1]==source.NAME)
  for at in[24,source.elf_slot_offset(before,source.ENTRY,380),source.elf_slot_offset(before,source.ENTRY+24*4,4),source.elf_slot_offset(before,0x1505EEB0,4),source.elf_slot_offset(before,self.report['protected_data']['address'],1),symbol[0]+4,symbol[0]+8,symbol[3]]:
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth})
 def test_08_closed_live_inputs_addresses_guards_and_data(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
if __name__=='__main__':unittest.main()
