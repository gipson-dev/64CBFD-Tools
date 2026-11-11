"""Ground-motion callback and indirect-dispatch ABI qualification."""
import unittest
from tools.experiments import game_effect_ground_motion_150eae24_match as source
from tools.tests import game_effect_ground_motion_150eae24_oracle as guest
from tools.tests import game_effect_ground_motion_150eae24_native as native
from tools.tests import game_effect_ground_motion_150eae24_callers as callers
from tools.tests import game_effect_ground_motion_150eae24_caller_native as caller_native
from tools.tests import game_effect_ground_motion_150eae24_connected as connected
from tools.tests import game_effect_ground_motion_150eae24_boundaries as boundaries
ROOT=source.ROOT
class GroundMotionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['guards'],0);self.assertEqual(r['non_target_neighbors'],10);self.assertEqual(r['caller_functions_unchanged'],78)
 def test_02_retail_guest(self):
  r=guest.main();self.assertEqual(r['cases'],32);self.assertEqual(r['retail_body_words_visited'],74);self.assertTrue(r['retail_equals_compiled']);self.assertTrue(r['global_and_output_pointer_mutations'])
 def test_03_defined_native_and_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==16 and v['negative_controls']==9 and v['UBSan'] for v in r['profiles'].values()));self.assertTrue(r['finite_float_only'])
 def test_04_original_dispatcher_and_table(self):
  r=callers.main();self.assertEqual(r['cases'],16);self.assertEqual(r['index'],19);self.assertTrue(r['original_dispatcher_exact']);self.assertTrue(r['original_table_entry_verified']);self.assertTrue(r['full_parent_executed_bounded'])
 def test_05_corrected_dispatcher_native(self):
  r=caller_native.main();self.assertTrue(all(v['cases']==16 and v['negative_controls']==3 and v['UBSan'] for v in r['profiles'].values()));self.assertTrue(r['other_table_entry_types_not_qualified'])
 def test_06_original_ground_helper(self):
  r=connected.main();self.assertEqual(r['cases'],16);self.assertEqual(r['original_ground_helper_words_visited'],29);self.assertTrue(r['precheck_and_fallback_modeled'])
 def test_07_padding_rebases_and_access_cuts(self):
  r=boundaries.main();self.assertEqual(r['guards'],0);self.assertEqual(r['alignment_words'],1);self.assertTrue(r['raw_generic_generated_original_bindings_equal']);self.assertEqual(r['GNU_rebased_links'],16);self.assertEqual(r['access_cut_quads'],64)
 def test_08_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before) if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,296),source.q.elf_slot_offset(before,source.ENTRY+292,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_09_closed_inputs_and_unchanged_guards(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((source.out/'proposed-guards.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
if __name__=='__main__':unittest.main()
