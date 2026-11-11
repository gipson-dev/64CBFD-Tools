"""Actor position pair: callback windows, direction helper and strict image."""
import unittest
from tools.experiments import game_actor_position_pair_15195528_match as source
from tools.tests import game_actor_position_pair_15195528_oracle as guest
from tools.tests import game_actor_position_pair_15195528_native as native
from tools.tests import game_actor_position_pair_15195528_callers as callers
from tools.tests import game_actor_position_pair_15195528_connected as connected
from tools.tests import game_actor_position_pair_15195528_boundaries as boundaries
ROOT=source.ROOT
class ActorPositionPairTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertIs(source.q.p,source.q);self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['changed_bytes'],242);self.assertEqual(len(r['image']['metadata_groups']),1);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['actual_Make_commands'],5);self.assertEqual(r['non_target_neighbors'],28);self.assertEqual(r['guards'],0)
 def test_02_retail_guest(self):
  r=guest.main();self.assertEqual(r['cases'],108);self.assertEqual(r['null_actor_fault_cases'],1);self.assertEqual(r['words_visited'],74);self.assertTrue(r['retail_equals_compiled']);self.assertTrue(r['finite_nearest_rounding_only'])
 def test_03_native_and_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==108 and v['negative_controls']==10 and v['UBSan'] for v in r['profiles'].values()));self.assertTrue(r['actor_nonnull_only'])
 def test_04_original_callers(self):
  r=callers.main();self.assertEqual(r['dispatcher_windows'],2);self.assertEqual(r['callback_index'],27);self.assertEqual(r['cases'],24);self.assertTrue(r['full_parents_not_qualified'])
 def test_05_connected_direction(self):
  r=connected.main();self.assertEqual(r['cases'],12);self.assertEqual(r['original_direction_helper_words'],22);self.assertTrue(r['sine_cosine_modeled']);self.assertTrue(r['submit_modeled'])
 def test_06_padding_relocations_and_access_cuts(self):
  r=boundaries.main();self.assertEqual(r['body_words'],74);self.assertEqual(r['guards'],0);self.assertEqual(r['GNU_rebased_links'],16);self.assertEqual(r['access_cut_quads'],72)
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before)if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,296),source.q.elf_slot_offset(before,source.ENTRY+292,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((source.out/'proposed-guards.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
if __name__=='__main__':unittest.main()
