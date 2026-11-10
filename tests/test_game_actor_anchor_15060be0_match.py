"""Anchor C semantics, guarded zero/FP roles and strict complete-image gates."""
import csv,io,unittest
from tools.experiments import game_actor_anchor_15060be0_match as source
from tools.tests import game_actor_anchor_15060be0_oracle as guest
from tools.tests import game_actor_anchor_15060be0_native as native
from tools.tests import game_actor_anchor_15060be0_controls as controls
from tools.tests import game_actor_anchor_15060be0_boundaries as boundaries
from tools.tests import game_actor_anchor_15060be0_callers as callers
ROOT=source.ROOT
class ActorAnchorTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_guarded_target_and_complete_image(self):
  self.assertEqual(self.report['image']['changed_bytes'],258);self.assertEqual(self.report['image']['strict_exclusions'],0);self.assertEqual(self.report['actual_Make_commands'],5);self.assertEqual(self.report['non_target_neighbors'],88);self.assertEqual(self.report['guards'],27)
 def test_02_guest_edges_aliases_and_invalid_conversion_prefixes(self):
  r=guest.main();self.assertEqual(r['cases'],961);self.assertEqual(r['normal_returns'],891);self.assertEqual(r['invalid_conversion_prefix_cases'],70);self.assertEqual(r['coverage'],92);self.assertEqual(r['missing'],[53]);self.assertEqual(r['complete_normalized_retail_pairs'],961);self.assertFalse(r['invalid_conversion_results_or_FCSR_qualified'])
 def test_03_native_SDK32_O0_O2_O3_UBSan_alias_views(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==619 and v['exact_output_bytes']==6190 and v['UBSan']and v['float_cast_overflow_sanitized']and not v['strict_aliasing']for v in r['profiles'].values()))
 def test_04_seventeen_effective_compiled_controls(self):
  r=controls.main();self.assertEqual(r['controls'],17);self.assertTrue(all(v['normal_completion']and v['execution_errors']==0 for v in r['effective_compiled_controls'].values()))
 def test_05_guard_FP_proof_padders_rebases_and_fault_cuts(self):
  r=boundaries.main();self.assertEqual(r['CFG']['unreachable'],[53]);self.assertEqual(r['padders']['word_and_binding_corruptions'],97);self.assertEqual(r['padders']['guard_record_corruptions'],3);self.assertEqual(r['padders']['independent_stale_guard_rejections'],2);self.assertEqual(r['rebases']['executions'],48);self.assertEqual(r['faults']['exact_normalized_retail_access_cut_pairs'],72)
 def test_06_no_direct_callers_and_one_pointer_ABI(self):
  r=callers.main();self.assertEqual(r['poisoned_non_input_executions'],72);self.assertEqual(r['complete_normalized_retail_pairs'],24);self.assertEqual(r['census']['aligned_direct_J_or_JAL_sites'],[]);self.assertEqual(r['census']['aligned_literal_pointers'],[]);self.assertEqual(r['census']['caller_windows_qualified'],0);self.assertFalse(r['original_C_return_type_proven'])
 def test_07_eight_complete_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.symbol_rows(before)if v[1]==source.NAME)
  for at in[24,source.elf_slot_offset(before,source.ENTRY,372),source.elf_slot_offset(before,source.ENTRY+53*4,4),source.elf_slot_offset(before,0x15060D54,4),source.elf_slot_offset(before,self.report['protected_data']['address'],1),symbol[0]+4,symbol[0]+8,symbol[3]]:
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth})
 def test_08_closed_live_inputs_addresses_data_and_guard_prefix(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);before=(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();actual=(source.out/'proposed-guards.csv').read_bytes();self.assertTrue(actual.startswith(before));self.assertEqual(list(csv.DictReader(io.StringIO(actual.decode())))[-27:],source.MANIFEST['guard_rows'])
if __name__=='__main__':unittest.main()
