"""Sequence direction: bounded behavior, ABI and strict image qualification."""
import unittest
from tools.experiments import game_sequence_direction_1501fe68_match as source
from tools.tests import game_sequence_direction_1501fe68_oracle as guest
from tools.tests import game_sequence_direction_1501fe68_native as native
from tools.tests import game_sequence_direction_1501fe68_boundaries as boundaries
from tools.tests import game_sequence_direction_1501fe68_callers as callers
from tools.tests import game_sequence_direction_1501fe68_helpers as helpers
ROOT=source.ROOT
class SequenceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_owner_and_strict_image(self):
  r=self.report;self.assertEqual(r['image'],source.MANIFEST['image']);self.assertEqual(r['image']['changed_bytes'],432);self.assertEqual(r['image']['strict_exclusions'],0);self.assertEqual(r['actual_Make_commands'],3);self.assertEqual(r['non_target_neighbors'],54);self.assertEqual(r['typed_placeholder_helpers'],2);self.assertEqual(r['guards'],8)
 def test_02_original_raw_and_normalized_guest(self):
  r=guest.main();self.assertEqual(r['cases'],590);self.assertEqual(r['coverage'],96);self.assertEqual(r['missing'],[]);self.assertEqual(r['normalized_original_complete_machine_pairs'],590);self.assertTrue(r['FCSR_and_hardware_not_qualified'])
 def test_03_defined_native_and_effective_controls(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==436 and v['effective_completed_controls']==8 and v['UBSan']and v['strict_aliasing']for v in r['profiles'].values()));self.assertTrue(r['unfinished_helpers_modeled_as_typed_providers'])
 def test_04_padding_relocations_and_fault_cuts(self):
  r=boundaries.main();self.assertEqual(r['padders']['byte_and_binding_corruptions'],410);self.assertEqual(r['padders']['individual_guard_corruptions'],8);self.assertEqual(r['rebases']['GNU_linker_comparisons'],16);self.assertEqual(r['rebases']['executions'],64);self.assertEqual(r['faults']['literal_access_cut_triples'],123)
 def test_05_real_caller_window(self):
  r=callers.main();self.assertEqual(r['caller_triples'],112);self.assertTrue(r['delay_store_and_continuation_reload_verified']);self.assertFalse(r['full_parent_or_gameplay_qualified'])
 def test_06_typed_placeholder_effects(self):
  r=helpers.main();self.assertEqual(r['stub_pairs'],128);self.assertEqual(r['direct_caller_linear_windows'],6);self.assertFalse(r['real_helpers_qualified'])
 def test_07_full_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE];payloads={source.NAME:truth}
  for name in ('func_1501F72C','func_1501FFE8'):payloads[name]=source.payload(source.out/'make-shadow/src/game/generated_49D30.c.o',name)[0]
  symbols={v[1]:v for v in source.symbol_rows(before)}
  addresses=[24,source.elf_slot_offset(before,source.ENTRY,384),source.elf_slot_offset(before,source.ENTRY+380,4),source.elf_slot_offset(before,0x800A2CD0,1)]
  for name in payloads:
   row=symbols[name];addresses.extend((source.elf_slot_offset(before,row[2][1],1),row[0]+8))
  for at in addresses:
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),payloads,source.MANIFEST['image']['metadata_groups'])
 def test_08_closed_inputs_addresses_and_guard_history(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact']);self.assertTrue((source.out/'proposed-guards.csv').read_bytes().startswith((source.out/'frozen/conker/retail_word_patches.us.csv').read_bytes()))
if __name__=='__main__':unittest.main()
