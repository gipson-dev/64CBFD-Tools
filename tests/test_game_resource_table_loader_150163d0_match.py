"""Resource table loader: bounded semantics, caller, padder and image gates."""
import unittest
from tools.experiments import game_resource_table_loader_150163d0_match as source
from tools.tests import game_resource_table_loader_150163d0_oracle as guest
from tools.tests import game_resource_table_loader_150163d0_native as native
from tools.tests import game_resource_table_loader_150163d0_callers as callers
from tools.tests import game_resource_table_loader_150163d0_boundaries as boundaries
from tools.tests import game_resource_table_loader_150163d0_rebase as rebase
from tools.tests import game_resource_table_loader_150163d0_cuts as cuts
from tools.tests import game_resource_table_loader_150163d0_guards as guards
ROOT=source.ROOT
class ResourceLoaderTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['non_target_neighbors'],0);self.assertEqual(r['guards'],52)
 def test_02_retail_guest(self):
  r=guest.main();self.assertEqual(r['cases'],195);self.assertEqual(r['retail_words_visited'],74);self.assertTrue(r['return_register_unqualified'])
 def test_03_defined_native_and_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==65 and v['negative_controls']==9 and v['UBSan'] for v in r['profiles'].values()))
 def test_04_original_caller_window(self):
  r=callers.main();self.assertEqual(r['cases'],195);self.assertEqual(r['caller'],'func_15007B3C');self.assertFalse(r['full_parent_qualified'])
 def test_05_padding_rebases_and_access_cuts(self):
  r=boundaries.main();self.assertTrue(r['dual_padder_matches_retail']);self.assertEqual(r['guard_rows'],52);self.assertEqual(rebase.main()['gnu_rebased_links'],12);self.assertEqual(cuts.main()['access_cut_triples'],100)
 def test_06_guard_corruption_rejection(self):self.assertEqual(guards.main()['rejected_corruptions'],104)
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before) if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,300),source.q.elf_slot_offset(before,source.ENTRY+296,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);before=(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();after=(source.out/'proposed-guards.csv').read_bytes();self.assertTrue(after.startswith(before));self.assertEqual(len(source.rows(*source.payload(source.out/'independent-selected.o'))),52)
if __name__=='__main__':unittest.main()
