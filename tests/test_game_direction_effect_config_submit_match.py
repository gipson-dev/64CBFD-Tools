"""ABI, semantics, owner and image gates for func_151C61A0."""

from dataclasses import dataclass
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_direction_effect_config_submit_match as match
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
FACTORY = 0x15154684
GLOBALS = (0x800AAAF4, 0x800AAAF8, 0x800AAAFC)


@dataclass(frozen=True)
class Case:
    provider: int
    request: int
    channel: int
    owner: int
    globals: tuple
    phase: int = 0


def fixture(case):
    memory = {STACK + case.phase + index: (index * 29 + 0xA7) & 0xFF
              for index in range(-0x180, 0x100)}
    for address, value in zip(GLOBALS, case.globals):
        put(memory, address, value)
    return memory


def expected_descriptor(before, address, case):
    data = bytearray(before[address + index] for index in range(60))
    struct.pack_into(">hhIhhhhIIIII", data, 0,
                     10, 4, case.provider, 0, -24, 255, 25,
                     bits(5.0), bits(7.0), *case.globals)
    struct.pack_into(">BBhh", data, 0x24, 190, 65, 200, 150)
    struct.pack_into(">III", data, 0x2C,
                     bits(96.0), bits(109.0), bits(1.0))
    struct.pack_into(">I", data, 0x38, case.request)
    return bytes(data)


class ConfigOracle(AreaOracle):
    def __init__(self, words, memory, case):
        super().__init__(words, memory,
                         (case.provider, case.request, case.channel, case.owner),
                         phase=case.phase, entry=match.ENTRY)

    def record_call(self, target):
        if target != FACTORY:
            raise AssertionError("Unexpected direction-effect call %08X" % target)
        pointer = self.r[4]
        payload = bytes(self.memory[pointer + index] for index in range(60))
        self.calls.append((target, pointer, payload, self.r[5], self.r[6]))

    def hook(self, target):
        if target != FACTORY:
            raise AssertionError("Unexpected direction-effect hook %08X" % target)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]


def native_harness(body):
    return r'''
typedef unsigned char u8;
typedef short s16;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
''' + match.DECLARATIONS + body + r'''
f32 D_800AAAF4, D_800AAAF8, D_800AAAFC;
static void *wanted_provider;
static s32 wanted_request, wanted_owner;
static u32 wanted_channel, wanted_globals[3], calls, error;
static u32 word(f32 value) { union { f32 f; u32 u; } v; v.f = value; return v.u; }
static f32 real(u32 value) { union { f32 f; u32 u; } v; v.u = value; return v.f; }
__attribute__((noinline,noclone)) void func_15154684(
        DirectionEffectInput *p, s32 channel, s32 owner) {
    calls++;
    if (calls != 1 || p->countBase != 10 || p->countRange != 4 ||
            p->providerType != wanted_provider || p->reserved8 != 0 ||
            p->secondAngleBase != -24 || p->reservedC != 255 ||
            p->secondAngleRange != 25 || word(p->radiusBase) != 0x40A00000u ||
            word(p->radiusRange) != 0x40E00000u ||
            word(p->scaleBase) != wanted_globals[0] ||
            word(p->scaleRange) != wanted_globals[1] ||
            word(p->modeWord) != wanted_globals[2] || p->selectorBase != 190 ||
            p->selectorRange != 65 || p->durationBase != 200 ||
            p->durationRange != 150 || word(p->timeBase) != 0x42C00000u ||
            word(p->timeRange) != 0x42DA0000u ||
            word(p->opaqueChance) != 0x3F800000u ||
            p->requestValue != wanted_request || (u32)channel != wanted_channel ||
            owner != wanted_owner) error = 1;
}
static int run(void) {
    union { u32 align; u8 bytes[96]; } storage;
    u32 n;
    for (n = 0; n < 4096; n++) {
        wanted_provider = storage.bytes + (n & 31u);
        wanted_request = (s32)(0x81234567u ^ (n * 0x10203u));
        wanted_channel = (n * 37u + 19u) & 255u;
        wanted_owner = (s32)(0x76543210u ^ (n * 0x301u));
        wanted_globals[0] = 0x3E800000u ^ (n * 17u);
        wanted_globals[1] = 0xBF200000u ^ (n * 29u);
        wanted_globals[2] = 0x41200000u ^ (n * 43u);
        D_800AAAF4 = real(wanted_globals[0]);
        D_800AAAF8 = real(wanted_globals[1]);
        D_800AAAFC = real(wanted_globals[2]);
        calls = error = 0;
        func_151C61A0(wanted_provider, wanted_request, (u8)wanted_channel,
                      wanted_owner);
        if (calls != 1 || error) return 10;
    }
    return 0;
}
''' + START


def controls():
    selected = match.SELECTED
    return {
        "wrong_count": selected.replace("input.countBase = 10;", "input.countBase = 11;"),
        "wrong_provider": selected.replace("input.providerType = providerType;",
                                             "input.providerType = (void *)0;"),
        "wrong_reserved8": selected.replace("input.reserved8 = 0;", "input.reserved8 = 1;"),
        "wrong_angle": selected.replace("input.secondAngleBase = -24;",
                                          "input.secondAngleBase = -23;"),
        "wrong_reservedC": selected.replace("input.reservedC = 255;", "input.reservedC = 254;"),
        "wrong_radius": selected.replace("input.radiusBase = 5.0f;",
                                           "input.radiusBase = 6.0f;"),
        "wrong_global": selected.replace("input.scaleBase = D_800AAAF4;",
                                           "input.scaleBase = D_800AAAF8;"),
        "wrong_selector": selected.replace("input.selectorBase = 190;",
                                             "input.selectorBase = 191;"),
        "wrong_duration": selected.replace("input.durationBase = 200;",
                                             "input.durationBase = 201;"),
        "wrong_time": selected.replace("input.timeBase = 96.0f;",
                                         "input.timeBase = 95.0f;"),
        "wrong_opacity": selected.replace("input.opaqueChance = 1.0f;",
                                            "input.opaqueChance = 0.5f;"),
        "wrong_request": selected.replace("input.requestValue = requestValue;",
                                            "input.requestValue = requestValue + 1;"),
        "wrong_channel": selected.replace("&input, channel, owner",
                                            "&input, channel + 1, owner"),
        "wrong_owner": selected.replace("&input, channel, owner",
                                          "&input, channel, owner + 1"),
    }


class DirectionEffectConfigSubmitTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.out = ROOT / match.BUILD
        (cls.report, cls.before_owner, cls.after_owner,
         cls.before_elf, cls.after_elf) = match.prepare(ROOT)
        image = cls.after_elf.read_bytes()
        at = elf_slot_offset(image, match.ENTRY, match.SIZE)
        cls.words = struct.unpack_from(">%dI" % match.WORDS, image, at)
        cls.retail = struct.unpack_from(">%dI" % match.WORDS,
                                        (ROOT / match.ROM_IMAGE).read_bytes(), match.ROM)
        cls.fresh = cls.out / ("test-run-" + str(os.getpid()))
        cls.fresh.mkdir(exist_ok=False)

    @classmethod
    def tearDownClass(cls):
        (cls.out / ("test-receipt-" + str(os.getpid()) + ".json")).write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_direct_owner_image_caller_and_data_closure(self):
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.report["words"], self.report["frame"],
                          self.report["natural_positional_differences"],
                          self.report["guards"], self.report["relocations"]),
                         (60, 0x58, 0, 0, 7))
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["caller"]["direct_jal_calls"],
                         [hex(match.CALL_ROM)])
        self.assertEqual(self.report["caller"]["aligned_pointer_literals"], [])
        self.assertEqual((self.report["strict_exclusions"],
                          self.report["game_data"]["different_bytes"],
                          self.report["game_data"]["bytes"]),
                         (0, 0, 189088))
        self.receipt["closure"] = self.report

    def test_02_guest_descriptor_forwarding_and_all_word_coverage(self):
        global_rows = ((bits(1.0), bits(-2.5), bits(10.0)),
                       (0x00000001, 0x7FC12345, 0xFF800000))
        cases = []
        for phase, row, seed in itertools.product((0, 8), global_rows, (0, 1, 19, 255)):
            cases.append(Case(0x30203040 ^ seed, 0x81234567 ^ (seed * 0x10101),
                              0xA5000000 | (seed * 37 & 0xFFFF),
                              0x76543210 ^ (seed * 0x301), row, phase))
        coverage = set()
        for case in cases:
            before = fixture(case)
            model = ConfigOracle(self.words, before.copy(), case).run()
            self.assertEqual(len(model.calls), 1)
            target, pointer, payload, channel, owner = model.calls[0]
            self.assertEqual(target, FACTORY)
            self.assertEqual(payload, expected_descriptor(before, pointer, case), case)
            self.assertEqual((channel, owner), (case.channel & 0xFF, case.owner))
            self.assertEqual(payload[0x2A:0x2C],
                             bytes(before[pointer + index] for index in (0x2A, 0x2B)))
            coverage.update(pc for pc in model.visits
                            if match.ENTRY <= pc < match.ENTRY + match.SIZE)
        self.assertEqual(coverage, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.receipt["guest"] = {
            "cases": len(cases), "covered_words": len(coverage),
            "stack_phases": 2, "global_bit_patterns": len(global_rows),
            "private_bytes_preserved": ["+0x2A", "+0x2B"],
            "channel_low_byte_forwarded": True,
        }

    def test_03_native32_defined_domain_and_compiled_controls(self):
        selected = self.fresh / "native-selected.c"
        selected.write_text(native_harness(match.SELECTED))
        rows = []
        for profile in ("-O0", "-O2", "-O3"):
            target = self.fresh / ("native-selected" + profile)
            build = subprocess.run(native_command(profile) + [str(selected), "-o", str(target)],
                                   cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(target)], capture_output=True)
            self.assertEqual(run.returncode, 0, (profile, run.stdout, run.stderr))
            rows.append({"profile": profile, "cases": 4096, "UBSan_trap": True})
        effective = []
        for name, body in controls().items():
            source = self.fresh / ("control-" + name + ".c")
            target = self.fresh / ("control-" + name)
            source.write_text(native_harness(body))
            build = subprocess.run(native_command("-O2", valid=False) +
                                   [str(source), "-o", str(target)], cwd=ROOT,
                                   capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, (name, build.stdout, build.stderr))
            run = subprocess.run([str(target)], capture_output=True)
            self.assertNotEqual(run.returncode, 0, name)
            effective.append(name)
        self.receipt["native"] = {"profiles": rows, "effective_controls": effective}

    def test_04_payload_and_complete_image_reject_stale_inputs(self):
        raw, bindings = match.payload(self.out / "qualified-compact.o", match.FUNCTION)
        match.checked_candidate(ROOT, self.out / "qualified-compact.o")
        with self.assertRaises(ValueError):
            match.checked_candidate(ROOT, self.out / "predecessor-compact.o")
        before = self.before_elf.read_bytes()
        retail = match.retail_bytes(ROOT)
        expected = match.expected_image(before, retail)
        self.assertEqual(expected, self.after_elf.read_bytes())
        cycle = ("D_800AAAF8", "D_800A113C", "D_8009CC3C",
                 "D_8009E63C", "func_15155FD4")
        rows = {name: (at, string_at)
                for at, name, _, string_at in match.symbol_rows(before)}
        function_symbol = rows[match.FUNCTION][0]
        positions = [elf_slot_offset(before, match.ENTRY, match.SIZE),
                     function_symbol + 8]
        positions.extend(rows[name][0] for name in cycle)
        positions.extend(rows[name][1] for name in cycle)
        for position in positions:
            bad = bytearray(expected)
            bad[position] ^= 1
            with self.assertRaises(ValueError):
                match.check_image(before, bytes(bad), retail)
        with self.assertRaises(ValueError):
            match.check_image(before, expected[:-1], retail)
        self.assertEqual(bindings, match.BINDINGS)
        self.assertEqual(raw, match.retail_object_bytes(ROOT))
        self.receipt["rejections"] = {
            "payload_hash_and_bindings": True,
            "image_corruptions": len(positions) + 1,
            "closed_symbol_cycle": list(cycle), "strict_exclusions": 0,
        }


if __name__ == "__main__":
    unittest.main()
