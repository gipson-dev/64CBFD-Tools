"""Guard, owner, and complete-image gates for func_150A23E4."""

import csv
import io
from pathlib import Path
import struct
import unittest

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_record_sound_start_guard_match as match
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_four_head_lookup_match import payload
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools


class GameRecordSoundStartGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / match.BUILD
        (cls.report, cls.rows, cls.candidate, cls.predecessor_owner,
         cls.qualified_owner, cls.predecessor_elf,
         cls.qualified_elf) = match.prepare(cls.root, cls.output)
        cls.retail = match.retail_bytes(cls.root)
        cls.retail_raw, cls.retail_bindings = match.retail_object_payload(cls.root)

    def function_blob(self, path, name):
        text, functions, relocations = parse_object(path)
        function = functions[name]
        start, end = function["value"], function["value"] + function["size"]
        bindings = {offset - start: rows for offset, rows in relocations.items()
                    if start <= offset < end}
        return text[start:end], bindings

    def test_01_nine_checked_rows_and_one_insertion_reproduce_retail(self):
        raw, bindings = payload(self.candidate, match.FUNCTION)
        self.assertEqual((raw, bindings),
                         (match.candidate.checked_payload(raw, bindings)))
        self.assertEqual(match.normalized_payload(raw, self.rows), self.retail_raw)
        self.assertEqual((len(self.rows), self.report["replacements"],
                          self.report["insertions"]), (9, 9, 1))
        self.assertEqual(tuple(int(row["offset"], 0) for row in self.rows),
                         match.OFFSETS)
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
            changed[index]["expected"] = "0x%08X" % (
                int(row["expected"], 0) ^ 1)
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(changed)
            path = self.output / ("stale-%02d.csv" % index)
            path.write_text(stream.getvalue())
            with self.assertRaisesRegex(ValueError, "stale word patch"):
                emit_padded_assembly(
                    self.candidate, layout, word_patches_path=path,
                    filename=match.FILENAME)
            failures += 1
        self.assertEqual(failures, 9)

    def test_03_owner_neighbors_pools_and_target_are_closed(self):
        self.assertEqual(same_functions(
            self.predecessor_owner, self.qualified_owner,
            (match.FUNCTION,)), 27)
        self.assertEqual(normalized_pools(self.predecessor_owner),
                         normalized_pools(self.qualified_owner))
        self.assertEqual(self.function_blob(self.qualified_owner, match.FUNCTION),
                         (self.retail_raw, self.retail_bindings))

    def test_04_full_image_is_literal_prediction_with_no_exclusions(self):
        predicted = match.expected_image(
            self.predecessor_elf.read_bytes(), self.retail)
        self.assertEqual(self.qualified_elf.read_bytes(), predicted)
        self.assertEqual(self.report["closure"]["changed_bodies"],
                         [match.FUNCTION])
        self.assertTrue(self.report["closure"]["all_addresses_fixed"])
        self.assertEqual(self.report["closure"]["strict_exclusions"], 0)
        data = audit_layout(self.qualified_elf, self.root / "conker")
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))

    def test_05_live_source_guards_owner_and_image_form_one_state(self):
        _, installed = match.candidate.production_source(
            (self.root / match.SOURCE).read_text())
        self.assertEqual(installed, self.report["installed"])
        with (self.root / match.PATHS["guards"]).open(newline="") as stream:
            live = [row for row in csv.DictReader(stream)
                    if row["function"] == match.FUNCTION]
        self.assertEqual(live, self.rows if installed else [])
        expected_owner = (self.qualified_owner if installed
                          else self.predecessor_owner)
        current_owner = self.root / match.OBJECT
        self.assertEqual(self.function_blob(current_owner, match.FUNCTION),
                         self.function_blob(expected_owner, match.FUNCTION))
        self.assertEqual(normalized_pools(current_owner),
                         normalized_pools(expected_owner))
        current_elf = (self.root / match.PATHS["elf"]).read_bytes()
        expected_elf = (self.qualified_elf if self.report["image_installed"]
                        else self.predecessor_elf)
        self.assertEqual(current_elf, expected_elf.read_bytes())


if __name__ == "__main__":
    unittest.main()
