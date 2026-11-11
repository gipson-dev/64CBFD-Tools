"""Direct oscillation callback: behavior, dispatch and whole-image gates."""
import unittest
from tools.experiments import game_oscillation_callback_150d317c_match as source
from tools.tests import game_oscillation_callback_150d317c_oracle as guest
from tools.tests import game_oscillation_callback_150d317c_native as native
from tools.tests import game_oscillation_callback_150d317c_boundaries as boundaries
from tools.tests import game_oscillation_callback_150d317c_callers as callers
from tools.tests import game_oscillation_callback_150d317c_connected as connected
ROOT=source.ROOT
class OscillationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_owner_and_strict_image(self):
  r=self.report;self.assertIs(source.q.p,source.q);self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['changed_bytes'],283);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['actual_Make_commands'],3);self.assertEqual(r['non_target_neighbors'],5);self.assertEqual(r['guards'],0)
 def test_02_original_raw_guest(self):
  r=guest.main();self.assertEqual(r['cases'],480);self.assertEqual(r['visited_words'],95);self.assertEqual(r['missing'],[77]);self.assertTrue(r['FCSR_restored_bounded_nontrapping_model'])
 def test_03_defined_native_and_effective_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==162 and v['controls']==8 and v['UBSan']for v in r['profiles'].values()));self.assertTrue(r['finite_float_to_u32_in_range_only'])
 def test_04_padding_relocations_and_fault_cuts(self):
  r=boundaries.main();self.assertTrue(r['raw_generic_generated_original_bindings_equal']);self.assertEqual(r['GNU_rebased_links'],16);self.assertEqual(r['access_cut_quads'],165);self.assertEqual(r['unreachable_duplicate_word'],77)
 def test_05_original_indirect_dispatch(self):
  r=callers.main();self.assertEqual(r['caller_cases'],240);self.assertEqual(r['index'],38);self.assertTrue(r['return_controls_removal']);self.assertTrue(r['full_parent_not_qualified'])
 def test_06_connected_original_angle_helper(self):
  r=connected.main();self.assertEqual(r['cases'],98);self.assertEqual(r['original_angle_helper_words'],24);self.assertEqual(r['visited_helper_words'],24);self.assertTrue(r['sine_still_modeled'])
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before)if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,384),source.q.elf_slot_offset(before,source.ENTRY+380,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_inputs_addresses_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((source.out/'proposed-guards.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
if __name__=='__main__':unittest.main()
