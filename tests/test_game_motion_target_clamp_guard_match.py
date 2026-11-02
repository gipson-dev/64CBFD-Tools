"""Guard, semantics, callback ABI, owner, and image gates for func_150DFCA8."""

import csv
import io
from pathlib import Path
import struct
import subprocess
import unittest

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_motion_target_clamp_guard_match as match
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import (
    SYMBOL, emit_padded_assembly, parse_object, parse_relocation_spec)
from tools.tests import game_motion_target_clamp_native as native
from tools.tests import game_motion_target_clamp_oracle as oracle


class MotionTargetClampGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / "conker/build/game-motion-target-clamp-150DFCA8-guard-match"
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.candidate, cls.linked_words = match.compile_candidate(cls.root, cls.output)
        cls.rows = match.guard_rows(cls.root, cls.candidate, cls.linked_words)
        cls.isolated_guards = cls.output / "isolated-guards.csv"
        match.write_rows(cls.isolated_guards, cls.rows)

        text, functions, relocations = parse_object(cls.candidate)
        isolated_source, unresolved = emit_function(
            text, functions[match.FUNCTION], relocations, match.FUNCTION, match.SYMBOLS)
        if unresolved:
            raise ValueError("Unresolved motion-target bindings: %r" % unresolved)
        cls.isolated_candidate_asm = cls.output / "isolated-candidate.s"
        cls.isolated_candidate_asm.write_text(isolated_source)
        cls.isolated_candidate = cls.output / "isolated-candidate.o"
        subprocess.run(
            ["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
             "-mabi=32", "-o", str(cls.isolated_candidate),
             str(cls.isolated_candidate_asm)], check=True, capture_output=True)

        cls.layout = cls.output / "isolated-layout.s"
        lines = ["glabel " + match.FUNCTION]
        for index in range(match.WORDS):
            lines.append("/* %06X %08X 00000000 */ nop" %
                         (match.ROM + index * 4, match.ENTRY + index * 4))
        cls.layout.write_text("\n".join(lines) + "\n")
        cls.guarded_asm = cls.output / "isolated-guarded.s"
        cls.guarded_asm.write_text(emit_padded_assembly(
            cls.isolated_candidate, cls.layout, word_patches_path=cls.isolated_guards,
            filename=match.FILENAME))
        cls.guarded_obj = cls.output / "isolated-guarded.o"
        subprocess.run(
            ["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
             "-mabi=32", "-I", str(cls.root / "conker/include"),
             "-o", str(cls.guarded_obj), str(cls.guarded_asm)],
            check=True, capture_output=True)

        cls.current_guards = cls.root / "conker/retail_word_patches.us.csv"
        current = cls.current_guards.read_bytes()
        with cls.current_guards.open(newline="") as stream:
            installed = [row for row in csv.DictReader(stream)
                         if row["function"] == match.FUNCTION]
        cls.installed = bool(installed)
        if installed:
            if installed != cls.rows:
                raise ValueError("Installed motion-target guards differ from qualification")
            combined = current
        else:
            if not current.endswith((b"\n", b"\r")):
                raise ValueError("Guard table has no terminating newline")
            combined = current + match.suffix_bytes(cls.rows)
        cls.combined_guards = cls.output / "qualified-guards.csv"
        cls.combined_guards.write_bytes(combined)

        owner_source = match.candidate_owner(cls.root)
        cls.compact_owner, diagnostics = compile_owner(
            cls.root, cls.output, owner_source, "qualified-owner-compact")
        if diagnostics:
            raise ValueError("Motion-target owner diagnostics changed: " + diagnostics)
        cls.owner_asm = cls.output / "qualified-owner.s"
        cls.owner_asm.write_text(emit_padded_assembly(
            cls.compact_owner, cls.root / match.ASM,
            function_objects={match.FUNCTION: cls.candidate},
            word_patches_path=cls.combined_guards, filename=match.FILENAME,
            rodata_symbol="D_800A0FD0"))
        cls.qualified_owner = cls.output / "qualified-owner.o"
        subprocess.run(
            ["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
             "-mabi=32", "-I", str(cls.root / "conker/include"),
             "-o", str(cls.qualified_owner), str(cls.owner_asm)],
            check=True, capture_output=True)

    @staticmethod
    def function_blob(path, name):
        text, functions, relocations = parse_object(path)
        info = functions[name]
        start, end = info["value"], info["value"] + info["size"]
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
        return tuple(struct.unpack(">%dI" % match.WORDS, result))

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

    def predicted_image(self):
        current = (self.root / "conker/build/conker.us.elf").read_bytes()
        expected = bytearray(current)
        offset = elf_slot_offset(current, match.ENTRY, match.WORDS * 4)
        retail = (self.root / "conker/conker.us.bin").read_bytes()[
            match.ROM:match.ROM + match.WORDS * 4]
        expected[offset:offset + len(retail)] = retail
        rows = [(at, fields) for at, name, fields, _ in symbol_rows(current)
                if name == match.FUNCTION]
        self.assertEqual(len(rows), 1)
        at, fields = rows[0]
        self.assertEqual((fields[1], fields[3] & 15), (match.ENTRY, 2))
        if fields[2] == 12:
            changed = list(fields)
            changed[2] = match.WORDS * 4
            SYMBOL.pack_into(expected, at, *changed)
        else:
            self.assertEqual(fields[2], match.WORDS * 4)
        return current, bytes(expected), offset

    def test_01_complete_checked_floating_register_closure(self):
        self.assertEqual(len(self.rows), 24)
        self.assertEqual(tuple(int(row["offset"], 0) for row in self.rows), match.OFFSETS)
        self.assertEqual(sum(row["expected_relocations"] != "-" for row in self.rows), 3)
        raw, bindings = self.normalized_candidate()
        guarded_raw, guarded_bindings = payload(self.guarded_obj, match.FUNCTION)
        self.assertEqual((guarded_raw, guarded_bindings), (raw, bindings))
        candidate = self.linked_words
        retail = struct.unpack_from(">%dI" % match.WORDS,
                                    (self.root / "conker/conker.us.bin").read_bytes(),
                                    match.ROM)
        for offset in match.OFFSETS:
            left, right = candidate[offset // 4], retail[offset // 4]
            op = left >> 26
            self.assertEqual(op, right >> 26)
            if op in (49, 57):
                mask = ~(31 << 16) & 0xFFFFFFFF
            else:
                self.assertEqual(op, 17)
                mask = ~((31 << 16) | (31 << 11) | (31 << 6)) & 0xFFFFFFFF
            self.assertEqual(left & mask, right & mask)

    def test_02_original_link_and_three_independent_rebases(self):
        raw, bindings = self.normalized_candidate()
        layouts = (
            (match.ENTRY, match.SYMBOLS),
            (0x17007FFC, {
                "D_800A0FA0": 0x80407FF0, "D_800A0FA4": 0x80408004,
                "D_800A0FA8": 0x80418000, "D_800A0FAC": 0x8041FFFC,
                "D_800BE9E4": 0x80528004,
            }),
            (0x2500FFFC, {
                "D_800A0FA0": 0x80637FFC, "D_800A0FA4": 0x80638000,
                "D_800A0FA8": 0x80648004, "D_800A0FAC": 0x8064FFF0,
                "D_800BE9E4": 0x8075FFFC,
            }),
        )
        for index, (entry, symbols) in enumerate(layouts):
            self.assertEqual(self.link_isolated(entry, symbols, "rebase-%d" % index),
                             self.relocated(raw, bindings, symbols))
        retail = struct.unpack_from(">%dI" % match.WORDS,
                                    (self.root / "conker/conker.us.bin").read_bytes(),
                                    match.ROM)
        self.assertEqual(self.link_isolated(match.ENTRY, match.SYMBOLS, "retail-link"),
                         retail)

    def test_03_each_expected_word_and_relocation_guard_fails_closed(self):
        failures = 0
        for index, row in enumerate(self.rows):
            for field, value in (("expected", "0x%08X" % (int(row["expected"], 0) ^ 1)),
                                 ("expected_relocations", "R_MIPS_HI16:wrong_symbol")):
                changed = [dict(item) for item in self.rows]
                changed[index][field] = value
                stream = io.StringIO(newline="")
                writer = csv.DictWriter(stream, fieldnames=tuple(self.rows[0]),
                                        lineterminator="\n")
                writer.writeheader()
                writer.writerows(changed)
                path = self.output / ("stale-%02d-%s.csv" % (index, field))
                path.write_text(stream.getvalue())
                with self.assertRaisesRegex(ValueError, "stale word patch|stale relocations"):
                    emit_padded_assembly(self.isolated_candidate, self.layout,
                                         word_patches_path=path,
                                         filename=match.FILENAME)
                failures += 1
        self.assertEqual(failures, 48)

    def test_04_guest_semantics_callback_abi_and_native_controls(self):
        retail = struct.unpack_from(">%dI" % match.WORDS,
                                    (self.root / "conker/conker.us.bin").read_bytes(),
                                    match.ROM)
        guarded = self.link_isolated(match.ENTRY, match.SYMBOLS, "semantic-guarded")
        report = oracle.qualify(self.root, (retail, self.linked_words, guarded))
        self.assertEqual((report["cases"], report["executions"], report["covered_words"]),
                         (1167, 3501, 60))
        self.assertEqual(report["paths"], {"low": 400, "middle": 434, "high": 333})
        self.assertEqual((report["alias_cases"], report["caller_cases"]), (15, 3))
        reports = native.qualify(self.root, self.output)
        self.assertEqual(len(reports), 3)
        for item in reports:
            self.assertEqual((item["cases"], item["executions"], len(item["controls"])),
                             (1152, 11520, 9))

    def test_05_owner_neighbors_image_prediction_and_protected_data(self):
        production = self.root / "conker/build/src/game/generated_10CD70.c.o"
        neighbors = same_functions(production, self.qualified_owner, (match.FUNCTION,))
        self.assertGreaterEqual(neighbors, 10)
        self.assertEqual(self.function_blob(self.qualified_owner, match.FUNCTION),
                         self.normalized_candidate())
        current, expected, offset = self.predicted_image()
        changed = [index for index, pair in enumerate(zip(current, expected))
                   if pair[0] != pair[1]]
        self.assertTrue(self.installed or changed)
        slot = range(offset, offset + match.WORDS * 4)
        symbol_offsets = set()
        for at, name, _, _ in symbol_rows(current):
            if name == match.FUNCTION:
                symbol_offsets.update(range(at + 8, at + 12))
        self.assertTrue(all(index in slot or index in symbol_offsets for index in changed))
        predicted = self.output / "expected-conker.us.elf"
        predicted.write_bytes(expected)
        data = audit_layout(predicted, self.root / "conker")
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))

    def test_06_live_install_exact_when_source_and_guards_are_present(self):
        production = self.root / "conker/build/src/game/generated_10CD70.c.o"
        source = (self.root / match.SOURCE).read_text()
        if self.installed:
            self.assertIn(match.BODY.rstrip(), source)
            self.assertEqual(production.read_bytes(), self.qualified_owner.read_bytes())
            current, expected, _ = self.predicted_image()
            self.assertEqual(current, expected)
        else:
            self.assertIn("s32 func_150DFCA8() {\n    return 0;\n}", source)
            self.assertNotEqual(self.function_blob(production, match.FUNCTION),
                                self.normalized_candidate())


if __name__ == "__main__":
    unittest.main()
