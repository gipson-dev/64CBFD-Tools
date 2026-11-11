"""Packed-record update: guarded temporaries, real helpers and strict image."""
import unittest
from tools.experiments import game_packed_motion_1516a648_match as source
from tools.tests import game_packed_motion_1516a648_oracle as guest
from tools.tests import game_packed_motion_1516a648_native as native
from tools.tests import game_packed_motion_1516a648_roles as roles
from tools.tests import game_packed_motion_1516a648_boundaries as boundaries
from tools.tests import game_packed_motion_1516a648_caller as caller
from tools.tests import game_packed_motion_1516a648_connected as connected
ROOT=source.ROOT
class MotionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_and_strict_image(self):
  r=self.report;self.assertIs(source.q.p,source.q);self.assertEqual(r["image"],source.MANIFEST["image"]);self.assertEqual(r["image"]["changed_bytes"],221);self.assertEqual(r["image"]["strict_exclusions"],0);self.assertEqual(r["non_target_neighbors"],3);self.assertEqual(r["guards"],6);self.assertEqual(r["padding_words"],1)
 def test_02_retail_raw_and_normalized_guest(self):
  r=guest.main();self.assertEqual(r["cases"],2816);self.assertEqual(r["executions"],8448);self.assertEqual(r["retail_words_visited"],72);self.assertTrue(r["normalized_complete_state"])
 def test_03_defined_native_and_controls(self):
  r=native.main();self.assertEqual(set(r["profiles"]),{"-O0","-O2","-O3"});self.assertTrue(all(v["cases"]==768 and v["negative_controls"]==10 and v["UBSan"] for v in r["profiles"].values()))
 def test_04_closed_register_roles(self):
  r=roles.main();self.assertEqual(r["guard_words"],6);self.assertEqual(len(r["closed_temporary_pairs"]),3);self.assertTrue(r["delay_slot_store_before_call"])
 def test_05_padding_relocations_and_access_cuts(self):
  r=boundaries.main();self.assertEqual(r["byte_and_binding_corruptions"],306);self.assertEqual(r["individual_guard_corruptions"],6);self.assertEqual(r["GNU_rebased_links"],16);self.assertEqual(r["access_cut_quads"],89);self.assertEqual(r["padding_words"],1)
 def test_06_original_dispatcher_window(self):
  r=caller.main();self.assertEqual(r["cases"],512);self.assertEqual(r["executions"],1536);self.assertTrue(r["return_one_selects_removal"])
 def test_07_connected_original_helpers(self):
  r=connected.main();self.assertEqual(r["cases"],2250);self.assertEqual(sorted(r["original_helpers"].values()),[12,12,14,34]);self.assertTrue(r["height_helper_modeled"])
 def test_08_full_image_corruptions(self):
  before=(source.out/"frozen/conker/build/conker.us.elf").read_bytes();actual=(source.out/"qualified-image.elf").read_bytes();truth=(ROOT/"conker/conker.us.bin").read_bytes()[source.ROM:source.ROM+source.SIZE];symbol=next(v for v in source.q.symbol_rows(before)if v[1]==source.NAME)
  for at in (24,source.q.elf_slot_offset(before,source.ENTRY,292),source.q.elf_slot_offset(before,source.ENTRY+288,4),source.q.elf_slot_offset(before,source.ENTRY+292,4),source.q.elf_slot_offset(before,0x800A2CD0,1),symbol[0]+8):
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),{source.NAME:truth},source.MANIFEST["image"]["metadata_groups"])
 def test_09_closed_inputs_and_guard_history(self):
  source.live_inputs(self.report["source_installed"]);self.assertTrue(self.report["all_addresses_fixed"]);self.assertEqual(self.report["functions"],6050);self.assertTrue(self.report["protected_data"]["exact"]);self.assertTrue((source.out/"proposed-guards.csv").read_bytes().startswith((source.out/"frozen/conker/retail_word_patches.us.csv").read_bytes()))
if __name__=="__main__":unittest.main()
