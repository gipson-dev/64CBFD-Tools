"""Owner effect packet, actual helper chain and strict complete-image gates."""
import unittest
from tools.experiments import game_owner_payload_effect_151b4cd0_match as source
from tools.tests import game_owner_payload_effect_151b4cd0_oracle as guest
from tools.tests import game_owner_payload_effect_151b4cd0_native as native
from tools.tests import game_owner_payload_effect_151b4cd0_controls as controls
from tools.tests import game_owner_payload_effect_151b4cd0_boundaries as boundaries
from tools.tests import game_owner_payload_effect_151b4cd0_callers as callers
ROOT=source.ROOT
class OwnerPayloadTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_complete_owner_and_strict_image(self):
  self.assertEqual(self.report['image'],source.MANIFEST['image']);self.assertEqual(self.report['image']['changed_bytes'],316);self.assertEqual(self.report['image']['strict_exclusions'],0);self.assertEqual(self.report['actual_Make_commands'],5);self.assertEqual(self.report['non_target_neighbors'],5);self.assertEqual(self.report['guards'],0)
 def test_02_guest_live_inputs_packet_padding_and_machine(self):
  r=guest.main();self.assertEqual(r['cases'],622);self.assertEqual(r['coverage'],95);self.assertEqual(r['missing'],[]);self.assertEqual(r['complete_machine_and_trace_pairs'],622);self.assertTrue(r['all_48_packet_bytes_guest_checked'])
 def test_03_native_SDK32_O0_O2_O3_UBSan_and_defined_fields(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==412 and v['exact_public_and_defined_packet_call_bytes']==586724 and v['UBSan']and v['strict_aliasing']for v in r['profiles'].values()));self.assertTrue(r['padding_not_read_or_asserted'])
 def test_04_twenty_one_completed_semantic_controls(self):
  r=controls.main();self.assertEqual(r['controls'],21);self.assertTrue(all(v['normal_completion']and v['execution_errors_before_witness']==0 for v in r['effective_compiled_controls'].values()));self.assertTrue(r['private_addresses_and_padding_not_witnesses'])
 def test_05_padders_relocations_and_literal_access_cuts(self):
  r=boundaries.main();self.assertEqual(r['padders']['word_and_binding_corruptions'],106);self.assertEqual(r['padders']['guards'],0);self.assertEqual(r['rebases']['executions'],64);self.assertEqual(r['rebases']['GNU_linker_comparisons'],16);self.assertEqual(r['faults']['exact_normalized_retail_access_cut_pairs'],119)
 def test_06_real_caller_classifier_RNG64_factory_copy(self):
  r=callers.main();self.assertEqual(r['caller_pairs'],96);self.assertEqual(r['caller_window_words'],4);self.assertEqual(r['real_helpers']['pairs'],448);self.assertEqual(r['real_helpers']['covered_helper_words'],181);self.assertTrue(r['real_helpers']['real_notification_RNG64_factory_and_copy']);self.assertFalse(r['full_parent_or_gameplay_qualified'])
 def test_07_eight_complete_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.symbol_rows(before)if v[1]==source.NAME)
  for at in[24,source.elf_slot_offset(before,source.ENTRY,380),source.elf_slot_offset(before,source.ENTRY+56*4,4),source.elf_slot_offset(before,0x151B4EA4,4),source.elf_slot_offset(before,0x800A3FE6,1),symbol[0]+4,symbol[0]+8,symbol[3]]:
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_inputs_addresses_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes());self.assertEqual((ROOT/'conker/Makefile').read_bytes(),(source.out/'frozen/conker/Makefile').read_bytes())
if __name__=='__main__':unittest.main()
