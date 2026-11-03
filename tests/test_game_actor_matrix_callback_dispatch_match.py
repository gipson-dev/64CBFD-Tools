"""Actor matrix callback dispatch semantics, ABI, direct match and image closure."""

from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import os
import struct
import subprocess
import tempfile
import unittest

from tools.experiments import game_actor_matrix_callback_dispatch_candidates as candidate
from tools.experiments import game_actor_matrix_callback_dispatch_match as source
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_projected_packet_draw import native_command


ROOT = Path(__file__).resolve().parents[2]
ACTOR, GATE = 0x20000, 0x26000
TABLE, SLOT = 0x8008998C, 0x800BE9C0
GUARD, DESTROY = 0x151464B8, 0x1516972C
CALLBACK_BASE = 0x15200000


@dataclass(frozen=True)
class Case:
    flags: int = 0
    gate: bool = True
    guard_result: int = 0
    callback_result: int = 1
    slot: int = 0
    selector: int = 0
    phase: int = 0
    guard_flags: int | None = None
    callback_flags: int | None = None


def fixture(case):
    memory = {STACK + case.phase + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x300, 0x100)}
    memory.update({ACTOR + index: (index * 29 + 7) & 0xFF
                   for index in range(0x4100)})
    memory.update({GATE + index: (index * 11 + 3) & 0xFF for index in range(16)})
    put(memory, ACTOR + 0x60, case.flags)
    put(memory, ACTOR + 0x6C, GATE if case.gate else 0)
    memory[ACTOR + 0x78] = case.selector
    memory[SLOT] = case.slot
    for selector in range(256):
        put(memory, TABLE + selector * 4, CALLBACK_BASE + selector * 4)
    return memory


def external(memory, phase):
    return {address: value for address, value in memory.items()
            if not STACK + phase - 0x300 <= address < STACK + phase + 0x100}


def reference(initial, case):
    memory = dict(initial)
    calls = []
    flags = read(memory, ACTOR + 0x60) & ~0x200000
    put(memory, ACTOR + 0x60, flags)
    if flags & 0x20000:
        return memory, calls
    if flags & 0x400 and case.gate:
        calls.append(("guard", GATE))
        if case.guard_flags is not None:
            put(memory, ACTOR + 0x60, case.guard_flags)
        if case.guard_result != 0:
            return memory, calls
    flags = read(memory, ACTOR + 0x60)
    if flags & 0x80000:
        put(memory, ACTOR + 0x60, flags | 0x200000)
        return memory, calls
    output = ACTOR + (case.slot << 6) + 0x90
    calls.append(("callback", case.selector, output, ACTOR))
    if case.callback_flags is not None:
        put(memory, ACTOR + 0x60, case.callback_flags)
    if case.callback_result == -1:
        calls.append(("destroy", ACTOR))
        return memory, calls
    flags = read(memory, ACTOR + 0x60)
    if case.callback_result == 0:
        flags &= ~0x40000
    else:
        flags |= 0x240000
    put(memory, ACTOR + 0x60, flags)
    return memory, calls


class DispatchOracle(TimingOracle):
    def __init__(self, words, memory, case):
        super().__init__(words, memory, phase=case.phase, entry=source.ENTRY,
                         arguments=(ACTOR,))
        self.case = case

    def record_call(self, target):
        if target == GUARD:
            call = ("guard", self.arguments(1)[0])
        elif target == DESTROY:
            call = ("destroy", self.arguments(1)[0])
        else:
            selector = (target - CALLBACK_BASE) // 4
            output, actor = self.arguments(2)
            call = ("callback", selector, output, actor)
        self.calls.append(call)
        self.events.append(("CALL", target, call))

    def hook(self, target):
        if target == GUARD:
            if self.case.guard_flags is not None:
                self.put(ACTOR + 0x60, self.case.guard_flags, 4)
            result = self.case.guard_result
        elif target == DESTROY:
            result = 0x5A5A0002
        else:
            if self.case.callback_flags is not None:
                self.put(ACTOR + 0x60, self.case.callback_flags, 4)
            result = self.case.callback_result
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.lo, self.hi, self.r[2] = 0xA5000010, 0xA5000011, result & 0xFFFFFFFF


def semantic_controls():
    body = candidate.SELECTED
    controls = {
        "wrong_active_clear": body.replace("~0x200000", "~0x100000", 1),
        "wrong_early_gate": body.replace("flags & 0x20000", "flags & 0x10000", 1),
        "wrong_helper_gate": body.replace("flags & 0x400", "flags & 0x800", 1),
        "wrong_busy_gate": body.replace("flags & 0x80000", "flags & 0x40000", 1),
        "wrong_callback_index": body.replace(
            "D_8008998C[actor->matrixCallback]",
            "D_8008998C[(u8)(actor->matrixCallback + 1)]", 1),
        "wrong_output_stride": body.replace("D_800BE9C0 << 6", "D_800BE9C0 << 5", 1),
        "negative_range": body.replace("result == -1", "result < 0", 1),
        "wrong_zero_clear": body.replace("~0x40000", "~0x20000", 1),
        "wrong_positive_mask": body.replace("|= 0x240000", "|= 0x200000", 1),
        "missing_destroy": body.replace(
            "        func_1516972C((u8 *)actor);",
            "        (void)actor;", 1),
    }
    assert all(value != body for value in controls.values())
    return controls


def native_harness():
    variants = {"selected": candidate.SELECTED, **semantic_controls()}
    declarations = r'''
typedef unsigned char u8; typedef unsigned int u32; typedef signed int s32;
typedef struct { u32 words[16]; } Mtx;
#define NULL ((void *)0)
extern u8 D_800BE9C0;
typedef s32 (*ActorMatrixCallback15F680)(Mtx *, u8 *);
extern ActorMatrixCallback15F680 D_8008998C[];
s32 func_151464B8(void *);
void func_1516972C(u8 *);
typedef struct { u8 retained00[0x60]; u32 flags; u8 retained64[8];
 void *gate; u8 retained70[8]; u8 matrixCallback; } ActorMatrixDispatch15F680;
'''
    bodies = "\n".join(body.replace(candidate.FUNCTION, name)
                       for name, body in variants.items())
    support = r'''
u8 D_800BE9C0; ActorMatrixCallback15F680 D_8008998C[256];
typedef union { u32 align; u8 bytes[0x4100]; } ActorBank;
static ActorBank bank; static u32 gateWord; static ActorMatrixDispatch15F680 *actor;
static s32 guardResult, callbackResult; static u32 guardCalls, callbackCalls;
static u32 destroyCalls, badCalls, callbackBad, mutateGuard, mutateCallback;
static u32 guardFlags, callbackFlags; static u8 selectedIndex;
static s32 wrongCallback(Mtx *output,u8 *owner){(void)output;(void)owner;badCalls++;return callbackResult;}
static s32 matrixCallback(Mtx *output,u8 *owner){callbackCalls++;
 if(owner!=(u8*)actor||output!=(Mtx*)((u8*)actor+((u32)D_800BE9C0<<6)+0x90))callbackBad=1;
 if(mutateCallback)actor->flags=callbackFlags;return callbackResult;}
s32 func_151464B8(void *gate){guardCalls++;if(gate!=&gateWord)callbackBad=2;
 if(mutateGuard)actor->flags=guardFlags;return guardResult;}
void func_1516972C(u8 *owner){destroyCalls++;if(owner!=(u8*)actor)callbackBad=3;}
static void setup(u32 flags,u32 hasGate,s32 guard,s32 callback,u8 slot,u8 index){u32 i;
 actor=(ActorMatrixDispatch15F680*)bank.bytes;for(i=0;i<sizeof(bank.bytes);i++)bank.bytes[i]=(u8)(i*29+7);
 actor->flags=flags;actor->gate=hasGate?&gateWord:NULL;actor->matrixCallback=index;
 D_800BE9C0=slot;selectedIndex=index;guardResult=guard;callbackResult=callback;
 guardCalls=callbackCalls=destroyCalls=badCalls=callbackBad=mutateGuard=mutateCallback=0;
 for(i=0;i<256;i++)D_8008998C[i]=wrongCallback;D_8008998C[index]=matrixCallback;}
typedef void (*Fn)(ActorMatrixDispatch15F680 *);
static int exercise(Fn fn){
 if(sizeof(void*)!=4||sizeof(Mtx)!=64||__builtin_offsetof(ActorMatrixDispatch15F680,flags)!=0x60||
    __builtin_offsetof(ActorMatrixDispatch15F680,gate)!=0x6C||
    __builtin_offsetof(ActorMatrixDispatch15F680,matrixCallback)!=0x78)return 90;
 setup(0x00260444u,1,0,1,3,5);fn(actor);
 if(actor->flags!=0x00060444u||guardCalls||callbackCalls||destroyCalls)return 1;
 setup(0x00240444u,1,1,1,3,5);fn(actor);
 if(actor->flags!=0x00040444u||guardCalls!=1||callbackCalls||destroyCalls)return 2;
 setup(0x00000400u,0,0,1,7,9);fn(actor);
 if(actor->flags!=0x00240400u||guardCalls||callbackCalls!=1||callbackBad||badCalls)return 3;
 setup(0x00080400u,1,0,1,2,11);fn(actor);
 if(actor->flags!=0x00280400u||guardCalls!=1||callbackCalls)return 4;
 setup(0x00240000u,1,0,-1,4,13);fn(actor);
 if(actor->flags!=0x00040000u||callbackCalls!=1||destroyCalls!=1||callbackBad)return 5;
 setup(0x00000000u,1,0,-2,5,15);fn(actor);
 if(actor->flags!=0x00240000u||callbackCalls!=1||destroyCalls||callbackBad)return 6;
 setup(0x00240100u,1,0,0,6,17);fn(actor);
 if(actor->flags!=0x00000100u||callbackCalls!=1||destroyCalls||callbackBad)return 7;
 setup(0x00000100u,1,0,1,8,19);fn(actor);
 if(actor->flags!=0x00240100u||callbackCalls!=1||callbackBad)return 8;
 setup(0x00000400u,1,0,1,9,21);mutateGuard=1;guardFlags=0x00080123u;fn(actor);
 if(actor->flags!=0x00280123u||guardCalls!=1||callbackCalls)return 9;
 setup(0x00000000u,1,0,0,10,23);mutateCallback=1;callbackFlags=0x00040123u;fn(actor);
 if(actor->flags!=0x00000123u||callbackCalls!=1||callbackBad)return 10;
 setup(0x00000000u,1,0,1,255,25);mutateCallback=1;callbackFlags=0x10000123u;fn(actor);
 if(actor->flags!=0x10240123u||callbackCalls!=1||callbackBad)return 11;
 return 0;}
int run(void){u32 result=exercise(selected);if(result)return result;
'''
    checks = "\n".join("if(!exercise(%s))return %d;" % (name, index)
                       for index, name in enumerate(semantic_controls(), 20))
    return declarations + bodies + support + checks + "\nreturn 0;}\n" + \
        "void _start(void){int r=run();__asm__ volatile(\"movl %0,%%ebx;movl $1,%%eax;int $0x80\"::\"r\"(r):\"eax\",\"ebx\");}\n"


class ActorMatrixDispatchTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        cls.result = source.prepare(ROOT, cls.output)
        cls.report = cls.result["report"]
        cls.rom = (ROOT / source.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(">62I", cls.rom, source.ROM))
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.fresh = Path(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        (cls.output / ("test-receipt-" + str(os.getpid()) + ".json")).write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def compare(self, case):
        initial = fixture(case)
        expected, calls = reference(initial, case)
        model = DispatchOracle(self.words, initial, case).run()
        self.assertEqual(model.calls, calls, case)
        self.assertEqual(external(model.memory, case.phase),
                         external(expected, case.phase), case)
        return model

    def test_01_direct_object_owner_image_and_protected_data(self):
        self.assertEqual((self.report["words"], self.report["natural_frame"],
                          self.report["retail_frame"],
                          self.report["natural_positional_differences"],
                          self.report["guards"], self.report["relocations"],
                          self.report["neighbors"]), (62, 24, 24, 0, 0, 6, 30))
        self.assertEqual(self.report["changed_bodies"], [source.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        self.assertEqual((self.report["game_data"]["exact"],
                          self.report["game_data"]["bytes"],
                          self.report["game_data"]["owner_count"],
                          self.report["game_data"]["different_bytes"]),
                         (True, 189088, 720, 0))
        qualified = self.result["qualified_elf"].read_bytes()
        start = elf_slot_offset(qualified, source.ENTRY, source.SIZE)
        self.assertEqual(qualified[start:start + source.SIZE],
                         self.rom[source.ROM:source.ROM + source.SIZE])
        self.receipt["closure"] = self.report

    def test_02_guest_all_routes_clobbers_live_reloads_and_word_coverage(self):
        base = (
            Case(flags=0x260444),
            Case(flags=0x240444, guard_result=1),
            Case(flags=0x400, gate=False, callback_result=1),
            Case(flags=0x400, guard_result=0, callback_result=1),
            Case(flags=0x80400, guard_result=0),
            Case(flags=0x240000, callback_result=-1),
            Case(flags=0, callback_result=-2),
            Case(flags=0x240100, callback_result=0),
            Case(flags=0x100, callback_result=1),
            Case(flags=0x400, guard_flags=0x80123),
            Case(flags=0, callback_result=0, callback_flags=0x40123),
            Case(flags=0, callback_result=1, callback_flags=0x10000123),
        )
        visits, cases = set(), 0
        for original, slot, selector, phase in itertools.product(
                base, (0, 1, 255), (0, 5, 255), (0, 8)):
            case = Case(**{**original.__dict__, "slot": slot,
                           "selector": selector, "phase": phase})
            model = self.compare(case)
            visits.update(model.visits)
            cases += 1
        unreachable = {source.ENTRY + 0xD8}
        self.assertEqual(visits,
                         set(range(source.ENTRY, source.ENTRY + source.SIZE, 4)) - unreachable)
        self.receipt["guest"] = dict(cases=cases, stack_phases=[0, 8],
            slots=[0, 1, 255], callback_indices=[0, 5, 255],
            all_61_reachable_words=True,
            one_branch_likely_shadow_reload_unreachable=True,
            helper_and_callback_clobbers=True, live_post_call_flag_reloads=True)

    def test_03_native32_actual_C_O0_O2_O3_and_ten_controls(self):
        text = native_harness()
        for option in ("-O0", "-O2", "-O3"):
            path = self.fresh / ("native-" + option[1:] + ".c")
            path.write_text(text)
            binary = path.with_suffix("")
            command = native_command(option) + ["-fno-builtin", "-fno-strict-aliasing",
                                                 str(path), "-o", str(binary)]
            built = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            path.with_suffix(".diagnostics.txt").write_text(
                built.stdout + built.stderr)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            self.assertEqual(subprocess.run([str(binary)], timeout=120).returncode,
                             0, option)
        self.receipt["native"] = dict(profiles=["O0", "O2", "O3"],
            pointer_bits=32, actor_offsets=[0x60, 0x6C, 0x78],
            semantic_controls=list(semantic_controls()))

    def test_04_descriptor_abi_callback_contract_and_relocations(self):
        direct = 0x0C000000 | ((source.ENTRY >> 2) & 0x03FFFFFF)
        self.assertFalse(any(struct.unpack_from(">I", self.rom, offset)[0] == direct
                             for offset in range(0, len(self.rom) - 3, 4)))
        pointers = [offset for offset in range(0, len(self.rom) - 3, 4)
                    if struct.unpack_from(">I", self.rom, offset)[0] == source.ENTRY]
        self.assertEqual(pointers, [0x230488, 0x230E14])
        registry = (ROOT / "conker/asm/data/22FF90.rodata.s").read_text()
        self.assertEqual(registry.count(".word " + source.FUNCTION), 2)
        compact = self.result["qualified_compact"]
        raw, bindings = source.function_blob(compact)
        self.assertEqual((raw, bindings),
                         (source.retail_object_bytes(ROOT), source.BINDINGS))
        caller = struct.unpack_from(">14I", self.rom, 0x15FFA8)
        self.assertEqual(caller, (
            0xAFA50018, 0x90AC0078, 0x914AE9C0, 0x3C198009, 0x000C6880,
            0x032DC821, 0x8F39998C, 0x000A5980, 0x00AB2021, 0x0320F809,
            0x24840090, 0x2401FFFF, 0x14410005, 0x8FA50018,
        ))
        self.receipt["abi"] = dict(direct_ROM_JALs=0,
            descriptor_pointer_literals=pointers, callback_table="D_8008998C",
            output="actor + D_800BE9C0*0x40 + 0x90",
            callback_result_routes=[-1, 0, "nonzero"])

    def test_05_wrong_semantic_source_fails_closed(self):
        qualified = (self.output / "proposed-owner.c").read_text()
        wrong_source = qualified.replace("flags & 0x80000", "flags & 0x40000", 1)
        negative = self.output / ("negative-test-" + str(os.getpid()))
        negative.mkdir(exist_ok=True)
        wrong, _ = candidate.compile_owner(
            ROOT, negative, wrong_source, "wrong-busy-gate")
        with self.assertRaises(ValueError):
            source.checked_candidate(ROOT, wrong)
        self.receipt["fail_closed"] = dict(guards=0, bindings=6,
            wrong_semantic_source_rejected=True, direct_object_equals_retail=True)


if __name__ == "__main__":
    unittest.main()
