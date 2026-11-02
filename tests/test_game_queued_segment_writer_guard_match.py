"""Guard, owner, caller and complete-image gates for func_1510D8C0."""

import csv
import hashlib
from pathlib import Path
import struct
import unittest

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_queued_segment_writer_guard_match as source
from tools.experiments.game_four_head_lookup_match import payload


class QueuedSegmentWriterGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        values = source.prepare(cls.root)
        (cls.baseline, cls.guards, cls.qualified, cls.first_link,
         cls.first_map, cls.expected) = values
        cls.retail, cls.template = source.retail_slots(cls.baseline["rom"].read_bytes())

    def test_01_exact_guarded_slot_relocations_and_staleness(self):
        raw, bindings = source.source_slot(self.baseline["object"])
        self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest(), bindings),
                         (source.SIZE, source.RAW_SLOT_SHA, source.CANDIDATE_BINDINGS))
        with self.guards.open(newline="") as stream:
            rows = [row for row in csv.DictReader(stream)
                    if row["function"] == source.FUNCTION]
        self.assertEqual(len(rows), 38)
        self.assertTrue(all(row["filename"] == source.OWNER and not row["insert_after"]
                            and row["omit"] == "false" for row in rows))
        qualified, qualified_bindings = payload(self.qualified, source.FUNCTION)
        self.assertEqual(qualified, self.template[:source.RAW_SIZE])
        self.assertEqual(qualified_bindings, source.RETAIL_BINDINGS)
        before = self.baseline["guards"].read_bytes()
        self.assertEqual(source.guard_manifest(before, raw, bindings, self.template),
                         self.guards.read_bytes())
        for offset in (0, 0x28, 0x64, 0x9C):
            changed = bytearray(raw)
            changed[offset + 3] ^= 1
            with self.assertRaises(ValueError):
                source.guard_manifest(before, bytes(changed), bindings, self.template)

    def test_02_single_caller_and_existing_semantic_source(self):
        rom = self.baseline["rom"].read_bytes()
        jal = 0x0C000000 | ((source.ENTRY >> 2) & 0x03FFFFFF)
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == jal], [0x140F84])
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == source.ENTRY], [])
        text = self.baseline["source"].read_text()
        self.assertIn("Gfx *func_1510D8C0(Gfx *arg0, s32 arg1)", text)
        self.assertEqual(text.count("gSPSegment(arg0++"), 2)

    def test_03_complete_image_closure_protected_data_and_install_state(self):
        expected = source.expected_image(self.baseline["elf"].read_bytes(), self.retail)
        self.assertEqual(self.expected.read_bytes(), expected)
        self.assertEqual(self.first_link.read_bytes(), expected)
        proof = source.closure_audit(self.baseline["elf"], self.first_link)
        self.assertEqual((proof["changed_bodies"], proof["strict_exclusions"]),
                         ([source.FUNCTION], 0))
        data = audit_layout(self.first_link, self.root / "conker")
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))

        current_guards = (self.root / source.PATHS["guards"]).read_bytes()
        installed = current_guards == self.guards.read_bytes()
        self.assertIn(current_guards, (self.baseline["guards"].read_bytes(),
                                       self.guards.read_bytes()))
        if not installed:
            for key in ("source", "object", "elf", "map", "linker", "progress"):
                self.assertEqual((self.root / source.PATHS[key]).read_bytes(),
                                 self.baseline[key].read_bytes(), key)
            return
        current_elf = self.root / source.PATHS["elf"]
        self.assertEqual(current_elf.read_bytes(), expected)
        source.closure_audit(self.baseline["elf"], current_elf)
        data = audit_layout(current_elf, self.root / "conker")
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))


if __name__ == "__main__":
    unittest.main()
