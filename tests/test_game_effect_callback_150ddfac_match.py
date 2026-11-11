"""Direct effect callback: behavior, dispatch and whole-image gates."""
import unittest
from tools.experiments import game_effect_callback_150ddfac_match as source
from tools.tests import game_effect_callback_150ddfac_oracle as guest
from tools.tests import game_effect_callback_150ddfac_native as native
from tools.tests import game_effect_callback_150ddfac_boundaries as boundaries
from tools.tests import game_effect_callback_150ddfac_callers as callers
from tools.tests import game_effect_callback_150ddfac_connected as connected
ROOT=source.ROOT
class EffectCallbackTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_owner_and_strict_image(self):
  r=self.report;self.assertIs(source.q.p,source.q);self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['changed_bytes'],297);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['actual_Make_commands'],3);self.assertEqual(r['non_target_neighbors'],11);self.assertEqual(r['guards'],0)
 def test_02_original_raw_guest(self):
  r=guest.main();self.assertEqual(r['cases'],332);self.assertEqual(r['visited_words'],94);self.assertEqual(r['missing'],[29,30]);self.assertTrue(r['descriptor_defined_fields_checked'])
 def test_03_defined_native_and_effective_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==216 and v['controls']==8 and v['UBSan']for v in r['profiles'].values()));self.assertTrue(r['argument_home_mutation_excluded_from_native'])
 def test_04_padding_relocations_and_fault_cuts(self):
  r=boundaries.main();self.assertTrue(r['raw_generic_generated_original_bindings_equal']);self.assertEqual(r['GNU_rebased_links'],16);self.assertEqual(r['access_cut_quads'],245);self.assertEqual(r['unreachable_masked_branch_words'],[29,30])
 def test_05_original_indirect_dispatch(self):
  r=callers.main();self.assertEqual(r['caller_cases'],72);self.assertEqual(r['index'],3);self.assertTrue(r['six_arguments_checked']);self.assertTrue(r['full_parent_not_qualified'])
 def test_06_connected_original_rng_helpers(self):
  r=connected.main();self.assertEqual(r['cases'],12);self.assertEqual(r['original_rng_words'],43);self.assertEqual(r['visited_rng_words'],43);self.assertTrue(r['submission_still_modeled'])
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before)if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,384),source.q.elf_slot_offset(before,source.ENTRY+380,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_inputs_addresses_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertEqual((source.out/'proposed-guards.csv').read_bytes(),(source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
if __name__=='__main__':unittest.main()
