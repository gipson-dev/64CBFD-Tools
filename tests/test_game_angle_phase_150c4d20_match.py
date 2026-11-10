"""Angular update, callback ABI, guarded schedule and complete image gates."""
import unittest
from tools.experiments import game_angle_phase_150c4d20_match as source
from tools.tests import game_angle_phase_150c4d20_oracle as guest
from tools.tests import game_angle_phase_150c4d20_native as native
from tools.tests import game_angle_phase_150c4d20_controls as controls
from tools.tests import game_angle_phase_150c4d20_boundaries as boundaries
from tools.tests import game_angle_phase_150c4d20_callers as callers
ROOT=source.ROOT
class AnglePhaseTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_owner_pool_and_complete_image(self):
  self.assertEqual(self.report['image'],source.MANIFEST['image']);self.assertEqual(self.report['image']['changed_bytes'],325);self.assertEqual(self.report['image']['strict_exclusions'],0);self.assertEqual(self.report['actual_Make_commands'],3);self.assertEqual(self.report['non_target_neighbors'],5);self.assertEqual(self.report['guards'],6)
 def test_02_guest_float_cases_mutations_aliases_and_machine(self):
  r=guest.main();self.assertEqual(r['cases'],844);self.assertEqual(r['coverage'],94);self.assertEqual(r['missing'],[84]);self.assertEqual(r['raw_normal_final_pairs'],844);self.assertEqual(r['normalized_retail_machine_trace_pairs'],844);self.assertEqual(r['invalid_conversion_prefixes'],0)
 def test_03_native_SDK32_typed_records_O0_O2_O3_UBSan(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==832 and v['exact_public_and_call_bytes']==177664 and v['UBSan']and v['strict_aliasing']for v in r['profiles'].values()))
 def test_04_fourteen_completed_compiled_controls(self):
  r=controls.main();self.assertEqual(r['controls'],14);self.assertTrue(all(v['normal_completion']and v['execution_errors_before_witness']==0 for v in r['effective_compiled_controls'].values()))
 def test_05_both_padders_relocations_and_fault_cuts(self):
  r=boundaries.main();self.assertEqual(r['padders']['word_and_binding_corruptions'],105);self.assertEqual(r['padders']['guards'],6);self.assertEqual(r['rebases']['executions'],64);self.assertEqual(r['rebases']['GNU_linker_comparisons'],16);self.assertEqual(r['faults']['exact_normalized_retail_access_cut_pairs'],138)
 def test_06_actual_registration_calls_and_real_trig(self):
  r=callers.main();self.assertEqual(r['registration_windows'],48);self.assertEqual(r['callback_pairs'],144);self.assertEqual(r['callback_window_covered_words'],14);self.assertEqual(r['real_trig']['pairs'],512);self.assertEqual(r['real_trig']['helper_covered_words'],48);self.assertFalse(r['census']['original_C_return_type_proven']);self.assertFalse(r['full_parent_or_gameplay_qualified'])
 def test_07_eight_complete_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.symbol_rows(before)if v[1]==source.NAME)
  for at in[24,source.elf_slot_offset(before,source.ENTRY,380),source.elf_slot_offset(before,source.ENTRY+56*4,4),source.elf_slot_offset(before,0x150C522C,4),source.elf_slot_offset(before,0x800A03F4,1),symbol[0]+4,symbol[0]+8,symbol[3]]:
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_live_inputs_addresses_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);old=(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();new=(source.out/'proposed-guards.csv').read_bytes();self.assertTrue(new.startswith(old));self.assertEqual(len(list(source.csv.DictReader(source.io.StringIO(new.decode()))))-len(list(source.csv.DictReader(source.io.StringIO(old.decode())))),6);self.assertEqual((ROOT/'conker/Makefile').read_bytes(),(source.out/'frozen/conker/Makefile').read_bytes())
if __name__=='__main__':unittest.main()
