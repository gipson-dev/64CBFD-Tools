"""Semantic, ABI, guarded-owner and full-image gates for func_1515EB84."""

import csv
import itertools
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_point_record_search_candidates as candidate
from tools.experiments import game_point_record_search_match as match
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK, put, read
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
HELPER = 0x150A1DA0
NODE0, NODE1 = 0x220000, 0x220040
RECORD0, RECORD1 = 0x230000, 0x230040


def float_bits(value):
    return struct.unpack(">I", struct.pack(">f", float(signed(value))))[0]


def fixture(records):
    memory = {STACK + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x500, 0x100)}
    nodes = (NODE0, NODE1)
    addresses = (RECORD0, RECORD1)
    for index, fields in enumerate(records):
        node = nodes[index]
        record = addresses[index]
        for offset in range(0x34):
            memory[record + offset] = (offset * 23 + index * 41 + 0x37) & 0xFF
        put(memory, node, nodes[index + 1] if index + 1 < len(records) else 0)
        put(memory, node + 4, record)
        memory[record + 0x14] = fields[0]
        memory[record + 0x15] = fields[1]
        put(memory, record + 0x18, fields[2])
    return memory


def accepted(status, kind, word, mask):
    return (status == 0 and
            (mask == 0 or ((word >> 24) & mask) != 0) and
            ((kind >> 2) == 24 or (word >> 31) == 0))


def reference(records, mask, helper_results):
    calls = []
    for index, (status, kind, word) in enumerate(records):
        record = (RECORD0, RECORD1)[index]
        if accepted(status, kind, word, mask):
            calls.append(record)
            if helper_results.get(record, 0) == 0:
                return record, calls
    return 0, calls


class PointRecordSearchOracle(TimingOracle):
    def __init__(self, words, memory, arguments, helper_results, phase=0):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=arguments)
        self.helper_results = helper_results
        self.query_snapshots = []

    def record_call(self, target):
        if target != HELPER:
            raise AssertionError("Unexpected point-record-search call %08X" % target)
        args = self.arguments(3)
        query = args[0]
        snapshot = tuple(read(self.memory, query + offset) for offset in
                         (0x14, 0x18, 0x1C, 0x2C, 0x30, 0x34, 0x180))
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))
        self.query_snapshots.append(snapshot)

    def hook(self, target):
        if target != HELPER:
            raise AssertionError("Unexpected point-record-search hook %08X" % target)
        record = self.calls[-1][1][1]
        for register in (1, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.r[2] = self.helper_results.get(record, 0)


def native_harness(body):
    return r'''
#include <ultra64.h>
#include "structs.h"
typedef struct LinkedNode {
    struct LinkedNode *next;
    u8 data[0x30];
} LinkedNode;
s32 func_150A1DA0(struct127 *, s32, s32);
''' + body + r'''
typedef union { u32 align; u8 bytes[0x34]; } Record;
static LinkedNode nodes[2];
static Record records[2];
static s32 expectedX, expectedY, expectedZ, helperMode, calls, bad;
static void word(u8 *p, u32 v) {
    *(u32 *)p = v;
}
static void setup(u8 s0, u8 k0, u32 w0, u8 s1, u8 k1, u32 w1) {
    u32 i;
    for (i = 0; i < sizeof(records); i++) ((u8 *)records)[i] = (u8)(i * 23u + 0x37u);
    for (i = 0; i < sizeof(nodes); i++) ((u8 *)nodes)[i] = (u8)(i * 19u + 0x51u);
    nodes[0].next = &nodes[1]; nodes[1].next = 0;
    *(u8 **)&nodes[0].data[0] = records[0].bytes;
    *(u8 **)&nodes[1].data[0] = records[1].bytes;
    records[0].bytes[0x14] = s0; records[0].bytes[0x15] = k0; word(records[0].bytes + 0x18, w0);
    records[1].bytes[0x14] = s1; records[1].bytes[0x15] = k1; word(records[1].bytes + 0x18, w1);
    calls = bad = 0;
}
s32 func_150A1DA0(struct127 *query, s32 rawRecord, s32 zero) {
    u8 *record = (u8 *)rawRecord;
    if (zero || query->x_position != (f32)expectedX ||
            query->y_position != (f32)expectedY || query->z_position != (f32)expectedZ ||
            query->old_x_position != (f32)expectedX ||
            query->old_y_position != (f32)expectedY ||
            query->old_z_position != (f32)expectedZ || query->unk180 != (f32)expectedY)
        bad = 1;
    calls++;
    if (helperMode == 1 && record == records[0].bytes) return 1;
    return 0;
}
static int one(u8 s0, u8 k0, u32 w0, u8 s1, u8 k1, u32 w1,
               u32 mask, s32 x, s32 y, s32 z, s32 mode, s32 expected) {
    u8 *result;
    setup(s0, k0, w0, s1, k1, w1);
    expectedX = x; expectedY = y; expectedZ = z; helperMode = mode;
    result = func_1515EB84(x, y, z, (s32)mask, &nodes[0]);
    if (bad) return 20;
    if (result != (expected < 0 ? 0 : records[expected].bytes)) return 21;
    if (calls != (mode == 1 && expected == 1 ? 2 : (expected < 0 ? 0 : 1))) return 11;
    return 0;
}
static int run(void) {
    u32 status, kind, high, mask;
    static const s32 coords[][3] = {
        {0, 0, 0}, {1, -1, 32767}, {-32768, 0x123456, -0x654321},
        {0x7FFFFFFF, (s32)0x80000000u, -17}
    };
    for (status = 0; status < 3; status++)
        for (kind = 0; kind < 5; kind++)
            for (high = 0; high < 5; high++)
                for (mask = 0; mask < 4; mask++) {
                    u8 s = (u8[]){0, 1, 255}[status];
                    u8 k = (u8[]){0, 95, 96, 99, 255}[kind];
                    u8 h = (u8[]){0, 1, 64, 128, 255}[high];
                    u32 m = (u32[]){0, 1, 128, 255}[mask];
                    u32 w = (u32)h << 24 | 0x00123456u;
                    s32 ok = s == 0 && (m == 0 || (h & m)) && ((k >> 2) == 24 || !(w >> 31));
                    const s32 *c = coords[(status + kind + high + mask) & 3];
                    int code = one(s, k, w, 1, 0, 0, m, c[0], c[1], c[2], 0, ok ? 0 : -1);
                    if (code) return code;
                }
    if (one(0, 96, 0, 0, 96, 0, 0, 17, -91, 255, 1, 1)) return 12;
    setup(0, 96, 0, 0, 96, 0); expectedX = 1; expectedY = 2; expectedZ = 3; helperMode = 0;
    if (func_1515EB84(1, 2, 3, 0, 0) != 0 || calls || bad) return 13;
    return 0;
}
''' + START


def controls():
    body = candidate.SELECTED
    return {
        "wrong-status-byte": body.replace("record[0x14] == 0", "record[0x13] == 0"),
        "wrong-mask-byte": body.replace(">> 24", ">> 16", 1),
        "wrong-mask-gate": body.replace("mask == 0 ||", "mask != 0 ||"),
        "wrong-type-shift": body.replace("record[0x15] >> 2", "record[0x15] >> 3"),
        "wrong-type-class": body.replace("== 24", "== 23"),
        "wrong-sign-bit": body.replace(">> 31", ">> 30"),
        "wrong-helper-result": body.replace(") == 0) {", ") != 0) {"),
        "wrong-query-y": body.replace("query.unk180 = y", "query.unk180 = x"),
        "wrong-query-old-y": body.replace("query.old_y_position = y", "query.old_y_position = x"),
        "wrong-traversal": body.replace("node = node->next", "node = 0"),
    }


class GamePointRecordSearchGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = match.prepare(ROOT)
        cls.report = cls.state["report"]
        retail = (ROOT / candidate.ROM_IMAGE).read_bytes()
        cls.words = struct.unpack_from(">%dI" % match.WORDS, retail, match.ROM)
        cls.fresh = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.fresh.mkdir(exist_ok=False)

    def test_01_guarded_owner_image_callers_and_stale_rows(self):
        self.assertEqual(
            (self.report["words"], self.report["frame"],
             self.report["natural_positional_differences"],
             self.report["guards"], self.report["relocations"],
             self.report["neighbors"]),
            (61, 0x360, 4, 4, 1, 34))
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(self.report["functions"], 6051)
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        self.assertEqual(self.report["caller"]["direct_jal_calls"],
                         ["0x18b758", "0x18b904"])
        self.assertEqual(self.report["caller"]["aligned_pointer_literals"], [])
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))

        target_indices = [
            index for index, row in enumerate(self.state["qualified_rows"])
            if row["filename"] == match.FILENAME and
            row["function"] == match.FUNCTION
        ]
        self.assertEqual(len(target_indices), 4)
        for sequence, index in enumerate(target_indices):
            stale = [dict(row) for row in self.state["qualified_rows"]]
            stale[index]["expected"] = "0xDEADBEEF"
            path = self.fresh / ("stale-%d.csv" % sequence)
            match.write_patches(path, self.state["fields"], stale)
            with self.assertRaisesRegex(ValueError, "stale .*word patch"):
                emit_padded_assembly(
                    self.state["qualified_compact"], ROOT / match.ASM,
                    word_patches_path=path, filename=match.FILENAME)

    def test_02_guest_routes_query_payload_and_word_coverage(self):
        coverage = set()
        cases = 0
        statuses = (0, 1, 255)
        kinds = (0, 95, 96, 99, 255)
        highs = (0, 1, 128, 255)
        masks = (0, 1, 128, 255)
        coords = ((0, 0, 0), (1, -1, 32767),
                  (-32768, 0x123456, -0x654321),
                  (0x7FFFFFFF, 0x80000000, -17))
        for ordinal, values in enumerate(itertools.product(
                statuses, kinds, highs, masks)):
            status, kind, high, mask = values
            word = (high << 24) | 0x123456
            records = ((status, kind, word),)
            x, y, z = coords[ordinal & 3]
            helpers = {RECORD0: 0}
            expected, called = reference(records, mask, helpers)
            model = PointRecordSearchOracle(
                self.words, fixture(records),
                (x & 0xFFFFFFFF, y & 0xFFFFFFFF, z & 0xFFFFFFFF,
                 mask, NODE0), helpers, phase=(ordinal & 1) * 8).run()
            self.assertEqual(model.r[2], expected)
            self.assertEqual([args[1] for _, args in model.calls], called)
            query = tuple(float_bits(value) for value in (x, y, z, x, y, z, y))
            self.assertEqual(model.query_snapshots, [query] * len(called))
            coverage.update(pc for pc in model.visits
                            if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            cases += 1

        records = ((0, 96, 0), (0, 96, 0))
        helpers = {RECORD0: 1, RECORD1: 0}
        model = PointRecordSearchOracle(
            self.words, fixture(records), (17, -91 & 0xFFFFFFFF, 255, 0, NODE0),
            helpers).run()
        self.assertEqual(model.r[2], RECORD1)
        self.assertEqual([args[1] for _, args in model.calls], [RECORD0, RECORD1])
        coverage.update(pc for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
        cases += 1

        model = PointRecordSearchOracle(
            self.words, fixture(()), (1, 2, 3, 0, 0), {}).run()
        self.assertEqual((model.r[2], model.calls), (0, []))
        coverage.update(pc for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
        cases += 1
        reachable = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4))
        reachable.remove(match.ENTRY + 0xC8)
        self.assertEqual(coverage, reachable)
        self.assertEqual(cases, 242)

    def test_03_native32_profiles_and_effective_controls(self):
        selected = self.fresh / "native-selected.c"
        selected.write_text(native_harness(candidate.SELECTED))
        for profile in ("-O0", "-O2", "-O3"):
            target = self.fresh / ("native-selected" + profile)
            build = subprocess.run(
                native_command(profile) + ["-mstackrealign", str(selected),
                                           "-o", str(target)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(target)], capture_output=True)
            self.assertEqual(run.returncode, 0, (profile, run.stdout, run.stderr))

        effective = []
        for name, body in controls().items():
            source = self.fresh / ("control-" + name + ".c")
            target = self.fresh / ("control-" + name)
            source.write_text(native_harness(body))
            build = subprocess.run(
                native_command("-O2") + ["-mstackrealign", str(source),
                                          "-o", str(target)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, (name, build.stdout, build.stderr))
            run = subprocess.run([str(target)], capture_output=True)
            self.assertNotEqual(run.returncode, 0, name)
            effective.append(name)
        self.assertEqual(len(effective), 10)


if __name__ == "__main__":
    unittest.main()
