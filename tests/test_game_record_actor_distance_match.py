"""Semantic, caller, and strict-image gates for func_15178C9C."""

import itertools
import math
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_record_actor_distance_candidates as candidate
from tools.experiments import game_record_actor_distance_match as match
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK, put


ROOT = Path(__file__).resolve().parents[2]
RECORD = 0x220000
ACTORS = 0x800CC2D0
LOOKUP = 0x15178B98
STRIDE = 0x32C


def f32(value):
    return floating(bits(value))


def cases():
    deltas = (
        (0.0, 0.0, 0.0),
        (1.75, 2.5, 3.25),
        (-1.75, -2.5, -3.25),
        (12.875, -34.75, 56.625),
        (-100.5, 200.25, -300.75),
        (1024.875, -768.5, 512.25),
    )
    for seed in range(120):
        record = (
            (seed * 37 % 2001) - 1000,
            (seed * 53 % 2401) - 1200,
            (seed * 71 % 2801) - 1400,
        )
        delta = deltas[seed % len(deltas)]
        yield {
            "seed": seed,
            "record_id": (seed * 29 + 3) & 0xFF,
            "actor_index": (0, 1, 7, 24, 25)[seed % 5],
            "record": record,
            "actor": tuple(f32(record[index] + delta[index]) for index in range(3)),
            "found": seed % 7 != 0,
        }


def fixture(case):
    memory = {STACK + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x300, 0x100)}
    memory.update({RECORD + index: (index * 13 + case["seed"] * 19 + 0x59) & 0xFF
                   for index in range(0x40)})
    actor = ACTORS + case["actor_index"] * STRIDE
    memory.update({actor + index: (index * 23 + case["seed"] * 11 + 0x31) & 0xFF
                   for index in range(0x30)})
    for offset, value in zip((0x18, 0x1C, 0x20), case["record"]):
        put(memory, RECORD + offset, value)
    for offset, value in zip((0x14, 0x18, 0x1C), case["actor"]):
        put(memory, actor + offset, bits(value))
    return memory


def reference(case):
    if not case["found"]:
        return 1
    delta = []
    for actor, record in zip(case["actor"], case["record"]):
        delta.append(math.trunc(f32(actor - f32(record))))
    squared = (delta[0] * delta[0] + delta[1] * delta[1]) & 0xFFFFFFFF
    squared = (squared + delta[2] * delta[2]) & 0xFFFFFFFF
    assert squared < 0x80000000
    return math.trunc(f32(math.sqrt(f32(signed(squared))))) & 0xFFFFFFFF


class RecordActorDistanceOracle(TimingOracle):
    def __init__(self, words, memory, case, phase=0):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(case["record_id"], case["actor_index"]))
        self.case = case

    def execute(self, word):
        op = word >> 26
        rs = word >> 21 & 31
        source = word >> 11 & 31
        destination = word >> 6 & 31
        function = word & 63
        if op == 17 and rs == 16 and function == 4:  # sqrt.s
            self.f[destination] = bits(math.sqrt(floating(self.f[source])))
        elif op == 17 and rs == 16 and function == 13:  # trunc.w.s
            self.f[destination] = math.trunc(floating(self.f[source])) & 0xFFFFFFFF
        else:
            super().execute(word)

    def record_call(self, target):
        if target != LOOKUP:
            raise AssertionError("Unexpected record-distance call %08X" % target)
        call = (target, (self.r[4] & 0xFF,))
        self.calls.append(call)
        self.events.append(("CALL", target, call[1]))

    def hook(self, target):
        if target != LOOKUP:
            raise AssertionError("Unexpected record-distance call %08X" % target)
        result = RECORD if self.case["found"] else 0
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.lo, self.hi = 0xA5000010, 0xA5000011
        self.r[2] = result


def controls():
    body = candidate.SELECTED
    variants = {
        "missing-record-zero": body.replace("    return 1;\n}", "    return 0;\n}", 1),
        "next-actor": body.replace("D_800CC2D0[actorIndex]",
                                    "D_800CC2D0[actorIndex + 1]"),
        "wrong-x-field": body.replace(".positionX", ".positionY", 1),
        "add-x": body.replace(".positionX - (f32)record->positionX",
                              ".positionX + (f32)record->positionX", 1),
        "wrong-y-record": body.replace("record->positionY", "record->positionX", 1),
        "omit-y-square": body.replace("deltaY * deltaY", "deltaY * 0", 1),
        "omit-z-square": body.replace("deltaZ * deltaZ", "deltaZ * 0", 1),
        "distance-bias": body.replace("deltaZ * deltaZ));",
                                      "deltaZ * deltaZ)) + 1;", 1),
    }
    if len(variants) != 8 or any(value == body for value in variants.values()):
        raise AssertionError("A record-distance semantic control did not alter the source")
    return variants


def native_source(body):
    body = body.replace(
        "(DistanceRecord15178C9C *)func_15178B98(recordId)",
        "nativeLookup(recordId)", 1)
    return r'''typedef unsigned char u8;
typedef signed int s32;
typedef unsigned int u32;
typedef float f32;
#define NULL ((void *)0)
''' + candidate.TYPES + r'''
DistanceActor15178C9C D_800CC2D0[27];
static DistanceRecord15178C9C record;
static u8 wantedId;
static DistanceRecord15178C9C *nativeLookup(u8 recordId) {
    return recordId == wantedId ? &record : NULL;
}
f32 sqrtf(f32 value) {
    f32 result;
    __asm__("sqrtss %1,%0" : "=x"(result) : "x"(value));
    return result;
}
''' + body + r'''
static s32 truncf32(f32 value) { return (s32)value; }
static s32 expected(u32 found, u32 actorIndex) {
    DistanceActor15178C9C *actor;
    s32 x, y, z;
    u32 squared;
    if (!found) return 1;
    actor = &D_800CC2D0[actorIndex];
    x = truncf32(actor->positionX - (f32)record.positionX);
    y = truncf32(actor->positionY - (f32)record.positionY);
    z = truncf32(actor->positionZ - (f32)record.positionZ);
    squared = (u32)(x * x + y * y) + (u32)(z * z);
    return truncf32(sqrtf((f32)(s32)squared));
}
static int one(u32 seed) {
    static const f32 delta[6][3] = {
        {0.0f,0.0f,0.0f}, {1.75f,2.5f,3.25f}, {-1.75f,-2.5f,-3.25f},
        {12.875f,-34.75f,56.625f}, {-100.5f,200.25f,-300.75f},
        {1024.875f,-768.5f,512.25f}
    };
    static const u32 indices[5] = {0,1,7,24,25};
    u32 found = seed % 7u != 0, index = indices[seed % 5u], i;
    s32 wanted, actual;
    u8 *bytes = (u8 *)D_800CC2D0;
    for (i = 0; i < sizeof(D_800CC2D0); i++) bytes[i] = (u8)(i * 23u + seed * 11u + 0x31u);
    bytes = (u8 *)&record;
    for (i = 0; i < sizeof(record); i++) bytes[i] = (u8)(i * 13u + seed * 19u + 0x59u);
    record.positionX = (s32)(seed * 37u % 2001u) - 1000;
    record.positionY = (s32)(seed * 53u % 2401u) - 1200;
    record.positionZ = (s32)(seed * 71u % 2801u) - 1400;
    D_800CC2D0[index].positionX = (f32)record.positionX + delta[seed % 6u][0];
    D_800CC2D0[index].positionY = (f32)record.positionY + delta[seed % 6u][1];
    D_800CC2D0[index].positionZ = (f32)record.positionZ + delta[seed % 6u][2];
    D_800CC2D0[index + 1u].positionX = (f32)record.positionX + 10.25f;
    D_800CC2D0[index + 1u].positionY = (f32)record.positionY - 20.5f;
    D_800CC2D0[index + 1u].positionZ = (f32)record.positionZ + 30.75f;
    wantedId = found ? (u8)(seed * 29u + 3u) : (u8)(seed * 29u + 4u);
    wanted = expected(found, index);
    actual = func_15178C9C((u8)(seed * 29u + 3u), (s32)index);
    return actual != wanted;
}
int main(void) { u32 seed; for (seed = 0; seed < 600u; seed++) if (one(seed)) return 1; return 0; }
'''


def run_native(label, body, optimization, expected):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / (label + ".exe")
    source.write_text(native_source(body))
    command = [
        "gcc", "-msse2", "-mfpmath=sse", optimization,
        "-std=c99", "-fno-strict-aliasing", "-ffp-contract=off",
        "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
        "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if executed.returncode != expected:
        raise AssertionError((label, executed.returncode, executed.stderr))


class RecordActorDistanceMatchTest(unittest.TestCase):
    def test_guest_semantics_cover_every_word(self):
        data = (ROOT / match.ROM_IMAGE).read_bytes()[match.ROM:match.ROM + match.SIZE]
        words = list(struct.unpack(">%dI" % match.WORDS, data))
        seen = set()
        count = 0
        for case, phase in itertools.product(cases(), (0, 8)):
            model = RecordActorDistanceOracle(words, fixture(case), case, phase).run()
            self.assertEqual(model.r[2], reference(case))
            self.assertEqual(model.calls, [(LOOKUP, (case["record_id"],))])
            seen.update(pc - match.ENTRY for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            count += 1
        self.assertEqual(count, 240)
        self.assertEqual(seen, set(range(0, match.SIZE, 4)))

    def test_native_profiles_and_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED,
                       optimization, 0)
        for label, body in controls().items():
            run_native("control-" + label, body, "-O2", 1)

    def test_guarded_owner_caller_and_full_image(self):
        candidate_report = candidate.compare("test-guarded-owner", candidate.SELECTED)
        self.assertEqual(candidate_report["words"], match.WORDS)
        self.assertEqual(candidate_report["differences"], len(match.PATCH_ROWS))
        self.assertEqual([row["offset"] for row in candidate_report["difference_rows"]],
                         [int(row["offset"], 0) for row in match.PATCH_ROWS])
        registry = match.registry_evidence(ROOT)
        self.assertEqual(registry["direct_jal_calls"], ["0xcb3a4"])
        self.assertEqual(registry["aligned_pointer_literals"], [])
        result = match.prepare(ROOT)
        report = result["report"]
        installed = candidate.SELECTED in (ROOT / candidate.SOURCE).read_text()
        self.assertEqual(report["source_installed"], installed)
        self.assertEqual(report["guards"], len(match.PATCH_ROWS))
        self.assertEqual(report["natural_positional_differences"], len(match.PATCH_ROWS))
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertTrue(report["game_data"]["exact"])


if __name__ == "__main__":
    unittest.main()
