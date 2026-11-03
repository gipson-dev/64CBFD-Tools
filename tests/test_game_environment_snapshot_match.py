"""Semantic, caller, and strict-image gates for func_151732E0."""

import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_environment_snapshot_candidates as candidate
from tools.experiments import game_environment_snapshot_match as match
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK, put, read


ROOT = Path(__file__).resolve().parents[2]
STATE = 0x220000
STATE_POINTER = 0x800B0DF0
SNAPSHOT = 0x8008CC70
ACTIVE = 0x800DD2E0
PROVIDER = 0x151733E4


def signed(value, width=32):
    mask = (1 << width) - 1
    return ((value & mask) ^ (1 << (width - 1))) - (1 << (width - 1))


def cases():
    ranges = (
        (0, 0, 0, 0),
        (-32768, 7, 32767, 7),
        (32767, -1, -32768, 1),
        (-1, -32768, 1, 32767),
    )
    overrides = (-1, 0, 1, 127, -128, 63, -2)
    contexts = (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
    for seed in range(140):
        first, second, third, fourth = ranges[seed % len(ranges)]
        yield {
            "seed": seed,
            "first": first,
            "second": second,
            "third": third,
            "fourth": fourth,
            "red": (seed * 17 + 3) & 0xFF,
            "green": (seed * 29 + 5) & 0xFF,
            "blue": (seed * 43 + 7) & 0xFF,
            "alpha": (seed * 61 + 11) & 0xFF,
            "selected": (seed * 0x101 + 0x8000) & 0xFFFF,
            "fallback": (seed * 0x307 + 0xFFFF) & 0xFFFF,
            "override": overrides[(seed // len(ranges)) % len(overrides)],
            "context": contexts[(seed // (len(ranges) * len(overrides))) % len(contexts)],
        }


def fixture(case):
    memory = {STACK + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x300, 0x100)}
    memory.update({STATE + index: (index * 13 + case["seed"] * 19 + 0x59) & 0xFF
                   for index in range(0x50)})
    memory.update({SNAPSHOT + index: 0xA5 for index in range(0x20)})
    memory.update({ACTIVE + index: 0xA5 for index in range(4)})
    memory.update({STATE_POINTER + index: 0xA5 for index in range(4)})
    put(memory, STATE_POINTER, STATE)
    put(memory, STATE + 0x00, case["fallback"], 2)
    put(memory, STATE + 0x02, case["selected"], 2)
    put(memory, STATE + 0x3A, case["first"], 2)
    put(memory, STATE + 0x3C, case["second"], 2)
    put(memory, STATE + 0x3E, case["third"], 2)
    put(memory, STATE + 0x40, case["fourth"], 2)
    for offset, name in ((0x42, "red"), (0x43, "green"),
                         (0x44, "blue"), (0x45, "alpha")):
        put(memory, STATE + offset, case[name], 1)
    put(memory, STATE + 0x46, case["override"], 1)
    return memory


def reference(initial, case):
    memory = dict(initial)
    second = signed(read(memory, STATE + 0x3C, 2), 16)
    fourth = signed(read(memory, STATE + 0x40, 2), 16)
    if fourth == second and second == 0:
        put(memory, STATE + 0x40, 100, 2)
    for destination, source, size in (
            (0x00, 0x42, 1), (0x01, 0x43, 1),
            (0x02, 0x44, 1), (0x03, 0x45, 1),
            (0x04, 0x3A, 2), (0x06, 0x3C, 2),
            (0x08, 0x3E, 2), (0x0A, 0x40, 2),
            (0x0C, 0x02, 2), (0x0E, 0x00, 2)):
        put(memory, SNAPSHOT + destination, read(memory, STATE + source, size), size)
    override = signed(read(memory, STATE + 0x46, 1), 8)
    selected = override if override != -1 else 0
    put(memory, ACTIVE, 1 if override != -1 else 0, 1)
    call = (PROVIDER, (selected & 0xFFFFFFFF, selected & 0xFFFFFFFF,
                       case["context"] & 0xFFFFFFFF, 0, 0xFFFFFFFF))
    return memory, [call]


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x300 <= address < STACK + 0x100}


class EnvironmentSnapshotOracle(TimingOracle):
    def __init__(self, words, memory, case, phase=0):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(case["context"],))

    def execute(self, word):
        if word >> 26 == 32:  # lb
            base = self.r[word >> 21 & 31]
            target = word >> 16 & 31
            self.r[target] = signed(self.get(
                (base + signed(word, 16)) & 0xFFFFFFFF, 1), 8) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)

    def record_call(self, target):
        self.assert_provider(target)
        args = tuple(self.arguments(5))
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    @staticmethod
    def assert_provider(target):
        if target != PROVIDER:
            raise AssertionError("Unexpected environment provider %08X" % target)

    def hook(self, target):
        self.assert_provider(target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.lo, self.hi = 0xA5000010, 0xA5000011


def controls():
    body = candidate.SELECTED
    zero_repair = (
        "    if ((D_800B0DF0->fourthRange == secondRange) && (secondRange == 0)) {\n"
        "        D_800B0DF0->fourthRange = 100;\n"
        "    }\n")
    dispatch = (
        "    if (D_800B0DF0->value != -1) {\n"
        "        D_800DD2E0 = 1;\n"
        "        selection = D_800B0DF0->value;\n"
        "        func_151733E4(selection, selection, context, 0, -1);\n"
        "        return;\n"
        "    }\n"
        "    D_800DD2E0 = 0;\n"
        "    func_151733E4(0, 0, context, 0, -1);\n")
    variants = {
        "missing-zero-repair": body.replace(
            "D_800B0DF0->fourthRange = 100",
            "D_800B0DF0->fourthRange = secondRange", 1),
        "wrong-repair-value": body.replace("fourthRange = 100", "fourthRange = 99", 1),
        "wrong-second-snapshot": body.replace(
            "D_8008CC70.secondRange = D_800B0DF0->secondRange;",
            "D_8008CC70.secondRange = D_800B0DF0->firstRange;", 1),
        "swapped-output-values": body.replace(
            "D_8008CC70.selectedValue = D_800B0DF0->selectedValue;\n"
            "    D_8008CC70.fallbackValue = D_800B0DF0->fallbackValue;",
            "D_8008CC70.selectedValue = D_800B0DF0->fallbackValue;\n"
            "    D_8008CC70.fallbackValue = D_800B0DF0->selectedValue;", 1),
        "zero-sentinel": body.replace("value != -1", "value != 0", 1),
        "inverted-active-flag": body.replace("D_800DD2E0 = 1", "D_800DD2E0 = 0", 1),
        "missing-second-selection": body.replace(
            "func_151733E4(selection, selection", "func_151733E4(selection, 0", 1),
        "always-default-provider": body.replace(
            dispatch,
            "    selection = 0;\n"
            "    D_800DD2E0 = 0;\n"
            "    func_151733E4(selection, selection, context, 0, -1);\n", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("An environment snapshot semantic control did not alter the source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef signed char s8;
typedef signed short s16;
typedef unsigned short u16;
typedef signed int s32;
typedef unsigned int u32;
''' + candidate.INSTALL_TYPES + r'''
static Generated1A0790State state;
Generated1A0790State *D_800B0DF0 = &state;
EnvironmentSnapshot151732E0 D_8008CC70;
s8 D_800DD2E0;
static s32 calls, captured[5];
s32 func_151733E4(s32 a, s32 b, s32 c, s32 d, s32 e) {
    calls++; captured[0] = a; captured[1] = b; captured[2] = c;
    captured[3] = d; captured[4] = e; return 0x13579BDF;
}
''' + body + r'''
static int one(u32 seed) {
    static const s16 ranges[4][4] = {
        {0,0,0,0}, {-32768,7,32767,7}, {32767,-1,-32768,1}, {-1,-32768,1,32767}
    };
    static const s8 overrides[7] = {-1,0,1,127,-128,63,-2};
    static const u32 contexts[5] = {0,1,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};
    EnvironmentSnapshot151732E0 expected;
    u8 *source = (u8 *)&state, *actual = (u8 *)&D_8008CC70, *wanted = (u8 *)&expected;
    u32 i, row = seed % 4u, context = contexts[(seed / 28u) % 5u];
    for (i = 0; i < sizeof(state); i++) source[i] = (u8)(i * 13u + seed * 19u + 0x59u);
    for (i = 0; i < sizeof(D_8008CC70); i++) actual[i] = 0xA5;
    state.fallbackValue = (u16)(seed * 0x307u + 0xFFFFu);
    state.selectedValue = (u16)(seed * 0x101u + 0x8000u);
    state.firstRange = ranges[row][0]; state.secondRange = ranges[row][1];
    state.thirdRange = ranges[row][2]; state.fourthRange = ranges[row][3];
    state.red = (u8)(seed * 17u + 3u); state.green = (u8)(seed * 29u + 5u);
    state.blue = (u8)(seed * 43u + 7u); state.alpha = (u8)(seed * 61u + 11u);
    state.value = overrides[(seed / 4u) % 7u];
    if (state.fourthRange == state.secondRange && state.secondRange == 0) state.fourthRange = 100;
    expected.red = state.red; expected.green = state.green;
    expected.blue = state.blue; expected.alpha = state.alpha;
    expected.firstRange = state.firstRange; expected.secondRange = state.secondRange;
    expected.thirdRange = state.thirdRange; expected.fourthRange = state.fourthRange;
    expected.selectedValue = state.selectedValue; expected.fallbackValue = state.fallbackValue;
    /* Restore the input repaired by the reference before running the candidate. */
    state.fourthRange = ranges[row][3];
    calls = 0; D_800DD2E0 = (s8)0xA5;
    for (i = 0; i < 5; i++) captured[i] = (s32)0xA5A5A5A5u;
    func_151732E0((s32)context);
    for (i = 0; i < sizeof(expected); i++) if (actual[i] != wanted[i]) return 1;
    if (state.fourthRange != expected.fourthRange || calls != 1) return 1;
    if (state.value == -1) {
        if (D_800DD2E0 != 0 || captured[0] != 0 || captured[1] != 0) return 1;
    } else {
        if (D_800DD2E0 != 1 || captured[0] != state.value || captured[1] != state.value) return 1;
    }
    if ((u32)captured[2] != context || captured[3] != 0 || captured[4] != -1) return 1;
    return 0;
}
int main(void) { u32 seed; for (seed = 0; seed < 560u; seed++) if (one(seed)) return 1; return 0; }
'''


def run_native(label, body, optimization, expected):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / (label + ".exe")
    source.write_text(native_source(body))
    command = [
        "gcc", optimization, "-std=c99", "-fno-strict-aliasing",
        "-ffp-contract=off", "-fsanitize=undefined",
        "-fsanitize-undefined-trap-on-error", "-Wall", "-Wextra", "-Werror",
        str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if executed.returncode != expected:
        raise AssertionError((label, executed.returncode, executed.stderr))


class EnvironmentSnapshotMatchTest(unittest.TestCase):
    def test_guest_semantics_cover_every_word(self):
        data = (ROOT / match.ROM_IMAGE).read_bytes()[match.ROM:match.ROM + match.SIZE]
        words = list(struct.unpack(">%dI" % match.WORDS, data))
        seen = set()
        count = 0
        for case, phase in itertools.product(cases(), (0, 8)):
            initial = fixture(case)
            wanted, calls = reference(initial, case)
            model = EnvironmentSnapshotOracle(words, initial, case, phase).run()
            self.assertEqual(public(model.memory), public(wanted))
            self.assertEqual(model.calls, calls)
            seen.update(pc - match.ENTRY for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            count += 1
        self.assertEqual(count, 280)
        self.assertEqual(seen, set(range(0, match.SIZE, 4)))

    def test_native_profiles_and_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED,
                       optimization, 0)
        for label, body in controls().items():
            run_native("control-" + label, body, "-O2", 1)

    def test_guarded_owner_callers_and_full_image(self):
        candidate_report = candidate.compare("test-guarded-owner", candidate.SELECTED)
        self.assertEqual(candidate_report["words"], match.WORDS)
        self.assertEqual(candidate_report["differences"], 1)
        self.assertEqual([row["offset"] for row in candidate_report["difference_rows"]],
                         [0x28])
        registry = match.registry_evidence(ROOT)
        self.assertEqual(registry["direct_jal_calls"], ["0x352a4", "0x3b9b4"])
        self.assertEqual(registry["aligned_pointer_literals"], [])
        result = match.prepare(ROOT)
        report = result["report"]
        installed = candidate.SELECTED in (ROOT / candidate.SOURCE).read_text()
        self.assertEqual(report["source_installed"], installed)
        self.assertEqual(report["guards"], 1)
        self.assertEqual(report["natural_positional_differences"], 1)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertTrue(report["game_data"]["exact"])


if __name__ == "__main__":
    unittest.main()
