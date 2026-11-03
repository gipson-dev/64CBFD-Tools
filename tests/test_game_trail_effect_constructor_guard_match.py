"""Semantic and strict-image gates for func_151DA6F8's guarded match."""

import itertools
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

from tools.experiments import game_trail_effect_constructor_candidates as candidate
from tools.experiments import game_trail_effect_constructor_guard_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests import test_game_trail_effect_constructor_recovery as oracle
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]


def function_words(obj):
    text, functions, _ = parse_object(obj)
    info = functions[match.FUNCTION]
    raw = text[info["value"]:info["value"] + info["size"]]
    return raw, list(struct.unpack(">%dI" % (len(raw) // 4), raw))


def relocation_field(text):
    if text in ("", "-"):
        return []
    return [tuple(value.split(":", 1)) for value in text.split(",")]


def native_source():
    return r'''typedef signed char s8;
typedef unsigned char u8;
typedef signed short s16;
typedef unsigned short u16;
typedef signed int s32;
typedef unsigned int u32;
typedef float f32;
#define NULL ((void *)0)
''' + candidate.SELECTED_TYPES + r'''
static u8 D_800AB404[16], D_800AB330[16], D_800AB3F4[16];
static f32 D_800AB498;
static union { u32 align; u8 bytes[512]; } storage, actor;
static TrailPosition151DA6F8 position, velocity;
static u8 *output = storage.bytes + 16;
static u8 *created = actor.bytes + 16;
static u32 expectedPattern, expectedOther, calls, copies, failResult, error;
static u32 expectedDuration, expectedSelector, expectedOpaque, expectedFade;
static u32 bits(f32 value) { union { f32 f; u32 u; } word; word.f=value; return word.u; }
static f32 number(u32 value) { union { f32 f; u32 u; } word; word.u=value; return word.f; }
static void *memcpy(void *destination, const void *source, unsigned int size) {
    u8 *out=destination; const u8 *in=source; unsigned int i;
    copies++; for(i=0;i<size;i++) out[i]=in[i]; return destination;
}
static u8 *func_15147DA0(void *requestPointer, void *descriptorPointer,
        s32 headerBytes, u8 active, u8 zero0, u8 zero1, u8 firstFlag,
        u8 secondFlag, u8 zero2, u8 fadeFlag, u8 fadeAlpha,
        void *renderPointer, s32 extraBytes, u8 channel, s32 context) {
    TrailRequest151DA6F8 *request=requestPointer;
    TrailDescriptor151DA6F8 *descriptor=descriptorPointer;
    TrailRender151DA6F8 *render=renderPointer;
    u32 flags=0x48u | (D_800AB404[expectedSelector]?0x20u:0u)
        | (D_800AB330[expectedSelector]?0x80u:0u);
    if(calls++ || request->duration!=(s16)(expectedDuration+16u)
       || request->kind!=53 || request->active!=1 || request->mode!=-1
       || request->selector!=0x80 || (u32)request->value!=0xFEDCBA98u
       || bits(request->position.x)!=bits(position.x)
       || bits(request->position.y)!=bits(position.y)
       || bits(request->position.z)!=bits(position.z)
       || bits(descriptor->time)!=expectedOther
       || bits(descriptor->scale)!=expectedPattern
       || bits(descriptor->velocity.x)!=bits(velocity.x)
       || bits(descriptor->velocity.y)!=bits(velocity.y)
       || bits(descriptor->velocity.z)!=bits(velocity.z)
       || bits(descriptor->limit)!=bits(D_800AB498)
       || descriptor->flags!=(u8)(flags|(expectedOpaque?3u:0u))
       || descriptor->kind!=D_800AB3F4[expectedSelector]
       || descriptor->alpha!=255 || descriptor->mode!=0xFE
       || descriptor->first!=(s16)expectedDuration
       || descriptor->second!=(s16)expectedDuration
       || headerBytes!=16 || active!=1 || zero0 || zero1 || zero2
       || firstFlag!=(expectedOpaque?7:0) || secondFlag!=(expectedOpaque?4:0)
       || fadeFlag!=(expectedFade?2:0) || fadeAlpha!=(expectedFade?255:0)
       || render->zero || render->command!=0x220005 || render->mode!=0x50600
       || render->kind!=3 || render->width!=70 || render->alpha!=128
       || render->count!=32 || render->flags || render->payloadBytes!=12
       || (u32)extraBytes!=0x81234567u || channel!=0x81
       || (u32)context!=0x89ABCDEFu) error=1;
    if(failResult) return NULL;
    memcpy(output, descriptor, 32); memcpy(output+0x28, render, 32);
    return created;
}
''' + candidate.SELECTED + r'''
static void initialize(u32 seed) {
    u32 i;
    for(i=0;i<512;i++) { storage.bytes[i]=(u8)(i*17u+seed*3u+0xA5u);
                         actor.bytes[i]=(u8)(i*13u+seed*5u+0x87u); }
    *(u8 **)(created+0x98)=output;
    position.x=number(0x80000000u|seed); position.y=number(seed+1u);
    position.z=number(0xBF800000u^(seed<<7));
    velocity.x=number(seed*0x10203u+1u); velocity.y=number(0x3F800000u+seed);
    velocity.z=number(0xC0000000u^(seed<<5));
    calls=copies=error=0;
}
int run(void) {
    u32 seed;
    for(seed=0;seed<4096u;seed++) {
        u8 *result;
        expectedDuration=seed*17u; expectedSelector=seed&15u;
        expectedOpaque=(seed>>4)&1u; expectedFade=(seed>>5)&1u;
        failResult=(seed>>6)&1u; expectedPattern=seed*0x10204081u;
        expectedOther=~expectedPattern;
        D_800AB404[expectedSelector]=(seed&0x80u)?129:0;
        D_800AB330[expectedSelector]=(seed&0x100u)?254:0;
        D_800AB3F4[expectedSelector]=(u8)(expectedSelector*13u+129u);
        D_800AB498=number(0xC61C4000u); initialize(seed);
        result=func_151DA6F8(&position,&velocity,number(expectedPattern),
            (s16)expectedDuration,0xFE,number(expectedOther),0x81234580,
            (u8)expectedOpaque,number(expectedPattern),number(expectedOther),
            (u8)expectedFade,(u8)expectedSelector,0x81234567,
            (s16)expectedDuration,(s16)expectedDuration,0xFEDCBA98,
            0x81,0x89ABCDEF);
        if(error || calls!=1 || copies!=(failResult?0u:3u)
           || result!=(failResult?NULL:created)) return 1;
        if(!failResult && (bits(*(f32 *)(output+0x48))!=expectedPattern
           || bits(*(f32 *)(output+0x4C))!=expectedOther
           || output[0x50]!=(u8)expectedSelector)) return 2;
    }
    return 0;
}
''' + START


class GameTrailEffectConstructorGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD
        cls.result = match.prepare(ROOT, cls.output)
        cls.report = cls.result["report"]
        cls.raw, _ = function_words(cls.result["qualified_compact"])
        functions, _, _ = load_elf_functions(
            str(cls.result["predecessor_elf"]), "mips-linux-gnu-objdump")
        cls.natural = functions[match.FUNCTION]
        image = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.retail_raw = image[match.ROM:match.ROM + match.SIZE]
        cls.retail = list(struct.unpack(">%dI" % match.WORDS, cls.retail_raw))

    def compare(self, memory, args, result, phase, words):
        wanted_call, wanted_payload = oracle.expected(memory, args)
        model = oracle.ConstructorOracle(
            words, memory, args, result, phase,
            mutation=result != 0).run()
        wanted_calls = [wanted_call]
        if result:
            wanted_calls.append(("copy", oracle.PAYLOAD + 0x48,
                                 wanted_payload, 12))
        self.assertEqual(model.calls, wanted_calls)
        self.assertEqual(model.r[2], result)
        return model

    def test_01_strict_owner_image_callers_and_data(self):
        self.assertEqual((self.report["words"], self.report["natural_frame"],
                          self.report["retail_frame"]), (144, 208, 208))
        self.assertEqual((self.report["natural_positional_differences"],
                          self.report["guards"], self.report["relocations"]),
                         (61, 61, 10))
        self.assertEqual((self.report["functions"], self.report["neighbors"],
                          self.report["changed_bodies"],
                          self.report["strict_exclusions"]),
                         (6051, 61, [match.FUNCTION], 0))
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertTrue(self.report["source_installed"])
        self.assertEqual(len(self.report["registry"]["direct_callers"]), 5)
        self.assertEqual((self.report["game_data"]["exact"],
                          self.report["game_data"]["bytes"],
                          self.report["game_data"]["owner_count"],
                          self.report["game_data"]["different_bytes"]),
                         (True, 189088, 720, 0))

    def test_02_all_guard_words_and_relocations_form_one_exact_body(self):
        normalized = bytearray(self.retail_raw)
        for offset, rows in match.BINDINGS.items():
            mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
            value = struct.unpack_from(">I", normalized, offset)[0] & mask
            struct.pack_into(">I", normalized, offset, value)
        patched = bytearray(self.raw)
        bindings = dict(match.NATURAL_BINDINGS)
        for value in match.PATCH_ROWS:
            offset = int(value["offset"], 0)
            self.assertEqual(struct.unpack_from(">I", patched, offset)[0],
                             int(value["expected"], 0))
            self.assertEqual(struct.unpack_from(">I", normalized, offset)[0],
                             int(value["replacement"], 0))
            struct.pack_into(">I", patched, offset, int(value["replacement"], 0))
            expected = relocation_field(value["expected_relocations"])
            replacement = relocation_field(value["replacement_relocations"])
            self.assertEqual(bindings.get(offset, []), expected)
            if replacement:
                bindings[offset] = replacement
            else:
                bindings.pop(offset, None)
        self.assertEqual(bytes(patched), bytes(normalized))
        self.assertEqual(bindings, match.BINDINGS)
        self.assertEqual(len({value["offset"] for value in match.PATCH_ROWS}), 61)

    def test_03_guest_semantics_aliases_mutations_and_all_words(self):
        count = 0
        natural_visits, retail_visits = set(), set()
        for selector, tables, opaque, fade, result, phase in itertools.product(
                range(16), range(4), (0, 255), (0, 128),
                (0, oracle.CREATED), (0, 8)):
            memory = oracle.fixture(selector, tables, count % 7)
            args = oracle.arguments(selector, opaque, fade)
            natural = self.compare(memory, args, result, phase, self.natural)
            retail = self.compare(memory, args, result, phase, self.retail)
            self.assertEqual((oracle.external(natural.memory),
                              oracle.public(natural.events), natural.calls),
                             (oracle.external(retail.memory),
                              oracle.public(retail.events), retail.calls))
            natural_visits.update(natural.visits)
            retail_visits.update(retail.visits)
            count += 1
        for source, result, phase in itertools.product(
                (oracle.POSITION, oracle.VELOCITY, oracle.CREATED, oracle.PAYLOAD),
                (0, oracle.CREATED), (0, 8)):
            args = list(oracle.arguments(15, 1, 1))
            args[0] = args[1] = source
            memory = oracle.fixture(15, 3, count % 7)
            natural = self.compare(memory, args, result, phase, self.natural)
            retail = self.compare(memory, args, result, phase, self.retail)
            self.assertEqual((oracle.external(natural.memory), natural.calls),
                             (oracle.external(retail.memory), retail.calls))
            count += 1
        self.assertEqual((len(natural_visits), len(retail_visits)), (144, 144))
        self.assertEqual(count, 1040)

    def test_04_compiled_semantic_controls_are_effective(self):
        body = candidate.SELECTED
        variants = {
            "duration": body.replace("duration + 16", "duration + 15", 1),
            "request-kind": body.replace("request.kind = 53", "request.kind = 54", 1),
            "request-active": body.replace("request.active = 1", "request.active = 0", 1),
            "request-mode": body.replace("request.mode = -1", "request.mode = 0", 1),
            "first-table": body.replace("D_800AB404[selector]", "D_800AB330[selector]", 1),
            "base-flags": body.replace("secondContribution | 8", "secondContribution | 4", 1),
            "opaque-bits": body.replace("descriptor.flags |= 3", "descriptor.flags |= 1", 1),
            "payload-first": body.replace("payload.first = first", "payload.first = second", 1),
            "render-command": body.replace("0x220005", "0x220004", 1),
            "fade-flag": body.replace("fadeFlag = 2", "fadeFlag = 1", 1),
            "copy-size": body.replace("sizeof(payload)", "8", 1),
            "return": body.replace("return created", "return NULL", 1),
        }
        self.assertEqual(len(variants), 12)
        self.assertTrue(all(value != body for value in variants.values()))
        controls = ROOT / match.BUILD / "controls"
        controls.mkdir(parents=True, exist_ok=True)
        for name, source in variants.items():
            _, words = candidate.compile_candidate(
                ROOT, controls, name, source, candidate.SELECTED_TYPES)
            accepted = True
            try:
                for tables, opaque, fade, result in itertools.product(
                        range(4), (0, 1), (0, 1), (0, oracle.CREATED)):
                    args = list(oracle.arguments(15, opaque, fade))
                    args[8], args[9] = 0x3F800000, 0x41400000
                    self.compare(oracle.fixture(15, tables),
                                 args, result, 0, words)
            except AssertionError:
                accepted = False
            self.assertFalse(accepted, name)

    def test_05_native_32bit_o0_o2_o3(self):
        compiler = shutil.which("cc")
        if compiler is None:
            self.skipTest("host compiler is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for optimization in ("-O0", "-O2", "-O3"):
                source = path / (optimization[1:] + ".c")
                binary = source.with_suffix("")
                source.write_text(native_source())
                command = [
                    compiler, "-m32", optimization, "-std=c99",
                    "-fno-strict-aliasing", "-fno-builtin", "-msse2",
                    "-mfpmath=sse", "-mstackrealign", "-ffreestanding",
                    "-nostdlib", "-static", "-fno-pie", "-no-pie",
                    "-fno-stack-protector", "-ffp-contract=off", "-Wall",
                    "-Wextra", "-Werror", "-Wno-unused-parameter",
                    "-Wno-unused-function", str(source), "-o", str(binary),
                ]
                built = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(built.returncode, 0, built.stderr)
                ran = subprocess.run([str(binary)], capture_output=True,
                                     timeout=20)
                self.assertEqual(ran.returncode, 0, optimization)


if __name__ == "__main__":
    unittest.main()
