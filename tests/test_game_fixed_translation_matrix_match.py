"""Compiler, semantic, ABI, owner and complete-image gates for func_150A7D00."""

import csv
import hashlib
import io
import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_fixed_translation_matrix_match as source
from tools.experiments.game_four_head_lookup_match import payload
from tools.tests import test_game_fixed_scale_matrix_match as scale


OUTPUT = 0x26000


def matrix_bytes(memory):
    return bytes(memory[OUTPUT + index] for index in range(64))


def reference(memory, values):
    result = dict(memory)
    for index in range(64):
        result[OUTPUT + index] = 0
    converted = [scale.fixed.integer(scale.fixed.scaled(word), 1) for word in values]
    for index in (0, 5, 10, 15):
        scale.put(result, OUTPUT + 2 * index, 1, 2)
    for value, index in zip(converted, (12, 13, 14)):
        scale.put(result, OUTPUT + 2 * index, value >> 16, 2)
    for value, index in zip(converted, (28, 29, 30)):
        scale.put(result, OUTPUT + 2 * index, value, 2)
    return result


class TranslationOracle(scale.ScaleOracle):
    def __init__(self, words, memory, values, phase=0):
        scale.machine.BurstOracle.__init__(
            self, words, memory, phase=phase, entry=source.ENTRY,
            symbols={"unused": 0}, arguments=(OUTPUT, *values))


class FixedTranslationMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / source.BUILD
        values = source.prepare(cls.root)
        (cls.baseline, cls.candidate, cls.guards, cls.qualified, cls.replay,
         cls.first_link, cls.first_map, cls.expected) = values
        cls.raw_bytes, cls.raw_bindings = payload(cls.candidate, source.FUNCTION)
        cls.retail_bytes = cls.baseline["rom"].read_bytes()[source.ROM:source.ROM + source.SIZE]
        cls.raw = list(struct.unpack(">40I", cls.raw_bytes))
        cls.retail = list(struct.unpack(">40I", cls.retail_bytes))

    def test_01_exact_slot_profile_guards_recipe_and_padded_owner(self):
        self.assertEqual((len(self.raw), self.raw_bindings,
                          hashlib.sha256(self.raw_bytes).hexdigest()),
                         (40, {}, source.RAW_SHA))
        self.assertEqual(hashlib.sha256(self.retail_bytes).hexdigest(), source.RETAIL_SHA)
        rows = list(csv.DictReader(io.StringIO(self.guards.read_text())))
        target = [row for row in rows if row["function"] == source.FUNCTION]
        self.assertEqual(len(target), 39)
        self.assertTrue(all(row["expected_relocations"] == row["replacement_relocations"] == "-"
                            and not row["insert_after"] and row["omit"] == "false"
                            for row in target))
        qualified, bindings, functions = source.complete_symbol(self.qualified)
        self.assertEqual((qualified, bindings), (self.retail_bytes, {}))
        self.assertEqual(set(functions), {source.FUNCTION})
        makefile = self.baseline["makefile"].read_text()
        self.assertEqual(source.recovered_makefile(makefile).count(source.PROFILE), 1)
        self.assertEqual(self.replay.read_bytes(), self.qualified.read_bytes())

    def test_02_guest_fixed_point_semantics_and_complete_reachable_words(self):
        values = tuple(scale.bits(value) for value in (
            -32768.0, -123.75, -2.5, -1.0, -0.5, -1.0 / 65536.0, -0.0,
            0.0, 1.0 / 65536.0, 0.25, 0.5, 1.0, 2.5, 123.75, 32767.5))
        cases = [(values[index], values[(index * 5 + 3) % len(values)],
                  values[(index * 7 + 8) % len(values)]) for index in range(len(values))]
        cases += list(itertools.permutations((scale.bits(-3.5), scale.bits(0.125),
                                               scale.bits(7.75))))
        raw_visits, retail_visits = set(), set()
        for phase, case in itertools.product((0, 8), cases):
            memory = scale.fixed.fixture(output=OUTPUT)
            expected = reference(memory, case)
            saved = None
            for label, words, visits in (("raw", self.raw, raw_visits),
                    ("retail", self.retail, retail_visits)):
                with self.subTest(label=label, phase=phase, case=case):
                    model = TranslationOracle(words, memory, case, phase).run()
                    self.assertEqual(matrix_bytes(model.memory), matrix_bytes(expected))
                    current = tuple(model.r[16:24]) + tuple(model.r[28:32])
                    if saved is None:
                        saved = current
                    self.assertEqual(current, saved)
                    self.assertFalse(model.calls)
                    visits.update(model.visits)
        slot = set(range(source.ENTRY, source.ENTRY + source.SIZE, 4))
        self.assertEqual(len(raw_visits & slot), 40)
        self.assertEqual(len(retail_visits & slot), 37)

    def test_03_native32_semantics_and_effective_controls(self):
        body = source.SELECTED.split("\n", 2)[2]
        controls = {
            "wrong_factor": body.replace("65536.0f", "32768.0f"),
            "wrong_x_integer": body.replace("matrix[12] = fixedX >> 16",
                                             "matrix[11] = fixedX >> 16"),
            "wrong_z_fraction": body.replace("matrix[30] = fixedZ", "matrix[31] = fixedZ"),
            "uncleared_tail": body.replace("    words[7] = 0;\n", ""),
        }
        variants = {"selected": body, **controls}
        prelude = ("typedef unsigned char u8;typedef signed short s16;typedef signed int s32;\n"
                   "typedef unsigned int u32;typedef unsigned long long u64;typedef float f32;\n")
        program = prelude
        for name, text in variants.items():
            program += text.replace(source.FUNCTION, "variant_" + name) + "\n"
        program += r'''
typedef void(*Fn)(volatile s16*,f32,f32,f32);
static union { u32 align[20]; s16 h[40]; } output;
static f32 values[]={-32768.0f,-123.75f,-2.5f,-1.0f,-0.5f,-0.0000152587890625f,
 -0.0f,0.0f,0.0000152587890625f,0.25f,0.5f,1.0f,2.5f,123.75f,32767.5f};
static int check(Fn fn){u32 a,b,c,i,differed=0;for(a=0;a<15;a++)for(b=0;b<15;b+=4)for(c=0;c<15;c+=7){
 s32 x=(s32)(values[a]*65536.0f),y=(s32)(values[b]*65536.0f),z=(s32)(values[c]*65536.0f);
 for(i=0;i<40;i++)output.h[i]=(s16)0x5AA5;fn(output.h,values[a],values[b],values[c]);
 for(i=0;i<32;i++){s16 wanted=0;if(i==0||i==5||i==10||i==15)wanted=1;
  if(i==12)wanted=(s16)(x>>16);if(i==13)wanted=(s16)(y>>16);if(i==14)wanted=(s16)(z>>16);
  if(i==28)wanted=(s16)x;if(i==29)wanted=(s16)y;if(i==30)wanted=(s16)z;
  if(output.h[i]!=wanted)differed=1;}
 }return differed;}
int run(void){if(check(variant_selected))return 10;
'''
        for index, name in enumerate(controls, 20):
            program += "if(!check(variant_%s))return %d;" % (name, index)
        program += "return 0;}\n" + scale.START
        for optimization in ("-O0", "-O2", "-O3"):
            path = self.output / ("native-fixed-translation-" + optimization[1:] + ".c")
            path.write_text(program)
            binary = path.with_suffix("")
            result = subprocess.run(scale.native_command(optimization) + ["-fno-strict-aliasing",
                str(path), "-o", str(binary)], cwd=self.root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(subprocess.run([str(binary)], timeout=60).returncode, 0,
                             optimization)

    def test_04_callers_sdk_provenance_and_guard_staleness(self):
        rom = self.baseline["rom"].read_bytes()
        jal = 0x0C000000 | ((source.ENTRY >> 2) & 0x03FFFFFF)
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == jal],
                         [0xC0F88, 0x13B614, 0x15A1D4, 0x15A4D4, 0x21BE00])
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == source.ENTRY], [])
        sdk_asm = self.baseline["sdk_asm"].read_text()
        sdk_c = self.baseline["sdk_c"].read_text()
        self.assertIn("void guTranslate(Mtx *m, float x, float y, float z)", sdk_c)
        self.assertIn("FTOFIX32", sdk_asm)
        self.assertIn("LEAF( guTranslate )", sdk_asm)
        before = self.baseline["guards"].read_bytes()
        self.assertEqual(source.guard_manifest(before, self.raw_bytes, self.retail_bytes),
                         self.guards.read_bytes())
        for offset in (0, 0x10, 0x50, 0x9C):
            changed = bytearray(self.raw_bytes)
            changed[offset + 3] ^= 1
            with self.assertRaises(ValueError):
                source.guard_manifest(before, bytes(changed), self.retail_bytes)

    def test_05_private_or_installed_full_image_closure_and_protected_data(self):
        source.freeze(self.root, self.output)
        expected, proof = source.predict_image(self.baseline["elf"].read_bytes(),
                                                self.retail_bytes)
        self.assertEqual(expected, self.expected.read_bytes())
        self.assertEqual(self.first_link.read_bytes(), expected)
        self.assertEqual(proof["removed_private_body"], source.PRIVATE)
        self.assertEqual(proof["retargeted_trampolines"], [])
        source.closure_audit(self.baseline["elf"], self.first_link)
        source.map_closure(self.first_map)

        current_source = (self.root / source.PATHS["source"]).read_bytes()
        installed = current_source == source.SELECTED.encode()
        self.assertIn(current_source, (self.baseline["source"].read_bytes(),
                                       source.SELECTED.encode()))
        if not installed:
            for key in ("makefile", "guards", "object", "elf", "map", "progress"):
                self.assertEqual((self.root / source.PATHS[key]).read_bytes(),
                                 self.baseline[key].read_bytes(), key)
            return
        self.assertEqual((self.root / source.PATHS["makefile"]).read_bytes(),
                         source.recovered_makefile(self.baseline["makefile"].read_text()).encode())
        self.assertEqual((self.root / source.PATHS["guards"]).read_bytes(),
                         self.guards.read_bytes())
        self.assertEqual((self.root / source.PATHS["object"]).read_bytes(),
                         self.qualified.read_bytes())
        current_elf = self.root / source.PATHS["elf"]
        self.assertEqual(current_elf.read_bytes(), expected)
        source.closure_audit(self.baseline["elf"], current_elf)
        source.map_closure(self.root / source.PATHS["map"])
        data = audit_layout(current_elf, self.root / "conker")
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))


if __name__ == "__main__":
    unittest.main()
