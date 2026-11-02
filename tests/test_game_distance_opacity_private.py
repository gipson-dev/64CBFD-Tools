"""Guest, native, callback, and source qualification for func_15179CB0."""
import hashlib
import itertools
import math
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_distance_opacity_guard_match as match
from tools.experiments.game_four_head_lookup_match import payload
from tools.tests import game_view_point_projection_oracle as point
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.test_game_projected_packet_draw import native_command


RECORD = 0x20000
VIEWER = 0x30000
VIEWER_GLOBAL = 0x800DBFF0
FCSRS = (0, 3, 0x800004, 0xA5A50003)


def fixture(record_x=0, record_z=0, viewer_x=0.0, viewer_z=0.0):
    memory = {RECORD + offset: 0xA5 for offset in range(0xB8)}
    memory.update({VIEWER + offset: 0xA5 for offset in range(0x304)})
    point.put(memory, RECORD + 0xA0, record_x & 0xFFFF, 2)
    point.put(memory, RECORD + 0x9C, record_z & 0xFFFF, 2)
    point.put(memory, VIEWER + 0x2F8, point.bits(viewer_x))
    point.put(memory, VIEWER + 0x300, point.bits(viewer_z))
    point.put(memory, VIEWER_GLOBAL, VIEWER)
    return memory


def signed_half(memory, address):
    value = point.read(memory, address, 2)
    return value if value < 0x8000 else value - 0x10000


def divided(a, b):
    return point.bits(point.floating(a) / point.floating(b))


def reference(initial):
    memory = dict(initial)
    viewer = point.read(memory, VIEWER_GLOBAL)
    dx = point.sub(point.bits(float(signed_half(memory, RECORD + 0xA0))),
                   point.read(memory, viewer + 0x300))
    dz = point.sub(point.bits(float(signed_half(memory, RECORD + 0x9C))),
                   point.read(memory, viewer + 0x2F8))
    squared = point.add(point.mul(dx, dx), point.mul(dz, dz))
    value = point.floating(squared)
    distance = point.bits(math.sqrt(value) if value >= 0.0 else math.nan)
    scaled = point.mul(point.bits(160.0), distance)
    opacity = point.sub(point.bits(255.0), divided(scaled, point.bits(1000.0)))
    number = point.floating(opacity)
    byte = math.trunc(number) & 0xFF if (math.isfinite(number) and
           0.0 <= number < 2.0 ** 32) else 0xFF
    point.put(memory, RECORD + 0xB4, byte, 1)
    return memory, byte


class Oracle(point.PointProjectionOracle):
    def __init__(self, words, memory, fcsr=0):
        super().__init__(words, memory, (RECORD,), [], entry=match.ENTRY)
        self.fcsr = self.initial_fcsr = fcsr

    def execute(self, word):
        op, rs, function = word >> 26, word >> 21 & 31, word & 63
        if op == 17 and (rs in (2, 6) or rs == 16 and function == 36):
            AreaOracle.execute(self, word)
        elif op == 17 and rs == 16 and function == 4:
            value = point.floating(self.f[word >> 11 & 31])
            self.f[word >> 6 & 31] = point.bits(
                math.sqrt(value) if value >= 0.0 else math.nan)
            self.r[0] = 0
        else:
            super().execute(word)


class GameDistanceOpacityPrivateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / match.BUILD
        cls.names = (match.SOURCE, match.PATHS["elf"], match.PATHS["object"],
                     match.PATHS["guards"], "conker/progress.csv")
        cls.before = {name: hashlib.sha256((cls.root / name).read_bytes()).hexdigest()
                      for name in cls.names}
        cls.report, _, cls.obj, *_ = match.prepare(cls.root, cls.output)
        raw, _ = payload(cls.obj, match.FUNCTION)
        cls.candidate = list(struct.unpack(">%dI" % (match.BODY_SIZE // 4),
                                           match.linked_payload(raw)))
        cls.retail = list(struct.unpack(">%dI" % (match.BODY_SIZE // 4),
            match.retail_slot(cls.root)[:match.BODY_SIZE]))

    def compare(self, memory, fcsr=0):
        expected, byte = reference(memory)
        machines = [Oracle(words, memory, fcsr).run()
                    for words in (self.retail, self.candidate)]
        for machine in machines:
            self.assertEqual(machine.memory, expected)
            self.assertEqual(machine.memory[RECORD + 0xB4], byte)
            self.assertEqual(machine.fcsr, fcsr)
        self.assertEqual((machines[0].r, machines[0].f, machines[0].condition),
                         (machines[1].r, machines[1].f, machines[1].condition))
        return machines

    def test_01_guest_distance_grid_conversion_paths_and_coverage(self):
        halves = (-32768, -1024, 0, 1024, 32767)
        viewers = (-32768.5, 0.0, 32767.5)
        seen = set()
        cases = 0
        for record_x, record_z, viewer_x, viewer_z in itertools.product(
                halves, halves, viewers, viewers):
            model = self.compare(fixture(record_x, record_z, viewer_x, viewer_z),
                                 FCSRS[cases % len(FCSRS)])[0]
            seen.update(model.visits)
            cases += 1
        for viewer_x, viewer_z in ((math.inf, 0.0), (-math.inf, 0.0),
                                   (math.nan, 0.0), (0.0, math.inf),
                                   (0.0, -math.inf), (0.0, math.nan)):
            model = self.compare(fixture(0, 0, viewer_x, viewer_z),
                                 FCSRS[cases % len(FCSRS)])[0]
            seen.update(model.visits)
            cases += 1
        self.assertEqual(cases, 231)
        self.assertGreaterEqual(len(seen), 57)

    def test_02_callback_table_and_frozen_inputs(self):
        rom = (self.root / "conker/conker.us.bin").read_bytes()
        self.assertEqual(struct.unpack_from(">I", rom, 0x2314C0)[0], match.ENTRY)
        table = (self.root / "conker/asm/data/22FF90.rodata.s").read_text()
        self.assertIn("2314C0 8008CA00 15179CB0", table)
        self.assertIn("func_15179CB0", table)
        self.assertEqual(self.before, {name: hashlib.sha256(
            (self.root / name).read_bytes()).hexdigest() for name in self.names})

    def test_03_native_profiles_and_effective_negative_controls(self):
        head = """typedef unsigned char u8;
typedef unsigned short u16;
typedef short s16;
typedef unsigned int u32;
typedef float f32;
extern u8 *D_800DBFF0;
f32 sqrtf(f32);
"""
        driver = self.output / "native-distance-opacity-driver.c"
        driver.write_text(NATIVE)
        controls = {
            "record-offset": match.candidate.SELECTED.replace(
                "record + 0xA0", "record + 0x9E"),
            "viewer-offset": match.candidate.SELECTED.replace(
                "viewer + 0x300", "viewer + 0x2FC"),
            "missing-axis": match.candidate.SELECTED.replace(
                "dx * dx + dz * dz", "dx * dx + dz * 0.0f"),
            "scale": match.candidate.SELECTED.replace("160.0f", "159.0f"),
            "base": match.candidate.SELECTED.replace("255.0f", "254.0f"),
            "store": match.candidate.SELECTED.replace("record[0xB4]", "record[0xB5]"),
        }
        for optimization in ("-O0", "-O2", "-O3"):
            for label, body in (("selected", match.candidate.SELECTED), *controls.items()):
                source = self.output / ("native-%s-%s.c" %
                                        (label, optimization[1:]))
                source.write_text(head + body + "\n")
                executable = self.output / ("native-%s-%s" %
                                            (label, optimization[1:]))
                subprocess.run(native_command(optimization) + ["-mstackrealign",
                    "-fno-builtin", "-fno-strict-aliasing",
                    str(source.relative_to(self.root)),
                    str(driver.relative_to(self.root)), "-o", str(executable)],
                    cwd=self.root, capture_output=True, check=True)
                result = subprocess.run([str(executable)], capture_output=True)
                if label == "selected":
                    self.assertEqual(result.returncode, 0,
                                     (optimization, result.stderr))
                else:
                    self.assertNotEqual(result.returncode, 0,
                                        (optimization, label))


NATIVE = r'''
typedef unsigned char u8;
typedef unsigned short u16;
typedef short s16;
typedef unsigned int u32;
typedef float f32;
static u8 viewer[0x304] __attribute__((aligned(4)));
static u8 record[0xB8] __attribute__((aligned(4)));
u8 *D_800DBFF0 = viewer;
void func_15179CB0(u8 *);
f32 sqrtf(f32 value) {
    f32 result;
    __asm__("sqrtss %1,%0" : "=x"(result) : "x"(value));
    return result;
}
static int run(void) {
    static s16 halves[] = {-800, -400, 0, 400, 800};
    static f32 views[] = {-100.0f, 0.0f, 100.0f};
    int x, z, vx, vz, i, count = 0;
    f32 dx, dz, distance, opacity;
    u8 expected;
    for (x = 0; x < 5; x++) for (z = 0; z < 5; z++)
    for (vx = 0; vx < 3; vx++) for (vz = 0; vz < 3; vz++) {
        for (i = 0; i < 0xB8; i++) record[i] = 0;
        for (i = 0; i < 0x304; i++) viewer[i] = 0;
        *(s16 *)(record + 0xA0) = halves[x];
        *(s16 *)(record + 0x9C) = halves[z];
        *(f32 *)(viewer + 0x2F8) = views[vx];
        *(f32 *)(viewer + 0x300) = views[vz];
        record[0xB4] = 0xA5;
        record[0xB5] = 0x5A;
        dx = (f32)halves[x] - views[vz];
        dz = (f32)halves[z] - views[vx];
        distance = sqrtf(dx * dx + dz * dz);
        opacity = 255.0f - distance * 160.0f / 1000.0f;
        if (!(opacity >= 0.0f && opacity <= 255.0f)) return 20;
        expected = (u8)(u32)opacity;
        func_15179CB0(record);
        if (record[0xB4] != expected || record[0xB5] != 0x5A) return 21;
        count++;
    }
    return count == 225 ? 0 : 22;
}
void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
'''


if __name__ == "__main__":
    unittest.main()
