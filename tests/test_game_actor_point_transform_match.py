"""Closure and bounded semantics for func_151606A8."""

import itertools
import json
import math
import os
from pathlib import Path
import struct
import subprocess
from types import SimpleNamespace
import unittest

from tools.experiments import game_actor_point_transform_match as match
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests import game_view_point_projection_oracle as point
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
STACK = point.STACK
STATE, TRANSFORM, OTHER, DEST, SECOND = (
    0x22000, 0x23000, 0x23800, 0x24000, 0x24800)
GLOBAL = 0x800A66B4
ROTATE, PROJECT = 0x150A8050, 0x150A7960
OUTPUTS = (
    (3.75, -4.5, 32767.75),
    (-32768.75, 0.0, -0.0),
    (123.25, -456.75, 789.5),
    (2147483520.0, -2147483648.0, 1.5),
)


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x400 <= address < STACK + 0x180}


def fixture(pattern, transform_mutation, destination_mutation, phase):
    memory = {STACK + offset: (offset * 17 + 0xA5) & 0xFF
              for offset in range(-0x400, 0x180)}
    for base in (STATE, TRANSFORM, OTHER, DEST, SECOND):
        memory.update({base + offset: (offset * 13 + 0x59) & 0xFF
                       for offset in range(0x80)})
    put(memory, STATE + 0x14, DEST)
    put(memory, STATE + 0x18, TRANSFORM)
    for base, bias in ((TRANSFORM, 0), (OTHER, 7)):
        for offset, value in ((0, 1.25 + bias), (4, -2.5 - bias),
                              (8, 3.75 + bias)):
            put(memory, base + offset, point.bits(value))
        for offset, value in ((0x10, -123 + bias), (0x12, 456 - bias),
                              (0x14, -789 + bias)):
            put(memory, base + offset, value & 0xFFFF, 2)
    for index, value in enumerate((0.0, -415.0, 0.0)):
        put(memory, GLOBAL + index * 4, point.bits(value))
    return memory


class TransformOracle(FactoryOracle):
    def __init__(self, words, memory, pattern, transform_mutation,
                 destination_mutation, phase):
        self.pattern = pattern
        self.transform_mutation = transform_mutation
        self.destination_mutation = destination_mutation
        self.observed_matrix = None
        super().__init__(words, memory, SimpleNamespace(phase=phase),
                         entry=match.ENTRY, s={},
                         arguments=(STATE,))
        self.pattern = pattern

    def execute(self, word):
        op, rs, rd, fd, fn = (word >> 26, word >> 21 & 31,
                              word >> 11 & 31, word >> 6 & 31, word & 63)
        if op == 17 and rs == 16 and fn == 13:
            value = math.trunc(point.floating(self.f[rd]))
            assert -(2 ** 31) <= value < 2 ** 31
            self.f[fd] = value & 0xFFFFFFFF
            self.dispatched_word = word
        else:
            super().execute(word)

    def arguments(self, count):
        return tuple(self.r[4 + index] if index < 4 else
                     read(self.memory, self.r[29] + index * 4)
                     for index in range(count))

    def record_call(self, target):
        assert target in (ROTATE, PROJECT), hex(target)
        args = self.arguments(4 if target == ROTATE else 7)
        self.calls.append((target, args))
        if target == PROJECT:
            self.observed_matrix = tuple(
                read(self.memory, args[0] + index * 4) for index in range(16))

    def hook(self, target):
        args = self.calls[-1][1]
        if target == ROTATE:
            for index in range(16):
                put(self.memory, args[0] + index * 4,
                    point.bits(1.0 if index in (0, 5, 10, 15) else 0.0))
            if self.transform_mutation:
                put(self.memory, STATE + 0x18, OTHER)
        else:
            for address, value in zip(args[4:], OUTPUTS[self.pattern]):
                put(self.memory, address, point.bits(value))
            if self.destination_mutation:
                put(self.memory, STATE + 0x14, SECOND)
        for index in range(4):
            put(self.memory, self.r[29] + index * 4, 0xB5000000 + index)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]


def expected(initial, pattern, transform_mutation, destination_mutation, phase):
    memory = dict(initial)
    matrix = STACK + phase - 0x88 + 0x40
    transform = OTHER if transform_mutation else TRANSFORM
    destination = SECOND if destination_mutation else DEST
    if transform_mutation:
        put(memory, STATE + 0x18, OTHER)
    if destination_mutation:
        put(memory, STATE + 0x14, SECOND)
    for index in range(16):
        put(memory, matrix + index * 4,
            point.bits(1.0 if index in (0, 5, 10, 15) else 0.0))
    translation = []
    for index, offset in enumerate((0x10, 0x12, 0x14)):
        value = read(memory, transform + offset, 2)
        if value & 0x8000:
            value -= 0x10000
        bits = point.bits(float(value))
        translation.append(bits)
        put(memory, matrix + (12 + index) * 4, bits)
    output_addresses = (STACK + phase - 0x88 + 0x34,
                        STACK + phase - 0x88 + 0x38,
                        STACK + phase - 0x88 + 0x3C)
    for address, value in zip(output_addresses, OUTPUTS[pattern]):
        put(memory, address, point.bits(value))
    for index, value in enumerate(OUTPUTS[pattern]):
        put(memory, destination + 0x0E + index * 2,
            math.trunc(value) & 0xFFFF, 2)
    calls = [
        (ROTATE, (matrix, read(initial, TRANSFORM), read(initial, TRANSFORM + 4),
                  read(initial, TRANSFORM + 8))),
        (PROJECT, (matrix, read(initial, GLOBAL), read(initial, GLOBAL + 4),
                   read(initial, GLOBAL + 8), *output_addresses)),
    ]
    return memory, calls, tuple(translation)


def controls():
    body = match.SELECTED
    rows = {
        "wrong_angle": body.replace("transform->unk4", "transform->unk8", 1),
        "wrong_translation": body.replace("pad12[0]", "pad12[2]", 1),
        "missing_translation": body.replace(
            "    matrix[3][2] = *(s16 *)&(*transformRef)->pad12[2];\n", "", 1),
        "wrong_input": body.replace("D_800A66B4[1]", "D_800A66B4[0]", 1),
        "wrong_output": body.replace(
            "arg0->unk14->unk10 = point.unk4", "arg0->unk14->unk10 = point.unk0", 1),
        "wrong_return": body.replace("    return 1;", "    return 0;", 1),
    }
    captured = body.replace(
        "    struct17 point;", "    struct17 point;\n    struct226 *captured;", 1)
    captured = captured.replace(
        "    transform = arg0->unk18;", "    captured = arg0->unk14;\n    transform = arg0->unk18;", 1)
    rows["captured_destination"] = captured.replace("arg0->unk14->", "captured->")
    assert all(value != body for value in rows.values())
    return rows


def native_harness(bodies):
    definitions = r'''
typedef unsigned char u8;
typedef short s16;
typedef int s32;
typedef unsigned int u32;
typedef float f32;
typedef struct { f32 unk0, unk4, unk8; } struct17;
typedef struct { u8 pad0[5]; u8 unk5,unk6,unk7,pad8,unk9; u8 padA[4]; s16 unkE,unk10,unk12,unk14; u8 tail[0x1A]; } struct226;
typedef struct { f32 unk0,unk4,unk8,unkC; s16 unk10; u8 pad12[0x12]; u8 unk24; } struct227;
typedef struct { u8 pad0[0x14]; struct226 *unk14; struct227 *unk18; } struct225;
f32 D_800A66B4[3] = {0.0f,-415.0f,0.0f};
void func_150A8050(f32 [4][4],f32,f32,f32);
void func_150A7960(f32 [4][4],f32,f32,f32,f32*,f32*,f32*);
'''
    named = []
    for index, body in enumerate(bodies):
        named.append(body.replace(match.FUNCTION, "candidate_%d" % index, 1))
    return definitions + "\n".join(named) + r'''
typedef s32 (*Candidate)(struct225 *);
static Candidate candidates[] = {''' + ",".join(
        "candidate_%d" % index for index in range(len(bodies))) + r'''};
static struct225 state;
static struct226 destinations[2];
static struct227 transforms[2];
static u32 mode,calls,error;
static s16 wanted[3];
void func_150A8050(f32 matrix[4][4],f32 x,f32 y,f32 z){u32 i;calls++;
 if(x!=transforms[0].unk0||y!=transforms[0].unk4||z!=transforms[0].unk8)error=1;
 for(i=0;i<16;i++)((u32*)matrix)[i]=0;matrix[0][0]=matrix[1][1]=matrix[2][2]=matrix[3][3]=1.0f;
 if(mode&1)state.unk18=&transforms[1];}
void func_150A7960(f32 matrix[4][4],f32 x,f32 y,f32 z,f32*ox,f32*oy,f32*oz){calls++;
 if(x!=0.0f||y!=-415.0f||z!=0.0f||matrix[3][0]!=(f32)wanted[0]||matrix[3][1]!=(f32)wanted[1]||matrix[3][2]!=(f32)wanted[2])error=1;
 *ox=3.75f;*oy=-4.5f;*oz=32767.75f;if(mode&2)state.unk14=&destinations[1];}
static int run(void){u32 n,j,k,killed=0;u8 *p;s16 *q;
 for(n=0;n<4096;n++)for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
  for(k=0;k<sizeof(destinations);k++)((u8*)destinations)[k]=0xA5;
  transforms[0].unk0=(f32)n+.25f;transforms[0].unk4=-(f32)n-.5f;transforms[0].unk8=(f32)n+.75f;
  transforms[0].unk10=(s16)(n*17u);*(s16*)&transforms[0].pad12[0]=(s16)(n*31u);*(s16*)&transforms[0].pad12[2]=(s16)(n*47u);
  transforms[1]=transforms[0];transforms[1].unk10++;*(s16*)&transforms[1].pad12[0]-=2;*(s16*)&transforms[1].pad12[2]+=3;
  mode=(n>>2)&3;state.unk14=&destinations[0];state.unk18=&transforms[0];q=(s16*)((mode&1)?&transforms[1].unk10:&transforms[0].unk10);
  wanted[0]=q[0];wanted[1]=q[1];wanted[2]=q[2];calls=error=0;
  k=candidates[j](&state);p=(u8*)((mode&2)?&destinations[1]:&destinations[0]);
  if(k!=1||calls!=2||error||*(s16*)(p+0xE)!=3||*(s16*)(p+0x10)!=-4||*(s16*)(p+0x12)!=32767){if(!j)return 10;killed|=1u<<(j-1);}
 }
 return killed==((1u<<(sizeof(candidates)/sizeof(candidates[0])-1))-1)?0:11;
}
''' + START


class ActorPointTransformTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.out = ROOT / match.BUILD
        (cls.report, cls.before_owner, cls.after_owner,
         cls.before_elf, cls.after_elf) = match.prepare(ROOT)
        image = cls.after_elf.read_bytes()
        at = elf_slot_offset(image, match.ENTRY, match.SIZE)
        cls.words = list(struct.unpack_from(">%dI" % match.WORDS, image, at))
        cls.retail = list(struct.unpack_from(">%dI" % match.WORDS,
                                             (ROOT / match.ROM_IMAGE).read_bytes(),
                                             match.ROM))

    @classmethod
    def tearDownClass(cls):
        (cls.out / ("test-receipt-%d.json" % os.getpid())).write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_guarded_owner_image_registry_and_data_closure(self):
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.report["words"], self.report["natural_words"],
                          self.report["frame"], self.report["guards"],
                          self.report["insertions"], self.report["relocations"]),
                         (63, 62, 136, 8, 1, 4))
        self.assertEqual(self.report["neighbors"], 77)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertEqual((self.report["strict_exclusions"],
                          self.report["game_data"]["different_bytes"]), (0, 0))
        self.receipt["closure"] = self.report

    def test_02_guest_helpers_live_reloads_truncation_and_coverage(self):
        seen = set()
        cases = 0
        for pattern, transform_mutation, destination_mutation, phase in itertools.product(
                range(4), range(2), range(2), (0, 8)):
            initial = fixture(pattern, transform_mutation, destination_mutation, phase)
            wanted, calls, translation = expected(
                initial, pattern, transform_mutation, destination_mutation, phase)
            machine = TransformOracle(
                self.words, initial, pattern, transform_mutation,
                destination_mutation, phase).run()
            self.assertEqual((public(machine.memory), machine.calls, machine.r[2]),
                             (public(wanted), calls, 1))
            self.assertEqual(machine.observed_matrix[12:15], translation)
            seen.update(pc for pc in machine.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            cases += 1
        self.assertEqual(seen, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.receipt["guest"] = {
            "cases": cases, "covered_words": len(seen), "stack_phases": 2,
            "live_transform_reload": True, "live_destination_reload": True,
            "signed_halfword_to_float": True, "trunc32_low_halfword": True,
            "full_public_memory": True,
        }

    def test_03_native32_profiles_and_effective_controls(self):
        variants = [match.SELECTED, *controls().values()]
        code = native_harness(variants)
        source = self.out / "native-actor-point-transform.c"
        source.write_text(code)
        reports = []
        for profile in ("-O0", "-O2", "-O3"):
            executable = self.out / ("native-actor-point-transform" + profile)
            result = subprocess.run(native_command(profile) + [
                "-o", str(executable), str(source)], cwd=ROOT,
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            run = subprocess.run([str(executable)], capture_output=True)
            self.assertEqual(run.returncode, 0, (profile, run.returncode, run.stderr))
            reports.append({"profile": profile, "cases": 4096,
                            "UBSan_trap": True})
        self.receipt["native"] = {
            "profiles": reports, "effective_controls": list(controls()),
            "canonical_32bit_pointers": True,
        }

    def test_04_payload_guard_and_complete_image_rejections(self):
        raw, bindings = match.checked_natural(
            self.out / "qualified-compact.o")
        wrong = bytearray(raw)
        wrong[0] ^= 1
        with self.assertRaises(ValueError):
            match.checked_parts(bytes(wrong), bindings)
        before = self.before_elf.read_bytes()
        actual = self.after_elf.read_bytes()
        retail = (ROOT / match.ROM_IMAGE).read_bytes()[match.ROM:match.ROM + match.SIZE]
        for offset in (0, len(actual) // 2, len(actual) - 1):
            damaged = bytearray(actual)
            damaged[offset] ^= 1
            with self.assertRaises(ValueError):
                match.check_image(before, bytes(damaged), retail)
        predecessor, installed = match.guard_manifests((ROOT / match.GUARDS).read_bytes())
        self.assertEqual((match.digest(predecessor), match.digest(installed)),
                         (match.INHERITED_GUARDS_SHA256,
                          match.INSTALLED_GUARDS_SHA256))
        self.receipt["rejections"] = {
            "natural_payload_hash": True, "guard_manifest": True,
            "image_corruptions": 3, "strict_exclusions": 0,
        }


if __name__ == "__main__":
    unittest.main()
