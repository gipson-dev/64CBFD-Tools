"""Semantic, registry, owner and strict-image gates for func_15171FC0."""

from dataclasses import dataclass
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_animated_quad_state_update_candidates as candidate
from tools.experiments import game_animated_quad_state_update_match as match
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_frame_timing_oracle import STACK, TimingOracle
from tools.tests.test_game_point_transform_match import put, read


ROOT = Path(__file__).resolve().parents[2]
RECORD = 0x22000
DESCRIPTORS = 0x30000
TICKS = 0x800BE9E4
TABLE = 0x8008CA4C
RELEASE = 0x1516972C


def u32(value):
    return value & 0xFFFFFFFF


def s32(value):
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def s16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


@dataclass(frozen=True)
class Case:
    lifetime: int = 1
    frame: int = 0
    step: int = 0x100
    frame_count: int = 2
    image: int = 0
    flags: int = 0
    ticks: int = 1
    phase: int = 0
    seed: int = 0


def fixture(case=Case()):
    memory = {STACK + index: (index * 17 + case.seed + 0xA5) & 0xFF
              for index in range(-0x400, 0x100)}
    for base, size in ((RECORD - 0x20, 0xA0), (DESCRIPTORS, 0x1000),
                       (TABLE, 0x400), (TICKS, 4)):
        memory.update({base + index: (index * 13 + case.seed * 19 + 0x59) & 0xFF
                       for index in range(size)})
    for image in range(256):
        descriptor = DESCRIPTORS + image * 0x10
        put(memory, TABLE + image * 4, descriptor)
        memory[descriptor + 4] = (image * 29 + 7) & 0xFF
    put(memory, RECORD + 0x50, case.lifetime, 2)
    put(memory, RECORD + 0x52, case.frame, 2)
    put(memory, RECORD + 0x54, case.step, 2)
    memory[RECORD + 0x58] = case.image & 0xFF
    memory[RECORD + 0x59] = case.flags & 0xFF
    memory[DESCRIPTORS + (case.image & 0xFF) * 0x10 + 4] = case.frame_count & 0xFF
    put(memory, TICKS, case.ticks)
    return memory


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x400 <= address < STACK + 0x100}


def reference(initial):
    memory = dict(initial)
    calls = []
    lifetime = s16(read(memory, RECORD + 0x50, 2))
    if lifetime < -1:
        lifetime = s16(lifetime + 1)
        put(memory, RECORD + 0x50, lifetime, 2)
        if lifetime == -1:
            calls.append((RELEASE, (RECORD,)))
    elif lifetime == 0:
        put(memory, RECORD + 0x50, -3, 2)
    elif lifetime != -1:
        flags = memory[RECORD + 0x59]
        if (flags & 4) == 0:
            ticks = read(memory, TICKS)
            if lifetime > s32(ticks):
                put(memory, RECORD + 0x50, u32(lifetime) - ticks, 2)
            else:
                put(memory, RECORD + 0x50, 0, 2)
        frame = s16(read(memory, RECORD + 0x52, 2))
        step = s16(read(memory, RECORD + 0x54, 2))
        frame = s16(frame + step)
        put(memory, RECORD + 0x52, frame, 2)
        image = memory[RECORD + 0x58]
        descriptor = read(memory, TABLE + image * 4)
        frame_count = memory[descriptor + 4]
        quotient = abs(frame) // 256
        if frame < 0:
            quotient = -quotient
        if quotient >= frame_count:
            if flags & 4:
                put(memory, RECORD + 0x50, -3, 2)
            else:
                put(memory, RECORD + 0x52, (frame_count << 8) - 256, 2)
    return memory, calls


class QuadOracle(TimingOracle):
    def __init__(self, words, memory, case=Case(), fault=None):
        super().__init__(words, memory, phase=case.phase, entry=match.ENTRY,
                         arguments=(RECORD,))
        self.root_fault = fault

    def record_call(self, target):
        if target != RELEASE:
            raise AssertionError("Unexpected animated-quad helper %08X" % target)
        args = tuple(self.arguments(1))
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target != RELEASE:
            raise AssertionError("Unbounded animated-quad helper %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.r[2] = 0x76543210


def controls():
    body = candidate.SELECTED
    variants = {
        "wrong-release-threshold": body.replace(
            "record->lifetime == -1", "record->lifetime == -2", 1),
        "wrong-zero-state": body.replace(
            "record->lifetime = -3;", "record->lifetime = -2;", 1),
        "wrong-tick-flag": body.replace("record->flags & 4", "record->flags & 8", 1),
        "skip-tick": body.replace(
            "                record->lifetime = (s32)((u32)record->lifetime -\n"
            "                                         (u32)D_800BE9E4);\n", "", 1),
        "wrong-frame-step": body.replace(
            "record->frame += record->frameStep;", "record->frame += 1;", 1),
        "arithmetic-frame-shift": body.replace(
            "record->frame / 256", "record->frame >> 8", 1),
        "wrong-frame-metadata": body.replace(
            "[record->imageIndex][4]", "[record->imageIndex][5]", 1),
        "wrong-clamp": body.replace("(frameCount << 8) - 256",
                                      "(frameCount << 8) - 128", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("An animated-quad control did not alter source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef unsigned short u16;
typedef signed short s16;
typedef signed int s32;
typedef unsigned int u32;
typedef struct struct102 { u8 retained[0x60]; } struct102;
typedef struct {
    u8 retained00[0x50];
    s16 lifetime;
    s16 frame;
    s16 frameStep;
    u16 color;
    u8 imageIndex;
    u8 flags;
    u8 retained5A[6];
} QuadEffect19F150;
static u8 descriptors[256][8];
u8 *D_8008CA4C[256];
s32 D_800BE9E4;
static s32 releases;
static QuadEffect19F150 *released;
void func_1516972C(struct102 *record) {
    releases++;
    released=(QuadEffect19F150 *)record;
}
''' + body + r'''
static s32 signed16(u32 value) {return (value&0x8000u)?(s32)(value|0xFFFF0000u):(s32)value;}
static void expected(QuadEffect19F150 *record,s32 *releaseExpected) {
    s32 lifetime=record->lifetime,frameCount,frame;
    if(lifetime < -1) {
        record->lifetime=(s16)(lifetime+1);
        if(record->lifetime == -1)*releaseExpected=1;
    } else if(lifetime == 0) record->lifetime=-3;
    else if(lifetime != -1) {
        if((record->flags&4)==0) {
            if(lifetime>D_800BE9E4)
                record->lifetime=(s16)((u32)lifetime-(u32)D_800BE9E4);
            else record->lifetime=0;
        }
        record->frame=(s16)((s32)record->frame+(s32)record->frameStep);
        frame=record->frame;
        frameCount=D_8008CA4C[record->imageIndex][4];
        if(frame/256>=frameCount) {
            if(record->flags&4)record->lifetime=-3;
            else record->frame=(s16)((frameCount<<8)-256);
        }
    }
}
static int one(u32 seed) {
    static const u16 lifetimes[]={0x8000,0xFFFD,0xFFFE,0xFFFF,0,1,2,0x7FFF};
    static const u16 frames[]={0x8000,0xFEFF,0xFF00,0xFFFF,0,0xFF,0x100,0x7FFF};
    static const u16 steps[]={0x8000,0xFF00,0xFFFF,0,1,0x100,0x7FFF};
    static const u8 counts[]={0,1,2,3,127,255};
    static const u8 flagValues[]={0,4,8,255};
    static const u32 tickValues[]={0,1,2,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};
    QuadEffect19F150 record,wanted;u8 *left=(u8 *)&record,*right=(u8 *)&wanted;
    u32 index;u8 image=(u8)seed;s32 releaseExpected=0;
    for(index=0;index<sizeof(record);index++)left[index]=(u8)(index*13u+seed*19u+0x59u);
    record.lifetime=(s16)signed16(lifetimes[seed%8]);
    record.frame=(s16)signed16(frames[(seed/3)%8]);
    record.frameStep=(s16)signed16(steps[(seed/5)%7]);
    record.imageIndex=image;record.flags=flagValues[(seed/7)%4];
    D_800BE9E4=(s32)tickValues[(seed/11)%6];
    for(index=0;index<256;index++) {D_8008CA4C[index]=descriptors[index];descriptors[index][4]=(u8)(index*29u+7u);}
    descriptors[image][4]=counts[(seed/13)%6];wanted=record;
    expected(&wanted,&releaseExpected);releases=0;released=(QuadEffect19F150 *)0;
    func_15171FC0(&record);
    for(index=0;index<sizeof(record);index++)if(left[index]!=right[index])return 1;
    if(releases!=releaseExpected)return 2;
    if(releaseExpected && released!=&record)return 3;
    if(!releaseExpected && released!=(QuadEffect19F150 *)0)return 4;
    return 0;
}
static int run(void) {
    u32 seed;
    if(sizeof(void *)!=4||sizeof(QuadEffect19F150)!=0x60)return 9;
    for(seed=0;seed<4096;seed++)if(one(seed))return 1;
    return 0;
}
void _start(void) {s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
'''


def run_native(label, body, optimization, expected):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / (label + ".elf")
    source.write_text(native_source(body))
    command = [
        "gcc", "-m32", "-std=c99", optimization, "-fno-pie", "-no-pie",
        "-ffreestanding", "-fno-strict-aliasing", "-fno-stack-protector",
        "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
        "-Wall", "-Wextra", "-Werror", "-nostdlib", str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if executed.returncode != expected:
        raise AssertionError((label, executed.returncode, executed.stderr))


class GameAnimatedQuadStateUpdateMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.retail = list(struct.unpack_from(">65I", (ROOT / match.ROM_IMAGE).read_bytes(),
                                                   match.ROM))

    def receipt(self, name, data):
        (self.output / (name + ".json")).write_text(json.dumps(data, indent=2) + "\n")

    def test_01_direct_shape_owner_neighbors_and_strict_image(self):
        for label, flags in (("debug", ("-O2", "-g3")), ("plain", ("-O2",))):
            direct = candidate.compare("test-" + label, candidate.SELECTED, flags)
            self.assertEqual((direct["words"], direct["frame"], direct["differences"],
                              direct["diagnostics"]), (65, 0x18, 0, ""))
            self.assertEqual(direct["bindings"], {
                "0x02C": [("R_MIPS_26", "func_1516972C")],
                "0x05C": [("R_MIPS_HI16", "D_800BE9E4")],
                "0x06C": [("R_MIPS_LO16", "D_800BE9E4")],
                "0x094": [("R_MIPS_HI16", "D_8008CA4C")],
                "0x0A8": [("R_MIPS_LO16", "D_8008CA4C")],
            })
        report = match.prepare(ROOT)["report"]
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertEqual((report["guards"], report["neighbors"],
                          report["strict_exclusions"]), (0, 6, 0))
        self.assertTrue(report["all_addresses_fixed"])
        self.assertTrue(report["game_data"]["exact"])

    def test_02_guest_lifetime_frame_table_and_all_words(self):
        explicit = [
            Case(-3, 0, 0, 2, 0, 0, 1),
            Case(-2, 0, 0, 2, 1, 0, 1),
            Case(-1, 0, 0, 2, 2, 0, 1),
            Case(0, 0, 0, 2, 3, 0, 1),
            Case(5, 0, 0x100, 2, 4, 0, 1),
            Case(5, 0x100, 0x100, 2, 5, 4, 1),
            Case(5, -1, -0xFF, 0, 6, 0, 0x80000000),
            Case(1, 0x7FFF, 1, 255, 7, 255, 0xFFFFFFFF),
        ]
        lifetimes = (-32768, -3, -2, -1, 0, 1, 2, 32767)
        frames = (-32768, -257, -256, -1, 0, 255, 256, 32767)
        steps = (-32768, -256, -1, 0, 1, 256, 32767)
        counts = (0, 1, 2, 3, 127, 255)
        flags = (0, 4, 8, 255)
        ticks = (0, 1, 2, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
        cases = list(explicit)
        for index in range(4096):
            cases.append(Case(lifetimes[index % len(lifetimes)],
                              frames[(index // 3) % len(frames)],
                              steps[(index // 5) % len(steps)],
                              counts[(index // 7) % len(counts)], index & 0xFF,
                              flags[(index // 11) % len(flags)],
                              ticks[(index // 13) % len(ticks)],
                              (index & 1) * 8, index & 0xFF))
        coverage = set()
        for case in cases:
            initial = fixture(case)
            wanted, calls = reference(initial)
            model = QuadOracle(self.retail, initial, case).run()
            self.assertEqual((public(model.memory), model.calls),
                             (public(wanted), calls))
            coverage.update(model.visits)
        self.assertEqual(coverage, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.receipt("guest-contract", {
            "cases": len(cases), "words": len(coverage), "all_image_indices": True,
            "signed_lifetime_and_frame_edges": True, "full_width_ticks": True,
            "release_and_clamp_paths": True,
        })

    def test_03_native_profiles_and_effective_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED,
                       optimization, 0)
        variants = controls()
        for label, body in variants.items():
            run_native("control-" + label, body, "-O2", 1)
        self.receipt("native-contract", {
            "profiles": ["O0", "O2", "O3"], "cases_per_profile": 4096,
            "controls": sorted(variants), "actual_32_bit_C": True,
        })

    def test_04_registry_abi_and_fired_root_fault_boundaries(self):
        evidence = match.registry_evidence(ROOT)
        self.assertEqual(evidence["direct_jal_calls"], [])
        self.assertEqual(evidence["aligned_pointer_literals"],
                         ["0x230274", "0x230d04"])
        case = Case(7, 0x100, 0x100, 2, 0xFF, 0, 1, 8, 7)
        initial = fixture(case)
        baseline = QuadOracle(self.retail, initial, case).run()
        states = []
        for cut in range(baseline.root_accesses):
            model = QuadOracle(self.retail, initial, case, fault=cut)
            with self.assertRaises(faults.AccessBoundary):
                model.run()
            states.append((model.current_pc, model.delay_of, model.root_accesses))
        self.assertEqual(len(states), baseline.root_accesses)
        self.assertGreater(len(states), 8)
        self.receipt("registry-and-faults", {
            "registry_pointer_offsets": evidence["aligned_pointer_literals"],
            "root_access_faults": states,
            "no_direct_call_sites_expected": True,
        })


if __name__ == "__main__":
    unittest.main()
