"""Effect-state callback: bounded semantics, dispatcher and strict image gates."""
import unittest
from tools.experiments import game_effect_state_callback_150bf0f4_match as source
from tools.tests import game_effect_state_callback_150bf0f4_oracle as guest
from tools.tests import game_effect_state_callback_150bf0f4_native as native
from tools.tests import game_effect_state_callback_150bf0f4_callers as callers
from tools.tests import game_effect_state_callback_150bf0f4_connected as connected
from tools.tests import game_effect_state_callback_150bf0f4_boundaries as boundaries
from tools.tests import game_effect_state_callback_150bf0f4_guards as guards
ROOT=source.ROOT
class EffectStateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['non_target_neighbors'],9);self.assertEqual(r['guards'],28);self.assertEqual(r['inserted_branches'],1)
 def test_02_retail_guest(self):
  r=guest.main();self.assertEqual(r['cases'],1020);self.assertEqual(r['retail_words_visited'],74);self.assertTrue(r['memory_return_and_saved_abi_match']);self.assertTrue(r['normalized_complete_state'])
 def test_03_defined_native_and_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==1020 and v['negative_controls']==11 and v['UBSan'] for v in r['profiles'].values()))
 def test_04_original_caller_window(self):
  r=callers.main();self.assertEqual(r['cases'],1020);self.assertEqual(r['table'],'D_8008CBA0[8]');self.assertTrue(r['branch_on_return_qualified'])
 def test_05_complete_original_dispatcher(self):
  r=connected.main();self.assertEqual(r['cases'],2040);self.assertEqual(r['original_parent_words_visited'],48);self.assertEqual(r['return_one_release_paths'],1524);self.assertTrue(r['release_helper_modeled']);self.assertTrue(r['linked_and_null_binding'])
 def test_06_padding_rebases_and_access_cuts(self):
  r=boundaries.main();self.assertEqual(r['guards'],28);self.assertTrue(r['generic_generated_original_bindings_equal']);self.assertEqual(r['GNU_rebased_links'],12);self.assertEqual(r['access_cut_triples'],26)
 def test_07_guard_corruption_rejection(self):
  r=guards.main();self.assertEqual(r['rejected_corruptions'],108)
 def test_08_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before) if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,296),source.q.elf_slot_offset(before,source.ENTRY+292,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_09_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);before=(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();after=(source.out/'proposed-guards.csv').read_bytes();self.assertTrue(after.startswith(before));self.assertEqual(len(source.rows(*source.payload(source.out/'independent-selected.o'))),28)
if __name__=='__main__':unittest.main()
