"""ABI, semantic, guard, owner, and image gates for func_150174C0."""

import csv
from dataclasses import dataclass
import itertools
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from tools.experiments import game_descriptor_tag_adjust_match as match
from tools.experiments.game_four_head_lookup_match import payload
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


TABLE = 0x50000


@dataclass(frozen=True)
class OracleCase:
    phase: int = 0


def signed(value):
    return ((value & 0xFFFFFFFF) ^ 0x80000000) - 0x80000000


def symbols(index=0):
    return {
        "D_80087380": (0x80087380, 0x03407FFC, 0x02428000)[index],
        "D_800D23C0": (0x800D23C0, 0x034123C0, 0x025223C0)[index],
    }


def relocated_words(raw, bindings, values):
    result = bytearray(raw)
    for offset, rows in bindings.items():
        kind, name = rows[0]
        value = values[name]
        word = struct.unpack_from(">I", result, offset)[0]
        immediate = ((value + 0x8000) >> 16) & 0xFFFF if kind == "R_MIPS_HI16" else value & 0xFFFF
        struct.pack_into(">I", result, offset, word & 0xFFFF0000 | immediate)
    return list(struct.unpack(">46I", result))


def fixture(count, pattern, adjustment, alias, values):
    memory = {STACK + i: (i * 17 + 0xA5) & 0xFF for i in range(-64, 64)}
    base = TABLE if alias == 0 else values["D_800D23C0"] - 8 if alias == 1 else values["D_80087380"] - 8
    for address in (TABLE, base):
        memory.update({address + i: 0xA5 for i in range(-16, 240)})
    for row in range(6):
        put(memory, base + 24 * row, 0x1000 + row, 2)
        put(memory, base + 24 * row + 2, (0, 1, 4, 8)[(pattern + row) % 4], 2)
        put(memory, base + 24 * row + 4, 0xABCDEF00 + row)
        for entry in range(8):
            value = ((entry + pattern) % 4) * 0x1000 + ((row * 29 + entry * 11) & 0xFFF)
            put(memory, base + 24 * row + 8 + 2 * entry, value, 2)
    put(memory, values["D_80087380"], count & 0xFFFFFFFF)
    put(memory, values["D_800D23C0"], base)
    if alias == 1:
        put(memory, base + 2, 2, 2)
        put(memory, base + 0x48 + 2, 3, 2)
    elif alias == 2:
        put(memory, base + 2, 2, 2)
    return memory, adjustment


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 64 <= address < STACK + 64}


def reference(initial, count, adjustment, values, cached_base=False, cached_outer=False):
    memory = dict(initial)
    outer = signed(read(memory, values["D_80087380"]))
    index = 0
    operations = 0
    if outer > 0:
        base = read(memory, values["D_800D23C0"])
        row = base
        offset = 0
        initial_base = base
        initial_outer = outer
        while True:
            entries = read(memory, row + 2, 2)
            entry_index = 0
            if entries > 0:
                while entry_index < entries:
                    at = base + index * 24 + 2 * entry_index + 8
                    value = read(memory, at, 2)
                    entry_index += 1
                    operations += 1
                    if operations >= 4096:
                        raise AssertionError("descriptor fixture escaped its bounded domain")
                    if value >> 12 == 2:
                        put(memory, at, value + adjustment, 2)
                        base = initial_base if cached_base else read(memory, values["D_800D23C0"])
                        row = base + offset
                        entries = read(memory, row + 2, 2)
                outer = initial_outer if cached_outer else signed(read(memory, values["D_80087380"]))
            index += 1
            offset += 24
            row += 24
            if index >= outer:
                break
    return public(memory), index


class DescriptorOracle(FactoryOracle):
    def __init__(self, words, memory, adjustment, entry, phase=0):
        super().__init__(words, memory, OracleCase(phase), entry=entry, s={},
                         arguments=(adjustment & 0xFFFFFFFF,))
        self.original_f = self.f[:]

    def record_call(self, target):
        raise AssertionError(("unexpected leaf call", hex(target)))

    def hook(self, target):
        raise AssertionError(("unexpected leaf hook", hex(target)))


class GameDescriptorTagAdjustMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        values = match.prepare(cls.root)
        cls.baseline, cls.guards, cls.qualified, cls.expected = values[0], values[1], values[2], values[5]
        cls.raw, cls.bindings = payload(cls.root / match.BUILD / "compact-candidate.o",
                                        match.FUNCTION)
        cls.retail, cls.template = match.retail_template(cls.baseline["rom"].read_bytes())

    def test_thirteen_checked_guards_close_the_same_length_loop_schedule(self):
        rows = match.guard_rows()
        self.assertEqual((len(rows), sum(bool(row["insert_after"]) for row in rows),
                          sum(row["omit"] == "true" for row in rows)), (13, 0, 0))
        self.assertEqual(match.normalized_payload(self.raw, self.bindings), self.template)
        self.assertEqual(self.bindings, match.BINDINGS)
        self.assertEqual([row["offset"] for row in rows],
            ["0x03C", "0x040", "0x044", "0x048", "0x04C", "0x050", "0x054",
             "0x058", "0x05C", "0x060", "0x070", "0x088", "0x08C"])

    def test_void_abi_table_declaration_and_sole_caller_are_explicit(self):
        baseline_source = self.baseline["source"].read_text()
        installed = match.proposed_source(baseline_source, "variables.h")
        self.assertIn("void func_150174C0(s32 adjustment)", installed)
        self.assertNotIn("return descriptor", installed)
        self.assertIn("func_150174C0(D_800DBF00);", installed)
        self.assertIn("D_800D23C0 = func_1502B5C8", installed)
        occurrences = []
        for path in (self.root / "conker/src").rglob("*.c"):
            count = path.read_text(errors="replace").count("func_150174C0(")
            occurrences.extend([path.relative_to(self.root).as_posix()] * count)
        self.assertEqual(occurrences, ["conker/src/game_447B0.c"] * 3)
        references = []
        for path in (self.root / "conker/src").rglob("*.c"):
            if "D_800D23C0" in path.read_text(errors="replace"):
                references.append(path.relative_to(self.root).as_posix())
        self.assertEqual(references, ["conker/src/game_447B0.c",
                                      "conker/src/game/generated_B3020.c"])

    def test_live_checkout_is_frozen_predecessor_or_complete_installed_state(self):
        source = (self.root / match.PATHS["source"]).read_text()
        header = (self.root / match.PATHS["header"]).read_text()
        with (self.root / match.PATHS["guards"]).open(newline="") as stream:
            rows = [row for row in csv.DictReader(stream) if row["function"] == match.FUNCTION]
        if not rows:
            self.assertEqual(source, self.baseline["source"].read_text())
            self.assertEqual(header, self.baseline["header"].read_text())
            return
        self.assertEqual(rows, match.guard_rows())
        self.assertEqual(source, match.proposed_source(self.baseline["source"].read_text(),
                                                       "variables.h"))
        self.assertEqual(header, match.proposed_header(self.baseline["header"].read_text()))
        self.assertEqual((self.root / match.PATHS["elf"]).read_bytes(), self.expected.read_bytes())

    def test_guest_routes_aliases_reloads_and_incidental_v0_match_retail(self):
        for layout in range(3):
            values = symbols(layout)
            entry = (match.ENTRY, 0x17018000, 0x1F00FFFC)[layout]
            candidate = relocated_words(self.raw, self.bindings, values)
            retail = relocated_words(self.template, self.bindings, values)
            cases = itertools.product((0, -1, -2147483648, 1, 2, 4), range(4),
                (0, 1, -1, 0xFFFF, 0x10000, -2147483648, 2147483647), (0, 8))
            for count, pattern, adjustment, phase in cases:
                initial, argument = fixture(count, pattern, adjustment, 0, values)
                expected = reference(initial, count, adjustment, values)
                models = [DescriptorOracle(words, initial, argument, entry, phase).run()
                          for words in (candidate, retail)]
                for model in models:
                    self.assertEqual((public(model.memory), model.r[2]), expected)
                    self.assertTrue(all(model.r[index] == model.before[index]
                                        for index in (*range(16, 24), 28, 29, 30, 31)))
                    self.assertEqual(model.f, model.original_f)
                self.assertEqual(models[0].trace, models[1].trace)
            for alias, count, adjustment in ((1, 1, 0x48), (2, 0x2001, -0x2000)):
                initial, argument = fixture(count, 0, adjustment, alias, values)
                expected = reference(initial, count, adjustment, values)
                models = [DescriptorOracle(words, initial, argument, entry).run()
                          for words in (candidate, retail)]
                self.assertEqual([(public(model.memory), model.r[2]) for model in models],
                                 [expected, expected])
                self.assertEqual(models[0].trace, models[1].trace)
        initial, _ = fixture(1, 0, 0x48, 1, symbols())
        correct = reference(initial, 1, 0x48, symbols())
        try:
            stale = reference(initial, 1, 0x48, symbols(), cached_base=True)
        except (AssertionError, KeyError):
            stale = None
        self.assertNotEqual(correct, stale)
        initial, _ = fixture(0x2001, 0, -0x2000, 2, symbols())
        correct = reference(initial, 0x2001, -0x2000, symbols())
        try:
            stale = reference(initial, 0x2001, -0x2000, symbols(), cached_outer=True)
        except (AssertionError, KeyError):
            stale = None
        self.assertNotEqual(correct, stale)

    def test_native_32bit_o0_o2_o3_valid_rows_and_canaries(self):
        code = '#include <ultra64.h>\n' + match.ROW_TYPE + r'''
u32 D_80087380;
u8 *D_800D23C0;
''' + match.SELECTED + r'''
static struct { u32 before[4]; DescriptorTagRow rows[6]; u32 after[4]; } storage;
static u32 counts[] = {0, 0xFFFFFFFFu, 0x80000000u, 1, 2, 4};
static s32 adjustments[] = {0, 1, -1, 0xFFFF, 0x10000, (s32)0x80000000u, 0x7FFFFFFF};
static int run(void) {
    u32 ci, pattern, ai, i, j, size = sizeof(storage);
    u8 *bytes = (u8 *)&storage;
    for (ci = 0; ci < 6; ci++) for (pattern = 0; pattern < 4; pattern++)
    for (ai = 0; ai < 7; ai++) {
        for (i = 0; i < size; i++) bytes[i] = 0xA5;
        for (i = 0; i < 6; i++) {
            storage.rows[i].unused = (u16)(0x1000 + i);
            storage.rows[i].count = (u16)((pattern + i) & 3);
            storage.rows[i].reserved = 0xABCDEF00u + i;
            for (j = 0; j < 8; j++)
                storage.rows[i].entries[j] = (u16)((((j + pattern) & 3) << 12) | ((i * 29 + j * 11) & 0xFFF));
        }
        D_80087380 = counts[ci]; D_800D23C0 = (u8 *)storage.rows;
        func_150174C0(adjustments[ai]);
        if (D_80087380 != counts[ci] || D_800D23C0 != (u8 *)storage.rows) return 2;
        for (i = 0; i < 4; i++) if (storage.before[i] != 0xA5A5A5A5u || storage.after[i] != 0xA5A5A5A5u) return 3;
        if ((s32)counts[ci] > 0) for (i = 0; i < counts[ci]; i++)
            for (j = 0; j < storage.rows[i].count; j++) {
                u16 initial = (u16)((((j + pattern) & 3) << 12) | ((i * 29 + j * 11) & 0xFFF));
                u16 expected = (initial >> 12) == 2 ? (u16)((u32)initial + (u32)adjustments[ai]) : initial;
                if (storage.rows[i].entries[j] != expected) return 4;
            }
    }
    return 0;
}
''' + START.replace("void _start(void)",
                    "__attribute__((force_align_arg_pointer)) void _start(void)")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "native.c"
            source.write_text(code)
            for profile in ("-O0", "-O2", "-O3"):
                binary = root / ("native-" + profile[1:])
                command = native_command(profile) + ["-fno-strict-aliasing", str(source),
                                                      "-o", str(binary)]
                subprocess.run(command, cwd=self.root, check=True, capture_output=True)
                subprocess.run([str(binary)], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
