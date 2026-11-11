"""Scaled vertex-radius initializer: bounded semantics and strict image gates."""
import unittest
from tools.experiments import game_scaled_vertex_radius_15004aac_match as source
from tools.tests import game_scaled_vertex_radius_15004aac_oracle as guest
from tools.tests import game_scaled_vertex_radius_15004aac_native as native
from tools.tests import game_scaled_vertex_radius_15004aac_callers as callers
from tools.tests import game_scaled_vertex_radius_15004aac_boundaries as boundaries
from tools.tests import game_scaled_vertex_radius_15004aac_guards as guards
ROOT=source.ROOT
class VertexRadiusTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['non_target_neighbors'],8);self.assertEqual(r['guards'],27)
 def test_02_retail_guest(self):
  r=guest.main();self.assertEqual(r['cases'],240);self.assertEqual(r['retail_words_visited'],81);self.assertTrue(r['memory_and_saved_abi_match']);self.assertTrue(r['normalized_complete_state'])
 def test_03_defined_native_and_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==240 and v['negative_controls']==10 and v['UBSan'] for v in r['profiles'].values()))
 def test_04_original_caller_window(self):
  r=callers.main();self.assertEqual(r['cases'],240);self.assertEqual(r['call_site'],'0x150041B4');self.assertTrue(r['full_parent_not_qualified'])
 def test_05_padding_rebases_and_access_cuts(self):
  r=boundaries.main();self.assertEqual(r['guards'],27);self.assertTrue(r['generic_generated_original_bindings_equal']);self.assertEqual(r['GNU_rebased_links'],12);self.assertEqual(r['access_cut_triples'],29)
 def test_06_guard_corruption_rejection(self):
  r=guards.main();self.assertEqual(r['rejected_corruptions'],114)
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before) if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,324),source.q.elf_slot_offset(before,source.ENTRY+320,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);before=(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();after=(source.out/'proposed-guards.csv').read_bytes();self.assertTrue(after.startswith(before));self.assertEqual(len(source.rows(*source.payload(source.out/'independent-selected.o'))),27)
if __name__=='__main__':unittest.main()
