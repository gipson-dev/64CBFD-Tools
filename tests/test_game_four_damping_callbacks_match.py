"""Four direct damping callbacks: retail semantics and linked image."""
import unittest
from tools.experiments import game_four_damping_callbacks_match as source
from tools.tests import game_four_damping_callbacks_guest as guest
from tools.tests import game_four_damping_callbacks_native as native
from tools.tests import game_four_damping_callbacks_window as window
from tools.tests import game_four_damping_callbacks_pad as pad
from tools.tests import game_four_damping_callbacks_boundaries as boundaries
ROOT=source.ROOT
class FourDampingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertEqual(r['image'],source.MANIFEST['qualification']['image']);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['non_target_neighbors'],[5,18,9,5]);self.assertEqual((r['guards_each'],r['inserted_words']),(0,0))
 def test_02_retail_guest(self):
  r=guest.main();self.assertEqual(len(r['targets']),4);self.assertTrue(all((x['cases'],x['retail_words_visited'])==(440,106) for x in r['targets']));self.assertEqual(r['helpers'],'none')
 def test_03_defined_native_and_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases_per_target']==440 and v['targets']==4 and v['negative_controls_per_target']==6 and v['UBSan'] for v in r['profiles'].values()))
 def test_04_original_dispatch(self):
  r=window.main();self.assertEqual(len(r['targets']),4);self.assertTrue(all(x['cases']==440 and x['return_negative_controls']==2 for x in r['targets']));self.assertEqual([x['index'] for x in r['targets']],[2,9,7,8]);self.assertFalse(r['full_parent_qualified'])
 def test_05_padding_rebases_and_access_cuts(self):
  p=pad.main();r=boundaries.main();self.assertEqual(len(p['targets']),4);self.assertTrue(all(x['dual_padder_matches_retail'] and x['guard_rows']==0 for x in p['targets']));self.assertTrue(all((x['gnu_rebased_links'],x['access_cut_triples'],x['high_tick_prefix_cuts'])==(12,68,80) for x in r['targets']))
 def test_06_fingerprint_corruption_rejection(self):
  count=0
  for target in source.TARGETS:
   raw,refs=source.payload(source.out/('ptr_'+target+'.o'),'func_'+target);source.verify(target,raw,refs)
   for i in range(106):
    wrong=bytearray(raw);wrong[4*i]^=1
    with self.assertRaises(ValueError):source.verify(target,bytes(wrong),refs)
    count+=1
   for i in refs:
    wrong={k:list(v) for k,v in refs.items()};kind,name=wrong[i][0];wrong[i][0]=(kind,name+'_changed')
    with self.assertRaises(ValueError):source.verify(target,raw,wrong)
    count+=1
  self.assertEqual(count,432)
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();rom=(ROOT/'conker/conker.us.bin').read_bytes();payloads={};sites=[24,source.q.elf_slot_offset(before,0x800A2CD0,1)]
  for target in source.TARGETS:
   addr=int(target,16);offset=addr-0x15000000+0x2d4b0;payloads['func_'+target]=rom[offset:offset+424];sites.append(source.q.elf_slot_offset(before,addr,1));symbol=next(v for v in source.q.symbol_rows(before) if v[1]=='func_'+target);sites.append(symbol[0]+8)
  for at in sites:
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),payloads,source.MANIFEST['qualification']['image']['metadata_groups'])
 def test_08_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((source.out/'proposed-guards.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
if __name__=='__main__':unittest.main()
