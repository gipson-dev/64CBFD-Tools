"""Guarded radial dispatcher: caller, helpers and strict image gates."""
import unittest
from tools.experiments import game_radial_dispatch_1514c2f0_match as source
from tools.tests import game_radial_dispatch_1514c2f0_oracle as guest
from tools.tests import game_radial_dispatch_1514c2f0_native as native
from tools.tests import game_radial_dispatch_1514c2f0_roles as roles
from tools.tests import game_radial_dispatch_1514c2f0_boundaries as boundaries
from tools.tests import game_radial_dispatch_1514c2f0_callers as callers
from tools.tests import game_radial_dispatch_1514c2f0_connected as connected
ROOT=source.ROOT
class RadialTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_both_owners_and_strict_image(self):
  r=self.report;self.assertIs(source.q.p,source.q);self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['changed_bytes'],299);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['actual_Make_commands'],8);self.assertEqual(r['non_target_neighbors'],35);self.assertEqual(r['guards'],17);self.assertEqual(r['caller_all_sections_identical'],11);self.assertTrue(r['caller_whole_object_identical'])
 def test_02_original_raw_and_normalized_guest(self):
  r=guest.main();self.assertEqual(r['cases'],900);self.assertEqual(r['executions'],2700);self.assertEqual(r['visited_words'],96);self.assertEqual(r['missing'],[]);self.assertTrue(r['raw_public_and_normalized_complete_state'])
 def test_03_defined_native_and_effective_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==750 and v['controls']==8 and v['UBSan']for v in r['profiles'].values()));self.assertTrue(r['stack_home_mutations_excluded_from_native'])
 def test_04_guarded_register_roles(self):
  r=roles.main();self.assertEqual(r['guard_words'],17);self.assertTrue(r['all_words_explained'])
 def test_05_padding_relocations_and_fault_cuts(self):
  r=boundaries.main();self.assertEqual(r['byte_and_binding_corruptions'],392);self.assertEqual(r['individual_guard_corruptions'],17);self.assertEqual(r['GNU_rebased_links'],16);self.assertEqual(r['access_cut_quads'],303)
 def test_06_three_original_caller_windows(self):
  r=callers.main();self.assertEqual(r['caller_triples'],144);self.assertEqual(r['original_windows'],3);self.assertTrue(r['return_unused_in_bounded_continuations'])
 def test_07_connected_original_sine_helper(self):
  r=connected.main();self.assertEqual(r['cases'],512);self.assertEqual(r['visited_sine_words'],27);self.assertTrue(r['all_256_input_angles_checked']);self.assertTrue(r['callback_still_modeled'])
 def test_08_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before)if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,384),source.q.elf_slot_offset(before,source.ENTRY+380,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_09_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertTrue((source.out/'proposed-guards.csv').read_bytes().startswith((source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes()))
if __name__=='__main__':unittest.main()
