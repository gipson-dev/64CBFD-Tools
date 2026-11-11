"""Qualify sorted-record insertion against retail and independent models."""
import unittest
from tools.experiments import game_sorted_record_insert_150241b4_match as source
from tools.tests import game_sorted_record_insert_150241b4_oracle as guest
from tools.tests import game_sorted_record_insert_150241b4_native as native
from tools.tests import game_sorted_record_insert_150241b4_window as window
from tools.tests import game_sorted_record_insert_150241b4_pad as pad
from tools.tests import game_sorted_record_insert_150241b4_boundaries as boundaries
from tools.tests import game_sorted_record_insert_150241b4_guards as guards
from tools.tests import game_sorted_record_insert_150241b4_membership as membership

ROOT = source.ROOT

class SortedRecordTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.report = source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['non_target_neighbors'],10);self.assertEqual((r['guards'],r['inserted_words']),(44,2))
 def test_02_retail_guest(self):
  r=guest.main();self.assertEqual(r['cases'],989);self.assertEqual(r['retail_words_visited'],80);self.assertTrue(r['valid_disjoint_sorted_storage'])
 def test_03_defined_native_and_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==989 and v['negative_controls']==11 and v['UBSan'] for v in r['profiles'].values()))
 def test_04_original_caller_window(self):
  r=window.main();self.assertEqual(r['cases'],989);self.assertEqual(r['caller'],'func_150242F8');self.assertEqual(r['helper'],'modeled');self.assertFalse(r['full_parent_qualified'])
 def test_05_padding_rebases_access_cuts_and_make_membership(self):
  p=pad.main();r=boundaries.main();m=membership.main();self.assertTrue(p['dual_padder_matches_retail']);self.assertEqual((p['guard_rows'],p['inserted_words']),(44,2));self.assertEqual((r['gnu_rebased_links'],r['access_cut_triples']),(12,175));self.assertTrue(m['moved_from_standard_to_mixed'] and m['other_object_lists_identical'])
 def test_06_guard_corruption_rejection(self):self.assertEqual(guards.main()['rejected_corruptions'],88)
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before) if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,324),source.q.elf_slot_offset(before,source.ENTRY+320,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);before=(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();after=(source.out/'proposed-guards.csv').read_bytes();self.assertTrue(after.startswith(before));self.assertEqual(len(source.rows(*source.payload(source.out/'independent-nounroll.o'))),44)

if __name__=='__main__': unittest.main()
