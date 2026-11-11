"""Scale-stepper source, original caller/helper and strict image checks."""
import unittest
from tools.experiments import game_scale_stepper_15053750_match as source
from tools.tests import game_scale_stepper_15053750_oracle as guest
from tools.tests import game_scale_stepper_15053750_native as native
from tools.tests import game_scale_stepper_15053750_callers as callers
from tools.tests import game_scale_stepper_15053750_connected as connected
from tools.tests import game_scale_stepper_15053750_boundaries as boundaries
ROOT=source.ROOT
class ScaleStepperTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertIs(source.q.p,source.q);self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['non_target_neighbors'],57);self.assertEqual(r['guards'],0)
 def test_02_retail_guest(self):
  r=guest.main();self.assertEqual(r['cases'],36);self.assertEqual(r['retail_words_visited'],79);self.assertEqual(r['unvisited'],['0x150537a8','0x15053844']);self.assertTrue(r['retail_equals_compiled'])
 def test_03_defined_native_and_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==28 and v['negative_controls']==8 and v['UBSan'] for v in r['profiles'].values()));self.assertTrue(r['finite_values_only'])
 def test_04_original_caller_window(self):
  r=callers.main();self.assertEqual(r['cases'],18);self.assertTrue(r['delay_slot_supplies_actor']);self.assertTrue(r['full_parent_not_qualified'])
 def test_05_connected_original_helper(self):
  r=connected.main();self.assertEqual(r['cases'],18);self.assertEqual(r['original_helper_words_visited'],77);self.assertEqual(r['actor_ids'],[255,3]);self.assertTrue(r['nested_helpers_modeled'])
 def test_06_padding_rebases_and_access_cuts(self):
  r=boundaries.main();self.assertEqual(r['guards'],0);self.assertTrue(r['raw_generic_generated_original_bindings_equal']);self.assertEqual(r['GNU_rebased_links'],16);self.assertEqual(r['access_cut_quads'],42)
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before) if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,324),source.q.elf_slot_offset(before,source.ENTRY+320,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((source.out/'proposed-guards.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
if __name__=='__main__':unittest.main()
