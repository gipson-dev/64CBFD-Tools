"""Semantic, caller, and strict-image gates for func_15189900."""

import itertools
import math
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_effect_motion_constructor_candidates as candidate
from tools.experiments import game_effect_motion_constructor_match as match
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK, put, read


ROOT = Path(__file__).resolve().parents[2]
DESCRIPTOR = 0x220000
CREATED = 0x230000
ALLOCATE = 0x15167A68
MEMCPY = 0x10022EC0
INITIALIZE = 0x1510F800
SPATIAL = 0x1510FD20


def f32(value):
    return floating(bits(value))


def cases():
    positions = (
        (0.0, 0.0, 0.0),
        (100.25, -50.5, 25.75),
        (-1000.75, 2000.5, -3000.25),
        (32767.5, -16384.25, 8192.75),
    )
    velocities = (
        (0.0, 0.0, 0.0),
        (7.75, -6.5, 5.25),
        (-11.5, 4.25, -3.75),
        (0.5, -0.25, -0.75),
        (-0.0, -0.0, 0.0),
    )
    enabled = (0, 1, 2, 0xFF, 0x100, 0x12345678)
    for seed in range(120):
        yield {
            "seed": seed,
            "position": tuple(f32(value) for value in positions[seed % len(positions)]),
            "velocity": tuple(f32(value) for value in velocities[seed % len(velocities)]),
            "enabled": enabled[seed % len(enabled)],
            "allocated": seed % 11 != 0,
        }


def fixture(case):
    memory = {STACK + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x300, 0x100)}
    memory.update({DESCRIPTOR + index: (index * 13 + case["seed"] * 19 + 0x51) & 0xFF
                   for index in range(0x50)})
    memory.update({CREATED + index: (index * 23 + case["seed"] * 11 + 0x37) & 0xFF
                   for index in range(0x78)})
    for offset, value in zip((0x08, 0x0C, 0x10), case["position"]):
        put(memory, DESCRIPTOR + offset, bits(value))
    for offset, value in zip((0x14, 0x18, 0x1C), case["velocity"]):
        put(memory, DESCRIPTOR + offset, bits(value))
    return memory


def midpoint(position, velocity):
    return math.trunc(f32(position + f32(velocity * f32(0.5)))) & 0xFFFFFFFF


def spatial_result(x, z):
    return (0x55000000 ^ ((x * 33 + z * 17) & 0x00FFFFFF)) & 0xFFFFFFFF


def expected(case, initial):
    memory = dict(initial)
    calls = [(ALLOCATE, (0x1A, 1, 0x78, 1, 0xFF, 1))]
    if not case["allocated"]:
        return memory, calls
    packet = bytes(memory[DESCRIPTOR + index] for index in range(0x50))
    for index, value in enumerate(packet):
        memory[CREATED + 0x10 + index] = value
    x = midpoint(case["position"][0], case["velocity"][0])
    z = midpoint(case["position"][2], case["velocity"][2])
    calls.extend([
        (MEMCPY, (CREATED + 0x10, DESCRIPTOR, 0x50)),
        (INITIALIZE, (0,)),
        (SPATIAL, (x, z)),
    ])
    put(memory, CREATED + 0x6C, spatial_result(x, z))
    memory[CREATED + 0x70] = 1 if case["enabled"] & 0xFF else 0
    put(memory, CREATED + 0x60, 0, 2)
    put(memory, CREATED + 0x64, bits(0.0))
    position_y, velocity_y = case["position"][1], case["velocity"][1]
    baseline = f32(position_y + velocity_y) if velocity_y < 0.0 else position_y
    put(memory, CREATED + 0x68, bits(baseline))
    return memory, calls


class MotionEffectOracle(TimingOracle):
    def __init__(self, words, memory, case, phase=0):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(DESCRIPTOR, case["enabled"]))
        self.case = case
        self.raw_calls = []

    def arguments(self, count):
        return tuple(self.r[4 + index] if index < 4 else
                     read(self.memory, self.r[29] + index * 4)
                     for index in range(count))

    def execute(self, word):
        op = word >> 26
        rs = word >> 21 & 31
        source = word >> 11 & 31
        destination = word >> 6 & 31
        function = word & 63
        if op == 17 and rs == 16 and function == 13:  # trunc.w.s
            self.f[destination] = math.trunc(floating(self.f[source])) & 0xFFFFFFFF
        else:
            super().execute(word)

    def record_call(self, target):
        counts = {ALLOCATE: 6, MEMCPY: 3, INITIALIZE: 1, SPATIAL: 2}
        if target not in counts:
            raise AssertionError("Unexpected motion-effect call %08X" % target)
        args = self.arguments(counts[target])
        self.raw_calls.append((target, args))
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        recorded, args = self.raw_calls[-1]
        if recorded != target:
            raise AssertionError((recorded, target))
        if target == ALLOCATE:
            result = CREATED if self.case["allocated"] else 0
        elif target == MEMCPY:
            destination, source, size = args
            if size != 0x50:
                raise AssertionError(args)
            for index in range(size):
                self.put(destination + index, self.get(source + index, 1), 1)
            result = destination
        elif target == INITIALIZE:
            result = 0x76543210
        else:
            result = spatial_result(*args)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.lo, self.hi = 0xA5000010, 0xA5000011
        self.r[2] = result


def controls():
    body = candidate.SELECTED
    variants = {
        "wrong-kind": body.replace("func_15167A68(0x1A, 1,", "func_15167A68(0x1B, 1,", 1),
        "wrong-size": body.replace("sizeof(MotionEffect15189900)", "0x74", 1),
        "short-copy": body.replace("sizeof(*descriptor)", "0x4C", 1),
        "skip-initialize": body.replace("        func_1510F800(0);", "        (void)0;", 1),
        "full-velocity": body.replace("velocityX * 0.5f", "velocityX * 1.0f", 1),
        "raw-enabled": body.replace("effect->enabled = enabledValue;",
                                     "effect->enabled = enabled + enabledValue * 0;", 1),
        "keep-age": body.replace("        effect->age = 0;",
                                  "        if (0) effect->age = 0;", 1),
        "omit-negative-y": body.replace(
            "effect->descriptor.positionY + effect->descriptor.velocityY",
            "effect->descriptor.positionY", 1),
    }
    if len(variants) != 8 or any(value == body for value in variants.values()):
        raise AssertionError("A motion-effect semantic control did not alter the source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef signed short s16;
typedef signed int s32;
typedef unsigned int u32;
typedef float f32;
#define NULL ((void *)0)
''' + candidate.TYPES + r'''
static MotionEffect15189900 effect;
static MotionEffect15189900 before;
static MotionEffectDescriptor15189900 descriptor;
static u32 allocated, allocateCalls, copyCalls, initializeCalls, spatialCalls;
static s32 allocateKind, allocateContext, allocateSize, allocateActive;
static u8 allocateChannel, allocateMode;
static s32 spatialX, spatialZ;
static void *func_15167A68(s32 kind,s32 context,s32 size,s32 active,u8 channel,u8 mode) {
    allocateCalls++;
    allocateKind=kind;allocateContext=context;allocateSize=size;allocateActive=active;
    allocateChannel=channel;allocateMode=mode;
    return allocated ? &effect : NULL;
}
static void *memcpy(void *destination,const void *source,u32 size) {
    u8 *out=(u8 *)destination;const u8 *in=(const u8 *)source;u32 i;
    copyCalls++;for(i=0;i<size;i++)out[i]=in[i];return destination;
}
static void __attribute__((unused)) func_1510F800(s32 value) { initializeCalls += value == 0; }
static s32 func_1510FD20(s32 x,s32 z) {
    spatialCalls++;spatialX=x;spatialZ=z;
    return (s32)(0x55000000u ^ (((u32)x*33u+(u32)z*17u)&0x00FFFFFFu));
}
''' + body + r'''
static u32 fbits(f32 value) { union {f32 f;u32 u;} bits;bits.f=value;return bits.u; }
static int equal(const u8 *left,const u8 *right,u32 size) {
    u32 i;for(i=0;i<size;i++)if(left[i]!=right[i])return 0;return 1;
}
static int one(u32 seed) {
    static const f32 positions[4][3]={{0,0,0},{100.25f,-50.5f,25.75f},
        {-1000.75f,2000.5f,-3000.25f},{32767.5f,-16384.25f,8192.75f}};
    static const f32 velocities[5][3]={{0,0,0},{7.75f,-6.5f,5.25f},
        {-11.5f,4.25f,-3.75f},{0.5f,-0.25f,-0.75f},{-0.0f,-0.0f,0.0f}};
    static const u32 enables[6]={0,1,2,255,256,0x12345678u};
    u8 *bytes;u32 i;f32 x,z,baseline;u32 enabled=enables[seed%6u];
    allocated=seed%11u!=0;allocateCalls=copyCalls=initializeCalls=spatialCalls=0;
    bytes=(u8 *)&effect;for(i=0;i<sizeof(effect);i++)bytes[i]=(u8)(i*23u+seed*11u+0x37u);
    before=effect;bytes=(u8 *)&descriptor;
    for(i=0;i<sizeof(descriptor);i++)bytes[i]=(u8)(i*13u+seed*19u+0x51u);
    descriptor.positionX=positions[seed%4u][0];descriptor.positionY=positions[seed%4u][1];
    descriptor.positionZ=positions[seed%4u][2];descriptor.velocityX=velocities[seed%5u][0];
    descriptor.velocityY=velocities[seed%5u][1];descriptor.velocityZ=velocities[seed%5u][2];
    func_15189900(&descriptor,(u8)enabled);
    if(allocateCalls!=1||allocateKind!=0x1A||allocateContext!=1||allocateSize!=0x78||
       allocateActive!=1||allocateChannel!=0xFF||allocateMode!=1)return 1;
    if(!allocated)return copyCalls||initializeCalls||spatialCalls||
        !equal((u8 *)&effect,(u8 *)&before,sizeof(effect));
    if(copyCalls!=1||initializeCalls!=1||spatialCalls!=1||
       !equal((u8 *)&effect.descriptor,(u8 *)&descriptor,sizeof(descriptor)))return 1;
    x=descriptor.positionX+descriptor.velocityX*0.5f;
    z=descriptor.positionZ+descriptor.velocityZ*0.5f;
    if(spatialX!=(s32)x||spatialZ!=(s32)z)return 1;
    if(effect.spatialHandle!=(s32)(0x55000000u^(((u32)spatialX*33u+(u32)spatialZ*17u)&0x00FFFFFFu))||
       effect.enabled!=((u8)enabled!=0)||effect.age!=0||fbits(effect.elapsed)!=0)return 1;
    baseline=descriptor.positionY;
    if(descriptor.velocityY<0.0f)baseline+=descriptor.velocityY;
    return fbits(effect.baselineY)!=fbits(baseline);
}
int main(void){u32 seed;for(seed=0;seed<300u;seed++)if(one(seed))return 1;return 0;}
'''


def run_native(label, body, optimization, expected):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / (label + ".exe")
    source.write_text(native_source(body))
    command = [
        "gcc", "-msse2", "-mfpmath=sse", optimization,
        "-std=c99", "-fno-builtin-memcpy", "-ffp-contract=off",
        "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
        "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if executed.returncode != expected:
        raise AssertionError((label, executed.returncode, executed.stderr))


class MotionEffectConstructorMatchTest(unittest.TestCase):
    def test_guest_semantics_cover_every_reachable_word(self):
        data = (ROOT / match.ROM_IMAGE).read_bytes()[match.ROM:match.ROM + match.SIZE]
        words = list(struct.unpack(">%dI" % match.WORDS, data))
        seen = set()
        count = 0
        for case, phase in itertools.product(cases(), (0, 8)):
            initial = fixture(case)
            wanted_memory, wanted_calls = expected(case, initial)
            model = MotionEffectOracle(words, initial, case, phase).run()
            self.assertEqual(model.calls, wanted_calls)
            self.assertEqual(bytes(model.memory[CREATED + index] for index in range(0x78)),
                             bytes(wanted_memory[CREATED + index] for index in range(0x78)))
            seen.update(pc - match.ENTRY for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            count += 1
        self.assertEqual(count, 240)
        # The lwc1 at +0xE4 is retail dead code: the preceding bc1fl either
        # jumps over it to +0xE8 or falls through the negative-Y arm, whose
        # unconditional branch reaches the epilogue.  Keep that fact explicit
        # instead of manufacturing an architecturally impossible guest path.
        self.assertEqual(seen, set(range(0, match.SIZE, 4)) - {0xE4})

    def test_native_profiles_and_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED,
                       optimization, 0)
        for label, body in controls().items():
            run_native("control-" + label, body, "-O2", 1)

    def test_owner_callers_and_full_image(self):
        candidate_report = candidate.compare("test-direct-owner", candidate.SELECTED)
        self.assertEqual(candidate_report["words"], match.WORDS)
        self.assertEqual(candidate_report["frame"], match.RETAIL_FRAME)
        self.assertEqual(candidate_report["differences"], 0)
        registry = match.registry_evidence(ROOT)
        self.assertEqual(registry["direct_jal_calls"], [hex(offset) for offset in match.CALLS])
        self.assertEqual(registry["aligned_pointer_literals"], [])
        result = match.prepare(ROOT)
        report = result["report"]
        installed = candidate.SELECTED in (ROOT / candidate.SOURCE).read_text()
        self.assertEqual(report["source_installed"], installed)
        self.assertEqual(report["guards"], 0)
        self.assertEqual(report["natural_positional_differences"], 0)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertTrue(report["game_data"]["exact"])


if __name__ == "__main__":
    unittest.main()
