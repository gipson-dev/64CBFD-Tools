"""Palette initializer semantics, complete relocation and whole-image gates."""
import unittest
from tools.experiments import game_palette_state_15000940_match as source
from tools.tests import game_palette_state_15000940_oracle as guest
from tools.tests import game_palette_state_15000940_native as native
from tools.tests import game_palette_state_15000940_symbolic as symbolic
from tools.tests import game_palette_state_15000940_boundaries as boundaries
from tools.tests import game_palette_state_15000940_callers as callers
ROOT=source.ROOT
class PaletteTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_owner_and_strict_image(self):
  self.assertEqual(self.report['image'],source.MANIFEST['image']);self.assertEqual(self.report['image']['changed_bytes'],406);self.assertEqual(self.report['image']['strict_exclusions'],0);self.assertEqual(self.report['actual_Make_commands'],3);self.assertEqual(self.report['non_target_neighbors'],0);self.assertEqual(self.report['guards'],73)
 def test_02_original_raw_and_normalized_guest(self):
  r=guest.main();self.assertEqual(r['cases'],304);self.assertEqual(r['coverage'],95);self.assertEqual(r['missing'],[]);self.assertEqual(r['complete_machine_pairs'],304);self.assertTrue(r['generic_outside_actual_table_domain_guest_only'])
 def test_03_defined_native_and_effective_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==2168 and v['effective_completed_controls']==10 and v['UBSan']and v['strict_aliasing']for v in r['profiles'].values()));self.assertTrue(r['actual_table_domain_only'])
 def test_04_symbolic_access_and_register_roles(self):
  r=symbolic.main();self.assertEqual(r['symbolic_ordered_memory_accesses'],130);self.assertEqual(r['symbolic_branch_decisions'],16);self.assertTrue(r['all_instructions_retained_once']);self.assertTrue(r['saved_GPRs_SP_RA_preserved'])
 def test_05_padding_relocations_aliases_and_fault_cuts(self):
  r=boundaries.main();self.assertEqual(r['padders']['byte_and_binding_corruptions'],432);self.assertEqual(r['padders']['guards'],73);self.assertEqual(r['rebases']['GNU_linker_comparisons'],16);self.assertEqual(r['rebases']['executions'],64);self.assertEqual(r['faults']['literal_access_cut_triples'],390);self.assertEqual(r['faults']['guest_alias_triples'],15)
 def test_06_real_caller_window(self):
  r=callers.main();self.assertEqual(r['caller_triples'],48);self.assertEqual(r['caller_window_words'],10);self.assertTrue(r['return_V0_overwritten_before_any_read']);self.assertFalse(r['full_parent_or_gameplay_qualified'])
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.symbol_rows(before)if v[1]==source.NAME)
  for at in[24,source.elf_slot_offset(before,source.ENTRY,380),source.elf_slot_offset(before,source.ENTRY+56*4,4),source.elf_slot_offset(before,source.ENTRY+380,4),source.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+4,symbol[0]+8,symbol[3]]:
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_inputs_addresses_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertTrue((source.out/'proposed-guards.csv').read_bytes().startswith((source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes()));self.assertTrue((source.out/'make-proposal.mk').read_bytes().startswith((source.out/'frozen/conker/Makefile').read_bytes()))
if __name__=='__main__':unittest.main()
