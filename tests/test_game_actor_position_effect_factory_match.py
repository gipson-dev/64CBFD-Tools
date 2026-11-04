"""Semantic, caller, owner and strict-image gates for func_151B6320."""

from dataclasses import dataclass
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_position_effect_factory_candidates as candidate
from tools.experiments import game_actor_position_effect_factory_match as match
from tools.match_progress import load_elf_functions
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_frame_timing_oracle import STACK, TimingOracle
from tools.tests.test_game_point_transform_match import put, read


ROOT = Path(__file__).resolve().parents[2]
ACTOR, RECORD, DESTINATION = 0x22000, 0x24000, 0x26000
CREATE, COPY, PRIOR = 0x15147A80, 0x10022EC0, 0x151B7144
CALLER, CALLER_ROM, CALLER_WORDS = 0x1506AA08, 0x97EB8, 16
PATTERNS = (
    0x00000000, 0x80000000, 0x3F800000, 0xBF400000,
    0x7F800000, 0xFF800000, 0x7FC12345, 0x7FA12345,
)


def u32(value):
    return value & 0xFFFFFFFF


@dataclass(frozen=True)
class Case:
    allocated: bool = True
    mutate_actor: bool = False
    channel: int = 0xFF
    context: int = 1
    phase: int = 0
    seed: int = 0


def fixture(case=Case()):
    memory = {
        STACK + index: (index * 17 + case.seed * 23 + 0xA5) & 0xFF
        for index in range(-0x500, 0x180)
    }
    for base, size in (
            (ACTOR - 0x20, 0xA0),
            (RECORD - 0x20, 0xE0),
            (DESTINATION - 0x20, 0x80)):
        memory.update({
            base + index: (index * 13 + case.seed * 19 + 0x59) & 0xFF
            for index in range(size)
        })
    for index in range(3):
        put(memory, ACTOR + 0x14 + index * 4,
            PATTERNS[(case.seed + index) % len(PATTERNS)])
    memory[ACTOR + 0x3B] = (case.seed * 29 + 0x6B) & 0xFF
    put(memory, RECORD + 0x98, DESTINATION)
    return memory


def expected_request(initial, case, stack=STACK):
    base = stack + case.phase - 0x90 + 0x74
    payload = {base + index: initial[base + index] for index in range(0x18)}
    for index in range(3):
        put(payload, base + index * 4, read(initial, ACTOR + 0x14 + index * 4))
    put(payload, base + 0x0C, 300, 2)
    put(payload, base + 0x0E, 6, 2)
    put(payload, base + 0x10, 13)
    payload[base + 0x15] = 10
    return bytes(payload[base + index] for index in range(0x18))


def expected_payload(initial, case, stack=STACK):
    base = stack + case.phase - 0x90 + 0x44
    payload = {base + index: initial[base + index] for index in range(0x2C)}
    put(payload, base, ACTOR)
    payload[base + 4] = initial[ACTOR + 0x3B]
    for index in range(3):
        put(payload, base + 8 + index * 4,
            read(initial, ACTOR + 0x14 + index * 4))
    for offset, value in (
            (0x14, 0), (0x18, 0),
            (0x1C, 0xC6800000), (0x20, 0xC6800000),
            (0x24, 0)):
        put(payload, base + offset, value)
    return bytes(payload[base + index] for index in range(0x2C))


def reference(initial, case=Case(), stack=STACK):
    memory = dict(initial)
    request = expected_request(initial, case, stack)
    payload = expected_payload(initial, case, stack)
    request_pointer = stack + case.phase - 0x90 + 0x74
    payload_pointer = stack + case.phase - 0x90 + 0x44
    calls = [(CREATE, (
        request_pointer, 0x30, 0x1C, 0xB, 0xB, 0xB,
        0, 0, 0, case.channel & 0xFF, u32(case.context),
    ))]
    if case.mutate_actor:
        for index in range(3):
            put(memory, ACTOR + 0x14 + index * 4,
                0xA1000000 + case.seed * 3 + index)
        memory[ACTOR + 0x3B] ^= 0x5A
    if case.allocated:
        calls.append((COPY, (DESTINATION, payload_pointer, 0x2C)))
        for index, value in enumerate(payload):
            memory[DESTINATION + index] = value
    return memory, calls, request, payload


def public(memory):
    return {
        address: value for address, value in memory.items()
        if not STACK - 0x500 <= address < STACK + 0x180
    }


class FactoryOracle(TimingOracle):
    def __init__(self, words, memory, case=Case(), entry=match.ENTRY,
                 arguments=None, connected=None, fault=None):
        super().__init__(
            words, memory, phase=case.phase, entry=entry,
            arguments=arguments or (ACTOR, case.channel, case.context),
            connected=connected,
        )
        self.case = case
        self.root_fault = fault
        self.request_snapshots = []
        self.payload_snapshots = []
        self.callbacks = []
        self.prior_calls = []

    def record_call(self, target):
        if target == match.ENTRY:
            self.callbacks.append(tuple(self.arguments(3)))
            return
        if target == PRIOR:
            self.prior_calls.append(tuple(self.arguments(3)))
            return
        widths = {CREATE: 11, COPY: 3}
        if target not in widths:
            raise AssertionError("Unexpected actor-position helper %08X" % target)
        arguments = tuple(u32(value) for value in self.arguments(widths[target]))
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))
        if target == CREATE:
            self.request_snapshots.append(bytes(
                self.memory[arguments[0] + index] for index in range(0x18)
            ))
        else:
            self.payload_snapshots.append(bytes(
                self.memory[arguments[1] + index] for index in range(0x2C)
            ))

    def hook(self, target):
        if target == CREATE:
            if self.case.mutate_actor:
                for index in range(3):
                    self.put(ACTOR + 0x14 + index * 4,
                             0xA1000000 + self.case.seed * 3 + index, 4)
                self.put(ACTOR + 0x3B,
                         self.get(ACTOR + 0x3B, 1) ^ 0x5A, 1)
            result = RECORD if self.case.allocated else 0
        elif target == COPY:
            destination, source, size = self.calls[-1][1]
            if size != 0x2C:
                raise AssertionError("Actor-position payload copy size changed")
            for index in range(size):
                self.put(destination + index, self.get(source + index, 1), 1)
            result = destination
        elif target == PRIOR:
            result = 0x76543210
        else:
            raise AssertionError("Unbounded actor-position helper %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678
        self.r[2] = u32(result)


def controls():
    body = candidate.SELECTED
    variants = {
        "wrong-x-source": body.replace("actor + 0x14", "actor + 0x10", 1),
        "wrong-duration": body.replace("duration = 300", "duration = 301", 1),
        "wrong-flags": body.replace("flags = 6", "flags = 7", 1),
        "wrong-owner": body.replace("owner = actor", "owner = actor + 1", 1),
        "wrong-identity": body.replace("actor[0x3B]", "actor[0x3A]", 1),
        "negative-zero": body.replace("velocityX = 0.0f", "velocityX = -0.0f", 1),
        "wrong-lower-bound": body.replace(
            "lowerBound = -16384.0f", "lowerBound = -8192.0f", 1),
        "wrong-kind": body.replace("kind = 13", "kind = 12", 1),
        "wrong-count": body.replace("count = 10", "count = 9", 1),
        "wrong-helper-size": body.replace(
            "&locals.request, 0x30", "&locals.request, 0x2C", 1),
        "short-copy": body.replace(
            "&locals.payload, 0x2C", "&locals.payload, 0x28", 1),
        "shifted-destination": body.replace(
            "*(void **)(record + 0x98)",
            "(u8 *)*(void **)(record + 0x98) + 1", 1),
    }
    if len(variants) != 12 or any(value == body for value in variants.values()):
        raise AssertionError("An actor-position factory control did not alter source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef signed short s16;
typedef unsigned short u16;
typedef signed int s32;
typedef unsigned int u32;
typedef float f32;
#define NULL ((void *)0)
''' + candidate.DECLARATIONS + r'''
static u32 actorWords[0x40], recordWords[0x40], outputWords[0x20];
static u32 wanted[3], createCalls, copyCalls, failed, allocated, mutateActor;
static u8 wantedIdentity, wantedChannel;
static s32 wantedContext;
static u32 load32(const void *pointer) { return *(const u32 *)pointer; }
static void store32(void *pointer, u32 value) { *(u32 *)pointer = value; }
u8 *func_15147A80(void *request, s32 payloadBytes, s32 entryBytes,
    s32 active, s32 first, s32 second, s32 resourceBytes, s32 value,
    void *optional, u8 channel, s32 context) {
    ActorEffectRequest151B6320 *packet = request;
    createCalls++;
    if (payloadBytes != 0x30 || entryBytes != 0x1C || active != 0xB ||
        first != 0xB || second != 0xB || resourceBytes != 0 || value != 0 ||
        optional != NULL || channel != wantedChannel || context != wantedContext)
        failed = 1;
    if (load32(&packet->position.x) != wanted[0] ||
        load32(&packet->position.y) != wanted[1] ||
        load32(&packet->position.z) != wanted[2] || packet->duration != 300 ||
        packet->flags != 6 || packet->kind != 13 || packet->count != 10)
        failed = 2;
    if (mutateActor) {
        store32((u8 *)actorWords + 0x14, 0xA1000001u);
        store32((u8 *)actorWords + 0x18, 0xA1000002u);
        store32((u8 *)actorWords + 0x1C, 0xA1000003u);
        *((u8 *)actorWords + 0x3B) ^= 0x5A;
    }
    return allocated ? (u8 *)recordWords : NULL;
}
void *memcpy(void *destination, const void *source, unsigned int size) {
    const ActorEffectPayload151B6320 *packet = source;
    u8 *out = destination;
    const u8 *in = source;
    u32 index;
    copyCalls++;
    if (destination != (u8 *)outputWords || size != 0x2C) failed = 3;
    if (packet->owner != (u8 *)actorWords || packet->identity != wantedIdentity ||
        load32(&packet->position.x) != wanted[0] ||
        load32(&packet->position.y) != wanted[1] ||
        load32(&packet->position.z) != wanted[2] ||
        load32(&packet->velocityX) != 0 || load32(&packet->velocityY) != 0 ||
        load32(&packet->lowerBound) != 0xC6800000u ||
        load32(&packet->upperBound) != 0xC6800000u ||
        load32(&packet->velocityZ) != 0)
        failed = 4;
    for (index = 0; index < size; index++) out[index] = in[index];
    return destination;
}
''' + body + r'''
static int one(u32 seed) {
    static const u32 patterns[8] = {0,0x80000000u,0x3F800000u,0xBF400000u,
        0x7F800000u,0xFF800000u,0x40490FDBu,0xC2480000u};
    u8 *actor = (u8 *)actorWords;
    u8 *record = (u8 *)recordWords;
    u8 *output = (u8 *)outputWords;
    u32 index;
    for (index = 0; index < sizeof(actorWords); index++) actor[index] = (u8)(seed * 11u + index * 7u);
    for (index = 0; index < sizeof(recordWords); index++) record[index] = (u8)(seed * 13u + index * 5u);
    for (index = 0; index < sizeof(outputWords); index++) output[index] = (u8)(seed * 17u + index * 3u);
    for (index = 0; index < 3; index++) {
        wanted[index] = patterns[(seed + index) & 7u];
        store32(actor + 0x14 + index * 4, wanted[index]);
    }
    wantedIdentity = (u8)(seed * 29u + 0x6Bu);
    actor[0x3B] = wantedIdentity;
    wantedChannel = (u8)(seed * 0x10101u + 0xFFu);
    wantedContext = (s32)(seed * 0x9E3779B9u + 0x12345678u);
    store32(record + 0x98, (u32)output);
    allocated = seed & 1u;
    mutateActor = (seed >> 1) & 1u;
    createCalls = copyCalls = failed = 0;
    func_151B6320(actor, wantedChannel, wantedContext);
    if (failed) return (int)(10u + failed);
    if (createCalls != 1) return 20;
    if (copyCalls != allocated) return 21;
    return 0;
}
static int run(void) {
    u32 seed;
    if (sizeof(void *) != 4 || sizeof(ActorEffectRequest151B6320) != 0x18 ||
        sizeof(ActorEffectPayload151B6320) != 0x2C ||
        sizeof(ActorEffectLocals151B6320) != 0x4C ||
        __builtin_offsetof(ActorEffectPayload151B6320, position) != 8 ||
        __builtin_offsetof(ActorEffectRequest151B6320, count) != 0x15)
        return 9;
    for (seed = 0; seed < 4096; seed++) {
        s32 result = one(seed);
        if (result) return result;
    }
    return 0;
}
void _start(void) {
    s32 code = run();
    __asm__ volatile("int $0x80"::"a"(1),"b"(code));
    __builtin_unreachable();
}
'''


def run_native(label, body, optimization, should_pass):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / (label + ".elf")
    source.write_text(native_source(body))
    command = [
        "gcc", "-m32", "-std=c99", optimization, "-fno-pie", "-no-pie",
        "-ffreestanding", "-fno-builtin-memcpy", "-fno-strict-aliasing",
        "-fno-stack-protector", "-fsanitize=undefined",
        "-fsanitize-undefined-trap-on-error", "-Wall", "-Wextra", "-Werror",
        "-nostdlib", str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if should_pass and executed.returncode != 0:
        raise AssertionError((label, executed.returncode, executed.stderr))
    if not should_pass and executed.returncode == 0:
        raise AssertionError((label, "semantic control passed"))


class GameActorPositionEffectFactoryMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.prepared = match.prepare(ROOT)
        cls.retail = list(struct.unpack_from(
            ">%dI" % match.WORDS,
            (ROOT / match.ROM_IMAGE).read_bytes(), match.ROM,
        ))
        cls.natural = cls.retail.copy()

    def receipt(self, name, data):
        (self.output / (name + ".json")).write_text(
            json.dumps(data, indent=2) + "\n"
        )

    def test_01_direct_profile_owner_neighbors_and_strict_image(self):
        selected = candidate.compare("test-selected", candidate.SELECTED)
        self.assertEqual(
            (selected["words"], selected["frame"], selected["differences"]),
            (64, 0x90, 0),
        )
        self.assertEqual(selected["bindings"], {
            "0x0D0": [("R_MIPS_26", "func_15147A80")],
            "0x0E4": [("R_MIPS_26", "memcpy")],
        })
        report = self.prepared["report"]
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(
            (report["guards"], report["neighbors"], report["strict_exclusions"]),
            (0, 16, 0),
        )
        self.assertTrue(report["all_addresses_fixed"])
        self.assertTrue(report["game_data"]["exact"])
        self.assertEqual(report["functions"], 6052)

    def test_02_guest_packet_helper_failure_success_and_all_words(self):
        cases = []
        for seed, values in enumerate(itertools.product(
                (False, True), (False, True),
                (0, 0xFF, 0x12345678, 0xFFFFFFFF),
                (0, 1, 0x7FFFFFFF, 0x80000000), (0, 8))):
            allocated, mutate, channel, context, phase = values
            cases.append(Case(allocated, mutate, channel, context, phase, seed))
        coverage = [set(), set()]
        for case in cases:
            initial = fixture(case)
            wanted, calls, request, payload = reference(initial, case)
            for index, words in enumerate((self.retail, self.natural)):
                model = FactoryOracle(words, initial, case).run()
                self.assertEqual((public(model.memory), model.calls),
                                 (public(wanted), calls), case)
                self.assertEqual(model.request_snapshots, [request])
                self.assertEqual(model.payload_snapshots,
                                 [payload] if case.allocated else [])
                coverage[index].update(model.visits)
        full = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4))
        self.assertEqual(coverage[0], full)
        self.assertEqual(coverage[1], full)
        self.receipt("guest-contract", {
            "cases": len(cases), "retail_words": len(coverage[0]),
            "natural_C_words": len(coverage[1]),
            "reserved_request_bytes_preserved": ["0x14", "0x16..0x17"],
            "reserved_payload_bytes_preserved": ["0x05..0x07", "0x28..0x2B"],
            "helper_actor_mutation_after_snapshot": True,
        })

    def test_03_native_profiles_and_effective_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED,
                       optimization, True)
        variants = controls()
        for label, body in variants.items():
            run_native("control-" + label, body, "-O2", False)
        self.receipt("native-contract", {
            "profiles": ["O0", "O2", "O3"], "cases_per_profile": 4096,
            "controls": sorted(variants), "actual_32_bit_C": True,
        })

    def test_04_actual_caller_connected_handoff_and_fault_boundaries(self):
        functions, _, addresses = load_elf_functions(
            str(ROOT / match.ELF), "mips-linux-gnu-objdump"
        )
        caller = functions["func_1506AA08"]
        retail_caller = list(struct.unpack_from(
            ">%dI" % CALLER_WORDS,
            (ROOT / match.ROM_IMAGE).read_bytes(), CALLER_ROM,
        ))
        self.assertEqual(addresses["func_1506AA08"], CALLER)
        self.assertEqual(caller, retail_caller)
        connected = dict(zip(
            range(match.ENTRY, match.ENTRY + match.SIZE, 4), self.retail
        ))
        caller_cases = 0
        for allocated, mutate, phase, seed in itertools.product(
                (False, True), (False, True), (0, 8), range(8)):
            case = Case(allocated, mutate, 0xFF, 1, phase, seed)
            initial = fixture(case)
            model = FactoryOracle(
                caller, initial, case, entry=CALLER,
                arguments=(ACTOR, 0xA5000000 + seed), connected=connected,
            ).run()
            self.assertEqual(model.prior_calls, [(ACTOR, 0xFF, 1)])
            self.assertEqual(model.callbacks, [(ACTOR, 0xFF, 1)])
            self.assertEqual(model.calls[0][0], CREATE)
            self.assertEqual(model.calls[0][1][9:], (0xFF, 1))
            self.assertEqual(len(model.calls), 2 if allocated else 1)
            caller_cases += 1
        evidence = match.registry_evidence(ROOT)
        self.assertEqual(evidence["direct_jal_calls"], ["0x97ee0"])
        self.assertEqual(evidence["aligned_pointer_literals"], [])
        states = []
        for words in (self.retail, self.natural):
            for allocated in (False, True):
                case = Case(allocated=allocated, mutate_actor=True, seed=7)
                initial = fixture(case)
                baseline = FactoryOracle(words, initial, case).run()
                for cut in range(baseline.root_accesses):
                    model = FactoryOracle(words, initial, case, fault=cut)
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.root_accesses, cut)
                    states.append((model.current_pc, model.delay_of, cut))
        self.assertGreater(len(states), 100)
        self.receipt("caller-and-faults", {
            "caller_cases": caller_cases, "caller_words": CALLER_WORDS,
            "fault_observations": len(states),
            "unique_boundaries": len(set(states)),
        })


if __name__ == "__main__":
    unittest.main()
