"""Startup initializer: caller, original helpers, guard and strict-image checks."""
import unittest
from tools.experiments import game_startup_initializer_1500e470_match as source
from tools.tests import game_startup_initializer_1500e470_oracle as guest
from tools.tests import game_startup_initializer_1500e470_native as native
from tools.tests import game_startup_initializer_1500e470_callers as callers
from tools.tests import game_startup_initializer_1500e470_connected as connected
from tools.tests import game_startup_initializer_1500e470_deeper as deeper
from tools.tests import game_startup_initializer_1500e470_boundaries as boundaries
from tools.tests import game_startup_initializer_1500e470_guards as guards
ROOT=source.ROOT
class StartupInitializerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['non_target_neighbors'],0);self.assertEqual(r['guards'],5)
 def test_02_retail_guest(self):
  guest.ARG=0x5341200;r=guest.main();self.assertEqual(r['cases'],12);self.assertEqual(r['retail_words_visited'],84);self.assertTrue(r['matched_memory_calls_and_abi']);self.assertTrue(r['normalized_complete_state'])
 def test_03_defined_native_and_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==12 and v['negative_controls']==8 and v['UBSan'] for v in r['profiles'].values()))
 def test_04_original_caller_window(self):
  r=callers.main();self.assertEqual(r['cases'],12);self.assertEqual(r['call_site'],'0x15007FA4');self.assertTrue(r['full_parent_not_qualified']);guest.ARG=0x5341200
 def test_05_original_bzero(self):
  r=connected.main();self.assertEqual(r['cases'],12);self.assertEqual(r['original_bzero_words_visited'],22);self.assertTrue(r['other_helpers_modeled'])
 def test_06_original_category_helper(self):
  r=deeper.main();self.assertEqual(r['cases'],30);self.assertEqual(r['original_bzero_words_visited'],22);self.assertEqual(r['original_category_helper_words_visited'],17);self.assertTrue(r['other_helpers_modeled'])
 def test_07_padding_rebases_and_access_cuts(self):
  r=boundaries.main();self.assertEqual(r['guards'],5);self.assertTrue(r['generic_generated_original_bindings_equal']);self.assertEqual(r['GNU_rebased_links'],12);self.assertEqual(r['access_cut_triples'],45)
 def test_08_guard_corruption_rejection(self):
  r=guards.main();self.assertEqual(r['rejected_corruptions'],137)
 def test_09_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before) if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,336),source.q.elf_slot_offset(before,source.ENTRY+332,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_10_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);before=(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();after=(source.out/'proposed-guards.csv').read_bytes();self.assertTrue(after.startswith(before));self.assertEqual(len(source.rows(*source.payload(source.out/'independent-selected.o'))),5)
if __name__=='__main__':unittest.main()
