"""Selected attached-actor matrix: semantics, callback ABI, guards and image closure."""

from dataclasses import dataclass
from pathlib import Path
import csv
import itertools
import json
import os
import struct
import subprocess
import tempfile
import unittest

from tools.experiments import game_selected_actor_matrix_match as source
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
ACTOR, ATTACHED, MATRICES, OUTPUT = 0x20000, 0x22000, 0x30000, 0x40000
FLAG, MEMCPY, CONVERT = 0x800C3E90, 0x10022EC0, 0x150A7790
CALLER, TABLE, TABLE_ROM = 0x15132A88, 0x8008998C, 0x22E44C
TABLE_WORDS = (
    0x15133510, 0x150B9D14, 0x15133760, 0x150C773C, 0x151B9310,
    source.ENTRY, 0x15133E84, 0x15133EB8, 0x15133FD8, 0x15132570,
    0x151C15FC,
)


@dataclass(frozen=True)
class Case:
    selector: int = 0
    flag: int = 0
    gate: str = "valid"
    phase: int = 0
    mutate: bool = False


def selected_payload(selector):
    return bytes(((selector * 37 + index * 13 + 0x5A) & 0xFF)
                 for index in range(64))


def fixture(case):
    memory = {STACK + case.phase + i: (i * 17 + 0xA5) & 0xFF
              for i in range(-0x300, 0x100)}
    for base, size in ((ACTOR, 0x180), (ATTACHED, 0x1E0),
                       (MATRICES, 0x4000), (OUTPUT, 0x40)):
        memory.update({base + i: (i * 29 + 7) & 0xFF for i in range(size)})
    for selector in range(256):
        for index, value in enumerate(selected_payload(selector)):
            memory[MATRICES + selector * 0x40 + index] = value
    put(memory, ACTOR + 0x7C, 0 if case.gate == "null-attached" else ATTACHED)
    put(memory, ATTACHED, 0 if case.gate == "empty-attached" else 0x13579BDF)
    memory[ATTACHED + 4] = 0xFF if case.gate == "sentinel" else 0x42
    memory[ACTOR + 0x80] = 0x3D
    memory[ATTACHED + 0x3B] = 0x7E if case.gate == "identity" else 0x3D
    put(memory, ATTACHED + 0x1D4,
        0 if case.gate == "null-matrices" else MATRICES)
    memory[ATTACHED + 0x74] = 0xAF if case.gate == "disabled-slot" else 0xA2
    memory[ACTOR + 0x170] = case.selector
    memory[FLAG] = case.flag
    return memory


def normalized_words(payload):
    words = list(struct.unpack(">16I", payload))
    words[3] = words[7] = words[11] = 0
    words[15] = 0x3F800000
    return tuple(words)


def converted_payload(payload):
    return struct.pack(">16I", *(word ^ 0x13579BDF
                                  for word in normalized_words(payload)))


def external(memory, phase):
    return {address: value for address, value in memory.items()
            if not STACK + phase - 0x300 <= address < STACK + phase + 0x100}


def reference(initial, case):
    memory = dict(initial)
    if case.gate in {"null-attached", "empty-attached", "sentinel", "identity"}:
        return memory, 0xFFFFFFFF, []
    if case.gate in {"null-matrices", "disabled-slot"}:
        return memory, 0, []
    payload = selected_payload(case.selector)
    selected = MATRICES + case.selector * 0x40
    if case.flag:
        for index, value in enumerate(payload):
            memory[OUTPUT + index] = value
        calls = [("copy-output", OUTPUT, selected, 0x40)]
    else:
        payload = converted_payload(payload)
        for index, value in enumerate(payload):
            memory[OUTPUT + index] = value
        calls = [("copy-local", selected, 0x40),
                 ("convert", OUTPUT, normalized_words(selected_payload(case.selector)))]
    if case.mutate:
        memory[ACTOR + 0x170] ^= 0xFF
        memory[ATTACHED + 0x3B] ^= 0xFF
        memory[FLAG] ^= 0xFF
    return memory, 1, calls


class SelectedMatrixOracle(TimingOracle):
    def __init__(self, words, memory, case):
        super().__init__(words, memory, phase=case.phase, entry=source.ENTRY,
                         arguments=(OUTPUT, ACTOR))
        self.case = case

    def record_call(self, target):
        if target == MEMCPY:
            destination, origin, length = self.arguments(3)
            if destination == OUTPUT:
                call = ("copy-output", destination, origin, length)
            else:
                assert STACK + self.case.phase - 0x100 <= destination < STACK + self.case.phase
                call = ("copy-local", origin, length)
        else:
            assert target == CONVERT, hex(target)
            matrix, destination = self.arguments(2)
            assert STACK + self.case.phase - 0x100 <= matrix < STACK + self.case.phase
            call = ("convert", destination,
                    tuple(self.get(matrix + index * 4, 4) for index in range(16)))
        self.calls.append(call)
        self.events.append(("CALL", target, call))

    def hook(self, target):
        if target == MEMCPY:
            destination, origin, length = self.arguments(3)
            payload = [self.get(origin + index, 1) for index in range(length)]
            for index, value in enumerate(payload):
                self.put(destination + index, value, 1)
            result = destination
        else:
            matrix, destination = self.arguments(2)
            for index in range(16):
                self.put(destination + index * 4,
                         self.get(matrix + index * 4, 4) ^ 0x13579BDF, 4)
            result = 0xA5A50002
        if self.case.mutate and target == MEMCPY:
            self.memory[ACTOR + 0x170] ^= 0xFF
            self.memory[ATTACHED + 0x3B] ^= 0xFF
            self.memory[FLAG] ^= 0xFF
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.lo, self.hi, self.r[2] = 0xA5000010, 0xA5000011, result


def native_controls():
    body = source.SELECTED
    controls = {
        "wrong_identity_byte": body.replace("actor[0x80]", "actor[0x81]"),
        "wrong_selector_byte": body.replace("actor[0x170]", "actor[0x171]"),
        "short_copy": body.replace("0x40);", "0x3C);"),
        "missing_normalization": body.replace(
            "        workspace.matrix[2][3] = 0.0f;\n", ""),
        "reversed_representation": body.replace(
            "D_800C3E90 != 0", "D_800C3E90 == 0"),
        "wrong_success": body.replace("    return 1;\n}", "    return 2;\n}"),
    }
    assert all(value != body for value in controls.values())
    return controls


def native_harness():
    variants = {"selected": source.SELECTED, **native_controls()}
    declarations = r'''
typedef unsigned char u8; typedef unsigned int u32; typedef signed int s32;
typedef float f32; typedef struct { u32 words[16]; } Mtx;
#define NULL ((void *)0)
typedef struct { f32 matrix[4][4]; u8 reserved40[8]; } MatrixWorkspace15F680;
u8 D_800C3E90;
void *memcpy(void *, const void *, unsigned int);
void guMtxF2L(f32 [4][4], Mtx *);
'''
    bodies = "\n".join(body.replace(source.FUNCTION, name)
                       for name, body in variants.items())
    support = r'''
typedef union { u32 align; u8 bytes[0x180]; } ActorBank;
typedef union { u32 align; u8 bytes[0x1E0]; } AttachedBank;
typedef union { u32 align; u8 bytes[0x4000]; } MatrixBank;
typedef union { u32 align; u8 bytes[0x80]; } OutputBank;
static ActorBank actor; static AttachedBank attached;
static MatrixBank matrices; static OutputBank output;
static u32 selector, copyCalls, convertCalls, stage, error;
static u32 load(const u8 *p){return (u32)p[0]|((u32)p[1]<<8)|((u32)p[2]<<16)|((u32)p[3]<<24);}
static void store(u8*p,u32 v){p[0]=(u8)v;p[1]=(u8)(v>>8);p[2]=(u8)(v>>16);p[3]=(u8)(v>>24);}
static u8 pattern(u32 s,u32 i){return (u8)(s*37+i*13+0x5A);}
void *memcpy(void *d,const void *s,unsigned int n){u32 i;u8*o=(u8*)d;const u8*p=(const u8*)s;
 copyCalls++;stage++;for(i=0;i<n;i++)o[i]=p[i];return d;}
void guMtxF2L(f32 matrix[4][4],Mtx *destination){u32 i,w;
 convertCalls++;stage++;if((u8*)destination!=output.bytes)error=1;
 for(i=0;i<16;i++){w=load((u8*)matrix+i*4);
  if((i==3||i==7||i==11)?w!=0:i==15?w!=0x3F800000:
     w!=load(matrices.bytes+selector*0x40+i*4))error=2;
  store(output.bytes+i*4,w^0x13579BDFu);}}
static void setup(u32 s,u32 representation){u32 i;selector=s;stage=copyCalls=convertCalls=error=0;
 for(i=0;i<sizeof(actor.bytes);i++)actor.bytes[i]=(u8)(i*29+7);
 for(i=0;i<sizeof(attached.bytes);i++)attached.bytes[i]=(u8)(i*29+7);
 for(i=0;i<sizeof(matrices.bytes);i++)matrices.bytes[i]=pattern(i>>6,i&63);
 for(i=0;i<sizeof(output.bytes);i++)output.bytes[i]=0xA5;
 *(u8**)(actor.bytes+0x7C)=attached.bytes;*(u32*)attached.bytes=0x13579BDFu;
 attached.bytes[4]=0x42;actor.bytes[0x80]=attached.bytes[0x3B]=0x3D;
 *(u8**)(attached.bytes+0x1D4)=matrices.bytes;attached.bytes[0x74]=0xA2;
 actor.bytes[0x170]=(u8)s;actor.bytes[0x171]=0;D_800C3E90=(u8)representation;}
typedef s32 (*Fn)(Mtx*,u8*);
static int exercise(Fn fn){u32 s,r,i,w;
 if(sizeof(void*)!=4||sizeof(Mtx)!=64||sizeof(MatrixWorkspace15F680)!=72)return 90;
 for(r=0;r<2;r++)for(s=0;s<256;s++){setup(s,r);if(fn((Mtx*)output.bytes,actor.bytes)!=1)return 10;
  if(copyCalls!=1||convertCalls!=(r?0:1)||stage!=(r?1:2)||error)return 11;
  for(i=0;i<64;i++){u8 expected;if(r)expected=pattern(s,i);else{
    w=load(matrices.bytes+s*0x40+(i&~3u));if((i>>2)==3||(i>>2)==7||(i>>2)==11)w=0;
    if((i>>2)==15)w=0x3F800000;w^=0x13579BDFu;expected=(u8)(w>>(8*(i&3)));}
    if(output.bytes[i]!=expected)return 12;}}
 setup(3,1);*(u8**)(actor.bytes+0x7C)=0;if(fn((Mtx*)output.bytes,actor.bytes)!=-1)return 20;
 setup(3,1);*(u32*)attached.bytes=0;if(fn((Mtx*)output.bytes,actor.bytes)!=-1)return 21;
 setup(3,1);attached.bytes[4]=0xFF;if(fn((Mtx*)output.bytes,actor.bytes)!=-1)return 22;
 setup(3,1);attached.bytes[0x3B]^=0xFF;if(fn((Mtx*)output.bytes,actor.bytes)!=-1)return 23;
 setup(3,1);*(u8**)(attached.bytes+0x1D4)=0;if(fn((Mtx*)output.bytes,actor.bytes)!=0)return 24;
 setup(3,1);attached.bytes[0x74]=0xAF;if(fn((Mtx*)output.bytes,actor.bytes)!=0)return 25;
 return 0;}
int run(void){u32 result=exercise(selected);if(result)return result;
'''
    checks = "\n".join("if(!exercise(%s))return %d;" % (name, index)
                       for index, name in enumerate(native_controls(), 2))
    return declarations + bodies + support + checks + "\nreturn 0;}\n" + START


class SelectedActorMatrixTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        report = json.loads((cls.output / "qualification.json").read_text())
        if report.get("function") != source.FUNCTION:
            report = source.prepare(ROOT, cls.output)[0]
        cls.report = report
        cls.rom = (ROOT / source.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(">65I", cls.rom, source.ROM))
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.fresh = Path(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        (cls.output / ("test-receipt-" + str(os.getpid()) + ".json")).write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def compare(self, case):
        initial = fixture(case)
        expected, result, calls = reference(initial, case)
        model = SelectedMatrixOracle(self.words, initial, case).run()
        self.assertEqual(model.r[2], result, case)
        self.assertEqual(model.calls, calls, case)
        self.assertEqual(external(model.memory, case.phase),
                         external(expected, case.phase), case)
        return model

    def test_01_literal_shape_owner_image_and_protected_data(self):
        self.assertEqual((self.report["words"], self.report["frame"],
                          self.report["natural_positional_differences"],
                          self.report["guards"], self.report["relocations"],
                          self.report["neighbors"]), (65, 104, 2, 2, 5, 30))
        self.assertEqual(self.report["changed_bodies"], [source.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        self.assertEqual((self.report["game_data"]["exact"],
                          self.report["game_data"]["bytes"],
                          self.report["game_data"]["owner_count"],
                          self.report["game_data"]["different_bytes"]),
                         (True, 189088, 720, 0))
        qualified = (self.output / "qualified-image/conker.us.elf").read_bytes()
        start = source.elf_slot_offset(qualified, source.ENTRY, source.SIZE)
        self.assertEqual(qualified[start:start + source.SIZE],
                         self.rom[source.ROM:source.ROM + source.SIZE])
        self.receipt["closure"] = self.report

    def test_02_guest_all_selectors_representations_stack_phases_and_gates(self):
        visits, cases = set(), 0
        for selector, flag, phase in itertools.product(range(256), (0, 1), (0, 8)):
            model = self.compare(Case(selector, flag, "valid", phase))
            visits.update(model.visits)
            cases += 1
        for gate, flag, phase in itertools.product(
                ("null-attached", "empty-attached", "sentinel", "identity",
                 "null-matrices", "disabled-slot"), (0, 1), (0, 8)):
            model = self.compare(Case(0xA5, flag, gate, phase))
            visits.update(model.visits)
            cases += 1
        unreachable = {source.ENTRY + offset for offset in (0x50, 0x64, 0xB0)}
        self.assertEqual(visits,
                         set(range(source.ENTRY, source.ENTRY + source.SIZE, 4)) - unreachable)
        self.receipt["guest"] = dict(cases=cases, all_256_unsigned_selectors=True,
            raw_and_float_routes=True, stack_phases=[0, 8],
            all_62_reachable_words=True, three_branch_likely_shadow_copies_unreachable=True,
            independent_memory_and_call_reference=True)

    def test_03_helper_clobbers_and_source_selection_are_stable(self):
        for selector, flag, phase in itertools.product((0, 1, 127, 255), (0, 1), (0, 8)):
            self.compare(Case(selector, flag, "valid", phase, True))
        self.receipt["clobbers"] = dict(cases=32,
            actor_tag_selector_and_representation_mutated_after_copy=True,
            caller_saved_integer_float_hi_lo_clobbered=True)

    def test_04_native32_actual_C_O0_O2_O3_and_six_controls(self):
        text = native_harness()
        for option in ("-O0", "-O2", "-O3"):
            path = self.fresh / ("native-" + option[1:] + ".c")
            path.write_text(text)
            binary = path.with_suffix("")
            command = native_command(option) + ["-fno-builtin", "-fno-strict-aliasing",
                                                 str(path), "-o", str(binary)]
            built = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            (path.with_suffix(".diagnostics.txt")).write_text(built.stdout + built.stderr)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            self.assertEqual(subprocess.run([str(binary)], timeout=120).returncode, 0, option)
        self.receipt["native"] = dict(profiles=["O0", "O2", "O3"],
            cases_per_profile=518, pointer_bits=32, matrix_bytes=64,
            workspace_bytes=72, semantic_controls=list(native_controls()))

    def test_05_callback_registry_and_indirect_caller_contract(self):
        direct = 0x0C000000 | ((source.ENTRY >> 2) & 0x03FFFFFF)
        self.assertFalse(any(struct.unpack_from(">I", self.rom, offset)[0] == direct
                             for offset in range(0, len(self.rom) - 3, 4)))
        pointers = [offset for offset in range(0, len(self.rom) - 3, 4)
                    if struct.unpack_from(">I", self.rom, offset)[0] == source.ENTRY]
        self.assertEqual(pointers, [0x22E460])
        self.assertEqual(struct.unpack_from(">11I", self.rom, TABLE_ROM), TABLE_WORDS)
        caller = struct.unpack_from(">14I", self.rom, 0x15FFA8)
        self.assertEqual(caller, (
            0xAFA50018, 0x90AC0078, 0x914AE9C0, 0x3C198009, 0x000C6880,
            0x032DC821, 0x8F39998C, 0x000A5980, 0x00AB2021, 0x0320F809,
            0x24840090, 0x2401FFFF, 0x14410005, 0x8FA50018,
        ))
        self.receipt["caller"] = dict(direct_ROM_JALs=0,
            aligned_pointer_literals=pointers, registry_index=5,
            output="actor + D_800BE9C0*0x40 + 0x90", actor_argument="a1",
            return_minus_one_branch_preserved=True)

    def test_06_guards_bindings_and_actual_padder_fail_closed(self):
        compact = self.output / "qualified-compact.o"
        raw, bindings = source.function_blob(compact, source.FUNCTION)
        self.assertEqual(bindings, source.RAW_BINDINGS)
        natural = struct.unpack(">65I", raw)
        for offset, expected, replacement in source.GUARD_ROWS:
            self.assertEqual((natural[offset // 4], self.words[offset // 4]),
                             (expected, replacement))
            nr, er, rr = natural[offset // 4] >> 21 & 31, natural[offset // 4] >> 16 & 31, natural[offset // 4] >> 11 & 31
            ng, eg, rg = replacement >> 21 & 31, replacement >> 16 & 31, replacement >> 11 & 31
            self.assertEqual((nr, er, rr), (eg, ng, rg))
        proposed = self.output / "proposed-guards.csv"
        for index, (_, expected, _) in enumerate(source.GUARD_ROWS):
            with proposed.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            selected = [row for row in rows if row["filename"] == source.FILENAME and
                        row["function"] == source.FUNCTION]
            selected[index]["expected"] = "0x%08X" % (expected ^ 1)
            bad = self.fresh / ("bad-guard-%d.csv" % index)
            with bad.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator="\n")
                writer.writeheader(); writer.writerows(rows)
            with self.assertRaises(ValueError):
                emit_padded_assembly(compact, ROOT / source.ASM,
                                     word_patches_path=bad, filename=source.FILENAME)
        wrong_source = (self.output / "proposed-owner.c").read_text().replace(
            "actor[0x170]", "actor[0x171]")
        negative = self.output / ("negative-test-" + str(os.getpid()))
        negative.mkdir(exist_ok=True)
        wrong, _ = source.compile_owner(ROOT, negative, wrong_source, "wrong-selector")
        with self.assertRaises(ValueError):
            source.checked_candidate(wrong)
        self.receipt["fail_closed"] = dict(guards=2, bindings=5,
            guards_are_commutative_operand_swaps=True,
            each_stale_expected_word_rejected=True, wrong_source_rejected=True)


if __name__ == "__main__":
    unittest.main()
