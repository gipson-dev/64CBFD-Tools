"""Retail paired effect constructors: owner, caller, padder and image gates."""
import csv,io,unittest
from tools.experiments import game_twin_effect_constructors_match as source
from tools.tests import game_twin_effect_constructors_a_oracle as ga, game_twin_effect_constructors_b_oracle as gb
from tools.tests import game_twin_effect_constructors_a_native as na, game_twin_effect_constructors_b_native as nb
from tools.tests import game_twin_effect_constructors_a_window as wa, game_twin_effect_constructors_b_window as wb
from tools.tests import game_twin_effect_constructors_a_pad as pa, game_twin_effect_constructors_b_pad as pb
from tools.tests import game_twin_effect_constructors_a_boundaries as ba, game_twin_effect_constructors_b_boundaries as bb
from tools.tests import game_twin_effect_constructors_a_guards as xa, game_twin_effect_constructors_b_guards as xb
ROOT=source.ROOT
class TwinEffectTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertEqual(r['image'],source.MANIFEST['qualification']['image']);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['non_target_neighbors'],[32,5]);self.assertEqual((r['guards_each'],r['inserted_words']),(10,0))
 def test_02_retail_guest(self):
  for g in (ga,gb):
   r=g.main();self.assertEqual((r['cases'],r['retail_words_visited']),(416,82));self.assertEqual(r['helpers'],'modeled')
 def test_03_defined_native_and_controls(self):
  for n in (na,nb):
   r=n.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==416 and v['negative_controls']==12 and v['UBSan'] for v in r['profiles'].values()))
 def test_04_original_wrappers(self):
  for w in (wa,wb):
   r=w.main();self.assertEqual(r['cases'],416);self.assertFalse(r['full_parent_qualified'])
 def test_05_padding_rebases_and_access_cuts(self):
  for p,b in ((pa,ba),(pb,bb)):
   r=p.main();self.assertTrue(r['dual_padder_matches_retail']);self.assertEqual((r['guard_rows'],r['inserted_words']),(10,0));r=b.main();self.assertEqual((r['gnu_rebased_links'],r['access_cut_triples']),(12,102))
 def test_06_guard_corruption_rejection(self):
  for g in (xa,xb):self.assertEqual(g.main()['rejected_corruptions'],20)
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();retail=(ROOT/'conker/conker.us.bin').read_bytes();payloads={'func_151AF388':retail[0x1dc838:0x1dc838+328],'func_151B50F4':retail[0x1e25a4:0x1e25a4+328]}
  symbols={v[1]:v for v in source.q.symbol_rows(before) if v[1] in payloads}
  for at in (24,source.q.elf_slot_offset(before,0x151AF388,1),source.q.elf_slot_offset(before,0x151B50F4+324,1),source.q.elf_slot_offset(before,0x800A2CD0,1),symbols['func_151AF388'][0]+8,symbols['func_151B50F4'][0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),payloads,source.MANIFEST['qualification']['image']['metadata_groups'])
 def test_08_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);before=(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();after=(source.out/'proposed-guards.csv').read_bytes();self.assertTrue(after.startswith(before));self.assertEqual(len(list(csv.DictReader(io.StringIO(after[len(before):].decode()),fieldnames=next(csv.reader(io.StringIO(before.decode())))))),20)
if __name__=='__main__':unittest.main()
