"""Guard, relocation, owner, and image gates for func_150E8B1C."""

import csv
import io
from pathlib import Path
import struct
import subprocess
import unittest

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_weighted_event_emitter_guard_match as match
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import emit_padded_assembly, parse_object, parse_relocation_spec
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle, put
from tools.tests.test_game_queued_segment_writer import STACK


RECORD = 0x20000
ORIGIN = 0x21000
NODES = 0x22000
DESCRIPTORS = 0x23000
CHILDREN = 0x24000


def bits(value):
    return struct.unpack(">I", struct.pack(">f", value))[0]


def emitter_memory(progress=2.0, initial_fraction=0.0, rate=0.0,
                   total=10.0, weights=(3.0, 7.0)):
    memory = {STACK + offset: 0xA5 for offset in range(-0x500, 0x100)}
    for base, size in ((RECORD, 0x80), (ORIGIN, 0x20), (NODES, 0x40),
                       (DESCRIPTORS, 0x40), (CHILDREN, 0x200)):
        memory.update({base + offset: 0xA5 for offset in range(size)})
    put(memory, match.SYMBOLS["D_800BE9E8"], 0x80000001)
    put(memory, match.SYMBOLS["D_800BE9A4"], bits(rate))
    put(memory, match.SYMBOLS["D_800DCD90"], bits(total))
    put(memory, match.SYMBOLS["D_800DCDC4"], NODES)
    put(memory, match.SYMBOLS["D_800A1384"], 0x3F85F40A)
    put(memory, match.SYMBOLS["D_800A1388"], 0x3EA25D8D)
    put(memory, match.SYMBOLS["D_800A138C"], bits(4.0))
    put(memory, RECORD + 0x28, bits(0.25))
    put(memory, RECORD + 0x2C, bits(0.5))
    put(memory, RECORD + 0x30, bits(progress))
    put(memory, RECORD + 0x0C, 0xC3, 1)
    put(memory, RECORD + 0x01, 0x91, 1)
    for axis in range(3):
        put(memory, ORIGIN + axis * 4, bits(0.0))
    for index, weight in enumerate(weights):
        node = NODES + index * 0x10
        put(memory, node, DESCRIPTORS + index * 0x10)
        put(memory, node + 4, 0xA5000000 + index)
        put(memory, node + 8, bits(weight))
        put(memory, node + 12, NODES + (index + 1) * 0x10 if index + 1 < len(weights) else 0)
    return memory


class WeightedEmitterOracle(TriangleOracle):
    """Execute the real retail/raw instructions with bounded callback models."""

    def __init__(self, words, memory, fractions, integers, points, failures=(), phase=0):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(RECORD,))
        self.fractions = list(fractions)
        self.integers = list(integers)
        self.points = list(points)
        self.failures = set(failures)
        self.float_index = self.integer_index = self.position_index = 0
        self.allocation_index = 0
        self.trace = []
        self.callback_calls = []
        self.hi = self.lo = 0

    def execute(self, word):
        op, function = word >> 26, word & 63
        if op == 0 and function in (16, 27):
            rs, rt, rd = word >> 21 & 31, word >> 16 & 31, word >> 11 & 31
            if function == 16:
                self.r[rd] = self.hi
            else:
                divisor = self.r[rt]
                assert divisor
                self.lo = self.r[rs] // divisor
                self.hi = self.r[rs] % divisor
            self.r[0] = 0
            return
        super().execute(word)

    def callback_arguments(self, target):
        if target == match.SYMBOLS["func_15149130"]:
            return tuple(self.r[4:8]) + tuple(self.get(self.r[29] + offset, 4)
                                               for offset in (0x10, 0x14, 0x18, 0x1C, 0x20))
        if target == match.SYMBOLS["memcpy"]:
            return tuple(self.r[4:7])
        return tuple(self.r[4:6])

    def record_call(self, target):
        self.callback_calls.append((target, self.callback_arguments(target)))

    def clobber(self):
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5F00000 + index for index in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011

    def hook(self, target):
        arguments = self.callback_calls[-1][1]
        if target == match.SYMBOLS["func_15144B34"]:
            assert arguments[0] == 0x80000001
            self.trace.append("origin")
            self.clobber()
            self.r[2] = ORIGIN
        elif target == match.SYMBOLS["func_150ADA68"]:
            value = self.fractions[self.float_index]
            self.float_index += 1
            self.trace.append("float")
            self.clobber()
            self.f[0] = bits(value)
        elif target == match.SYMBOLS["func_1514470C"]:
            descriptor, output = arguments
            index = (descriptor - DESCRIPTORS) // 0x10
            assert descriptor == DESCRIPTORS + index * 0x10
            point = self.points[self.position_index]
            self.position_index += 1
            self.trace.append("position-%d" % index)
            for axis, value in enumerate(point):
                self.put(output + axis * 4, bits(value), 4)
            self.clobber()
        elif target == match.SYMBOLS["func_150ADA20"]:
            value = self.integers[self.integer_index]
            self.integer_index += 1
            self.trace.append("integer")
            self.clobber()
            self.r[2] = value & 0xFFFFFFFF
        elif target == match.SYMBOLS["func_15149130"]:
            duration, index, kind, source, active, mode, size, slot, context = arguments
            assert (index, kind, source, active, mode, size, slot, context) == (
                0xFFFFFFFF, 0x34, 0xFFFFFFFF, 1, 0, 24, 0xC3, 0x91)
            assert duration == self.integers[self.allocation_index] % 13 + 5
            failed = self.allocation_index in self.failures
            self.trace.append("allocation-fail" if failed else "allocation")
            child = CHILDREN + self.allocation_index * 0x40
            self.allocation_index += 1
            self.clobber()
            self.r[2] = 0 if failed else child
        elif target == match.SYMBOLS["memcpy"]:
            destination, source, length = arguments
            assert length == 24
            self.trace.append("copy")
            values = [self.get(source + offset, 1) for offset in range(length)]
            for offset, value in enumerate(values):
                self.put(destination + offset, value, 1)
            self.clobber()
            self.r[2] = destination
        else:
            raise AssertionError(("unexpected callback", hex(target)))


def observable(model):
    memory = {address: value for address, value in model.memory.items()
              if not STACK - 0x500 <= address < STACK + 0x100}
    saved = tuple(model.r[index] for index in (*range(16, 24), 28, 29, 30, 31))
    calls = tuple((target, tuple("private-stack" if STACK - 0x500 <= value < STACK + 0x100
                                else value for value in arguments))
                  for target, arguments in model.callback_calls)
    return memory, tuple(model.trace), calls, saved, tuple(model.f[20:])


class GameWeightedEventEmitterGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / "conker/build/game-weighted-event-emitter-150E8B1C-match"
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
        subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
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
                raise ValueError("Installed weighted-emitter guards differ from qualification")
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
            raise ValueError("Weighted-emitter owner compiler diagnostics changed: " + diagnostics)
        cls.owner_asm = cls.output / "qualified-owner.s"
        cls.owner_asm.write_text(emit_padded_assembly(
            cls.compact_owner, cls.root / "conker/asm/113D60.s",
            word_patches_path=cls.combined_guards, filename=match.FILENAME,
            rodata_symbol="D_800A1350"))
        cls.qualified_owner = cls.output / "qualified-owner.o"
        subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
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

    def link_isolated(self, entry, symbols, label):
        script = self.output / (label + ".ld")
        elf = self.output / (label + ".elf")
        binary = self.output / (label + ".bin")
        script.write_text("SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n" % entry)
        subprocess.run(["mips-linux-gnu-ld", "-m", "elf32btsmip", "-T", str(script),
                        "-e", match.FUNCTION,
                        *("--defsym=%s=0x%X" % item for item in symbols.items()),
                        "-o", str(elf), str(self.guarded_obj)], check=True,
                       capture_output=True)
        subprocess.run(["mips-linux-gnu-objcopy", "-O", "binary", "-j", ".text",
                        str(elf), str(binary)], check=True, capture_output=True)
        data = binary.read_bytes()
        self.assertEqual(len(data), match.WORDS * 4)
        return tuple(struct.unpack(">%dI" % match.WORDS, data))

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

    def test_01_all_44_checked_words_close_the_complete_retail_slot(self):
        self.assertEqual(len(self.rows), 44)
        self.assertEqual(tuple(int(row["offset"], 0) for row in self.rows), match.OFFSETS)
        self.assertTrue(all(row["filename"] == match.FILENAME and
                            row["function"] == match.FUNCTION and
                            row["omit"] == "false" and not row["insert_after"]
                            for row in self.rows))
        raw, bindings = self.normalized_candidate()
        guarded_raw, guarded_bindings = payload(self.guarded_obj, match.FUNCTION)
        self.assertEqual((guarded_raw, guarded_bindings), (raw, bindings))
        self.assertEqual(len(raw), 576)
        self.assertEqual(0x10000 - (struct.unpack_from(">I", raw)[0] & 0xFFFF), 0xC8)

    def test_02_original_link_and_three_independent_rebases(self):
        raw, bindings = self.normalized_candidate()
        layouts = []
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
            linked = self.link_isolated(entry, symbols, "rebase-%d" % index)
            expected = self.relocated(raw, bindings, symbols)
            self.assertEqual(linked, expected)
            layouts.append((entry, symbols))
        retail = struct.unpack_from(">%dI" % match.WORDS,
                                    (self.root / "conker/conker.us.bin").read_bytes(),
                                    match.ROM)
        self.assertEqual(self.link_isolated(match.ENTRY, match.SYMBOLS, "retail-link"), retail)
        self.assertEqual(len(layouts), 3)

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
        self.assertEqual(failures, 88)

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

    def test_05_raw_c_guest_execution_matches_retail_callbacks_and_state(self):
        retail = struct.unpack_from(">%dI" % match.WORDS,
                                    (self.root / "conker/conker.us.bin").read_bytes(),
                                    match.ROM)
        cases = (
            dict(progress=0.5, rate=0.0, fractions=(0.0,), integers=(), points=()),
            dict(progress=2.0, rate=0.0, fractions=(0.0, 0.0), integers=(0,),
                 points=((0.0, 0.0, 0.0),)),
            dict(progress=2.0, rate=0.0, fractions=(0.0, 0.5), integers=(),
                 points=((3.0, 0.0, 0.0),)),
            dict(progress=3.0, rate=0.0, fractions=(0.0, 0.2, 0.8),
                 integers=(12, 13), points=((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
                 failures=(1,)),
            dict(progress=0.5, rate=1.0, total=2.0, fractions=(0.5, 1.0),
                 integers=(0,), points=((0.0, 0.0, 0.0),)),
            dict(progress=2.0, rate=0.0, fractions=(0.0, 0.3), integers=(),
                 points=((2.0, 0.0, 0.0),)),
            dict(progress=2.0, rate=0.0, fractions=(0.0, 0.8), integers=(0,),
                 points=((0.0, 0.0, 0.0),), weights=(2.0, 3.0, 5.0)),
        )
        coverage = set()
        executions = 0
        for phase in (0, 8):
            for case in cases:
                initial = emitter_memory(case["progress"], case["fractions"][0],
                                         case["rate"], case.get("total", 10.0),
                                         case.get("weights", (3.0, 7.0)))
                models = [WeightedEmitterOracle(
                    words, initial, case["fractions"], case["integers"], case["points"],
                    case.get("failures", ()), phase).run()
                    for words in (self.linked_words, retail)]
                self.assertEqual(observable(models[0]), observable(models[1]), case)
                self.assertEqual(models[0].r[29], STACK + phase)
                coverage.update(models[0].visits)
                coverage.update(models[1].visits)
                executions += 2
        dead = set(range(match.ENTRY, match.ENTRY + match.WORDS * 4, 4)) - coverage
        self.assertEqual(dead, {match.ENTRY + 0x1B4})
        self.assertEqual(executions, 28)

    def test_06_strict_full_image_prediction_changes_only_the_target_slot(self):
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


if __name__ == "__main__":
    unittest.main()
