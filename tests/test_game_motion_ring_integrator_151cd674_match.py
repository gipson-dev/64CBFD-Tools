"""Ring entry update: bounded semantics, dispatcher, padder and image gates."""
import unittest
from tools.experiments import game_motion_ring_integrator_151cd674_match as source
from tools.tests import game_motion_ring_integrator_151cd674_oracle as guest
from tools.tests import game_motion_ring_integrator_151cd674_native as native
from tools.tests import game_motion_ring_integrator_151cd674_window as window
from tools.tests import game_motion_ring_integrator_151cd674_parent as parent
from tools.tests import game_motion_ring_integrator_151cd674_pad as pad
from tools.tests import game_motion_ring_integrator_151cd674_boundaries as boundaries
from tools.tests import game_motion_ring_integrator_151cd674_guards as guards
ROOT=source.ROOT
class MotionRingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['non_target_neighbors'],51);self.assertEqual((r['guards'],r['inserted_words']),(50,1))
 def test_02_retail_guest(self):
  r=guest.main();self.assertEqual(r['cases'],1856);self.assertEqual(r['retail_words_visited'],78);self.assertTrue(r['valid_finite_disjoint_ring_storage'])
 def test_03_defined_native_and_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==1856 and v['negative_controls']==9 and v['UBSan'] for v in r['profiles'].values()))
 def test_04_original_dispatch(self):
  w=window.main();p=parent.main();self.assertEqual((w['cases'],p['cases']),(1856,1856));self.assertEqual(w['table'],'D_8008A200[9]');self.assertTrue(p['bounded_parent_paths']);self.assertEqual(p['release'],'modeled')
 def test_05_padding_rebases_and_access_cuts(self):
  p=pad.main();r=boundaries.main();self.assertTrue(p['dual_padder_matches_retail']);self.assertEqual((p['guard_rows'],p['inserted_words']),(50,1));self.assertEqual((r['gnu_rebased_links'],r['access_cut_triples']),(12,144))
 def test_06_guard_corruption_rejection(self):self.assertEqual(guards.main()['rejected_corruptions'],100)
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before)if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,328),source.q.elf_slot_offset(before,source.ENTRY+324,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);before=(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();after=(source.out/'proposed-guards.csv').read_bytes();self.assertTrue(after.startswith(before));self.assertEqual(len(source.rows(*source.payload(source.out/'independent-selected.o'))),50)
if __name__=='__main__':unittest.main()
