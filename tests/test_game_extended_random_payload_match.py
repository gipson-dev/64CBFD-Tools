"""Semantic, owner, guard and full-image gates for func_1515AA84."""

from dataclasses import dataclass
import csv
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_extended_random_payload_candidates as candidate
from tools.experiments import game_extended_random_payload_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_actor_mask_scan_match import MaskOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_vertical_rate_match import RateOracle
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults


ROOT = Path(__file__).resolve().parents[2]
OWNER, VECTOR, RESULT = 0x30000, 0x38000, 0x40000
RNG, CREATE, COPY = 0x150ADA20, 0x15149130, 0x10022EC0
TABLE = 0x8008F970
WINDOW, END, WINDOW_ROM = 0x151A8E9C, 0x151A8EC4, 0x1D634C
RANDOMS = (0, 1, 2, 31, 132, 133, 0x7FFFFFFF, 0x80000000,
           0xFFFFFFFE, 0xFFFFFFFF)
PATTERNS = (0, 0x80000000, 0x7F812345, 0xFF800000,
            0x3F800000, 0xA55A00FF)
SYMBOLS = dict(func_150ADA20=RNG, func_15149130=CREATE, memcpy=COPY)


@dataclass(frozen=True)
class Case:
    random: int = 0xFFFFFFFF
    minimum: int = -69
    range_minus_one: int = 132
    route: int = 255
    slot: int = 128
    layout: int = 0
    destination: int = 1
    mode: int = 0
    phase: int = 0
    scalar: int = 0x3F800000


def signed16(value):
    value &= 0xFFFF
    return value if value < 0x8000 else value - 0x10000


def mutate(memory, position):
    put(memory, OWNER + 1, 0xE3, 1)
    put(memory, OWNER + 0xC, 0xA7, 1)
    put(memory, OWNER + 0x80, (-321) & 0xFFFF, 2)
    put(memory, OWNER + 0x82, 36, 2)
    for index in range(40):
        put(memory, OWNER + 0x84 + index, 0xD0 ^ index, 1)
    for index in range(3):
        put(memory, position + index * 4, 0x76543210 ^ index)


def fixture(case):
    memory = {STACK + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-1024, 1024)}
    for base in (OWNER, VECTOR, RESULT):
        memory.update({base + index: (index * 13 + 0xA5) & 0xFF
                       for index in range(-64, 320)})
    frame = STACK + case.phase - 0x80
    position = (VECTOR, OWNER + 0x20, frame + 0x48,
                frame + 0x44, frame + 0x80)[case.layout]
    for index in range(3):
        put(memory, position + index * 4,
            PATTERNS[(case.slot + index) % len(PATTERNS)])
    put(memory, OWNER + 1, case.route, 1)
    put(memory, OWNER + 0xC, case.slot, 1)
    put(memory, OWNER + 0x80, case.minimum & 0xFFFF, 2)
    put(memory, OWNER + 0x82, case.range_minus_one & 0xFFFF, 2)
    for index in range(40):
        put(memory, OWNER + 0x84 + index,
            (index * 29 + case.slot * 7 + 0x31) & 0xFF, 1)
    result = (0, RESULT, OWNER - 0x28, VECTOR - 0x28)[case.destination]
    return memory, (OWNER, position, case.scalar, 0xFEDCBA98), result


def reference(initial, args, result, case):
    memory = dict(initial)
    frame = STACK + case.phase - 0x80
    payload = frame + 0x44
    for address, value in ((frame + 0x80, args[0]),
                           (frame + 0x8C, args[3])):
        put(memory, address, value)
    put(memory, payload, 0)
    for index in range(3):
        put(memory, payload + 4 + index * 4,
            read(memory, args[1] + index * 4))
    put(memory, payload + 0x10, args[2])
    for index in range(40):
        put(memory, payload + 0x14 + index,
            memory[OWNER + 0x84 + index], 1)
    if case.mode:
        mutate(memory, args[1])
    divisor = (signed16(read(memory, OWNER + 0x82, 2)) + 1) & 0xFFFFFFFF
    if divisor == 0:
        raise ZeroDivisionError
    duration = signed16((case.random & 0xFFFFFFFF) % divisor +
                        signed16(read(memory, OWNER + 0x80, 2)))
    creation = (duration & 0xFFFFFFFF, 0xFFFFFFFF, 0x3F, 0xFFFFFFFF,
                1, 0, 0x3C, memory[OWNER + 0xC], memory[OWNER + 1])
    if result:
        for index in range(60):
            put(memory, result + 0x28 + index, memory[payload + index], 1)
    return memory, creation


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 1024 <= address < STACK + 1024}


class ExtendedPayloadOracle(RateOracle, RayOracle):
    get = MaskOracle.get
    put = MaskOracle.put

    def __init__(self, words, memory, args, result, case,
                 connected=None, entry=match.ENTRY):
        TimingOracle.__init__(self, words, memory, phase=case.phase,
                              entry=entry, arguments=args,
                              connected=connected)
        self.payload_args = args
        self.result = result
        self.case = case
        self.symbols = SYMBOLS
        self.hi = self.lo = 0

    def execute(self, word):
        if word >> 26 == 32:
            return RayOracle.execute(self, word)
        return RateOracle.execute(self, word)

    def record_call(self, target):
        counts = {RNG: 0, CREATE: 9, COPY: 3, match.ENTRY: 4,
                  0x151A91AC: 4, 0x151A9634: 4, 0x150B1EE0: 4}
        if target not in counts:
            raise AssertionError("Unexpected extended-payload helper %08X" % target)
        arguments = self.arguments(counts[target])
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))
        if target == RNG and self.case.mode:
            mutate(self.memory, self.payload_args[1])

    def hook(self, target):
        if target == COPY:
            destination, source, size = self.arguments(3)
            if size != 60:
                raise AssertionError("Extended payload copy size changed")
            for index in range(size):
                self.put(destination + index, self.get(source + index, 1), 1)
            value = destination
        elif target == RNG:
            value = self.case.random & 0xFFFFFFFF
        elif target == CREATE:
            value = self.result
        else:
            raise AssertionError("Unbounded extended-payload helper %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.r[2] = value


class WindowBoundary(Exception):
    pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self, pc):
        if pc == END:
            raise WindowBoundary
        return super().__getitem__(pc)


def controls():
    body = candidate.SELECTED_MATCH
    variants = {
        "negative-zero": body.replace("payload.zero = 0.0f",
                                       "payload.zero = -0.0f", 1),
        "wrong-position": body.replace("payload.position = *position",
                                       "payload.position.x = position->y; payload.position.y = position->y; payload.position.z = position->z", 1),
        "wrong-scalar": body.replace("payload.scalar = scalar",
                                     "payload.scalar = 0.0f", 1),
        "wrong-state-offset": body.replace("owner + 0x84",
                                           "owner + 0x80", 1),
        "wrong-range": body.replace("range->rangeMinusOne",
                                    "range->minimum", 1),
        "wrong-kind": body.replace("0x3F", "0x3E", 1),
        "wrong-token": body.replace("(void *)0x3C", "(void *)0x38", 1),
        "wrong-route": body.replace("ownerAfter[1]", "ownerAfter[2]", 1),
        "short-copy": body.replace("sizeof(payload)",
                                    "sizeof(payload) - 1", 1),
        "wrong-destination": body.replace("record + 0x28",
                                          "record + 0x24", 1),
        "late-state-copy": body.replace(
            "    payload.ownerState = *(OwnerState1515AA84 *)(owner + 0x84);\n",
            "", 1).replace("    ownerAfter = owner;",
                            "    ownerAfter = owner;\n    payload.ownerState = *(OwnerState1515AA84 *)(ownerAfter + 0x84);", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("An extended-payload control did not alter the source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef signed char s8;
typedef unsigned short u16;
typedef signed short s16;
typedef unsigned int u32;
typedef signed int s32;
typedef float f32;
typedef unsigned int size_t;
#define NULL ((void *)0)
''' + candidate.INSTALL_TYPES.replace("#include <string.h>\n", "") + candidate.DECLARATIONS + r'''
static u8 ownerBytes[0xC0], output[0x90], expected[60];
static PayloadVector1515AA84 inputVector;
static u32 randomWord;
static int error, calls, copies, mode, failed;
static void copy_bytes(void *destination, const void *source, u32 size) {
    u32 index;
    for (index = 0; index < size; index++)
        ((u8 *)destination)[index] = ((const u8 *)source)[index];
}
static void mutation(void) {
    u32 index;
    ownerBytes[1] = 0xE3; ownerBytes[0xC] = 0xA7;
    *(s16 *)(ownerBytes + 0x80) = -321;
    *(s16 *)(ownerBytes + 0x82) = 36;
    for (index = 0; index < 40; index++) ownerBytes[0x84 + index] = (u8)(0xD0u ^ index);
    for (index = 0; index < 12; index++) ((u8 *)&inputVector)[index] = (u8)(index + 99u);
}
s32 func_150ADA20(void) {
    if (mode) mutation();
    return (s32)randomWord;
}
u8 *func_15149130(s16 duration, s8 first, s8 kind, s8 sentinel,
        u8 active, u8 flags, void *token, u8 slot, s32 route) {
    u32 divisor = (u32)((s32)*(s16 *)(ownerBytes + 0x82) + 1);
    s16 wanted = (s16)(randomWord % divisor + *(s16 *)(ownerBytes + 0x80));
    calls++;
    if (duration != wanted || first != -1 || kind != 0x3F || sentinel != -1 ||
            active != 1 || flags != 0 || (u32)token != 0x3C ||
            slot != ownerBytes[0xC] || route != ownerBytes[1]) error = 1;
    return failed ? NULL : output;
}
void *memcpy(void *destination, const void *source, size_t size) {
    u32 index;
    copies++;
    if (destination != output + 0x28 || size != 60) error = 2;
    for (index = 0; index < size && index < 60; index++)
        if (((const u8 *)source)[index] != expected[index]) error = 3;
    copy_bytes(destination, source, (u32)size);
    return destination;
}
''' + body + r'''
static int one(u32 value, u32 byte, int selectedMode, int selectedFailure) {
    union { u32 word; f32 value; } scalar;
    u32 index;
    randomWord = value; mode = selectedMode; failed = selectedFailure;
    calls = copies = error = 0;
    for (index = 0; index < sizeof(ownerBytes); index++) ownerBytes[index] = (u8)(index * 13u + byte);
    for (index = 0; index < sizeof(output); index++) output[index] = 0xA5;
    ownerBytes[1] = (u8)byte; ownerBytes[0xC] = (u8)(255u - byte);
    *(s16 *)(ownerBytes + 0x80) = (s16)(byte * 257u);
    *(s16 *)(ownerBytes + 0x82) = (s16)(byte % 31u);
    for (index = 0; index < 40; index++) ownerBytes[0x84 + index] = (u8)(index * 29u + byte * 7u + 0x31u);
    for (index = 0; index < 12; index++) ((u8 *)&inputVector)[index] = (u8)(index * 17u + byte);
    scalar.word = value ^ 0xA55A00FFu;
    for (index = 0; index < 60; index++) expected[index] = 0;
    copy_bytes(expected + 4, &inputVector, 12);
    copy_bytes(expected + 0x10, &scalar.word, 4);
    copy_bytes(expected + 0x14, ownerBytes + 0x84, 40);
    func_1515AA84(ownerBytes, &inputVector, scalar.value, (s32)0xFEDCBA98);
    if (error || calls != 1 || copies != !failed) return 1;
    if (!failed)
        for (index = 0; index < 60; index++)
            if (output[0x28 + index] != expected[index]) return 1;
    return 0;
}
int run(void) {
    static const u32 values[8] = {0, 1, 132, 133, 0x7FFFFFFF,
        0x80000000, 0xFFFFFFFE, 0xFFFFFFFF};
    u32 value, byte; int selectedMode, selectedFailure, result = 0;
    if (sizeof(void *) != 4 || sizeof(PayloadVector1515AA84) != 12 ||
            sizeof(OwnerState1515AA84) != 40 ||
            sizeof(ExtendedRandomPayload1515AA84) != 60) return 9;
    for (value = 0; value < 8; value++)
        for (byte = 0; byte < 256; byte++)
            for (selectedMode = 0; selectedMode < 2; selectedMode++)
                for (selectedFailure = 0; selectedFailure < 2; selectedFailure++)
                    result |= one(values[value], byte, selectedMode, selectedFailure);
    return result;
}
''' + START


def run_native(label, body, optimization, expected):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / label
    source.write_text(native_source(body))
    command = native_command(optimization) + ["-mstackrealign", str(source),
                                               "-o", str(binary)]
    compiled = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if ((expected == 0 and executed.returncode != 0) or
            (expected != 0 and executed.returncode == 0)):
        raise AssertionError((label, executed.returncode, executed.stderr))


class ExtendedRandomPayloadMatchTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.values = match.prepare(ROOT, cls.output)
        cls.report = cls.values["report"]
        image = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.retail = list(struct.unpack_from(">%dI" % match.WORDS,
                                             image, match.ROM))
        candidate.compare("test-direct-owner", candidate.SELECTED_MATCH)
        raw_object = ROOT / candidate.BUILD / "test-direct-owner.o"
        linked, functions = candidate.link_owner(ROOT, ROOT / candidate.BUILD,
                                                  raw_object, candidate.OWNER)
        cls.raw = list(struct.unpack_from(">%dI" % match.WORDS, linked,
                                          functions[match.FUNCTION]["value"]))
        cls.connected = {}

    @classmethod
    def tearDownClass(cls):
        (cls.output / "test-receipt.json").write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def compare(self, case):
        memory, args, result = fixture(case)
        expected, creation = reference(memory, args, result, case)
        models = [ExtendedPayloadOracle(words, memory, args, result, case,
                                        self.connected).run()
                  for words in (self.retail, self.raw)]
        self.assertEqual(
            (public(models[0].memory), models[0].calls, models[0].r[2]),
            (public(models[1].memory), models[1].calls, models[1].r[2]))
        for model in models:
            self.assertEqual(public(model.memory), public(expected), case)
            self.assertIn((CREATE, creation), model.calls)
            self.assertEqual(sum(target == RNG for target, _ in model.calls), 1)
            self.assertEqual(sum(target == COPY for target, _ in model.calls),
                             bool(result))
        return models[0]

    def test_01_owner_image_registry_relocations_and_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_frame"],
             report["retail_frame"], report["natural_positional_differences"],
             report["guards"], report["relocations"], report["neighbors"]),
            (65, 0x80, 0x80, 19, 19, 3, 36))
        self.assertEqual(report["functions"], 6052)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"]["aligned_pointer_literals"],
                         ["0x234438"])
        self.assertEqual(report["registry"]["registry"], "D_8008F970[2]")
        self.assertEqual(report["game_data"]["bytes"], 189088)
        self.assertEqual(report["game_data"]["owner_count"], 720)
        self.assertTrue(report["game_data"]["exact"])
        _, functions, relocations = parse_object(self.values["qualified_owner"])
        info = functions[match.FUNCTION]
        bindings = {offset - info["value"]: rows
                    for offset, rows in relocations.items()
                    if info["value"] <= offset < info["value"] + info["size"]}
        self.assertEqual(bindings, match.RETAIL_BINDINGS)
        with (ROOT / match.GUARDS).open(newline="") as stream:
            rows = [row for row in csv.DictReader(stream)
                    if row["filename"] == match.FILENAME and
                    row["function"] == match.FUNCTION]
        expected = [match.complete_row(row) for row in match.PATCH_ROWS]
        self.assertEqual(rows, expected if report["source_installed"] else [])
        self.receipt["owner_image"] = dict(
            words=65, guards=19, relocations=3, neighbors=36,
            functions=6052, protected_game_data_bytes=189088)

    def test_02_guest_semantics_aliases_and_reachable_words(self):
        count = 0
        reached = set()
        for random, layout, destination, phase in itertools.product(
                RANDOMS, range(5), range(4), (0, 8)):
            model = self.compare(Case(random=random, layout=layout,
                                      destination=destination, phase=phase))
            reached.update(model.visits)
            count += 1
        for byte, mode, destination in itertools.product(
                range(256), range(2), (0, 1)):
            self.compare(Case(minimum=signed16(byte * 257),
                              range_minus_one=byte % 31,
                              route=byte, slot=255 - byte, mode=mode,
                              destination=destination,
                              scalar=PATTERNS[byte % len(PATTERNS)]))
            count += 1
        reachable = reached & set(range(match.ENTRY, match.ENTRY + match.SIZE, 4))
        self.assertEqual(len(reachable), 64)
        self.assertNotIn(match.ENTRY + 0xC4, reachable)
        self.receipt["guest"] = dict(
            cases=count, reachable_words=64,
            dead_zero_divisor_break_not_executed=True,
            all_route_bytes=True, stack_aliases=True,
            post_rng_owner_mutations=True, full_states_equal=True)

    def test_03_actual_callback_table_and_dispatch_window(self):
        image = (ROOT / match.ROM_IMAGE).read_bytes()
        table = struct.unpack_from(">4I", image, 0x234430)
        self.assertEqual(table, (0x151A91AC, 0x151A9634,
                                 match.ENTRY, 0x150B1EE0))
        window = list(struct.unpack_from(">10I", image, WINDOW_ROM))
        count = 0
        for phase in (0, 8):
            case = Case(phase=phase)
            memory, args, result = fixture(case)
            put(memory, OWNER + 0x4E, 2, 1)
            for index, entry in enumerate(table):
                put(memory, TABLE + index * 4, entry)
            put(memory, STACK + phase + 0x5C, args[2])
            for index, value in enumerate(PATTERNS[:3]):
                put(memory, STACK + phase + 0x64 + index * 4, value)
            models = []
            for words in (self.retail, self.raw):
                code = {match.ENTRY + index * 4: word
                        for index, word in enumerate(words)}
                callback_args = (OWNER, STACK + phase + 0x64, args[2], 0x98)
                model = ExtendedPayloadOracle(window, memory, callback_args,
                                              result, case, code, entry=WINDOW)
                model.code[END] = 0
                for register, value in ((16, OWNER + 0x28), (19, OWNER),
                                        (17, callback_args[1]), (22, TABLE),
                                        (30, 0xFFFFFFFF), (18, args[3])):
                    model.r[register] = model.before[register] = value
                model.code = WindowCode(model.code, model)
                with self.assertRaises(WindowBoundary):
                    model.run()
                calls = [(target, values) for target, values in model.calls
                         if target in table]
                self.assertEqual(calls, [(match.ENTRY, callback_args)])
                models.append(model)
            self.assertEqual(
                (public(models[0].memory), models[0].calls, models[0].r[2]),
                (public(models[1].memory), models[1].calls, models[1].r[2]))
            count += 1
        self.receipt["caller"] = dict(
            cases=count, table_slot=2, original_window_words=10,
            parent_C_still_uncredited=True)

    def test_04_native_profiles_and_effective_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:],
                       candidate.SELECTED_MATCH, optimization, 0)
        variants = controls()
        for label, body in variants.items():
            run_native("control-" + label, body, "-O2", 1)
        self.receipt["native"] = dict(
            profiles=["O0", "O2", "O3"],
            cases_per_profile=8192, controls=sorted(variants),
            trap_UBSan=True, canonical_pointer_token_not_dereferenced=True)

    def test_05_direct_candidate_shape_and_retail_closure(self):
        result = candidate.compare("test-closure-owner",
                                   candidate.SELECTED_MATCH)
        self.assertEqual(
            (result["words"], result["frame"], result["differences"],
             result["raw_sha256"], result["retail_sha256"]),
            (65, 0x80, 19,
             "e330ef407ee9862846ad06613048cfb61c4e6c5fc95adea49ccce8d8e45cf280",
             match.RETAIL_SHA256))
        self.assertEqual(
            [row["offset"] for row in result["difference_rows"]],
            [int(row["offset"], 0) for row in match.PATCH_ROWS])
        old, _, _ = load_elf_functions(
            str(self.values["predecessor_elf"]), "mips-linux-gnu-objdump")
        new, _, _ = load_elf_functions(
            str(self.values["qualified_elf"]), "mips-linux-gnu-objdump")
        self.assertNotEqual(old[match.FUNCTION], self.retail)
        self.assertEqual(new[match.FUNCTION], self.retail)
        self.receipt["closure"] = dict(
            natural_differences=19,
            retail_sha256=result["retail_sha256"],
            changed_bodies=self.report["changed_bodies"])


if __name__ == "__main__":
    unittest.main()
