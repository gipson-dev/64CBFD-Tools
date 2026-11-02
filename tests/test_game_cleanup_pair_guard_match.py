"""Guard, semantics, callback registration, owner, and image gates for the cleanup pair."""

import csv
import io
from pathlib import Path
import struct
import subprocess
import unittest

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_cleanup_pair_guard_match as match
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import (
    SYMBOL, emit_padded_assembly, parse_object, parse_relocation_spec)
from tools.tests import game_cleanup_pair_native as native
from tools.tests import game_cleanup_pair_oracle as oracle


class CleanupPairGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / "conker/build/game-cleanup-pair-151C94D4-151C95D8-guard-match"
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.candidate, cls.linked_words = match.compile_candidate(cls.root, cls.output)
        cls.rows = match.guard_rows(cls.root, cls.candidate, cls.linked_words)
        cls.isolated_guards = cls.output / "isolated-guards.csv"
        match.write_rows(cls.isolated_guards, cls.rows)

        text, functions, relocations = parse_object(cls.candidate)
        cls.isolated_candidates = {}
        cls.guarded_objects = {}
        cls.layouts = {}
        for name, entry, rom, _ in match.TARGETS:
            function_guards = cls.output / (name + "-guards.csv")
            match.write_rows(function_guards,
                             [row for row in cls.rows if row["function"] == name])
            isolated_source, unresolved = emit_function(
                text, functions[name], relocations, name, match.SYMBOLS)
            if unresolved:
                raise ValueError("Unresolved cleanup-pair bindings for %s: %r" %
                                 (name, unresolved))
            candidate_asm = cls.output / (name + "-candidate.s")
            candidate_asm.write_text(isolated_source)
            candidate = cls.output / (name + "-candidate.o")
            subprocess.run(
                ["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
                 "-mabi=32", "-o", str(candidate), str(candidate_asm)],
                check=True, capture_output=True)
            cls.isolated_candidates[name] = candidate

            layout = cls.output / (name + "-layout.s")
            lines = ["glabel " + name]
            for index in range(match.WORDS):
                lines.append("/* %06X %08X 00000000 */ nop" %
                             (rom + index * 4, entry + index * 4))
            layout.write_text("\n".join(lines) + "\n")
            cls.layouts[name] = layout
            guarded_asm = cls.output / (name + "-guarded.s")
            guarded_asm.write_text(emit_padded_assembly(
                candidate, layout, word_patches_path=function_guards,
                filename=match.OWNER))
            guarded = cls.output / (name + "-guarded.o")
            subprocess.run(
                ["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
                 "-mabi=32", "-I", str(cls.root / "conker/include"),
                 "-o", str(guarded), str(guarded_asm)], check=True,
                capture_output=True)
            cls.guarded_objects[name] = guarded

        cls.current_guards = cls.root / "conker/retail_word_patches.us.csv"
        current = cls.current_guards.read_bytes()
        names = {item[0] for item in match.TARGETS}
        with cls.current_guards.open(newline="") as stream:
            installed = [row for row in csv.DictReader(stream)
                         if row["function"] in names]
        cls.installed = bool(installed)
        if installed:
            if installed != cls.rows:
                raise ValueError("Installed cleanup-pair guards differ from qualification")
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
            raise ValueError("Cleanup-pair owner diagnostics changed: " + diagnostics)
        cls.owner_asm = cls.output / "qualified-owner.s"
        cls.owner_asm.write_text(emit_padded_assembly(
            cls.compact_owner, cls.root / match.ASM,
            function_objects={name: cls.candidate for name in names},
            word_patches_path=cls.combined_guards, filename=match.OWNER))
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

    def normalized_candidate(self, name):
        raw, bindings = payload(self.candidate, name)
        result = bytearray(raw)
        normalized = {offset: list(rows) for offset, rows in bindings.items()}
        for row in self.rows:
            if row["function"] != name:
                continue
            offset = int(row["offset"], 0)
            struct.pack_into(">I", result, offset, int(row["replacement"], 0))
            normalized[offset] = parse_relocation_spec(row["replacement_relocations"])
            if not normalized[offset]:
                normalized.pop(offset, None)
        return bytes(result), normalized

    def link_isolated(self, name, entry, symbols, label):
        script = self.output / (label + ".ld")
        elf = self.output / (label + ".elf")
        binary = self.output / (label + ".bin")
        script.write_text("SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n" % entry)
        subprocess.run(
            ["mips-linux-gnu-ld", "-m", "elf32btsmip", "-T", str(script),
             "-e", name, *("--defsym=%s=0x%X" % item for item in symbols.items()),
             "-o", str(elf), str(self.guarded_objects[name])],
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
        offsets = {}
        rom = (self.root / "conker/conker.us.bin").read_bytes()
        for name, entry, rom_offset, _ in match.TARGETS:
            offset = elf_slot_offset(current, entry, match.WORDS * 4)
            retail = rom[rom_offset:rom_offset + match.WORDS * 4]
            expected[offset:offset + len(retail)] = retail
            offsets[name] = offset
            rows = [(at, fields) for at, row_name, fields, _ in symbol_rows(current)
                    if row_name == name]
            self.assertEqual(len(rows), 1)
            at, fields = rows[0]
            self.assertEqual((fields[1], fields[3] & 15), (entry, 2))
            if fields[2] == 12:
                changed = list(fields); changed[2] = match.WORDS * 4
                SYMBOL.pack_into(expected, at, *changed)
            else:
                self.assertEqual(fields[2], match.WORDS * 4)
        return current, bytes(expected), offsets

    def test_01_complete_closed_owner_register_cycles(self):
        self.assertEqual(len(self.rows), 8)
        for name, _, _, _ in match.TARGETS:
            rows = [row for row in self.rows if row["function"] == name]
            self.assertEqual(tuple(int(row["offset"], 0) for row in rows), match.OFFSETS)
            self.assertTrue(all(row["expected_relocations"] == "-" and
                                row["replacement_relocations"] == "-" for row in rows))
            raw, bindings = self.normalized_candidate(name)
            guarded_raw, guarded_bindings = payload(self.guarded_objects[name], name)
            self.assertEqual((guarded_raw, guarded_bindings), (raw, bindings))
            _, _, rom_offset, _ = next(item for item in match.TARGETS if item[0] == name)
            retail = struct.unpack_from(">%dI" % match.WORDS,
                                        (self.root / "conker/conker.us.bin").read_bytes(),
                                        rom_offset)
            for offset in match.OFFSETS:
                left, right = self.linked_words[name][offset // 4], retail[offset // 4]
                self.assertEqual(left >> 26, right >> 26)
                self.assertEqual(left & 0xFC00FFFF, right & 0xFC00FFFF)

    def test_02_original_links_and_independent_rebases(self):
        layouts = (
            (0, match.SYMBOLS),
            (0x17004000, {key: value + 0x01000000 for key, value in match.SYMBOLS.items()}),
            (0x25008000, {key: value + 0x10000000 for key, value in match.SYMBOLS.items()}),
        )
        rom = (self.root / "conker/conker.us.bin").read_bytes()
        for name, original_entry, rom_offset, _ in match.TARGETS:
            raw, bindings = self.normalized_candidate(name)
            for index, (entry, symbols) in enumerate(layouts):
                entry = original_entry if entry == 0 else entry
                self.assertEqual(
                    self.link_isolated(name, entry, symbols, "%s-rebase-%d" % (name, index)),
                    self.relocated(raw, bindings, symbols))
            retail = struct.unpack_from(">%dI" % match.WORDS, rom, rom_offset)
            self.assertEqual(
                self.link_isolated(name, original_entry, match.SYMBOLS, name + "-retail"),
                retail)

    def test_03_each_expected_word_and_relocation_guard_fails_closed(self):
        failures = 0
        for index, row in enumerate(self.rows):
            name = row["function"]
            function_rows = [dict(item) for item in self.rows
                             if item["function"] == name]
            function_index = next(position for position, item in enumerate(function_rows)
                                  if item["offset"] == row["offset"])
            for field, value in (("expected", "0x%08X" % (int(row["expected"], 0) ^ 1)),
                                 ("expected_relocations", "R_MIPS_HI16:wrong_symbol")):
                changed = [dict(item) for item in function_rows]
                changed[function_index][field] = value
                stream = io.StringIO(newline="")
                writer = csv.DictWriter(stream, fieldnames=tuple(self.rows[0]),
                                        lineterminator="\n")
                writer.writeheader(); writer.writerows(changed)
                path = self.output / ("stale-%02d-%s.csv" % (index, field))
                path.write_text(stream.getvalue())
                with self.assertRaisesRegex(ValueError, "stale word patch|stale relocations"):
                    emit_padded_assembly(self.isolated_candidates[name], self.layouts[name],
                                         word_patches_path=path, filename=match.OWNER)
                failures += 1
        self.assertEqual(failures, 16)

    def test_04_guest_semantics_callback_abi_and_native_controls(self):
        rom = (self.root / "conker/conker.us.bin").read_bytes()
        programs = {}
        for name, entry, rom_offset, _ in match.TARGETS:
            retail = struct.unpack_from(">%dI" % match.WORDS, rom, rom_offset)
            guarded = self.link_isolated(name, entry, match.SYMBOLS, name + "-semantic")
            programs[name] = (retail, self.linked_words[name], guarded)
        report = oracle.qualify(programs)
        self.assertEqual((report["cases_per_function"], report["functions"],
                          report["executions"], report["covered_words_per_function"]),
                         (618, 2, 3708, 65))
        reports = native.qualify(self.root, self.output)
        self.assertEqual(len(reports), 3)
        for item in reports:
            self.assertEqual((item["cases_per_variant"], item["variants"],
                              item["controls_per_function"]), (2560, 18, 8))

    def test_05_owner_neighbors_image_prediction_and_protected_data(self):
        production = self.root / "conker/build/src/game/generated_1F4650.c.o"
        names = tuple(item[0] for item in match.TARGETS)
        neighbors = same_functions(production, self.qualified_owner, names)
        self.assertGreaterEqual(neighbors, 40)
        for name in names:
            self.assertEqual(self.function_blob(self.qualified_owner, name),
                             self.normalized_candidate(name))
        current, expected, offsets = self.predicted_image()
        changed = [index for index, pair in enumerate(zip(current, expected))
                   if pair[0] != pair[1]]
        self.assertTrue(self.installed or changed)
        slots = set()
        for offset in offsets.values():
            slots.update(range(offset, offset + match.WORDS * 4))
        symbol_offsets = set()
        for at, name, _, _ in symbol_rows(current):
            if name in names:
                symbol_offsets.update(range(at + 8, at + 12))
        self.assertTrue(all(index in slots or index in symbol_offsets for index in changed))
        predicted = self.output / "expected-conker.us.elf"
        predicted.write_bytes(expected)
        data = audit_layout(predicted, self.root / "conker")
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))

    def test_06_registration_table_and_live_install(self):
        rom = (self.root / "conker/conker.us.bin").read_bytes()
        expected_pointers = {"func_151C94D4": 0x22E9D0, "func_151C95D8": 0x22EA04}
        for name, entry, _, _ in match.TARGETS:
            locations = [offset for offset in range(0, len(rom) - 3, 4)
                         if struct.unpack_from(">I", rom, offset)[0] == entry]
            self.assertIn(expected_pointers[name], locations)
        production = self.root / "conker/build/src/game/generated_1F4650.c.o"
        source_text = (self.root / match.SOURCE).read_text()
        if self.installed:
            for body in match.selected_bodies().values():
                self.assertIn(body.rstrip(), source_text)
            self.assertEqual(production.read_bytes(), self.qualified_owner.read_bytes())
            current, expected, _ = self.predicted_image()
            self.assertEqual(current, expected)
        else:
            for name, _, _, _ in match.TARGETS:
                self.assertIn("s32 %s() {\n    return 0;\n}" % name, source_text)
                self.assertNotEqual(self.function_blob(production, name),
                                    self.normalized_candidate(name))


if __name__ == "__main__":
    unittest.main()
