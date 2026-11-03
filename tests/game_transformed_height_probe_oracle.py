"""Semantic oracle for func_150CB0E0's transformed height probe."""

from dataclasses import dataclass
import itertools
from pathlib import Path
import struct
import subprocess

from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_actor_height_position_oracle import HeightOracle
from tools.tests.game_actor_height_position_oracle import Case as HeightCase
from tools.tests.game_actor_height_position_oracle import public
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path.cwd()
OUTPUT = ROOT / "conker/build/game-transformed-height-probe-150CB0E0-match"
FUNCTION = "func_150CB0E0"
ENTRY = 0x150CB0E0
ROM = 0xF8590
WORDS = 64
ACTOR = 0x20000
POSITION = 0x30000
RESULT = 0x34000
POINT_RIGHT = 0x800A05E0
POINT_LEFT = 0x800A05EC
POINT_RIGHT_NAME = "D_800A05E0"
POINT_LEFT_NAME = "D_800A05EC"
MODE_ONE_OFFSET = 0xA00
MODE_TWO_OFFSET = 0xBC0
OWNER_OBJECT = "generated_F8590.c.o"
TRANSFORM = 0x15143134
INITIALIZE = 0x1504715C
QUERY = 0x15046C80
SYMBOLS = {
    "D_800A05E0": POINT_RIGHT,
    "D_800A05EC": POINT_LEFT,
    "func_15143134": TRANSFORM,
    "func_1504715C": INITIALIZE,
    "func_15046C80": QUERY,
}
VALUES = (
    0x00000000, 0x80000000, 0x3F800000, 0xBF800000,
    0x42C80000, 0xC2C80000, 0x41200000, 0xC1200000,
)


@dataclass(frozen=True)
class Case(HeightCase):
    """One ABI, alias, callback-mutation, and return-value case."""


def position(case):
    if case.position_override is not None:
        return case.position_override
    return (
        POSITION, ACTOR + 0x14, ACTOR + 0x18,
        ACTOR + 0x180, ACTOR + 0x1D4, ACTOR + 0x1C,
    )[case.position_layout]


def result(case):
    if not case.query:
        return 0
    if case.result_override is not None:
        return case.result_override
    return (RESULT, position(case), ACTOR + 0x14, ACTOR + 0x1D4)[
        case.result_layout
    ]


def fixture(case):
    memory = {STACK + i: (i * 17 + 0xA5) & 0xFF
              for i in range(-2048, 2048)}
    for base, size in ((ACTOR, 0x900), (POSITION, 128), (RESULT, 128)):
        memory.update({base + i: (i * 13 + case.pattern) & 0xFF
                       for i in range(-32, size)})
    for base in (POINT_RIGHT, POINT_LEFT):
        memory.update({base + i: (i * 11 + case.pattern) & 0xFF
                       for i in range(12)})
    put(memory, ACTOR + 0x1D4, 0x50000000)
    return memory


def transformed_values(case, point):
    shift = 0 if point == POINT_LEFT else 3
    return tuple(VALUES[(case.pattern + shift + i) % len(VALUES)]
                 for i in range(3))


def transform_effect(memory, case, output, point):
    for index, value in enumerate(transformed_values(case, point)):
        put(memory, output + index * 4, value)


def initialize_effect(memory, case, target, output):
    for index in range(36):
        memory[target + index] = (index * 7 + case.mode) & 0xFF
    put(memory, target, 0x43960000)
    if case.mode & 1:
        put(memory, output + 4, 0x442F0000)


def query_effect(memory, case, target, output):
    memory[target + 28] = 0xD7
    if case.mode & 2:
        put(memory, output, 0xC3480000)


def visible(memory, case):
    result_memory = public(memory)
    for base, size in ((position(case), 12), (result(case), 36)):
        if base:
            result_memory.update({base + i: memory[base + i]
                                  for i in range(size)})
    return result_memory


def reference(initial, case, symbols=None):
    symbols = SYMBOLS if symbols is None else symbols
    memory = dict(initial)
    output = position(case)
    target = result(case)
    calls = []
    packets = []
    mode = case.fourth & 0xFF
    if mode not in (1, 2):
        return memory, calls, packets, 0
    point = symbols[POINT_LEFT_NAME] if mode == 1 else symbols[POINT_RIGHT_NAME]
    offset = MODE_ONE_OFFSET if mode == 1 else MODE_TWO_OFFSET
    matrix = read(memory, ACTOR + 0x1D4) + offset
    calls.append((symbols["func_15143134"], (point, output, matrix)))
    transform_effect(memory, case, output, point)
    if not target:
        return memory, calls, packets, 1
    start = (STACK + case.phase if case.child_home is None
             else case.child_home) - 12
    ray = (
        read(memory, output),
        bits(floating(read(memory, output + 4)) + 100.0),
        read(memory, output + 8),
    )
    for index, value in enumerate(ray):
        put(memory, start + index * 4, value)
    calls.append((symbols["func_1504715C"], (target, ACTOR)))
    initialize_effect(memory, case, target, output)
    lower = bits(floating(read(memory, output + 4)) - 500.0)
    calls.append((symbols["func_15046C80"], (start, 0, lower, target)))
    packets.append(ray)
    query_effect(memory, case, target, output)
    return memory, calls, packets, case.returned & 0xFFFFFFFF


class Oracle(HeightOracle):
    def __init__(self, words, memory, case, symbols=None, entry=None):
        symbols = SYMBOLS if symbols is None else symbols
        entry = ENTRY if entry is None else entry
        self.callback_symbols = symbols
        super().__init__(
            words, memory, case, entry=entry,
            initialize=symbols["func_1504715C"],
            query=symbols["func_15046C80"],
            arguments=(position(case), ACTOR, result(case), case.fourth),
        )

    def record_call(self, target):
        if target == self.callback_symbols["func_15143134"]:
            arguments = tuple(self.arguments(3))
            self.calls.append((target, arguments))
            self.events.append(("CALL", target, arguments))
        else:
            super().record_call(target)

    def hook(self, target):
        case = self.case
        arguments = self.calls[-1][1]
        output = position(case)
        if target == self.callback_symbols["func_15143134"]:
            transform_effect(self.memory, case, arguments[1], arguments[0])
            value = 0x12345678
        elif target == self.initialize:
            initialize_effect(self.memory, case, arguments[0], output)
            value = 0x76543210
        else:
            assert target == self.query
            query_effect(self.memory, case, arguments[3], output)
            value = case.returned & 0xFFFFFFFF
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.r[2] = value
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011


def linked(obj, label, entry=None, symbols=None):
    entry = ENTRY if entry is None else entry
    symbols = SYMBOLS if symbols is None else symbols
    text, functions, relocations = parse_object(obj)
    function = functions[FUNCTION]
    assembly, unknown = emit_function(
        text, function, relocations, FUNCTION, symbols)
    assert not unknown, unknown
    path = OUTPUT / label
    path.with_suffix(".s").write_text(assembly)
    assignments = "\n".join(
        "%s = 0x%X;" % (name, value) for name, value in symbols.items())
    path.with_suffix(".ld").write_text(
        "SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n%s\n"
        % (entry, assignments))
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-march=vr4300", "-o",
        str(path.with_suffix(".o")), str(path.with_suffix(".s")),
    ], check=True, capture_output=True)
    subprocess.run([
        "mips-linux-gnu-ld", "-m", "elf32btsmip", "-T",
        str(path.with_suffix(".ld")), "-e", FUNCTION, "-o",
        str(path.with_suffix(".elf")), str(path.with_suffix(".o")),
    ], check=True, capture_output=True)
    data = sections(path.with_suffix(".elf"))[".text"][1]
    return list(struct.unpack(">%dI" % WORDS, data[:WORDS * 4]))


def programs():
    retail = (ROOT / "conker/conker.us.bin").read_bytes()[ROM:ROM + WORDS * 4]
    result = [list(struct.unpack(">%dI" % WORDS, retail))]
    result.append(linked(
        OUTPUT / "qualified-compact.o", "semantic-compact",
        entry=ENTRY, symbols=SYMBOLS))
    result.append(linked(
        OUTPUT / ("qualified-owner/" + OWNER_OBJECT), "semantic-owner",
        entry=ENTRY, symbols=SYMBOLS))
    assert result[0] == result[1] == result[2]
    return result


def cases():
    for pattern, query, layout, result_layout, mutation, action, phase in \
            itertools.product(
                range(8), (False, True), range(6), range(4), range(4),
                (0, 1, 2, 3, 255), (0, 8)):
        yield Case(
            pattern=pattern, query=query, position_layout=layout,
            result_layout=result_layout, mode=mutation,
            returned=(0, 1, 0xFFFFFFFF, 0x80000000)[mutation],
            fourth=0xAB000000 | action, phase=phase)


def state(machine):
    return (
        machine.r, machine.f, machine.memory, machine.calls, machine.events,
        machine.trace, machine.hi, machine.lo, machine.packets,
    )


def verify(machine, initial, case, symbols=None):
    symbols = SYMBOLS if symbols is None else symbols
    wanted, calls, packets, value = reference(initial, case, symbols)
    assert (
        visible(machine.memory, case), machine.calls,
        machine.packets, machine.r[2]
    ) == (visible(wanted, case), calls, packets, value), case
    assert machine.r[29] == machine.before[29]
    assert machine.r[16:24] == machine.before[16:24]
    assert machine.r[28] == machine.before[28]
    assert machine.f[20:] == machine.saved_f


def run_suite():
    bodies = programs()
    count = 0
    visited = set()
    for case in cases():
        initial = fixture(case)
        machines = []
        for words in bodies:
            machine = Oracle(words, initial, case).run()
            verify(machine, initial, case)
            machines.append(machine)
        assert state(machines[0]) == state(machines[1]) == state(machines[2])
        visited.update(machines[0].visits)
        count += 1
    assert set(range(ENTRY, ENTRY + WORDS * 4, 4)) - visited == {ENTRY + 0x98}

    prefixes = 0
    delay_cuts = 0
    for case in (
            Case(fourth=0), Case(fourth=1, query=False), Case(fourth=1),
            Case(pattern=7, fourth=2, mode=3),
            Case(fourth=1, position_layout=4, result_layout=1),
            Case(fourth=2, phase=8)):
        initial = fixture(case)
        full = Oracle(bodies[0], initial, case).run()
        for cut in range(full.root_accesses):
            machines = []
            for words in bodies:
                machine = Oracle(words, initial, case)
                machine.root_fault = cut
                try:
                    machine.run()
                except AccessBoundary:
                    pass
                else:
                    raise AssertionError(("missing access prefix", cut, case))
                assert machine.root_accesses == cut
                machines.append(machine)
            assert state(machines[0]) == state(machines[1]) == state(machines[2])
            assert ((machines[0].current_pc, machines[0].delay_of) ==
                    (machines[1].current_pc, machines[1].delay_of))
            prefixes += 1
            delay_cuts += machines[0].delay_of is not None

    return {
        "cases": count,
        "executions": count * 3,
        "body_words": WORDS,
        "covered_reachable_words": WORDS - 1,
        "unreachable_duplicate_word": hex(ENTRY + 0x98),
        "frame": 56,
        "guards": 0,
        "full_retail_compact_owner_state_equal": True,
        "all_four_argument_ABI_and_three_helpers_checked": True,
        "mode_byte_domain_checked": True,
        "position_layouts": 6,
        "result_layouts": 4,
        "access_prefix_pairs": prefixes,
        "delay_slot_cuts": delay_cuts,
        "initializer_mutation_and_live_lower_read_checked": True,
    }


def native_harness(selected):
    body = selected
    mutants = {
        "gate": body.replace("mode != 1 && mode != 2", "mode != 1 && mode != 3"),
        "point1": body.replace(
            "point = %s;" % POINT_LEFT_NAME,
            "point = %s;" % POINT_RIGHT_NAME, 1),
        "point2": body.replace(
            "point = %s;" % POINT_RIGHT_NAME,
            "point = %s;" % POINT_LEFT_NAME, 1),
        "matrix1": body.replace(
            "+ 0x%X;" % MODE_ONE_OFFSET,
            "+ 0x%X;" % (MODE_ONE_OFFSET + 4), 1),
        "matrix2": body.replace(
            "+ 0x%X;" % MODE_TWO_OFFSET,
            "+ 0x%X;" % (MODE_TWO_OFFSET + 4), 1),
        "null_result": body.replace("return 1;", "return 0;", 1),
        "upper": body.replace("position[1] + 100.0f", "position[1] + 99.0f"),
        "lower": body.replace("position[1] - 500.0f", "position[1] - 499.0f"),
        "skip_initializer": body.replace(
            "    func_1504715C(result, (HeightActor71820 *)actor);\n", ""),
        "selector": body.replace("func_15046C80(start, 0,", "func_15046C80(start, 1,"),
        "return_value": body.replace(
            "return func_15046C80(start, 0, position[1] - 500.0f, result);",
            "func_15046C80(start, 0, position[1] - 500.0f, result);\n"
            "    return 1;"),
        "stale_height": body.replace(
            "    f32 start[3];", "    f32 start[3];\n    f32 lower;").replace(
            "    func_1504715C(result, (HeightActor71820 *)actor);",
            "    lower = position[1] - 500.0f;\n"
            "    func_1504715C(result, (HeightActor71820 *)actor);").replace(
            "return func_15046C80(start, 0, position[1] - 500.0f, result);",
            "return func_15046C80(start, 0, lower, result);"),
    }
    assert all(mutant != body for mutant in mutants.values())
    preamble = r'''
typedef signed int s32;
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
typedef float f32;
typedef struct HeightResult71820 HeightResult71820;
typedef struct HeightActor71820 HeightActor71820;
#define NULL ((void *)0)
extern f32 D_800A05E0[];
extern f32 D_800A05EC[];
void func_15143134(f32 *, f32 *, u8 *);
void func_1504715C(HeightResult71820 *, HeightActor71820 *);
s32 func_15046C80(f32 *, u16, f32, HeightResult71820 *);
'''
    text = preamble + "\n".join(
        mutant.replace(FUNCTION, "test_" + name)
        for name, mutant in {"selected": body, **mutants}.items())
    text += r'''
typedef char Pointer32[sizeof(void *) == 4 ? 1 : -1];
f32 D_800A05E0[3], D_800A05EC[3];
static u8 *actor, *out, *result;
static u8 expected[0x1000];
static u32 pattern, queryEnabled, layout, resultLayout, mutation;
static u32 returned, action, ncalls, error, cases;
static u32 expectedRay[3], expectedLower, expectedMatrix;
static const u32 values[] = {
    0, 0x80000000u, 0x3F800000u, 0xBF800000u,
    0x42C80000u, 0xC2C80000u, 0x41200000u, 0xC1200000u
};
static const s32 returns[] = {0, 1, -1, (-2147483647 - 1)};
static const u8 actions[] = {0, 1, 2, 3, 255};
static f32 fp(u32 value) { union { u32 w; f32 f; } x; x.w = value; return x.f; }
static u32 bits(f32 value) { union { u32 w; f32 f; } x; x.f = value; return x.w; }
static void putword(u8 *p, u32 value) {
    u8 *q = (u8 *)&value; u32 i; for (i = 0; i < 4; i++) p[i] = q[i];
}
static u32 word(const u8 *p) {
    u32 value; u8 *q = (u8 *)&value; u32 i;
    for (i = 0; i < 4; i++) q[i] = p[i]; return value;
}
__attribute__((noinline,noclone))
void func_15143134(f32 *point, f32 *position, u8 *matrix) {
    u32 i, shift = action == 1 ? 0 : 3;
    f32 *wanted = action == 1 ? D_800A05EC : D_800A05E0;
    u32 offset = action == 1 ? 0xA00u : 0xBC0u;
    if (point != wanted || (u8 *)position != out ||
            (u32)matrix != expectedMatrix + offset || ncalls++ != 0) error = 1;
    for (i = 0; i < 3; i++) putword(out + 4 * i, values[(pattern + shift + i) % 8]);
}
__attribute__((noinline,noclone))
void func_1504715C(HeightResult71820 *target, HeightActor71820 *owner) {
    u32 i;
    if ((u8 *)target != result || (u8 *)owner != actor || ncalls++ != 1) error = 1;
    for (i = 0; i < 36; i++) ((u8 *)target)[i] = (u8)(i * 7 + mutation);
    putword((u8 *)target, 0x43960000u);
    if (mutation & 1) putword(out + 4, 0x442F0000u);
}
__attribute__((noinline,noclone))
s32 func_15046C80(f32 *ray, u16 selector, f32 lower,
                  HeightResult71820 *target) {
    u32 i;
    if (selector || (u8 *)target != result || bits(lower) != expectedLower ||
            ncalls++ != 2) error = 1;
    for (i = 0; i < 3; i++) if (word((u8 *)ray + 4 * i) != expectedRay[i]) error = 1;
    ((u8 *)target)[28] = 0xD7;
    if (mutation & 2) putword(out, 0xC3480000u);
    return returns[returned];
}
'''
    text += "\n".join(
        "s32 test_%s(f32 *, u8 *, HeightResult71820 *, u8);" % name
        for name in ("selected", *mutants))
    text += r'''
typedef s32 (*Fn)(f32 *, u8 *, HeightResult71820 *, u8);
static int one(Fn function) {
    u32 i, p, d, shift, answer, enabled = action == 1 || action == 2;
    for (i = 0; i < 0x1000; i++) actor[i] = (u8)(i * 13 + pattern);
    putword(actor + 0x1D4, 0x50000000u);
    out = layout == 0 ? actor + 0x600 : layout == 1 ? actor + 0x14 :
          layout == 2 ? actor + 0x18 : actor + 0x1D4;
    result = !queryEnabled ? 0 : resultLayout == 0 ? actor + 0x700 :
             resultLayout == 1 ? out : actor + 0x14;
    for (i = 0; i < 0x1000; i++) expected[i] = actor[i];
    p = (u32)(out - actor); d = result ? (u32)(result - actor) : 0;
    expectedMatrix = word(expected + 0x1D4);
    if (enabled) {
        shift = action == 1 ? 0 : 3;
        for (i = 0; i < 3; i++) putword(expected + p + 4 * i,
                                        values[(pattern + shift + i) % 8]);
        if (queryEnabled) {
            expectedRay[0] = word(expected + p);
            expectedRay[1] = bits(fp(word(expected + p + 4)) + 100.0f);
            expectedRay[2] = word(expected + p + 8);
            for (i = 0; i < 36; i++) expected[d + i] = (u8)(i * 7 + mutation);
            putword(expected + d, 0x43960000u);
            if (mutation & 1) putword(expected + p + 4, 0x442F0000u);
            expectedLower = bits(fp(word(expected + p + 4)) - 500.0f);
            expected[d + 28] = 0xD7;
            if (mutation & 2) putword(expected + p, 0xC3480000u);
        }
    }
    ncalls = error = 0;
    answer = (u32)function((f32 *)out, actor, (HeightResult71820 *)result,
                           (u8)action);
    cases++;
    if (answer != (enabled ? (queryEnabled ? (u32)returns[returned] : 1u) : 0u) ||
            error || ncalls != (enabled ? (queryEnabled ? 3u : 1u) : 0u)) return 1;
    for (i = 0; i < 0x1000; i++) if (actor[i] != expected[i]) return 2;
    return 0;
}
static int corpus(Fn function) {
    u32 index; int code;
    for (pattern = 0; pattern < 8; pattern++)
    for (queryEnabled = 0; queryEnabled < 2; queryEnabled++)
    for (layout = 0; layout < 4; layout++)
    for (resultLayout = 0; resultLayout < 3; resultLayout++)
    for (mutation = 0; mutation < 4; mutation++)
    for (index = 0; index < 5; index++)
    for (returned = 0; returned < 4; returned++) {
        action = actions[index]; code = one(function); if (code) return code;
    }
    return 0;
}
static int run(void) {
    u32 address, requested, index;
    Fn bad[] = {'''
    text += ",".join("test_" + name for name in mutants)
    text += r'''};
    __asm__ volatile("int $0x80" : "=a"(address) : "a"(45), "b"(0) : "memory");
    requested = (address + 15u) & ~15u;
    __asm__ volatile("int $0x80" : "=a"(address) : "a"(45),
                     "b"(requested + 0x1000) : "memory");
    if (address < requested + 0x1000) return 90;
    actor = (u8 *)requested;
    if (corpus(test_selected)) return 91;
    if (cases != 15360) return 92;
    for (index = 0; index < sizeof(bad) / sizeof(bad[0]); index++)
        if (!corpus(bad[index])) return 93;
    return 0;
}
'''
    text += START.replace(
        "void _start(void)",
        "__attribute__((force_align_arg_pointer)) void _start(void)")
    text = text.replace("D_800A05E0", POINT_RIGHT_NAME)
    text = text.replace("D_800A05EC", POINT_LEFT_NAME)
    text = text.replace("0xA00", "0x%X" % MODE_ONE_OFFSET)
    text = text.replace("0xBC0", "0x%X" % MODE_TWO_OFFSET)
    return text, len(mutants)


def run_native(selected):
    text, controls = native_harness(selected)
    path = OUTPUT / "native.c"
    path.write_text(text)
    reports = {}
    for optimization in ("-O0", "-O2", "-O3"):
        executable = OUTPUT / ("native" + optimization)
        build = subprocess.run(
            native_command(optimization) + [
                "-mstackrealign", str(path), "-o", str(executable)],
            cwd=ROOT, capture_output=True, text=True)
        assert build.returncode == 0 and not build.stdout and not build.stderr, (
            build.stdout + build.stderr)
        run = subprocess.run([str(executable)], capture_output=True)
        assert run.returncode == 0, (optimization, run.returncode, run.stderr)
        reports[optimization] = {
            "exit": 0, "cases": 15360, "negative_controls": controls,
            "UBSan": True,
        }
    return {
        "profiles": reports,
        "cases": 15360,
        "negative_controls": controls,
        "signature": "s32(f32*,u8*,HeightResult71820*,u8)",
        "position_layouts": 4,
        "result_layouts": 3,
        "finite_float_payloads_and_aliases_checked": True,
        "initializer_mutation_and_live_lower_read_checked": True,
        "untyped_backing": True,
    }
