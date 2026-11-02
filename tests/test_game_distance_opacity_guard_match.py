"""Guard, owner, and complete-image gates for func_15179CB0."""
from pathlib import Path
import unittest

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_distance_opacity_guard_match as match
from tools.experiments.game_four_head_lookup_match import payload
from tools.pad_generated_object import parse_object


class GameDistanceOpacityGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / match.BUILD
        (cls.report, cls.rows, cls.candidate, cls.predecessor_owner,
         cls.qualified_owner, cls.predecessor_elf, cls.qualified_elf) = match.prepare(
             cls.root, cls.output)
        cls.retail = match.retail_slot(cls.root)

    @staticmethod
    def function_blob(path, name):
        text, functions, relocations = parse_object(path)
        function = functions[name]
        start, end = function["value"], function["value"] + function["size"]
        bindings = {offset - start: rows for offset, rows in relocations.items()
                    if start <= offset < end}
        return text[start:end], bindings

    def test_01_one_checked_word_reproduces_body_and_owner_tail(self):
        raw, bindings = payload(self.candidate, match.FUNCTION)
        self.assertEqual(bindings, match.BINDINGS)
        self.assertEqual(match.normalized_slot(raw, self.rows), self.retail)
        self.assertEqual((len(self.rows), self.report["replacements"],
                          self.report["omissions"], self.report["insertions"]),
                         (1, 1, 0, 0))
        self.assertEqual((self.report["body_words"], self.report["tail_words"]),
                         (62, 2))

    def test_02_expected_word_guard_fails_closed(self):
        path = self.output / "stale-guards.csv"
        original = (self.output / "qualified-guards.csv").read_bytes()
        needle = b"generated_1A6360,func_15179CB0,0x060,0x46080282,"
        changed = original.replace(
            needle, b"generated_1A6360,func_15179CB0,0x060,0x46080283,")
        self.assertNotEqual(changed, original)
        path.write_bytes(changed)
        proposed, _ = match.candidate.production_source(
            (self.root / match.SOURCE).read_text())
        with self.assertRaisesRegex(ValueError, "stale word patch"):
            match.build_owner(self.root, self.output, proposed, path, "stale-owner")

    def test_03_actual_owner_preserves_all_eight_neighbors(self):
        _, predecessor_functions, _ = parse_object(self.predecessor_owner)
        _, qualified_functions, _ = parse_object(self.qualified_owner)
        self.assertEqual(set(predecessor_functions), set(qualified_functions))
        self.assertEqual(len(qualified_functions), 9)
        for name in qualified_functions:
            if name != match.FUNCTION:
                self.assertEqual(self.function_blob(self.predecessor_owner, name),
                                 self.function_blob(self.qualified_owner, name), name)
        raw, bindings = self.function_blob(self.qualified_owner, match.FUNCTION)
        self.assertEqual(match.linked_payload(raw), self.retail[:match.BODY_SIZE])
        self.assertEqual(bindings, match.BINDINGS)

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
        _, functions, _ = parse_object(expected_owner)
        for name in functions:
            self.assertEqual(self.function_blob(current_owner, name),
                             self.function_blob(expected_owner, name), name)
        current_elf = (self.root / match.PATHS["elf"]).read_bytes()
        expected_elf = (self.qualified_elf if self.report["image_installed"]
                        else self.predecessor_elf)
        self.assertEqual(current_elf, expected_elf.read_bytes())


if __name__ == "__main__":
    unittest.main()
