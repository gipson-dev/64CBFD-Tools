"""Attachment updater: guarded body, real helpers and strict image."""
import unittest
from tools.experiments import game_attachment_1518a094_match as source
from tools.tests import game_attachment_1518a094_oracle as guest
from tools.tests import game_attachment_1518a094_native as native
from tools.tests import game_attachment_1518a094_roles as roles
from tools.tests import game_attachment_1518a094_boundaries as boundaries
from tools.tests import game_attachment_1518a094_caller as caller
from tools.tests import game_attachment_1518a094_connected as connected
from tools.tests import game_attachment_1518a094_matrix as matrix
from tools.tests import game_attachment_1518a094_lookup as lookup
ROOT=source.ROOT
class AttachmentTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertIs(source.q.p,source.q);self.assertEqual(r["image"],source.MANIFEST["image"]);self.assertEqual(r["image"]["changed_bytes"],339);self.assertEqual(r["image"]["strict_exclusions"],0);self.assertEqual(r["non_target_neighbors"],5);self.assertEqual(r["guards"],42)
 def test_02_retail_raw_and_normalized_guest(self):
  r=guest.main();self.assertEqual(r["cases"],2048);self.assertEqual(r["executions"],6144);self.assertEqual(r["retail_words_visited"],95);self.assertTrue(r["normalized_complete_state"])
 def test_03_defined_native_and_controls(self):
  r=native.main();self.assertEqual(set(r["profiles"]),{"-O0","-O2","-O3"});self.assertTrue(all(v["cases"]==1536 and v["negative_controls"]==8 and v["UBSan"] for v in r["profiles"].values()));self.assertTrue(r["negative_subtypes_excluded_from_native"])
 def test_04_guard_roles_and_callback_gate(self):
  r=roles.main();self.assertEqual(r["guard_words"],42);self.assertEqual(r["gate_cases"],1024);self.assertTrue(r["stack_slots_disjoint"])
 def test_05_padding_relocations_and_access_cuts(self):
  r=boundaries.main();self.assertEqual(r["byte_and_binding_corruptions"],394);self.assertEqual(r["individual_guard_corruptions"],42);self.assertEqual(r["GNU_rebased_links"],16);self.assertEqual(r["access_cut_quads"],132)
 def test_06_original_dispatcher_window(self):
  r=caller.main();self.assertEqual(r["cases"],1024);self.assertEqual(r["executions"],3072);self.assertTrue(r["return_controls_removal"])
 def test_07_connected_original_handlers(self):
  r=connected.main();self.assertEqual(r["cases"],768);self.assertEqual(sorted(r["handler_words_visited"].values()),[14,14,14,52])
 def test_08_connected_original_matrix(self):
  r=matrix.main();self.assertEqual(r["cases"],128);self.assertEqual(r["original_matrix_helper_words_visited"],40);self.assertTrue(r["finite_float_inputs_only"])
 def test_09_connected_original_lookup(self):
  r=lookup.main();self.assertEqual(r["cases"],162);self.assertEqual(r["actor_slots_tested"],26);self.assertEqual(r["original_lookup_words_visited"],68)
 def test_10_full_image_corruptions(self):
  before=(source.out/"frozen/conker/build/conker.us.elf").read_bytes();actual=(source.out/"qualified-image.elf").read_bytes();truth=(ROOT/"conker/conker.us.bin").read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before)if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,384),source.q.elf_slot_offset(before,source.ENTRY+380,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST["image"]["metadata_groups"])
 def test_11_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report["source_installed"]);self.assertTrue(self.report["all_addresses_fixed"]);self.assertEqual(self.report["functions"],6050);self.assertTrue(self.report["protected_data"]["exact"]);self.assertTrue((source.out/"proposed-guards.csv").read_bytes().startswith((source.out/"frozen/conker/retail_word_patches.us.csv").read_bytes()))
if __name__=="__main__":unittest.main()
