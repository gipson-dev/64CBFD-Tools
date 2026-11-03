"""Semantic, ABI, guarded-owner and full-image gates for func_151A9BA0."""

import itertools
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_height_sound_probe_candidates as candidate
from tools.experiments import game_height_sound_probe_match as match
from tools.pad_generated_object import emit_padded_assembly
from tools.tests import game_height_sound_probe_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]


def controls():
    body = candidate.SELECTED
    variants = {
        "threshold-equality": body.replace(
            "D_800A8F7C <", "D_800A8F7C <=", 1),
        "high-offset": body.replace("+ 100.0f", "+ 101.0f", 1),
        "low-offset": body.replace("+ 150.0f", "+ 151.0f", 1),
        "probe-depth": body.replace("- 300.0f", "- 299.0f", 1),
        "omit-result-height": body.replace(
            "        position[1] = *(f32 *)(owner + 0x34);\n", "", 1),
        "cached-metadata": body.replace(
            "    u8 *actor;", "    u8 *actor;\n    u8 category = owner[0xC];\n"
            "    u8 identity = owner[1];", 1).replace(
                "1, owner[0xC], owner[1]", "1, category, identity", 1),
        "wrong-effect-kind": body.replace(
            "1, owner[0xC], owner[1]", "3, owner[0xC], owner[1]", 1),
        "wrong-sound-id": body.replace("0x5208", "0x5209", 1),
        "wrong-sound-route": body.replace("0, 0x11, 0x5208", "0, 0x10, 0x5208", 1),
        "reload-sound-actor": body.replace(
            "func_10010FFC(0, 0x11, 0x5208, 0, 0, actor);",
            "func_10010FFC(0, 0x11, 0x5208, 0, 0,\n"
            "                       *(u8 **)(owner + 0x18));", 1),
        "omit-sound": body.replace(
            "        func_10010FFC(0, 0x11, 0x5208, 0, 0, actor);\n", "", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("A height/sound semantic control did not alter the source")
    return variants


def native_harness(body):
    declarations = (
        "s32 func_15045800(f32 *, u16, f32, void *);\n"
        "void func_151ABE40(f32 *, void *, s32, u8, s32);\n"
    )
    return ("#include <ultra64.h>\n" + candidate.DECLARATIONS +
            declarations + body + r'''
static u32 ownerWords[64], actorWords[96], otherWords[96];
static u8 before[256];
static s32 calls, bad, outcome, mode;
static u8 wantedIdentity, wantedCategory;
static f32 wantedY, wantedDepth;
f32 D_800A8F7C;
static u32 asBits(f32 value) { union { f32 value; u32 word; } cast; cast.value = value; return cast.word; }
static f32 asFloat(u32 word) { union { f32 value; u32 word; } cast; cast.word = word; return cast.value; }
s32 func_15045800(f32 *position, u16 selector, f32 threshold, void *result) {
    u8 *owner = (u8 *)ownerWords;
    if (calls++ != 0 || selector || result != owner + 52 ||
        asBits(position[0]) != asBits(125.25f) || asBits(position[1]) != asBits(wantedY) ||
        asBits(position[2]) != asBits(-75.5f) || asBits(threshold) != asBits(wantedDepth)) bad = 1;
    *(f32 *)(owner + 52) = 17.5f; owner[80] ^= 0x40;
    if (mode & 1) { owner[1] ^= 255; owner[12] ^= 0x55; }
    if (mode & 2) { position[0] = -77.25f; position[1] = -999.0f; position[2] = 99.5f; }
    if (mode & 4) *(void **)(owner + 24) = otherWords;
    return outcome;
}
void func_151ABE40(f32 *position, void *result, s32 kind, u8 category, s32 identity) {
    u8 *owner = (u8 *)ownerWords;
    if (calls++ != 1 || !outcome || result != owner + 52 || kind != 1 ||
        category != (u8)(wantedCategory ^ ((mode & 1) ? 0x55 : 0)) ||
        identity != (u8)(wantedIdentity ^ ((mode & 1) ? 255 : 0)) ||
        asBits(position[0]) != asBits((mode & 2) ? -77.25f : 125.25f) ||
        asBits(position[1]) != asBits(17.5f) ||
        asBits(position[2]) != asBits((mode & 2) ? 99.5f : -75.5f)) bad = 1;
    owner[53] ^= 0xAA; owner[81] ^= 0x20;
    if (mode & 8) *(void **)(owner + 24) = otherWords;
}
u16 func_10010FFC(s32 route, s32 slot, u16 sound, s16 arg3, u8 arg4, void *actor) {
    u8 *owner = (u8 *)ownerWords;
    if (calls++ != 2 || !outcome || route != 0 || slot != 0x11 || sound != 0x5208 ||
        arg3 != 0 || arg4 != 0 || actor != actorWords) bad = 1;
    owner[82] ^= 0x10;
    return 0xA55A;
}
typedef void (*Function)(u8 *);
static u32 tops[] = {0xC6147400u, 0xC6147000u, 0xC6146C00u, 0x7FC12345u, 0x7F800000u, 0xFF800000u};
static u32 ys[] = {0xC3160000u, 0x43480000u, 0x7FC12345u};
static s32 outcomes[] = {0, 1, -1};
static s32 modes[] = {0, 1, 2, 4, 8, 3, 7, 15};
static int check(Function function) {
    s32 top, y, answer, selectedMode, identity, index;
    u8 *owner = (u8 *)ownerWords, *actor = (u8 *)actorWords;
    for (top = 0; top < 6; top++) for (y = 0; y < 3; y++)
    for (answer = 0; answer < 3; answer++) for (selectedMode = 0; selectedMode < 8; selectedMode++)
    for (identity = 0; identity < 2; identity++) {
        for (index = 0; index < 256; index++) owner[index] = (u8)(index * 13 + 0x59);
        for (index = 0; index < 384; index++) {
            actor[index] = (u8)(index * 7 + 0xA5);
            ((u8 *)otherWords)[index] = (u8)(index * 3 + 0x35);
        }
        *(void **)(owner + 24) = actor; *(f32 *)(actor + 20) = 125.25f;
        *(f32 *)(actor + 24) = asFloat(ys[y]); *(f32 *)(actor + 28) = -75.5f;
        *(f32 *)(actor + 280) = asFloat(tops[top]);
        mode = modes[selectedMode]; outcome = outcomes[answer];
        wantedIdentity = owner[1] = identity ? 255 : 0; wantedCategory = owner[12] = 128;
        D_800A8F7C = -9500.0f;
        wantedY = (asFloat(tops[top]) > -9500.0f) ? asFloat(tops[top]) + 100.0f : asFloat(ys[y]) + 150.0f;
        wantedDepth = wantedY - 300.0f;
        for (index = 0; index < 256; index++) before[index] = owner[index];
        calls = bad = 0; function(owner);
        if (bad || calls != (outcome ? 3 : 1)) return 1;
        for (index = 0; index < 256; index++)
            if (!(index == 1 || index == 12 || (index >= 24 && index < 28) ||
                  (index >= 52 && index < 56) || index == 80 || index == 81 || index == 82) &&
                owner[index] != before[index]) return 2;
        if (owner[1] != (u8)(wantedIdentity ^ ((mode & 1) ? 255 : 0)) ||
            owner[12] != (u8)(wantedCategory ^ ((mode & 1) ? 0x55 : 0))) return 3;
    }
    return 0;
}
static int run(void) {
    if (sizeof(void *) != 4 || sizeof(f32) != 4) return 90;
    if (check(func_151A9BA0)) return 10;
    return 0;
}
''' + START)


class GameHeightSoundProbeGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = match.prepare(ROOT)
        cls.report = cls.state["report"]
        retail = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.words = struct.unpack_from(">%dI" % match.WORDS, retail, match.ROM)
        cls.fresh = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.fresh.mkdir(exist_ok=False)
        oracle.OUTPUT = cls.fresh
        cls.qualified = oracle.linked(cls.state["qualified_owner"], "qualified")
        cls.raw = oracle.linked(cls.state["qualified_compact"], "raw")
        assert tuple(cls.qualified) == cls.words

    def test_01_guarded_owner_image_registry_and_stale_rows(self):
        self.assertEqual(
            (self.report["words"], self.report["frame"],
             self.report["natural_positional_differences"],
             self.report["guards"], self.report["relocations"],
             self.report["neighbors"]),
            (64, 0x40, 11, 11, 5, 40))
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(self.report["functions"], 6051)
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        self.assertEqual(
            self.report["registry"],
            {"direct_jal_calls": [],
             "aligned_pointer_literals": ["0x22fa98"],
             "registry": "D_8008AFD0[2]",
             "abi": "one owner pointer; callback probes its attached actor and returns void"})
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))

        target_indices = [
            index for index, row in enumerate(self.state["qualified_rows"])
            if row["filename"] == match.FILENAME and
            row["function"] == match.FUNCTION]
        self.assertEqual(len(target_indices), 11)
        for sequence, index in enumerate(target_indices):
            stale = [dict(row) for row in self.state["qualified_rows"]]
            stale[index]["expected"] = "0xDEADBEEF"
            path = self.fresh / ("stale-%d.csv" % sequence)
            match.write_patches(path, self.state["fields"], stale)
            with self.assertRaisesRegex(ValueError, "stale .*word patch"):
                emit_padded_assembly(
                    self.state["qualified_compact"], ROOT / match.ASM,
                    word_patches_path=path, filename=match.FILENAME)

    def test_02_guest_probe_effect_sound_lifetimes_and_word_coverage(self):
        coverage = set()
        cases = 0
        threshold = oracle.floating(oracle.THRESHOLD)
        tops = (oracle.bits(threshold - 1.0), oracle.THRESHOLD,
                oracle.bits(threshold + 1.0), 0x7FC12345,
                0x7F800000, 0xFF800000)
        for top, y, outcome, mode, identity, phase in itertools.product(
                tops, (oracle.bits(-150.0), oracle.bits(200.0), 0x7FC12345),
                (0, 1, 0xFFFFFFFF), (0, 1, 2, 4, 8, 3, 7, 15),
                (0, 255), (0, 8)):
            case = oracle.Case(top=top, y=y, outcome=outcome, mode=mode,
                               identity=identity, phase=phase)
            initial = oracle.fixture(case)
            wanted, calls = oracle.reference(initial, case)
            models = []
            for words in (self.words, self.qualified, self.raw):
                model = oracle.Oracle(words, initial, case).run()
                self.assertEqual((oracle.public(model.memory), model.calls),
                                 (oracle.public(wanted), calls))
                models.append(model)
            self.assertEqual(
                (models[0].r, models[0].f, models[0].memory,
                 models[0].events, models[0].trace),
                (models[1].r, models[1].f, models[1].memory,
                 models[1].events, models[1].trace))
            coverage.update(pc for pc in models[0].visits
                            if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            cases += 1
        expected_coverage = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4))
        # The duplicate low-route Y load immediately before the branch-likely
        # target is structurally unreachable; the delay-slot copy is executed.
        expected_coverage.remove(match.ENTRY + 0x58)
        self.assertEqual(coverage, expected_coverage)
        self.assertEqual(cases, 1728)

    def test_03_native32_profiles_and_effective_controls(self):
        selected = self.fresh / "native-selected.c"
        selected.write_text(native_harness(candidate.SELECTED))
        for profile in ("-O0", "-O2", "-O3"):
            target = self.fresh / ("native-selected" + profile)
            build = subprocess.run(
                native_command(profile) + ["-mstackrealign", "-fno-strict-aliasing",
                                           str(selected), "-o", str(target)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(target)], capture_output=True, timeout=60)
            self.assertEqual(run.returncode, 0, (profile, run.stdout, run.stderr))

        effective = []
        for name, body in controls().items():
            source = self.fresh / ("control-" + name + ".c")
            target = self.fresh / ("control-" + name)
            source.write_text(native_harness(body))
            build = subprocess.run(
                native_command("-O2") + ["-mstackrealign", "-fno-strict-aliasing",
                                          str(source), "-o", str(target)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, (name, build.stdout, build.stderr))
            run = subprocess.run([str(target)], capture_output=True, timeout=60)
            self.assertNotEqual(run.returncode, 0, name)
            effective.append(name)
        self.assertEqual(len(effective), 11)


if __name__ == "__main__":
    unittest.main()
