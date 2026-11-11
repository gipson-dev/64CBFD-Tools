"""Camera reset: caller windows, camera helper and strict full image."""
import unittest
from tools.experiments import game_camera_reset_15127eb8_match as source
from tools.tests import game_camera_reset_15127eb8_oracle as guest
from tools.tests import game_camera_reset_15127eb8_native as native
from tools.tests import game_camera_reset_15127eb8_callers as callers
from tools.tests import game_camera_reset_15127eb8_connected as connected
from tools.tests import game_camera_reset_15127eb8_boundaries as boundaries
ROOT=source.ROOT
class CameraResetTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertIs(source.q.p,source.q);self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['changed_bytes'],265);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['actual_Make_commands'],5);self.assertEqual(r['non_target_neighbors'],44);self.assertEqual(r['guards'],0)
 def test_02_retail_guest(self):
  r=guest.main();self.assertEqual(r['cases'],128);self.assertEqual(r['words_visited'],77);self.assertTrue(r['retail_equals_compiled']);self.assertTrue(r['helper_state_mutations'])
 def test_03_native_and_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==128 and v['negative_controls']==11 and v['UBSan'] for v in r['profiles'].values()))
 def test_04_original_callers(self):
  r=callers.main();self.assertEqual(r['original_call_sites'],6);self.assertEqual(r['cases'],144);self.assertTrue(r['bounded_windows_only'])
 def test_05_connected_camera_helper(self):
  r=connected.main();self.assertEqual(r['cases'],48);self.assertEqual(r['original_camera_helper_words'],34);self.assertTrue(r['nested_helper_modeled'])
 def test_06_padding_relocations_and_access_cuts(self):
  r=boundaries.main();self.assertEqual(r['body_words'],77);self.assertEqual(r['guards'],0);self.assertEqual(r['GNU_rebased_links'],16);self.assertEqual(r['access_cut_quads'],104)
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before)if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,308),source.q.elf_slot_offset(before,source.ENTRY+304,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((source.out/'proposed-guards.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
if __name__=='__main__':unittest.main()
