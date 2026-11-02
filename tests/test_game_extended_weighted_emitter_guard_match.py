"""Guard, relocation, owner, and image gates for func_150E9178."""

import csv
import io
from pathlib import Path
import struct
import subprocess
import unittest

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_extended_weighted_emitter_guard_match as match
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import emit_padded_assembly, parse_object, parse_relocation_spec


class GameExtendedWeightedEmitterGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / "conker/build/game-extended-weighted-emitter-150E9178-match"
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.candidate, cls.linked_words = match.compile_candidate(cls.root, cls.output)
        cls.rows = match.guard_rows(cls.root, cls.candidate, cls.linked_words)
        cls.isolated_guards = cls.output / "isolated-guards.csv"
        match.write_rows(cls.isolated_guards, cls.rows)

        cls.layout = cls.output / "isolated-layout.s"
        lines = ["glabel " + match.FUNCTION]
        for index in range(match.WORDS):
            lines.append("/* %06X %08X 00000000 */ nop" %
                         (match.ROM + index * 4, match.ENTRY + index * 4))
        cls.layout.write_text("\n".join(lines) + "\n")
        cls.guarded_asm = cls.output / "isolated-guarded.s"
        cls.guarded_asm.write_text(emit_padded_assembly(
            cls.candidate, cls.layout, word_patches_path=cls.isolated_guards,
            filename=match.FILENAME))
        cls.guarded_obj = cls.output / "isolated-guarded.o"
        subprocess.run(
            ["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
             "-mabi=32", "-o", str(cls.guarded_obj), str(cls.guarded_asm)],
            check=True, capture_output=True)

        cls.current_guards = cls.root / "conker/retail_word_patches.us.csv"
        current = cls.current_guards.read_bytes()
        with cls.current_guards.open(newline="") as stream:
            installed = [row for row in csv.DictReader(stream)
                         if row["function"] == match.FUNCTION]
        cls.installed = bool(installed)
        if installed:
            if installed != cls.rows:
                raise ValueError("Installed extended-emitter guards differ from qualification")
            combined = current
        else:
            if not current.endswith((b"\n", b"\r")):
                raise ValueError("Guard table has no terminating newline")
            combined = current + match.suffix_bytes(cls.rows)
        cls.combined_guards = cls.output / "qualified-guards.csv"
        cls.combined_guards.write_bytes(combined)

        owner_source = (cls.root / match.SOURCE).read_text()
        cls.compact_owner, diagnostics = compile_owner(
            cls.root, cls.output, owner_source, "qualified-owner-compact")
        if diagnostics:
            raise ValueError("Extended-emitter owner compiler diagnostics changed: " + diagnostics)
        cls.owner_asm = cls.output / "qualified-owner.s"
        cls.owner_asm.write_text(emit_padded_assembly(
            cls.compact_owner, cls.root / "conker/asm/113D60.s",
            word_patches_path=cls.combined_guards, filename=match.FILENAME,
            rodata_symbol="D_800A1350"))
        cls.qualified_owner = cls.output / "qualified-owner.o"
        subprocess.run(
            ["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
             "-mabi=32", "-I", str(cls.root / "conker/include"),
             "-o", str(cls.qualified_owner), str(cls.owner_asm)],
            check=True, capture_output=True)

    @staticmethod
    def function_blob(path, name):
        text, functions, relocations = parse_object(path)
        function = functions[name]
        start, end = function["value"], function["value"] + function["size"]
        bindings = {offset - start: rows for offset, rows in relocations.items()
                    if start <= offset < end}
        return text[start:end], bindings

    @staticmethod
    def relocated(raw, bindings, symbols):
        result = bytearray(raw)
        for offset, rows in bindings.items():
            word = struct.unpack_from(">I", result, offset)[0]
            for kind, symbol in rows:
                value = symbols[symbol]
                if kind == "R_MIPS_HI16":
                    word = word & 0xFFFF0000 | ((value + 0x8000) >> 16 & 0xFFFF)
                elif kind == "R_MIPS_LO16":
                    word = word & 0xFFFF0000 | (value & 0xFFFF)
                elif kind == "R_MIPS_26":
                    word = word & 0xFC000000 | (value >> 2 & 0x03FFFFFF)
                else:
                    raise AssertionError((offset, kind, symbol))
            struct.pack_into(">I", result, offset, word)
        return tuple(struct.unpack(">%dI" % (len(result) // 4), result))

    def normalized_candidate(self):
        raw, bindings = payload(self.candidate, match.FUNCTION)
        result = bytearray(raw)
        normalized = {offset: list(rows) for offset, rows in bindings.items()}
        for row in self.rows:
            offset = int(row["offset"], 0)
            struct.pack_into(">I", result, offset, int(row["replacement"], 0))
            normalized[offset] = parse_relocation_spec(row["replacement_relocations"])
            if not normalized[offset]:
                normalized.pop(offset, None)
        return bytes(result), normalized

    def link_isolated(self, entry, symbols, label):
        script = self.output / (label + ".ld")
        elf = self.output / (label + ".elf")
        binary = self.output / (label + ".bin")
        script.write_text("SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n" % entry)
        subprocess.run(
            ["mips-linux-gnu-ld", "-m", "elf32btsmip", "-T", str(script),
             "-e", match.FUNCTION,
             *("--defsym=%s=0x%X" % item for item in symbols.items()),
             "-o", str(elf), str(self.guarded_obj)],
            check=True, capture_output=True)
        subprocess.run(
            ["mips-linux-gnu-objcopy", "-O", "binary", "-j", ".text",
             str(elf), str(binary)], check=True, capture_output=True)
        data = binary.read_bytes()
        self.assertGreaterEqual(len(data), match.WORDS * 4)
        self.assertFalse(any(data[match.WORDS * 4:]))
        return tuple(struct.unpack_from(">%dI" % match.WORDS, data))

    def test_01_all_54_checked_words_close_the_complete_retail_slot(self):
        self.assertEqual(len(self.rows), 54)
        self.assertEqual(tuple(int(row["offset"], 0) for row in self.rows), match.OFFSETS)
        self.assertTrue(all(row["filename"] == match.FILENAME and
                            row["function"] == match.FUNCTION and
                            row["omit"] == "false" and not row["insert_after"]
                            for row in self.rows))
        raw, bindings = self.normalized_candidate()
        guarded_raw, guarded_bindings = payload(self.guarded_obj, match.FUNCTION)
        self.assertEqual((guarded_raw, guarded_bindings), (raw, bindings))
        self.assertEqual(len(raw), match.WORDS * 4)
        self.assertEqual(0x10000 - (struct.unpack_from(">I", raw)[0] & 0xFFFF),
                         match.RETAIL_FRAME)

    def test_02_original_link_and_three_independent_rebases(self):
        raw, bindings = self.normalized_candidate()
        for index, entry in enumerate((match.ENTRY, 0x17007FFC, 0x2500FFFC)):
            if index == 0:
                symbols = dict(match.SYMBOLS)
            else:
                call_base = (entry + 0x10000) & 0xFFF00000
                data_base = 0x80400000 + index * 0x110000
                symbols = {}
                for ordinal, name in enumerate(match.SYMBOLS):
                    symbols[name] = (call_base + 0x1000 + ordinal * 0x104
                                     if name.startswith("func_") or name == "memcpy"
                                     else data_base + 0x7FF0 + ordinal * 0x10004)
            self.assertEqual(self.link_isolated(entry, symbols, "rebase-%d" % index),
                             self.relocated(raw, bindings, symbols))
        retail = struct.unpack_from(">%dI" % match.WORDS,
                                    (self.root / "conker/conker.us.bin").read_bytes(),
                                    match.ROM)
        self.assertEqual(self.link_isolated(match.ENTRY, match.SYMBOLS, "retail-link"), retail)

    def test_03_each_expected_word_and_relocation_guard_fails_closed(self):
        fields = tuple(self.rows[0])
        failures = 0
        for index, row in enumerate(self.rows):
            for field, value in (("expected", "0x%08X" % (int(row["expected"], 0) ^ 1)),
                                 ("expected_relocations", "R_MIPS_HI16:wrong_symbol")):
                changed = [dict(item) for item in self.rows]
                changed[index][field] = value
                stream = io.StringIO(newline="")
                writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(changed)
                path = self.output / ("stale-%02d-%s.csv" % (index, field))
                path.write_text(stream.getvalue())
                with self.assertRaisesRegex(ValueError, "stale word patch|stale relocations"):
                    emit_padded_assembly(self.candidate, self.layout,
                                         word_patches_path=path,
                                         filename=match.FILENAME)
                failures += 1
        self.assertEqual(failures, 108)

    def test_04_actual_owner_preserves_all_28_neighbors_and_relocations(self):
        production = self.root / "conker/build/src/game/generated_113D60.c.o"
        _, production_functions, _ = parse_object(production)
        _, qualified_functions, _ = parse_object(self.qualified_owner)
        self.assertEqual(set(qualified_functions), set(production_functions))
        neighbors = 0
        for name in production_functions:
            if name == match.FUNCTION:
                continue
            self.assertEqual(self.function_blob(self.qualified_owner, name),
                             self.function_blob(production, name), name)
            neighbors += 1
        self.assertEqual(neighbors, 28)
        self.assertEqual(self.function_blob(self.qualified_owner, match.FUNCTION),
                         self.normalized_candidate())

    def test_05_strict_full_image_prediction_changes_only_the_target_slot(self):
        current_path = self.root / "conker/build/conker.us.elf"
        current = current_path.read_bytes()
        expected = bytearray(current)
        offset = elf_slot_offset(current, match.ENTRY, match.WORDS * 4)
        retail = (self.root / "conker/conker.us.bin").read_bytes()[
            match.ROM:match.ROM + match.WORDS * 4]
        expected[offset:offset + len(retail)] = retail
        changed = [index for index, (before, after) in enumerate(zip(current, expected))
                   if before != after]
        self.assertTrue(self.installed or changed)
        self.assertTrue(all(offset <= index < offset + len(retail) for index in changed))
        predicted = self.output / "expected-conker.us.elf"
        predicted.write_bytes(expected)
        data = audit_layout(predicted, self.root / "conker")
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))

    def test_06_live_install_is_exact_when_guards_are_present(self):
        production = self.root / "conker/build/src/game/generated_113D60.c.o"
        current_blob = self.function_blob(production, match.FUNCTION)
        if self.installed:
            self.assertEqual(current_blob, self.normalized_candidate())
            elf = (self.root / "conker/build/conker.us.elf").read_bytes()
            offset = elf_slot_offset(elf, match.ENTRY, match.WORDS * 4)
            retail = (self.root / "conker/conker.us.bin").read_bytes()[
                match.ROM:match.ROM + match.WORDS * 4]
            self.assertEqual(elf[offset:offset + len(retail)], retail)
        else:
            retail = (self.root / "conker/conker.us.bin").read_bytes()[
                match.ROM:match.ROM + match.WORDS * 4]
            self.assertEqual(sum(a != b for a, b in zip(
                self.linked_words,
                struct.unpack(">%dI" % match.WORDS, retail))), 54)


if __name__ == "__main__":
    unittest.main()
