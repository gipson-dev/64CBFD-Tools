"""Camera heading normalizer semantics, ABI, guarded match and image closure."""

from dataclasses import dataclass
from pathlib import Path
import csv
import itertools
import json
import math
import struct
import subprocess
import unittest

from tools.experiments import game_camera_heading_normalizer_candidates as candidate
from tools.experiments import game_camera_heading_normalizer_match as source
from tools.match_progress import load_elf_functions
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK


ROOT = Path(__file__).resolve().parents[2]
CAMERA = 0x22000
ACTOR = 0x26000
DIFFERENCE = 0x15048F90
ANGLE = 0x15048FC8


def f32(value):
    return bits(float(value))


def add(left, right):
    return bits(floating(left) + floating(right))


def subtract(left, right):
    return bits(floating(left) - floating(right))


@dataclass(frozen=True)
class Case:
    active: int
    mode: int
    current: int
    tracked: int
    angle: int
    origin: tuple
    target: tuple
    phase: int = 0


def cases():
    points = (
        ((1.0, 2.0, 3.0), (4.0, 6.0, 8.0)),
        ((-5.0, 7.5, 11.0), (2.0, -3.0, -13.0)),
    )
    rows = []
    for active, mode, current, tracked, angle, pair, phase in itertools.product(
            (0, 1, -1), (0, 9, 10, 14, 15),
            (-1080.0, -359.5, 0.0, 45.0, 721.25),
            (-720.0, -1.0, 180.0, 540.0),
            (-1080.0, -360.0, 0.0, 90.0, 720.0), points, (0, 8)):
        rows.append(Case(active, mode, f32(current), f32(tracked), f32(angle),
                         tuple(map(f32, pair[0])), tuple(map(f32, pair[1])), phase))
    rows.extend((
        Case(0, 10, f32(-0.0), f32(float("nan")), f32(0.0),
             tuple(map(f32, points[0][0])), tuple(map(f32, points[0][1]))),
        Case(1, 10, f32(float("nan")), f32(0.0), f32(1.0),
             tuple(map(f32, points[1][0])), tuple(map(f32, points[1][1])), 8),
    ))
    return rows


def special(case):
    return case.active != 0 and case.mode in (10, 14)


def expected(case):
    if special(case):
        value = subtract(case.current, case.angle)
    else:
        value = subtract(subtract(case.tracked, case.current), f32(180.0))
        while floating(value) < 0.0:
            value = add(value, f32(360.0))
    while floating(value) < -360.0:
        value = add(value, f32(360.0))
    return value


def fixture(case):
    memory = {STACK + case.phase + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x300, 0x100)}
    memory.update({CAMERA + index: (index * 29 + 7) & 0xFF
                   for index in range(0x800)})
    memory.update({ACTOR + index: (index * 11 + 3) & 0xFF
                   for index in range(0x100)})
    put(memory, CAMERA + 0x6C8, case.active)
    put(memory, CAMERA + 0x6FC, case.mode)
    put(memory, CAMERA + 0x37C, case.current)
    put(memory, CAMERA + 0x390, f32(1234.5))
    put(memory, CAMERA + 0x3D0, ACTOR)
    put(memory, ACTOR + 0x40, case.tracked)
    for index, value in enumerate(case.origin):
        put(memory, CAMERA + 0x618 + index * 4, value)
    for index, value in enumerate(case.target):
        put(memory, CAMERA + 0x2A4 + index * 4, value)
    return memory


class HeadingOracle(TimingOracle):
    def __init__(self, words, case):
        self.case = case
        self.packets = []
        super().__init__(words, fixture(case), phase=case.phase,
                         entry=source.ENTRY, arguments=(CAMERA,))

    def record_call(self, target):
        if target == DIFFERENCE:
            args = self.arguments(4)
            expected_args = (CAMERA + 0x618, CAMERA + 0x2A4,
                             STACK + self.case.phase - 0x10, CAMERA)
            if args != expected_args:
                raise AssertionError((args, expected_args))
            packet = ("difference", args)
        elif target == ANGLE:
            args = self.arguments(1)
            expected_address = STACK + self.case.phase - 0x10
            if args != (expected_address,):
                raise AssertionError((args, expected_address))
            packet = ("angle", tuple(read(self.memory, args[0] + i * 4)
                                      for i in range(3)))
        else:
            raise AssertionError("Unbounded camera heading call " + hex(target))
        self.packets.append(packet)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def clobber(self):
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.lo, self.hi = 0x12345678, 0x87654321

    def hook(self, target):
        if target == DIFFERENCE:
            left, right, output, camera = self.arguments(4)
            if camera != CAMERA:
                raise AssertionError("Camera was not preserved in a3")
            for index in range(3):
                self.put(output + index * 4,
                         subtract(read(self.memory, right + index * 4),
                                  read(self.memory, left + index * 4)), 4)
            result = None
        else:
            result = self.case.angle
        self.clobber()
        if result is not None:
            self.f[0] = result


def native_harness(body, corpus):
    rows = []
    for case in corpus:
        rows.append("{%d,%d,0x%Xu,0x%Xu,0x%Xu,{%s},{%s},0x%Xu}" % (
            case.active, case.mode, case.current, case.tracked, case.angle,
            ",".join("0x%Xu" % value for value in case.origin),
            ",".join("0x%Xu" % value for value in case.target), expected(case)))
    declarations = r'''
typedef unsigned char u8; typedef unsigned int u32; typedef signed int s32;
typedef float f32;
typedef struct { f32 unk0, unk4, unk8; } struct17;
typedef struct { u8 pad0[0x40]; f32 unk40; } struct127;
typedef struct {
    u8 pad000[0x2A4]; f32 unk2A4, unk2A8, unk2AC;
    u8 pad2B0[0xCC]; f32 unk37C; u8 pad380[0x10]; f32 unk390;
    u8 pad394[0x3C]; struct127 *unk3D0; u8 pad3D4[0x244];
    s32 unk618; f32 unk61C, unk620; u8 pad624[0xA4];
    s32 unk6C8; u8 pad6CC[0x30]; s32 unk6FC;
} struct108;
extern void func_15048F90();
f32 func_15048FC8(struct17 *);
'''
    support = r'''
typedef struct { s32 active,mode;u32 current,tracked,angle,origin[3],target[3],expected; } Case;
static const Case cases[] = {''' + ",\n".join(rows) + r'''};
static struct108 camera; static struct127 actor; static const Case *item;
static u32 calls, error;
static f32 real(u32 value){union{u32 u;f32 f;}v;v.u=value;return v.f;}
static u32 word(f32 value){union{u32 u;f32 f;}v;v.f=value;return v.u;}
void func_15048F90(struct17 *origin,struct17 *target,struct17 *out,struct108 *owner){
    if(calls++!=0||origin!=(struct17*)&camera.unk618||target!=(struct17*)&camera.unk2A4||owner!=&camera)error=1;
    out->unk0=target->unk0-origin->unk0;out->unk4=target->unk4-origin->unk4;out->unk8=target->unk8-origin->unk8;
}
f32 func_15048FC8(struct17 *direction){
    if(calls++!=1||word(direction->unk0)!=word(camera.unk2A4-*(f32*)&camera.unk618)||
       word(direction->unk4)!=word(camera.unk2A8-camera.unk61C)||
       word(direction->unk8)!=word(camera.unk2AC-camera.unk620))error=2;
    return real(item->angle);
}
static int run(void){u32 n,i;
 if(sizeof(void*)!=4||__builtin_offsetof(struct108,unk2A4)!=0x2A4||
    __builtin_offsetof(struct108,unk37C)!=0x37C||__builtin_offsetof(struct108,unk390)!=0x390||
    __builtin_offsetof(struct108,unk3D0)!=0x3D0||__builtin_offsetof(struct108,unk618)!=0x618||
    __builtin_offsetof(struct108,unk6C8)!=0x6C8||__builtin_offsetof(struct108,unk6FC)!=0x6FC)return 90;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){item=&cases[n];calls=error=0;
  for(i=0;i<sizeof(camera);i++){((u8*)&camera)[i]=0xA5;}
  for(i=0;i<sizeof(actor);i++){((u8*)&actor)[i]=0x5A;}
  camera.unk6C8=item->active;camera.unk6FC=item->mode;camera.unk37C=real(item->current);
  camera.unk390=1234.5f;camera.unk3D0=&actor;actor.unk40=real(item->tracked);
  for(i=0;i<3;i++){((f32*)&camera.unk618)[i]=real(item->origin[i]);(&camera.unk2A4)[i]=real(item->target[i]);}
  func_15123070(&camera);
  if(error||calls!=((item->active!=0&&(item->mode==10||item->mode==14))?2u:0u)||word(camera.unk390)!=item->expected)return 23;
 }
 return 0;}
__attribute__((noreturn))void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    return declarations + "\n" + body + "\n" + support


class CameraHeadingNormalizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        cls.result = source.prepare(ROOT, cls.output)
        cls.report = cls.result["report"]
        cls.corpus = cases()
        cls.native_corpus = cls.corpus[::31] + cls.corpus[-2:]
        cls.retail = list(struct.unpack(">%dI" % source.WORDS,
            (ROOT / source.ROM_IMAGE).read_bytes()[source.ROM:source.ROM + source.SIZE]))
        linked, _, _ = load_elf_functions(
            str(cls.result["qualified_elf"]), "mips-linux-gnu-objdump")
        cls.qualified = linked[source.FUNCTION]
        cls.receipt = {"installed": cls.report["source_installed"]}

    @classmethod
    def tearDownClass(cls):
        (cls.output / "test-receipt.json").write_text(
            json.dumps(cls.receipt, indent=2) + "\n")
        print("camera heading normalizer qualification:", cls.receipt)

    def test_01_guarded_words_owner_and_full_image_closure(self):
        self.assertEqual(self.qualified, self.retail)
        self.assertEqual((self.report["words"], self.report["natural_frame"],
                          self.report["guards"], self.report["relocations"]),
                         (67, 0x30, 12, 2))
        self.assertEqual(self.report["changed_bodies"], [source.FUNCTION])
        self.assertEqual((self.report["neighbors"], self.report["functions"],
                          self.report["strict_exclusions"]), (44, 6051, 0))
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual((self.report["game_data"]["exact"],
                          self.report["game_data"]["bytes"],
                          self.report["game_data"]["owner_count"]),
                         (True, 189088, 720))
        with (self.output / "qualified-patches.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        target = [row for row in rows if row["function"] == source.FUNCTION]
        self.assertEqual(target, [source.complete_row(row) for row in source.PATCH_ROWS])
        self.receipt.update(words=67, frame=48, guards=12, relocations=2,
                            neighbors=44, functions=6051,
                            protected_game_bytes=189088, strict_exclusions=0)

    def test_02_complete_guest_semantics_calls_clobbers_and_loops(self):
        self.assertEqual(self.qualified, self.retail)
        visits = set()
        special_count = 0
        loop_count = 0
        for case in self.corpus:
            model = HeadingOracle(self.qualified, case).run()
            self.assertEqual(read(model.memory, CAMERA + 0x390), expected(case))
            wanted_calls = [DIFFERENCE, ANGLE] if special(case) else []
            self.assertEqual([target for target, _ in model.calls], wanted_calls)
            if special(case):
                special_count += 1
                difference = tuple(subtract(case.target[i], case.origin[i])
                                   for i in range(3))
                self.assertEqual(model.packets[1], ("angle", difference))
            if (not math.isnan(floating(expected(case))) and
                    (floating(case.current) - floating(case.angle) < -360.0 or
                     floating(case.tracked) - floating(case.current) - 180.0 < 0.0)):
                loop_count += 1
            self.assertEqual(model.r[29], STACK + case.phase)
            visits.update(model.visits)
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + source.SIZE, 4)))
        self.receipt.update(guest_cases=len(self.corpus), special_cases=special_count,
                            loop_cases=loop_count, all67_words_visited=True,
                            helper_fourth_argument_checked=True)

    def native(self, body, label, opt):
        unit = self.output / (label + opt + ".c")
        binary = self.output / (label + opt)
        unit.write_text(native_harness(body, self.native_corpus))
        command = ["gcc", "-m32", opt, "-std=gnu99", "-fno-strict-aliasing",
                   "-ffreestanding", "-nostdlib", "-static", "-fno-pie", "-no-pie",
                   "-fno-stack-protector", "-msse2", "-mfpmath=sse", "-mstackrealign",
                   "-ffp-contract=off", "-fsanitize=undefined,float-cast-overflow",
                   "-fsanitize-undefined-trap-on-error", "-Wall", "-Wextra", "-Werror",
                   "-Wno-unused-parameter", str(unit), "-o", str(binary)]
        result = subprocess.run(command, capture_output=True, text=True)
        (self.output / (label + opt + "-compiler.log")).write_text(
            result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr[:3000])
        return subprocess.run([str(binary)], capture_output=True, timeout=30).returncode

    def test_03_native32_profiles_and_semantic_controls(self):
        for opt in ("-O0", "-O2", "-O3"):
            self.assertEqual(self.native(candidate.SELECTED, "selected", opt), 0)
        controls = {
            "wrong-mode": candidate.SELECTED.replace("camera->unk6FC == 14", "camera->unk6FC == 13"),
            "missing-active": candidate.SELECTED.replace("camera->unk6C8 != 0", "camera->unk6C8 == 0"),
            "reversed-vector": candidate.SELECTED.replace(
                "(struct17 *)&camera->unk618, &camera->unk2A4",
                "(struct17 *)&camera->unk2A4, &camera->unk618"),
            "special-add": candidate.SELECTED.replace(
                "camera->unk37C - func_15048FC8", "camera->unk37C + func_15048FC8"),
            "wrong-tracked-field": candidate.SELECTED.replace("unk3D0->unk40", "unk3D0->pad0[0]"),
            "wrong-bias": candidate.SELECTED.replace("- 180.0f", "+ 180.0f"),
            "wrong-first-step": candidate.SELECTED.replace("heading += 360.0f", "heading += 180.0f"),
            "wrong-final-bound": candidate.SELECTED.replace("< -360.0f", "< -180.0f"),
            "wrong-final-step": candidate.SELECTED.replace(
                "camera->unk390 += 360.0f", "camera->unk390 += 180.0f"),
        }
        for name, body in controls.items():
            self.assertNotEqual(body, candidate.SELECTED)
            self.assertEqual(self.native(body, name, "-O2"), 23, name)
        self.receipt.update(native_profiles=3, native_cases=len(self.native_corpus) * 3,
                            compiled_semantic_controls=len(controls), trap_UBSan=True)

    def test_04_source_contract_routing_and_rejection_controls(self):
        live = (ROOT / source.SOURCE).read_text()
        predecessor, qualified, installed = source.source_states(live)
        self.assertEqual(installed, self.report["source_installed"])
        self.assertIn(candidate.PREDECESSOR_BLOCK, predecessor)
        self.assertIn(candidate.SELECTED, qualified)
        self.assertIn(candidate.LOOSE_VECTOR_INCLUDE, qualified)
        self.assertEqual(source.routing_evidence(ROOT), self.report["registry"])
        for mutation in (
                qualified.replace("special_heading", "wrong_heading", 1),
                qualified.replace("func_15048F90();", "func_15048F90(struct17 *);"),
                qualified.replace(candidate.TYPED_DECLARATION, candidate.DECLARATION)):
            with self.assertRaises(ValueError):
                source.source_states(mutation)
        natural, bindings = source.function_blob(self.result["qualified_compact"])
        self.assertEqual(hashlib_sha256(natural), source.RAW_SHA256)
        self.assertEqual(bindings, source.BINDINGS)
        with self.assertRaises(ValueError):
            source.checked_candidate(ROOT, self.output / "predecessor-compact.o")
        self.receipt.update(direct_call_sites=4, same_word_non_calls=3,
                            aligned_pointer_literals=0, source_rejections=3)


def hashlib_sha256(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    unittest.main()
