"""Direct view fill, actual callbacks/providers and strict complete-image gates."""
import unittest
from tools.experiments import game_view_split_borders_151103c8_match as source
from tools.tests import game_view_split_borders_151103c8_oracle as guest
from tools.tests import game_view_split_borders_151103c8_native as native
from tools.tests import game_view_split_borders_151103c8_controls as controls
from tools.tests import game_view_split_borders_151103c8_boundaries as boundaries
from tools.tests import game_view_split_borders_151103c8_callers as callers
ROOT=source.ROOT
class ViewBordersTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_complete_owner_and_exact_image(self):
  self.assertEqual(self.report['image'],dict(changed_bytes=309,metadata_groups=[],strict_exclusions=0));self.assertEqual(self.report['actual_Make_commands'],5);self.assertEqual(self.report['non_target_neighbors'],33);self.assertEqual(self.report['guards'],0)
 def test_02_guest_float_prefixes_live_callbacks_and_machine(self):
  r=guest.main();self.assertEqual(r['cases'],474);self.assertEqual(r['coverage'],95);self.assertEqual(r['missing'],[]);self.assertEqual(r['complete_machine_and_trace_pairs'],474);self.assertEqual(r['invalid_conversion_prefixes'],28);self.assertTrue(r['unused_float_homes_checked'])
 def test_03_native_SDK32_typed_records_O0_O2_O3_UBSan(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==434 and v['exact_public_and_call_bytes']==1993432 and v['UBSan']and v['strict_aliasing']for v in r['profiles'].values()))
 def test_04_fifteen_completed_compiled_controls(self):
  r=controls.main();self.assertEqual(r['controls'],15);self.assertTrue(all(v['normal_completion']and v['execution_errors_before_witness']==0 for v in r['effective_compiled_controls'].values()))
 def test_05_padders_relocations_and_literal_fault_cuts(self):
  r=boundaries.main();self.assertEqual(r['padders']['word_and_binding_corruptions'],119);self.assertEqual(r['padders']['guards'],0);self.assertEqual(r['rebases']['executions'],64);self.assertEqual(r['rebases']['GNU_linker_comparisons'],16);self.assertEqual(r['faults']['exact_normalized_retail_access_cut_pairs'],154)
 def test_06_actual_callback_and_complete_graphics_helpers(self):
  r=callers.main();self.assertEqual(r['callback_pairs'],216);self.assertEqual(r['callback_window_words'],17);self.assertEqual(r['real_helpers']['pairs'],72);self.assertEqual(r['real_helpers']['covered_provider_words'],160);self.assertTrue(r['real_helpers']['independent_complete_command_packets']);self.assertFalse(r['full_parent_or_gameplay_qualified'])
 def test_07_eight_complete_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.symbol_rows(before)if v[1]==source.NAME)
  for at in[24,source.elf_slot_offset(before,source.ENTRY,380),source.elf_slot_offset(before,source.ENTRY+56*4,4),source.elf_slot_offset(before,0x15110544,4),source.elf_slot_offset(before,0x80082FA0,1),symbol[0]+4,symbol[0]+8,symbol[3]]:
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth})
 def test_08_closed_inputs_addresses_and_preserved_guards(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes());self.assertEqual((ROOT/'conker/Makefile').read_bytes(),(source.out/'frozen/conker/Makefile').read_bytes())
if __name__=='__main__':unittest.main()
