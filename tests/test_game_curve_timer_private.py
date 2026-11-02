"""Guest, native, alias, and callback qualification for func_15131DEC."""
import hashlib
import itertools
import math
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_curve_timer_guard_match as match
from tools.experiments.game_four_head_lookup_match import payload
from tools.tests import game_view_point_projection_oracle as point
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_projected_packet_draw import native_command


STACK = point.STACK
RECORD = 0x20000
STEP = 0x800BE9A4
FCSRS = (0, 3, 0x800004, 0xA5A50003)


def fixture(time=4.0, limit=5.0, multiplier=1.5, base=255.75,
            decay=2.0, step=1.0, alias=0, event=0x12345678):
    record = (RECORD, STEP - 0xA8, STEP - 0xAC, STEP - 0xB0,
              STEP - 0xB4, STEP - 0xB8, STEP - 0x38, STEP - 0x3C)[alias]
    memory = {STACK + offset: (offset * 17 + 0xA5) & 0xFF
              for offset in range(-128, 128)}
    memory.update({record + offset: 0xA5 for offset in range(0xC0)})
    for offset, value in ((0xA8, time), (0xAC, limit), (0xB0, multiplier),
                          (0xB4, base), (0xB8, decay)):
        put(memory, record + offset, point.bits(value))
    put(memory, STEP, point.bits(step))
    return memory, record, event


def reference(initial, record):
    memory = dict(initial)
    time = read(memory, record + 0xA8)
    value = point.floating(time)
    root = point.bits(math.sqrt(value) if value >= 0.0 else math.nan)
    scale = point.mul(root, read(memory, record + 0xB0))
    put(memory, record + 0x3C, scale)
    put(memory, record + 0x38, scale)
    curve = point.sub(read(memory, record + 0xB4),
                      point.mul(point.mul(read(memory, record + 0xB8), time), time))
    number = point.floating(curve)
    byte = math.trunc(number) & 0xFF if (math.isfinite(number) and
           -1.0 < number < 2.0 ** 32) else 0xFF
    put(memory, record + 0x2B, byte, 1)
    updated = point.add(time, read(memory, STEP))
    put(memory, record + 0xA8, updated)
    result = 0 if point.floating(read(memory, record + 0xAC)) < \
        point.floating(updated) else 1
    return memory, result


class Oracle(point.PointProjectionOracle):
    def __init__(self, words, memory, record, event=0, fcsr=0):
        super().__init__(words, memory, (record, event), [], 0, match.ENTRY)
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


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 128 <= address < STACK + 128}


class GameCurveTimerPrivateTests(unittest.TestCase):
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
        cls.candidate = list(struct.unpack(">%dI" % match.WORDS,
                                           match.linked_payload(raw)))
        cls.retail = list(struct.unpack(">%dI" % match.WORDS,
                                        match.retail_bytes(cls.root)))

    def compare(self, memory, record, event=0, fcsr=0):
        expected, result = reference(memory, record)
        machines = [Oracle(words, memory, record, event, fcsr).run()
                    for words in (self.retail, self.candidate)]
        for machine in machines:
            self.assertEqual(public(machine.memory), public(expected))
            self.assertEqual(machine.r[2], result)
            self.assertEqual(machine.fcsr, fcsr)
        self.assertEqual((machines[0].r, machines[0].f, machines[0].condition),
                         (machines[1].r, machines[1].f, machines[1].condition))
        return machines

    def test_01_finite_guest_semantics_conversion_paths_and_coverage(self):
        cases = 0
        seen = set()
        for values in itertools.product(
                (0.0, 0.25, 1.0, 4.0),
                (0.5, 1.5, -2.0),
                (-2.0, 255.75, 2147483648.0, 4294967040.0, 4294967296.0),
                (0.0, 0.5, 2.0),
                (0.0, 2.0, 5.0),
                (0.25, 1.0)):
            time, multiplier, base, decay, limit, step = values
            machine = self.compare(*fixture(time, limit, multiplier, base,
                                            decay, step), fcsr=FCSRS[cases % 4])[0]
            seen.update(machine.visits)
            cases += 1
        self.assertEqual(cases, 1080)
        self.assertGreaterEqual(len(seen), 60)

    def test_02_aliases_event_values_callback_table_and_inputs(self):
        for alias, event, fcsr in itertools.product(range(8),
                (0, 1, -1, 0x7FFFFFFF), FCSRS):
            self.compare(*fixture(alias=alias, event=event), fcsr=fcsr)
        rom = (self.root / "conker/conker.us.bin").read_bytes()
        self.assertEqual(struct.unpack_from(">I", rom, 0x22E2BC)[0], match.ENTRY)
        table = (self.root / "conker/asm/data/22E220.rodata.s").read_text()
        self.assertIn("22E2BC 800897FC 15131DEC", table)
        self.assertIn("func_15131DEC", table)
        self.assertEqual(self.before, {name: hashlib.sha256(
            (self.root / name).read_bytes()).hexdigest() for name in self.names})

    def test_03_native_profiles_and_effective_negative_controls(self):
        head = """typedef unsigned char u8;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
extern f32 D_800BE9A4;
f32 sqrtf(f32);
"""
        driver = self.output / "native-curve-timer-driver.c"
        driver.write_text(NATIVE)
        controls = {
            "timer": match.candidate.SELECTED.replace(
                "+= D_800BE9A4", "-= D_800BE9A4"),
            "width": match.candidate.SELECTED.replace(
                "record[0x2B] =", "*(u32 *)(record + 0x2B) ="),
            "curve": match.candidate.SELECTED.replace(
                "*(f32 *)(record + 0xB8) * time * time",
                "*(f32 *)(record + 0xB8) * time"),
            "expiry": match.candidate.SELECTED.replace(
                "*(f32 *)(record + 0xAC) < *(f32 *)(record + 0xA8)",
                "*(f32 *)(record + 0xAC) > *(f32 *)(record + 0xA8)"),
        }
        for optimization in ("-O0", "-O2", "-O3"):
            for label, body in (("selected", match.candidate.SELECTED), *controls.items()):
                source = self.output / ("native-%s-%s.c" %
                                        (label, optimization[1:]))
                source.write_text(head + body + "\n")
                executable = self.output / ("native-%s-%s" %
                                            (label, optimization[1:]))
                subprocess.run(native_command(optimization) + ["-mstackrealign",
                    "-fno-builtin", str(source.relative_to(self.root)),
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
typedef unsigned int u32;
typedef int s32;
typedef float f32;
typedef struct {
    u8 pad0[0x2B];
    u8 value;
    u8 pad2C[0x0C];
    f32 scale0;
    f32 scale1;
    u8 pad40[0x68];
    f32 time;
    f32 limit;
    f32 multiplier;
    f32 base;
    f32 decay;
} Record;
static Record record;
f32 D_800BE9A4;
s32 func_15131DEC(u8 *, s32);
f32 sqrtf(f32 value) {
    f32 result;
    __asm__("sqrtss %1,%0" : "=x"(result) : "x"(value));
    return result;
}
static int run(void) {
    static f32 times[] = {0.0f, 0.25f, 1.0f, 4.0f};
    static f32 bases[] = {0.5f, 255.75f, 2147483648.0f, 4294967040.0f};
    int t, b, d, l, s, i, count = 0;
    f32 time, curve, scale;
    u8 expected;
    if (sizeof(void *) != 4 || __builtin_offsetof(Record, value) != 0x2B ||
        __builtin_offsetof(Record, time) != 0xA8) return 20;
    for (t = 0; t < 4; t++) for (b = 0; b < 4; b++)
    for (d = 0; d < 4; d++) for (l = 0; l < 3; l++) for (s = 0; s < 2; s++) {
        record.time = times[t];
        record.limit = (f32)l * 2.0f;
        record.multiplier = 1.5f;
        record.base = bases[b];
        record.decay = (f32)d * 0.5f;
        D_800BE9A4 = s ? 0.25f : 1.0f;
        record.scale0 = 17.0f;
        record.scale1 = 19.0f;
        record.value = 0xA5;
        for (i = 0; i < 12; i++) record.pad2C[i] = 0xA5;
        time = times[t];
        scale = sqrtf(time) * 1.5f;
        curve = bases[b] - ((f32)d * 0.5f * time) * time;
        expected = (u8)(u32)curve;
        if (func_15131DEC((u8 *)&record, 0x12345678) !=
            !(record.limit < time + D_800BE9A4)) return 21;
        if (record.scale0 != scale || record.scale1 != scale ||
            record.value != expected || record.time != time + D_800BE9A4)
            return 22;
        for (i = 0; i < 12; i++) if (record.pad2C[i] != 0xA5) return 23;
        count++;
    }
    return count == 384 ? 0 : 24;
}
void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
'''


if __name__ == "__main__":
    unittest.main()
