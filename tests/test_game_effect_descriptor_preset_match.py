"""Independent record, signed gate, alias, fault and image tests for the preset."""

import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_effect_descriptor_preset_candidates as candidate
from tools.experiments import game_effect_descriptor_preset_match as match
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_point_transform_match import put, read


ROOT = candidate.ROOT
PRESET, AUXILIARY = 0x22000, 0x23000
FLOATS = (0x800A0AB8, 0x800A0ABC, 0x800A0AC0, 0x800A0AC4, 0x800A0AC8)
COUNTER, STATE = 0x80082FA0, 0x8008FD8C
PATTERNS = (0, 0x80000000, 0x3F800000, 0xC2480000,
            0x7F800000, 0xFF800000, 0x7FC12345, 0x00000001)
COUNTERS = (-0x80000000, -1, 0, 1, 2, 3, 0x7FFFFFFF)
FIELDS32 = ((0x14, FLOATS[1]), (0x18, FLOATS[2]),
            (0x1C, 0x43160000), (0x20, 0x42D20000),
            (0x24, 0x43C60000), (0x28, 0x44190000),
            (0x2C, 4), (0x30, 3), (0x34, 0x41C80000),
            (0x38, FLOATS[3]), (0x3C, 0xC0000000), (0x40, FLOATS[4]))
FIELDS16 = ((0x44, 20), (0x46, 30), (0x48, 100),
            (0x4A, 100), (0x4C, 12), (0x4E, 20))


def signed(value, width=32):
    return value - (1 << width) if value & (1 << (width - 1)) else value


def fixture(counter, state, seed):
    memory = {STACK + i: (i * 17 + seed) & 255 for i in range(-0x100, 0x100)}
    memory.update({PRESET + i: (i * 29 + seed * 7) & 255 for i in range(-16, 0x70)})
    memory.update({AUXILIARY + i: (i * 3 + seed) & 255 for i in range(8)})
    for i, address in enumerate(FLOATS):
        put(memory, address, PATTERNS[(seed + i) & 7])
    put(memory, COUNTER, counter & 0xFFFFFFFF)
    memory[STATE] = state & 255
    return memory


def reference(initial, auxiliary):
    memory = dict(initial)
    put(memory, PRESET, 6)
    put(memory, PRESET + 4, 3)
    put(memory, auxiliary, read(memory, FLOATS[0]))
    for offset, value in FIELDS32:
        put(memory, PRESET + offset, read(memory, value) if value in FLOATS else value)
    for offset, value in FIELDS16:
        memory[PRESET + offset], memory[PRESET + offset + 1] = value >> 8, value & 255
    memory[PRESET + 0x50] = (255 if signed(read(memory, COUNTER)) >= 2 or
                                  signed(memory[STATE], 8) >= 8 else 0)
    return memory


class PresetOracle(TimingOracle):
    def __init__(self, words, memory, auxiliary=AUXILIARY, fault=None):
        super().__init__(words, memory, entry=match.ENTRY, arguments=(PRESET, auxiliary))
        self.root_fault = fault

    def execute(self, word):
        if word >> 26 == 0x20:
            rs, rt = (word >> 21) & 31, (word >> 16) & 31
            immediate = signed(word & 0xFFFF, 16)
            self.r[rt] = signed(self.get((self.r[rs] + immediate) & 0xFFFFFFFF, 1), 8) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)

    def record_call(self, target):
        raise AssertionError("Preset unexpectedly called a helper: %08X" % target)


def controls():
    replacements = {
        "kind": ("kind = 6", "kind = 5"),
        "variant": ("variant = 3", "variant = 4"),
        "auxiliary-source": ("*auxiliary = D_800A0AB8", "*auxiliary = D_800A0ABC"),
        "float-source14": ("value14 = D_800A0ABC", "value14 = D_800A0AB8"),
        "float-source18": ("value18 = D_800A0AC0", "value18 = D_800A0ABC"),
        "float-source38": ("value38 = D_800A0AC4", "value38 = D_800A0AC8"),
        "float-source40": ("value40 = D_800A0AC8", "value40 = D_800A0AC4"),
        "counter-threshold": ("D_80082FA0 >= 2", "D_80082FA0 >= 1"),
        "counter-sign": ("D_80082FA0 >= 2", "(u32)D_80082FA0 >= 2"),
        "state-threshold": ("D_8008FD8C >= 8", "D_8008FD8C >= 7"),
        "state-sign": ("D_8008FD8C >= 8", "(u8)D_8008FD8C >= 8"),
        "gate-and": (" || ", " && "),
        "mode": ("mode = -1", "mode = 1"),
        "reserved-write": ("preset->kind = 6;", "preset->kind = 6; preset->reserved08[0] = 0;"),
    }
    for field, value in (("value1C", "150.0f"), ("value20", "105.0f"),
                         ("value24", "396.0f"), ("value28", "612.0f"),
                         ("selector2C", "4"), ("selector30", "3"),
                         ("value34", "25.0f"), ("value3C", "-2.0f"),
                         ("value44", "20"), ("value46", "30"),
                         ("value48", "100"), ("value4A", "100"),
                         ("value4C", "12"), ("value4E", "20")):
        replacements[field] = (field + " = " + value, field + " = 1")
    result = {name: candidate.SELECTED.replace(old, new, 1)
              for name, (old, new) in replacements.items()}
    if any(body == candidate.SELECTED for body in result.values()):
        raise AssertionError("Ineffective preset source control")
    return result


def native_source(body):
    prelude = """typedef unsigned char u8; typedef signed char s8;
typedef signed short s16; typedef signed int s32; typedef unsigned int u32;
typedef float f32;
"""
    return prelude + candidate.DECLARATIONS + body + r'''
f32 D_800A0AB8, D_800A0ABC, D_800A0AC0, D_800A0AC4, D_800A0AC8;
s32 D_80082FA0;
s8 D_8008FD8C;
static union { u32 words[32]; u8 bytes[128]; } actual, expected;
static u32 float_bits(f32 value) { union { f32 f; u32 u; } bits; bits.f=value; return bits.u; }
static f32 from_bits(u32 value) { union { f32 f; u32 u; } bits; bits.u=value; return bits.f; }
static void store32(u8 *p, u32 value) { *(u32 *)p=value; }
static void store16(u8 *p, unsigned value) { *(unsigned short *)p=(unsigned short)value; }
static s32 one(unsigned seed) {
    static const s32 counters[8]={-2147483647-1,-1,0,1,2,3,2147483647,7};
    static const u32 patterns[8]={0,0x80000000,0x3F800000,0xC2480000,
        0x7F800000,0xFF800000,0x7FC12345,1};
    static const unsigned offsets[14]={0x1C,0x20,0x24,0x28,0x2C,0x30,0x34,0x3C,
        0x44,0x46,0x48,0x4A,0x4C,0x4E};
    static const u32 values[14]={0x43160000,0x42D20000,0x43C60000,0x44190000,
        4,3,0x41C80000,0xC0000000,20,30,100,100,12,20};
    unsigned i, route=seed>>11;
    f32 auxiliary=from_bits(0xA5123456), *out=&auxiliary;
    u32 f0=patterns[(seed+0)&7],f1=patterns[(seed+1)&7],
        f2=patterns[(seed+2)&7],f3=patterns[(seed+3)&7],f4=patterns[(seed+4)&7];
    for(i=0;i<128;i++) actual.bytes[i]=expected.bytes[i]=(u8)(seed*7u+i*29u);
    D_800A0AB8=from_bits(f0); D_800A0ABC=from_bits(f1); D_800A0AC0=from_bits(f2);
    D_800A0AC4=from_bits(f3); D_800A0AC8=from_bits(f4);
    D_80082FA0=counters[(seed>>8)&7]; D_8008FD8C=(s8)seed;
    store32(expected.bytes,6); store32(expected.bytes+4,3);
    if(route==1) out=(f32 *)(actual.bytes+0x14);
    else if(route==2) out=(f32 *)(actual.bytes+0x40);
    else if(route==3) { out=&D_800A0ABC; f1=f0; }
    store32(expected.bytes+0x14,f1); store32(expected.bytes+0x18,f2);
    store32(expected.bytes+0x38,f3); store32(expected.bytes+0x40,f4);
    for(i=0;i<14;i++) {
        if(i<8) store32(expected.bytes+offsets[i],values[i]);
        else store16(expected.bytes+offsets[i],values[i]);
    }
    expected.bytes[0x50]=(D_80082FA0>=2 || D_8008FD8C>=8)?255:0;
    func_150D64E8((EffectPreset150D64E8 *)actual.bytes,out);
    for(i=0;i<128;i++) if(actual.bytes[i]!=expected.bytes[i]) return 20;
    if(route==0 && float_bits(auxiliary)!=f0) return 21;
    if(route==3 && float_bits(D_800A0ABC)!=f0) return 22;
    return 0;
}
static s32 run(void) {
    unsigned seed;
    if(sizeof(void *)!=4 || sizeof(EffectPreset150D64E8)!=0x54) return 9;
    for(seed=0;seed<8192;seed++) { s32 code=one(seed); if(code) return code; }
    return 0;
}
void _start(void) {
    s32 code=run();
    __asm__ volatile("int $0x80"::"a"(1),"b"(code));
    __builtin_unreachable();
}
'''


def run_native(label, body, optimization, should_pass):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source, binary = output / (label + ".c"), output / (label + ".elf")
    source.write_text(native_source(body))
    subprocess.run([
        "gcc", "-m32", "-std=gnu89", optimization, "-fno-pie", "-no-pie",
        "-ffreestanding", "-fno-strict-aliasing", "-fno-stack-protector",
        "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
        "-Wall", "-Wextra", "-Werror", "-nostdlib", str(source), "-o", str(binary),
    ], check=True, capture_output=True)
    executed = subprocess.run([str(binary)], timeout=30)
    if should_pass != (executed.returncode == 0):
        raise AssertionError((label, executed.returncode))


class GameEffectDescriptorPresetMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = match.prepare(ROOT)
        cls.output = ROOT / match.BUILD
        cls.words = list(struct.unpack_from(">66I", (ROOT / match.ROM_IMAGE).read_bytes(), match.ROM))

    def receipt(self, name, value):
        (self.output / (name + ".json")).write_text(json.dumps(value, indent=2) + "\n")

    def test_01_direct_owner_and_literal_image(self):
        result = candidate.compare()
        self.assertEqual((result["words"], result["differences"]), (66, []))
        self.assertEqual(result["bindings"], match.BINDINGS)
        report = self.prepared["report"]
        self.assertEqual((report["neighbors"], report["guards"], report["functions"]), (16, 0, 6052))
        self.assertEqual(report["strict_changed_bytes"], 290)
        before = self.prepared["predecessor_elf"].read_bytes()
        after = self.prepared["qualified_elf"].read_bytes()
        mutated = bytearray(after)
        mutated[0x80] ^= 1
        with self.assertRaises(ValueError):
            match.strict_image(before, bytes(mutated), (ROOT / match.ROM_IMAGE).read_bytes()[match.ROM:match.ROM+match.SIZE])

    def test_02_guest_signed_byte_sweep_aliases_and_word_coverage(self):
        coverage, count = set(), 0
        auxiliaries = (AUXILIARY, PRESET+0x14, PRESET+0x40, FLOATS[1], COUNTER)
        for counter, state, auxiliary in itertools.product(COUNTERS, range(256), auxiliaries):
            initial = fixture(counter, state, count)
            model = PresetOracle(self.words, initial, auxiliary).run()
            self.assertEqual(model.memory, reference(initial, auxiliary), (counter,state,auxiliary))
            self.assertEqual(model.calls, [])
            coverage.update(model.visits)
            count += 1
        full = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4))
        unreachable = {match.ENTRY + 0xFC}
        self.assertEqual(coverage, full - unreachable)
        self.receipt("guest-contract", {"cases": count, "reachable_words":len(coverage),
            "unreachable_words":[hex(v) for v in unreachable], "reserved_bytes_preserved":True,
            "all_signed_state_bytes":256, "auxiliary_alias_routes":len(auxiliaries)})

    def test_03_native_profiles_and_effective_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED, optimization, True)
        variants = controls()
        for name, body in variants.items():
            run_native("control-" + name, body, "-O2", False)
        self.receipt("native-contract", {"profiles":["O0","O2","O3"],
            "cases_per_profile":8192, "controls":sorted(variants), "native_bits":32})

    def test_04_static_reference_limits_and_instruction_faults(self):
        census = match.registry_evidence(ROOT)
        self.assertEqual(census["direct_jal_calls"], [])
        self.assertEqual(census["aligned_pointer_literals"], [])
        observations=[]
        for counter,state in ((0,0),(1,7),(0,128),(2,0),(0,8)):
            initial=fixture(counter,state,17)
            baseline=PresetOracle(self.words,initial).run()
            for cut in range(baseline.root_accesses):
                model=PresetOracle(self.words,initial,fault=cut)
                with self.assertRaises(AccessBoundary): model.run()
                self.assertEqual(model.root_accesses,cut)
                observations.append((model.current_pc,model.delay_of,cut))
        self.assertGreater(len(observations),100)
        self.receipt("reference-and-faults", {"census":census,
            "fault_observations":len(observations),"unique_boundaries":len(set(observations))})


if __name__ == "__main__":
    unittest.main()
