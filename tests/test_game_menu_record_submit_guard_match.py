"""Guard, semantics, caller, owner, and image gates for func_151E2404."""

import csv
import io
from pathlib import Path
import struct
import subprocess
import unittest

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_menu_record_submit_guard_match as match
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import (
    SYMBOL, emit_padded_assembly, parse_object, parse_relocation_spec)
from tools.tests import game_menu_record_submit_native as native
from tools.tests import game_menu_record_submit_oracle as oracle


class MenuRecordSubmitGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / "conker/build/game-menu-record-submit-151E2404-guard-match"
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.candidate, cls.linked_words = match.compile_candidate(cls.root, cls.output)
        cls.rows = match.guard_rows(cls.root, cls.candidate, cls.linked_words)
        cls.isolated_guards = cls.output / "isolated-guards.csv"
        match.write_rows(cls.isolated_guards, cls.rows)

        text, functions, relocations = parse_object(cls.candidate)
        info = functions[match.FUNCTION]
        lines = [".section .text", ".balign 4", ".globl " + match.FUNCTION,
                 ".type " + match.FUNCTION + ", @function", match.FUNCTION + ":"]
        for offset in range(info["value"], info["value"] + info["size"], 4):
            for kind, symbol in relocations.get(offset, ()):
                if symbol == ".rodata":
                    symbol = match.RODATA_SYMBOL
                lines.append(".reloc ., %s, %s" % (kind, symbol))
            lines.append(".word 0x%08X" % struct.unpack_from(">I", text, offset)[0])
        lines.append(".size %s, . - %s" % (match.FUNCTION, match.FUNCTION))
        cls.isolated_candidate_asm = cls.output / "isolated-candidate.s"
        cls.isolated_candidate_asm.write_text("\n".join(lines) + "\n")
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
            cls.isolated_candidate, cls.layout,
            word_patches_path=cls.isolated_guards, filename=match.FILENAME))
        cls.guarded = cls.output / "isolated-guarded.o"
        subprocess.run(
            ["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
             "-mabi=32", "-I", str(cls.root / "conker/include"),
             "-o", str(cls.guarded), str(cls.guarded_asm)],
            check=True, capture_output=True)

        cls.current_guards = cls.root / "conker/retail_word_patches.us.csv"
        current = cls.current_guards.read_bytes()
        with cls.current_guards.open(newline="") as stream:
            installed = [row for row in csv.DictReader(stream)
                         if row["function"] == match.FUNCTION]
        cls.installed = bool(installed)
        if installed:
            if installed != cls.rows:
                raise ValueError("Installed menu record guards differ from qualification")
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
            raise ValueError("Menu record owner diagnostics changed: " + diagnostics)
        cls.owner_asm = cls.output / "qualified-owner.s"
        cls.owner_asm.write_text(emit_padded_assembly(
            cls.compact_owner, cls.root / match.ASM,
            word_patches_path=cls.combined_guards, filename=match.FILENAME,
            rodata_symbol=match.RODATA_SYMBOL))
        cls.qualified_owner = cls.output / "qualified-owner.o"
        subprocess.run(
            ["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
             "-mabi=32", "-I", str(cls.root / "conker/include"),
             "-o", str(cls.qualified_owner), str(cls.owner_asm)],
            check=True, capture_output=True)

        old = "build/src/game/generated_20AE20.c.o"
        new = str(cls.qualified_owner.relative_to(cls.root / "conker")).replace("\\", "/")
        linker = (cls.root / "conker/build/conker.ld").read_text()
        if linker.count(old) != 1:
            raise ValueError("Menu record owner linker reference changed")
        cls.linker = cls.output / "qualified-image.ld"
        cls.linker.write_text(linker.replace(old, new))
        cls.qualified_elf = cls.output / "qualified-image.elf"
        subprocess.run(
            ["mips-linux-gnu-ld", "-T", str(cls.linker.relative_to(cls.root / "conker")),
             "-Map", str((cls.output / "qualified-image.map").relative_to(cls.root / "conker")),
             "-T", "undefined_syms.us.txt", "-T", "undefined_funcs.us.txt",
             "-T", "undefined_syms_auto.txt", "-T", "undefined_funcs_auto.txt",
             "--no-check-sections", "--no-warn-mismatch", "-o",
             str(cls.qualified_elf.relative_to(cls.root / "conker"))],
            cwd=cls.root / "conker", check=True, capture_output=True)

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

    def candidate_state(self, guarded):
        raw, bindings = payload(self.guarded if guarded else self.candidate, match.FUNCTION)
        if not guarded:
            bindings = {offset: [(kind, match.RODATA_SYMBOL if symbol == ".rodata" else symbol)
                                 for kind, symbol in rows]
                        for offset, rows in bindings.items()}
        return raw, bindings

    def normalized_candidate(self):
        raw, bindings = self.candidate_state(False)
        result = bytearray(raw)
        normalized = {offset: list(rows) for offset, rows in bindings.items()}
        for row in self.rows:
            offset = int(row["offset"], 0)
            struct.pack_into(">I", result, offset, int(row["replacement"], 0))
            normalized[offset] = parse_relocation_spec(row["replacement_relocations"])
            if not normalized[offset]:
                normalized.pop(offset, None)
        return bytes(result), normalized

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
            changed = list(fields); changed[2] = match.WORDS * 4
            SYMBOL.pack_into(expected, at, *changed)
        else:
            self.assertEqual(fields[2], match.WORDS * 4)
        return current, bytes(expected), offset

    def test_01_complete_closed_register_cycle_and_relocations(self):
        self.assertEqual(len(self.rows), 20)
        self.assertEqual(tuple(int(row["offset"], 0) for row in self.rows), match.OFFSETS)
        self.assertEqual(sum(row["expected_relocations"] != "-" for row in self.rows), 4)
        self.assertTrue(all(row["expected_relocations"] == row["replacement_relocations"]
                            for row in self.rows))
        self.assertEqual(self.candidate_state(True), self.normalized_candidate())
        retail = struct.unpack_from(">%dI" % match.WORDS,
                                    (self.root / "conker/conker.us.bin").read_bytes(),
                                    match.ROM)
        linked = self.relocated(*self.normalized_candidate(), match.SYMBOLS)
        self.assertEqual(linked, retail)
        for offset in match.OFFSETS:
            left, right = self.linked_words[offset // 4], retail[offset // 4]
            self.assertEqual(left >> 26, right >> 26)

    def test_02_independent_rebases_and_fail_closed_guards(self):
        raw, bindings = self.normalized_candidate()
        for shift in (0, 0x01000000, 0x10000000):
            symbols = {name: value + shift for name, value in match.SYMBOLS.items()}
            words = self.relocated(raw, bindings, symbols)
            self.assertEqual(len(words), match.WORDS)
        failures = 0
        for index, row in enumerate(self.rows):
            for field, value in (("expected", "0x%08X" % (int(row["expected"], 0) ^ 1)),
                                 ("expected_relocations", "R_MIPS_HI16:wrong_symbol")):
                changed = [dict(item) for item in self.rows]
                changed[index][field] = value
                stream = io.StringIO(newline="")
                writer = csv.DictWriter(stream, fieldnames=tuple(self.rows[0]),
                                        lineterminator="\n")
                writer.writeheader(); writer.writerows(changed)
                path = self.output / ("stale-%02d-%s.csv" % (index, field))
                path.write_text(stream.getvalue())
                with self.assertRaisesRegex(ValueError, "stale word patch|stale relocations"):
                    emit_padded_assembly(self.isolated_candidate, self.layout,
                                         word_patches_path=path,
                                         filename=match.FILENAME)
                failures += 1
        self.assertEqual(failures, 40)

    def test_03_guest_native_and_caller_contract(self):
        retail = struct.unpack_from(">%dI" % match.WORDS,
                                    (self.root / "conker/conker.us.bin").read_bytes(),
                                    match.ROM)
        raw = self.relocated(*self.candidate_state(False), match.SYMBOLS)
        guarded = self.relocated(*self.candidate_state(True), match.SYMBOLS)
        report = oracle.qualify((retail, raw, guarded))
        self.assertEqual((report["cases"], report["executions"],
                          report["covered_words"], report["switch_cases"]),
                         (28, 84, 59, 10))
        reports = native.qualify(self.root, self.output)
        self.assertEqual(len(reports), 3)
        self.assertTrue(all((item["variants"], item["controls"],
                             item["cases_per_variant"], item["UBSan"])
                            == (8, 7, 168, True) for item in reports))
        rom = (self.root / "conker/conker.us.bin").read_bytes()
        jal = 0x0C000000 | (match.ENTRY >> 2 & 0x03FFFFFF)
        locations = [offset for offset in range(0, len(rom) - 3, 4)
                     if struct.unpack_from(">I", rom, offset)[0] == jal]
        self.assertEqual(locations, [0x20DF6C])
        self.assertEqual(struct.unpack_from(">3I", rom, 0x20DF64),
                         (0x11200003, 0x00000000, jal))

    def test_04_owner_neighbors_image_prediction_and_protected_data(self):
        production = self.root / "conker/build/src/game/generated_20AE20.c.o"
        self.assertGreaterEqual(same_functions(production, self.qualified_owner,
                                               (match.FUNCTION,)), 30)
        self.assertEqual(self.function_blob(self.qualified_owner, match.FUNCTION),
                         self.normalized_candidate())
        current, expected, offset = self.predicted_image()
        qualified = self.qualified_elf.read_bytes()
        # Allocated image bytes are a literal one-slot prediction. The new
        # external references reorder only equivalent ELF symbol/string table
        # rows after the final allocated section.
        nonalloc = 0x29064C
        self.assertEqual(qualified[:nonalloc], expected[:nonalloc])
        current_symbols = {name: fields for _, name, fields, _ in symbol_rows(current)}
        qualified_symbols = {name: fields for _, name, fields, _ in symbol_rows(qualified)}
        self.assertEqual(set(current_symbols), set(qualified_symbols))
        for name in current_symbols:
            left, right = current_symbols[name], qualified_symbols[name]
            if name == match.FUNCTION:
                self.assertEqual((left[1], left[3:]), (right[1], right[3:]))
                self.assertEqual(right[2], match.WORDS * 4)
            else:
                self.assertEqual(left[1:], right[1:], name)
        changed = [index for index, pair in enumerate(zip(current, expected))
                   if pair[0] != pair[1]]
        slot = set(range(offset, offset + match.WORDS * 4))
        symbol_offsets = set()
        for at, name, _, _ in symbol_rows(current):
            if name == match.FUNCTION:
                symbol_offsets.update(range(at + 8, at + 12))
        self.assertTrue(all(index in slot or index in symbol_offsets for index in changed))
        predicted = self.output / "expected-conker.us.elf"
        predicted.write_bytes(qualified)
        data = audit_layout(predicted, self.root / "conker")
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))

    def test_05_live_install_exact_when_source_and_guards_are_present(self):
        production = self.root / "conker/build/src/game/generated_20AE20.c.o"
        source = (self.root / match.SOURCE).read_text()
        if self.installed:
            self.assertIn(match.candidate.selected_body(), source)
            self.assertEqual(production.read_bytes(), self.qualified_owner.read_bytes())
            current, expected, _ = self.predicted_image()
            self.assertEqual(current, expected)
        else:
            self.assertIn("s32 func_151E2404() {\n    return 0;\n}", source)
            self.assertNotEqual(self.function_blob(production, match.FUNCTION),
                                self.normalized_candidate())


if __name__ == "__main__":
    unittest.main()
