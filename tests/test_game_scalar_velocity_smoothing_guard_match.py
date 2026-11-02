"""Guard, owner, and complete-image gates for func_150495B0."""

import csv
import io
from pathlib import Path
import struct
import subprocess
import unittest

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_scalar_velocity_smoothing_guard_match as match
from tools.experiments.game_four_head_lookup_match import payload
from tools.pad_generated_object import emit_padded_assembly, parse_object


class GameScalarVelocitySmoothingGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / match.BUILD
        (cls.report, cls.rows, cls.candidate, cls.predecessor_owner,
         cls.qualified_owner, cls.predecessor_elf, cls.qualified_elf) = match.prepare(
             cls.root, cls.output)
        cls.retail = match.retail_bytes(cls.root)

    def function_blob(self, path, name):
        text, functions, relocations = parse_object(path)
        function = functions[name]
        start, end = function["value"], function["value"] + function["size"]
        bindings = {offset - start: rows for offset, rows in relocations.items()
                    if start <= offset < end}
        return text[start:end], bindings

    def test_01_twenty_three_checked_rows_reproduce_complete_retail_slot(self):
        raw, bindings = payload(self.candidate, match.FUNCTION)
        self.assertFalse(bindings)
        self.assertEqual(match.normalized_payload(raw, self.rows), self.retail)
        self.assertEqual((len(self.rows), self.report["replacements"],
                          self.report["omissions"], self.report["insertions"]),
                         (23, 22, 1, 0))
        self.assertEqual(tuple(int(row["offset"], 0) for row in self.rows), match.OFFSETS)
        self.assertTrue(all(row["expected_relocations"] == "-" and
                            row["replacement_relocations"] == "-"
                            for row in self.rows))

    def test_02_every_expected_word_guard_fails_closed(self):
        layout = self.output / "guard-failure-layout.s"
        layout.write_text("\n".join(["glabel " + match.FUNCTION] + [
            "/* %06X %08X 00000000 */ nop" %
            (match.ROM + index * 4, match.ENTRY + index * 4)
            for index in range(match.RETAIL_WORDS)]) + "\n")
        fields = tuple(self.rows[0])
        failures = 0
        for index, row in enumerate(self.rows):
            changed = [dict(item) for item in self.rows]
            changed[index]["expected"] = "0x%08X" % (int(row["expected"], 0) ^ 1)
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(changed)
            path = self.output / ("stale-%02d.csv" % index)
            path.write_text(stream.getvalue())
            with self.assertRaisesRegex(ValueError, "stale word patch"):
                emit_padded_assembly(self.candidate, layout, word_patches_path=path,
                                     filename=match.FILENAME)
            failures += 1
        self.assertEqual(failures, 23)

    def test_03_actual_owner_preserves_the_neighbor_and_matches_retail(self):
        predecessor_text, predecessor_functions, _ = parse_object(self.predecessor_owner)
        qualified_text, qualified_functions, _ = parse_object(self.qualified_owner)
        self.assertEqual(set(predecessor_functions), set(qualified_functions))
        self.assertEqual(set(qualified_functions), {match.FUNCTION, "func_15049688"})
        self.assertEqual(self.function_blob(self.predecessor_owner, "func_15049688"),
                         self.function_blob(self.qualified_owner, "func_15049688"))
        self.assertEqual(self.function_blob(self.qualified_owner, match.FUNCTION),
                         (self.retail, {}))
        self.assertGreaterEqual(len(predecessor_text), match.RETAIL_SIZE)
        self.assertGreaterEqual(len(qualified_text), match.RETAIL_SIZE)

    def test_04_private_full_image_is_literal_prediction_with_no_exclusions(self):
        predicted = match.expected_image(self.predecessor_elf.read_bytes(), self.retail)
        self.assertEqual(self.qualified_elf.read_bytes(), predicted)
        self.assertEqual(self.report["closure"]["changed_bodies"], [match.FUNCTION])
        self.assertTrue(self.report["closure"]["all_addresses_fixed"])
        self.assertEqual(self.report["closure"]["strict_exclusions"], 0)
        data = audit_layout(self.qualified_elf, self.root / "conker")
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))

    def test_05_live_source_guards_owner_and_image_are_one_qualified_state(self):
        current_source = (self.root / match.SOURCE).read_text()
        _, source_installed = match.candidate.production_source(current_source)
        self.assertEqual(source_installed, self.report["installed"])
        current_owner = self.root / match.PATHS["object"]
        expected_owner = self.qualified_owner if source_installed else self.predecessor_owner
        for name in (match.FUNCTION, "func_15049688"):
            self.assertEqual(self.function_blob(current_owner, name),
                             self.function_blob(expected_owner, name), name)
        current_elf = (self.root / match.PATHS["elf"]).read_bytes()
        expected_elf = (self.qualified_elf if self.report["image_installed"]
                        else self.predecessor_elf)
        self.assertEqual(current_elf, expected_elf.read_bytes())


if __name__ == "__main__":
    unittest.main()
