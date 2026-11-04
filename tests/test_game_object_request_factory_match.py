"""Semantic, caller, owner and strict-image gates for func_1515BE50."""

from dataclasses import dataclass
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_object_request_factory_candidates as candidate
from tools.experiments import game_object_request_factory_match as match
from tools.match_progress import load_elf_functions
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_frame_timing_oracle import STACK, TimingOracle
from tools.tests.test_game_point_transform_match import put, read


ROOT = Path(__file__).resolve().parents[2]
REQUEST, OBJECT, ALT_OBJECT, OUTPUT = 0x22000, 0x24000, 0x25000, 0x28000
ALLOCATE, COPY, CONSUME = 0x15167A68, 0x10022EC0, 0x1514EC1C
CALLER, CALLER_ROM, CALLER_WORDS = 0x1514EE70, 0x17C320, 23
PATTERNS = (0x00000000, 0x80000000, 0x3F800000, 0xBF400000,
            0x7F800000, 0xFF800000, 0x7FC12345, 0x7FA12345)


def u32(value):
    return value & 0xFFFFFFFF


@dataclass(frozen=True)
class Case:
    object_present: bool = True
    outcome: bool = True
    allocator_mutation: bool = False
    copy_mutation: bool = False
    extra: int = 0
    channel: int = 0xFF
    context: int = 1
    phase: int = 0
    seed: int = 0


def fixture(case=Case(), request=REQUEST):
    memory = {STACK + index: (index * 17 + case.seed + 0xA5) & 0xFF
              for index in range(-0x500, 0x180)}
    for base, size in ((request - 0x20, 0x60), (OBJECT - 0x20, 0x80),
                       (ALT_OBJECT - 0x20, 0x80), (OUTPUT - 0x20, 0xA0)):
        memory.update({base + index: (index * 13 + case.seed * 19 + 0x59) & 0xFF
                       for index in range(size)})
    put(memory, request, OBJECT if case.object_present else 0)
    memory[request + 4] = (case.seed * 29 + 7) & 0xFF
    memory[request + 5] = (case.seed * 31 + 3) & 0xFF
    put(memory, request + 6, (case.seed * 257 + 0x12C) & 0xFFFF, 2)
    for index in range(3):
        put(memory, OBJECT + 0x14 + index * 4,
            PATTERNS[(case.seed + index) % len(PATTERNS)])
        put(memory, ALT_OBJECT + 0x14 + index * 4,
            PATTERNS[(case.seed + index + 3) % len(PATTERNS)])
    return memory


def mutate(memory, request, stage):
    if stage == "allocate":
        put(memory, request, ALT_OBJECT)
        memory[request + 4] ^= 0x5A
        put(memory, ALT_OBJECT + 0x14, 0x41234567)
    elif stage == "copy":
        put(memory, request, ALT_OBJECT)
        put(memory, ALT_OBJECT + 0x18, 0xC2345678)
        put(memory, ALT_OBJECT + 0x1C, 0x7FC0A5A5)


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x500 <= address < STACK + 0x180}


def reference(initial, case=Case(), request=REQUEST):
    memory = dict(initial)
    calls = []
    if read(memory, request) == 0:
        return memory, calls, 0
    calls.append((ALLOCATE, (0x32, u32(case.context), u32(case.extra + 0x50),
                             1, case.channel & 0xFF, 1)))
    if case.allocator_mutation:
        mutate(memory, request, "allocate")
    if not case.outcome:
        return memory, calls, 0
    calls.append((COPY, (OUTPUT + 0x18, request, 8)))
    for index in range(8):
        memory[OUTPUT + 0x18 + index] = memory[request + index]
    if case.copy_mutation:
        mutate(memory, request, "copy")
    for index in range(3):
        value = read(memory, read(memory, request) + 0x14 + index * 4)
        put(memory, OUTPUT + 0x20 + index * 4, value)
        put(memory, OUTPUT + 0x2C + index * 4, value)
    for offset, value in ((0x44, 0), (0x48, 0xFFFFFFFF),
                          (0x10, 1), (0x14, 0),
                          (0x38, 0), (0x3C, 0), (0x40, 0)):
        put(memory, OUTPUT + offset, value)
    return memory, calls, OUTPUT


class FactoryOracle(TimingOracle):
    def __init__(self, words, memory, case=Case(), request=REQUEST,
                 entry=match.ENTRY, arguments=None, connected=None, fault=None):
        super().__init__(words, memory, phase=case.phase, entry=entry,
                         arguments=arguments or (request, case.extra,
                                                  case.channel, case.context),
                         connected=connected)
        self.case, self.request = case, request
        self.root_fault = fault
        self.callbacks = []

    def record_call(self, target):
        if target == match.ENTRY:
            self.callbacks.append(tuple(self.arguments(4)))
            return
        widths = {ALLOCATE: 6, COPY: 3, CONSUME: 3}
        if target not in widths:
            raise AssertionError("Unexpected object-request helper %08X" % target)
        args = tuple(u32(value) for value in self.arguments(widths[target]))
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target == ALLOCATE:
            if self.case.allocator_mutation:
                mutate(self.memory, self.request, "allocate")
            value = OUTPUT if self.case.outcome else 0
        elif target == COPY:
            destination, source, size = self.calls[-1][1]
            if size != 8:
                raise AssertionError("Object request copy size changed")
            for index in range(size):
                self.put(destination + index, self.get(source + index, 1), 1)
            if self.case.copy_mutation:
                mutate(self.memory, self.request, "copy")
            value = destination
        elif target == CONSUME:
            value = 0x76543210
        else:
            raise AssertionError("Unbounded object-request helper %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.r[2] = u32(value)


def controls():
    body = candidate.SELECTED
    variants = {
        "wrong-category": body.replace("0x32, context", "0x31, context", 1),
        "wrong-size": body.replace("extraBytes + 0x50", "extraBytes + 0x4C", 1),
        "short-copy": body.replace("sizeof(*request)", "sizeof(*request) - 1", 1),
        "wrong-current-x": body.replace("request->object->x;", "request->object->y;", 1),
        "missing-previous-z": body.replace(
            "    record->previousZ = request->object->z;\n", "", 1),
        "wrong-list-index": body.replace("record->listIndex = -1", "record->listIndex = 0", 1),
        "negative-zero": body.replace("record->velocityX = 0.0f",
                                        "record->velocityX = -0.0f", 1),
        "wrong-active": body.replace("record->active = 1", "record->active = 0", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("An object-request factory control did not alter source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef unsigned short u16;
typedef signed int s32;
typedef unsigned int u32;
typedef float f32;
#define NULL ((void *)0)
''' + candidate.TYPES + r'''
static RequestedObject1515BE50 primary,alternate;
static ObjectRequest1515BE50 request;
static ObjectFollowRecord1515BE50 output;
static u8 expectedRequest[8];
static s32 failed,allocationFailure,allocationMutation,copyMutation;
static s32 expectedExtra,expectedChannel,expectedContext,allocations,copies;
static void copy_bytes(void *destination,const void *source,u32 size) {
    u32 index;for(index=0;index<size;index++)((u8 *)destination)[index]=((const u8 *)source)[index];
}
void *func_15167A68(s32 category,s32 context,s32 size,s32 one,u8 channel,u8 mode) {
    allocations++;
    if(category!=0x32 || context!=expectedContext || size!=expectedExtra+0x50 ||
       one!=1 || channel!=(u8)expectedChannel || mode!=1) failed=1;
    if(allocationMutation) {request.object=&alternate;request.uniqueId^=0x5A;alternate.x=10.25f;}
    return allocationFailure?NULL:&output;
}
void *memcpy(void *destination,const void *source,u32 size) {
    copies++;
    if(destination!=&output.request || source!=&request || size!=8) failed=2;
    copy_bytes(destination,source,size);
    if(copyMutation) {request.object=&alternate;alternate.y=-45.5f;alternate.z=123.25f;}
    return destination;
}
''' + body + r'''
static u32 bits(f32 value) {union {f32 f;u32 u;} data;data.f=value;return data.u;}
static int one(u32 seed,s32 absent,s32 allocFail,s32 allocMutate,s32 copyMutate) {
    u32 index;ObjectFollowRecord1515BE50 before;
    u8 *bytes=(u8 *)&output;
    for(index=0;index<sizeof(output);index++)bytes[index]=(u8)(index*13u+seed*19u+0x59u);
    before=output;
    primary.x=(f32)(s32)(seed-130u);primary.y=(f32)(seed*3u);primary.z=(f32)(-((s32)seed)-7);
    alternate.x=-31.5f;alternate.y=62.25f;alternate.z=-93.75f;
    request.object=absent?NULL:&primary;request.uniqueId=(u8)(seed*29u+7u);
    request.retained05=(u8)(seed*31u+3u);request.size=(u16)(seed*257u+0x12Cu);
    copy_bytes(expectedRequest,&request,8);
    expectedExtra=(s32)(seed*0x10203u);expectedChannel=(s32)(seed*0x10001u+0xABCD00FFu);
    expectedContext=(s32)(seed*0x1000001u+0x80000000u);
    failed=allocations=copies=0;allocationFailure=allocFail;
    allocationMutation=allocMutate;copyMutation=copyMutate;
    {ObjectFollowRecord1515BE50 *result=func_1515BE50(&request,expectedExtra,(u8)expectedChannel,expectedContext);
     if(absent) {if(result!=NULL || allocations || copies || failed)return 1;}
     else if(allocFail) {if(result!=NULL || allocations!=1 || copies || failed)return 2;}
     else {
       RequestedObject1515BE50 *selected;
       if(result!=&output || allocations!=1 || copies!=1 || failed)return 3;
       if(allocMutate) {expectedRequest[0]=((u8 *)&request.object)[0];expectedRequest[1]=((u8 *)&request.object)[1];
         expectedRequest[2]=((u8 *)&request.object)[2];expectedRequest[3]=((u8 *)&request.object)[3];
         expectedRequest[4]=request.uniqueId;}
       for(index=0;index<8;index++)if(((u8 *)&output.request)[index]!=expectedRequest[index])return 4;
       selected=request.object;
       if(bits(output.currentX)!=bits(selected->x)||bits(output.currentY)!=bits(selected->y)||bits(output.currentZ)!=bits(selected->z)||
          bits(output.previousX)!=bits(selected->x)||bits(output.previousY)!=bits(selected->y)||bits(output.previousZ)!=bits(selected->z)||
          bits(output.velocityX)||bits(output.velocityY)||bits(output.velocityZ)||output.listState!=0||output.listIndex!=-1||
          output.active!=1||output.state!=0)return 5;
       for(index=0;index<0x10;index++)if(((u8 *)&output)[index]!=((u8 *)&before)[index])return 6;
     }}
    return 0;
}
static int run(void) {
    u32 seed;int absent,allocFail,allocMutate,copyMutate;
    if(sizeof(void *)!=4||sizeof(ObjectRequest1515BE50)!=8||sizeof(ObjectFollowRecord1515BE50)!=0x4C)return 9;
    for(seed=0;seed<256;seed++)for(absent=0;absent<2;absent++)for(allocFail=0;allocFail<2;allocFail++)
      for(allocMutate=0;allocMutate<2;allocMutate++)for(copyMutate=0;copyMutate<2;copyMutate++)
        if(one(seed,absent,allocFail,allocMutate,copyMutate))return 1;
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


class GameObjectRequestFactoryMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.retail = list(struct.unpack_from(">64I", (ROOT / match.ROM_IMAGE).read_bytes(),
                                                   match.ROM))

    def test_01_direct_shape_owner_neighbors_and_strict_image(self):
        direct = candidate.compare("test-direct", candidate.SELECTED)
        self.assertEqual((direct["words"], direct["frame"], direct["differences"],
                          direct["diagnostics"]), (64, 0x30, 0, ""))
        self.assertEqual(direct["bindings"], {
            "0x04C": [("R_MIPS_26", "func_15167A68")],
            "0x070": [("R_MIPS_26", "memcpy")],
        })
        non_debug = candidate.compare("test-non-debug", candidate.SELECTED,
                                      flags=("-O2",))
        self.assertEqual((non_debug["words"], non_debug["frame"],
                          non_debug["differences"]), (64, 0x30, 14))
        report = match.prepare(ROOT)["report"]
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertEqual((report["guards"], report["neighbors"],
                          report["strict_exclusions"]), (0, 10, 0))
        self.assertTrue(report["all_addresses_fixed"])
        self.assertTrue(report["game_data"]["exact"])

    def test_02_guest_contract_live_helpers_and_all_words(self):
        cases, coverage = 0, set()
        corpus = itertools.product((False, True), (False, True), (False, True),
                                   (False, True), (0, 1, 0x7FFFFFFF, 0x80000000,
                                                     0xFFFFFFFF),
                                   (0, 0xABCD00FF, 0xFFFFFFFF),
                                   (0, 0x80000000, 0xFFFFFFFF), (0, 8))
        for present, outcome, allocate_mutation, copy_mutation, extra, channel, context, phase in corpus:
            case = Case(present, outcome, allocate_mutation, copy_mutation,
                        extra, channel, context, phase, cases & 255)
            initial = fixture(case)
            wanted, calls, result = reference(initial, case)
            model = FactoryOracle(self.retail, initial, case).run()
            self.assertEqual((public(model.memory), model.calls, model.r[2]),
                             (public(wanted), calls, result))
            coverage.update(model.visits)
            cases += 1
        self.assertEqual(cases, 1440)
        self.assertEqual(coverage, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        (self.output / "guest-contract.json").write_text(json.dumps({
            "cases": cases, "words": len(coverage), "allocator_mutations": True,
            "copy_mutations": True, "raw_float_patterns": list(PATTERNS),
        }, indent=2) + "\n")

    def test_03_native_profiles_and_effective_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED,
                       optimization, 0)
        variants = controls()
        for label, body in variants.items():
            run_native("control-" + label, body, "-O2", 1)
        (self.output / "native-contract.json").write_text(json.dumps({
            "profiles": ["O0", "O2", "O3"], "cases_per_profile": 4096,
            "controls": sorted(variants),
        }, indent=2) + "\n")

    def test_04_actual_caller_connected_handoff_and_fault_boundaries(self):
        functions, _, addresses = load_elf_functions(
            str(ROOT / match.ELF), "mips-linux-gnu-objdump")
        caller = functions["func_1514EE70"]
        retail_caller = list(struct.unpack_from(">%dI" % CALLER_WORDS,
                                                 (ROOT / match.ROM_IMAGE).read_bytes(),
                                                 CALLER_ROM))
        self.assertEqual(addresses["func_1514EE70"], CALLER)
        self.assertEqual(caller, retail_caller)
        connected = dict(zip(range(match.ENTRY, match.ENTRY + match.SIZE, 4),
                             self.retail))
        cases, coverage = 0, set()
        for outcome, phase, seed in itertools.product((False, True), (0, 8), range(16)):
            case = Case(True, outcome, False, False, 0, 0xFF, 1, phase, seed)
            initial = fixture(case, request=STACK + phase - 8)
            # The caller constructs its request in its own frame; only the object is input.
            wanted = dict(initial)
            direct_case = Case(True, outcome, False, False, 0, 0xFF, 1, phase, seed)
            request = STACK + phase - 8
            put(wanted, request, OBJECT)
            wanted[request + 4] = initial[OBJECT + 0x3B]
            wanted[request + 5] = 0
            put(wanted, request + 6, 0x12C, 2)
            wanted, helper_calls, result = reference(wanted, direct_case, request)
            expected_calls = [*helper_calls, (CONSUME, (result, OBJECT, 0x16))]
            model = FactoryOracle(caller, initial, direct_case, request=request,
                                  entry=CALLER, arguments=(OBJECT,),
                                  connected=connected).run()
            self.assertEqual(model.callbacks,
                             [(request, 0, 0xFF, 1)])
            self.assertEqual((public(model.memory), model.calls),
                             (public(wanted), expected_calls))
            coverage.update(model.visits)
            cases += 1
        target_words = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4))
        self.assertEqual(target_words - coverage,
                         {match.ENTRY + 0x30, match.ENTRY + 0x34})
        successful = Case(seed=7)
        initial = fixture(successful)
        baseline = FactoryOracle(self.retail, initial, successful).run()
        fault_states = []
        for cut in range(baseline.root_accesses):
            model = FactoryOracle(self.retail, initial, successful, fault=cut)
            with self.assertRaises(faults.AccessBoundary):
                model.run()
            fault_states.append((model.current_pc, model.delay_of, model.root_accesses))
        self.assertEqual(len(fault_states), baseline.root_accesses)
        self.assertGreater(len(fault_states), 20)
        (self.output / "caller-and-faults.json").write_text(json.dumps({
            "caller_cases": cases, "caller_words": CALLER_WORDS,
            "root_access_faults": fault_states,
        }, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main()
