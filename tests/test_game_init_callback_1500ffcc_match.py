"""Initialization callback: original dispatcher/helpers and guarded strict image."""
import unittest
from tools.experiments import game_init_callback_1500ffcc_match as source
from tools.tests import game_init_callback_1500ffcc_oracle as guest
from tools.tests import game_init_callback_1500ffcc_native as native
from tools.tests import game_init_callback_1500ffcc_roles as roles
from tools.tests import game_init_callback_1500ffcc_boundaries as boundaries
from tools.tests import game_init_callback_1500ffcc_callers as callers
from tools.tests import game_init_callback_1500ffcc_connected as connected
ROOT=source.ROOT
class InitCallbackTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertIs(source.q.p,source.q);self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['non_target_neighbors'],2);self.assertEqual(r['guards'],15);self.assertEqual(r['alignment_words'],2)
 def test_02_retail_raw_and_normalized_guest(self):
  r=guest.main();self.assertEqual(r['cases'],16);self.assertEqual(r['executions'],48);self.assertEqual(r['retail_words_visited'],79);self.assertTrue(r['normalized_complete_state'])
 def test_03_defined_native_and_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==16 and v['negative_controls']==9 and v['UBSan'] for v in r['profiles'].values()));self.assertTrue(r['bounded_allocations'])
 def test_04_call_preparation_roles(self):
  r=roles.main();self.assertEqual(r['guard_words'],15);self.assertTrue(r['identical_registers_and_stack_at_call']);self.assertTrue(r['disjoint_stack_slots']);self.assertEqual(r['scenarios'],20)
 def test_05_padding_relocations_and_access_cuts(self):
  r=boundaries.main();self.assertEqual(r['byte_and_binding_corruptions'],352);self.assertEqual(r['individual_guard_corruptions'],15);self.assertEqual(r['GNU_rebased_links'],16);self.assertEqual(r['access_cut_quads'],108)
 def test_06_original_table_dispatch(self):
  r=callers.main();self.assertEqual(r['cases'],8);self.assertEqual(r['executions'],24);self.assertEqual(r['table_index'],12);self.assertTrue(r['full_parent_not_qualified'])
 def test_07_connected_original_helpers(self):
  r=connected.main();self.assertEqual(r['cases'],16);self.assertEqual(sorted(r['original_helpers'].values()),[11,12]);self.assertTrue(r['nested_and_other_helpers_modeled'])
 def test_08_full_image_and_padding_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before) if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,316),source.q.elf_slot_offset(before,source.ENTRY+312,4),source.q.elf_slot_offset(before,source.ENTRY+316,4),source.q.elf_slot_offset(before,source.ENTRY+320,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_09_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertTrue((source.out/'proposed-guards.csv').read_bytes().startswith((source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes()))
if __name__=='__main__':unittest.main()
