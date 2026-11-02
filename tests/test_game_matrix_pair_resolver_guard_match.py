"""Guard recipe, relocation movement, and complete-image closure for func_15031070."""

import csv
import hashlib
import io
from pathlib import Path
import struct
import tempfile
import unittest

from tools.experiments import game_matrix_pair_resolver_guard_match as match
from tools.experiments import game_matrix_pair_resolver_key_candidates as candidate
from tools.experiments import game_matrix_pair_resolver_candidates as compiler
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_four_head_lookup_match import payload
from tools.match_progress import load_elf_functions


class GameMatrixPairResolverGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / "conker/build/game-matrix-pair-resolver-guard-test"
        cls.record, cls.raw_words = compiler.compile_candidate(
            cls.root, cls.output, "guard-current", candidate.SELECTED)
        cls.raw, cls.bindings = payload(cls.output / "guard-current.o", match.FUNCTION)
        cls.retail_bytes, cls.template = match.retail_slots(
            (cls.root / match.PATHS["rom"]).read_bytes())
        cls.retail_words = list(struct.unpack(">85I", cls.retail_bytes))
        cls.production, _, cls.addresses = load_elf_functions(
            str(cls.root / match.PATHS["elf"]), "mips-linux-gnu-objdump")

    def test_nine_checked_guards_reproduce_the_retail_template_and_relocations(self):
        self.assertEqual((self.record["body_words"], self.record["frame"],
                          self.record["differences"]), (84, 32, 40))
        normalized, relocations = match.normalized_payload(self.raw, self.bindings)
        self.assertEqual(normalized, self.template)
        self.assertEqual(relocations, match.RETAIL_BINDINGS)
        rows = match.guard_rows()
        self.assertEqual((len(rows), sum(bool(row["insert_after"]) for row in rows),
                          sum(row["omit"] == "true" for row in rows)), (9, 2, 1))
        self.assertEqual([row["offset"] for row in rows],
            ["0x03C", "0x06C", "0x0A8", "0x0B0", "0x0B4",
             "0x0BC", "0x104", "0x110", "0x114"])

    def test_live_manifest_is_either_the_frozen_predecessor_or_exact_recipe(self):
        path = self.root / match.PATHS["guards"]
        before = path.read_bytes()
        with path.open(newline="") as stream:
            live = list(csv.DictReader(stream))
        target = [row for row in live if row["function"] == match.FUNCTION]
        if target:
            self.assertEqual(target, match.guard_rows())
        else:
            proposed = match.guard_manifest(before, self.raw, self.bindings)
            rows = list(csv.DictReader(io.StringIO(proposed.decode(), newline="")))
            self.assertEqual(rows[-9:], match.guard_rows())
            self.assertEqual(proposed[:len(before)], before)

    def test_production_slot_is_only_predecessor_or_complete_retail_match(self):
        raw_slot = self.raw_words + [0]
        actual = self.production[match.FUNCTION]
        self.assertEqual(self.addresses[match.FUNCTION], match.ENTRY)
        self.assertIn(actual, (raw_slot, self.retail_words))
        if actual == raw_slot:
            self.assertEqual(hashlib.sha256(
                (self.root / match.PATHS["elf"]).read_bytes()).hexdigest(),
                match.BASELINE["elf"])
            return

        installed = (self.root / match.PATHS["elf"]).read_bytes()
        predecessor = bytearray(installed)
        from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
        at = elf_slot_offset(installed, match.ENTRY, match.SIZE)
        predecessor[at:at + match.SIZE] = struct.pack(">85I", *raw_slot)
        rows = [position for position, name, fields, _ in symbol_rows(installed)
                if name == match.FUNCTION and fields[1:3] == (match.ENTRY, match.SIZE)]
        self.assertEqual(len(rows), 1)
        struct.pack_into(">I", predecessor, rows[0] + 8, match.RAW_SIZE)
        predecessor = bytes(predecessor)
        self.assertEqual(hashlib.sha256(predecessor).hexdigest(), match.BASELINE["elf"])
        self.assertEqual(match.expected_image(predecessor, self.retail_bytes), installed)
        with tempfile.TemporaryDirectory() as directory:
            old_path = Path(directory) / "predecessor.elf"
            old_path.write_bytes(predecessor)
            old, _, old_addresses = load_elf_functions(str(old_path), "mips-linux-gnu-objdump")
        changed = [name for name in self.production if old[name] != self.production[name]]
        self.assertEqual(changed, [match.FUNCTION])
        self.assertEqual(old_addresses, self.addresses)


if __name__ == "__main__":
    unittest.main()
