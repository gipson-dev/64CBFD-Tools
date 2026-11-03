"""ABI, semantics, guard, owner and image gates for func_15107924."""

import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_linked_actor_point_update_match as match
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests import game_actor_direction_point_oracle as oracle
from tools.tests.game_actor_direction_point_oracle import (
    ACTOR, CHANGED, FRACTION, FRACTIONS, LINK, OWNER, STACK, TRIG_TABLE,
    Case, DirectionOracle, fixture, public, put, read)
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
CHILD = 0x15107A20


def controls():
    body = match.SELECTED
    result = {
        "wrong_link": body.replace("owner + 0x60", "owner + 0x64", 1),
        "wrong_actor_id": body.replace("actor + 0x3B", "actor + 0x3A", 1),
        "wrong_yaw": body.replace("link + 6", "link + 8", 1),
        "wrong_point": body.replace("owner + 0x14", "owner + 0x18", 1),
        "missing_clear": body.replace("    *changed = 0;\n", "", 1),
        "wrong_endpoint": body.replace("owner + 0x38", "owner + 0x34", 1),
        "wrong_first_output": body.replace("owner + 0x20", "owner + 0x24", 1),
        "wrong_second_output": body.replace("owner + 0x2C", "owner + 0x30", 1),
    }
    assert all(value != body for value in result.values())
    return result


def native_harness(body):
    return r'''
typedef unsigned char u8;
typedef short s16;
typedef int s32;
typedef unsigned int u32;
typedef float f32;
typedef struct { u8 bytes[0x100]; } struct127;
typedef struct { f32 unk0, unk4, unk8; } struct17;
typedef struct { f32 x, y, z; } vertex;
#define NULL ((void *)0)
void func_15107A20(struct127 *, s16, s16, vertex *, struct17 *);
void func_15107AE0(const f32 *, const f32 *, f32 *, f32 *);
''' + body + r'''
static u32 calls, error, mode;
static u8 *wanted_owner;
static struct127 *wanted_actor;
static s16 wanted_yaw, wanted_pitch;
static u32 word(f32 value) { union { f32 f; u32 u; } v; v.f = value; return v.u; }
static void store32(void *base, u32 offset, u32 value) { *(u32 *)((u8 *)base + offset) = value; }
void func_15107A20(struct127 *actor, s16 yaw, s16 pitch, vertex *point, struct17 *out) {
    calls++;
    if (calls != 1 || actor != wanted_actor || yaw != wanted_yaw ||
            pitch != wanted_pitch || (u8 *)point != wanted_owner + 0x14 || out != NULL) error = 1;
    if (mode & 1u) point->x += 1.0f;
    if (mode & 2u) point->y -= 2.0f;
    if (mode & 4u) point->z += 4.0f;
}
void func_15107AE0(const f32 *start, const f32 *end, f32 *first, f32 *second) {
    calls++;
    if (calls != 2 || (const u8 *)start != wanted_owner + 0x14 ||
            (const u8 *)end != wanted_owner + 0x38 ||
            (u8 *)first != wanted_owner + 0x20 ||
            (u8 *)second != wanted_owner + 0x2C) error = 1;
    first[0] = 10.0f; first[1] = 11.0f; first[2] = 12.0f;
    second[0] = 20.0f; second[1] = 21.0f; second[2] = 22.0f;
}
static int run(void) {
    union { u32 align; u8 bytes[0x100]; } owner_store, actor_store, link_store;
    u8 *owner = owner_store.bytes;
    u8 *actor = actor_store.bytes;
    u8 *link = link_store.bytes;
    u8 changed;
    u32 n, i, active, stale;
    for (n = 0; n < 4096; n++) {
        for (i = 0; i < 0x100; i++) {
            owner[i] = (u8)(n + i * 3u);
            actor[i] = (u8)(n + i * 5u);
            link[i] = (u8)(n + i * 7u);
        }
        *(u8 **)(owner + 0x60) = link;
        *(struct127 **)link = (struct127 *)actor;
        active = (n & 7u) != 0;
        stale = (n & 15u) == 1u;
        store32(actor, 0, active ? 1u : 0u);
        actor[0x3B] = 0xA7;
        link[4] = stale ? 0xA6 : 0xA7;
        wanted_yaw = (s16)(n * 257u);
        wanted_pitch = (s16)(n * 509u);
        *(s16 *)(link + 6) = wanted_yaw;
        *(s16 *)(link + 8) = wanted_pitch;
        ((f32 *)(owner + 0x14))[0] = (f32)n + 0.25f;
        ((f32 *)(owner + 0x14))[1] = (f32)n - 0.5f;
        ((f32 *)(owner + 0x14))[2] = -(f32)n - 0.75f;
        ((f32 *)(owner + 0x38))[0] = 50.0f;
        ((f32 *)(owner + 0x38))[1] = -60.0f;
        ((f32 *)(owner + 0x38))[2] = 70.0f;
        wanted_owner = owner;
        wanted_actor = (struct127 *)actor;
        mode = (n >> 4) & 7u;
        calls = error = 0;
        changed = 0xA5;
        if (func_15107924(owner, &changed) != (active && !stale)) return 10;
        if (!active || stale) {
            if (calls != 0 || changed != 0xA5 || error) return 11;
        } else if (mode == 0) {
            if (calls != 1 || changed != 0 || error) return 12;
        } else {
            if (calls != 2 || changed != 1 || error) return 13;
            if (word(((f32 *)(owner + 0x20))[0]) != word(10.0f) ||
                    word(((f32 *)(owner + 0x2C))[2]) != word(22.0f)) return 14;
        }
    }
    return 0;
}
''' + START


class LinkedActorPointUpdateTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.out = ROOT / match.BUILD
        (cls.report, cls.before_owner, cls.after_owner,
         cls.before_elf, cls.after_elf) = match.prepare(ROOT)
        image = cls.after_elf.read_bytes()
        at = elf_slot_offset(image, match.ENTRY, match.SIZE)
        cls.words = list(struct.unpack_from(">%dI" % match.WORDS, image, at))
        cls.rom = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.retail = list(struct.unpack_from(">%dI" % match.WORDS,
                                             cls.rom, match.ROM))
        cls.fresh = cls.out / ("test-run-" + str(os.getpid()))
        cls.fresh.mkdir(exist_ok=False)

    @classmethod
    def tearDownClass(cls):
        (cls.out / ("test-receipt-" + str(os.getpid()) + ".json")).write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def helpers(self):
        result = {}
        for va, rom, words in (
                (CHILD, 0x134ED0, 48),
                (0x1515C244, 0x1896F4, 41),
                (0x15143794, 0x170C44, 40),
                (0x151423D8, 0x16F888, 27),
                (FRACTION, 0x134F90, 38)):
            body = struct.unpack_from(">%dI" % words, self.rom, rom)
            result.update({va + index * 4: word
                           for index, word in enumerate(body)})
        return result

    def tables(self, memory):
        result = dict(memory)
        for va, size in ((TRIG_TABLE, 260), (FRACTIONS, 8)):
            at = elf_slot_offset(self.after_elf.read_bytes(), va, size)
            result.update({va + index: value for index, value in
                           enumerate(self.after_elf.read_bytes()[at:at + size])})
        return result

    def fractions(self, memory, start, end):
        return tuple(tuple(
            oracle.add(start[index], oracle.mul(
                oracle.sub(end[index], start[index]),
                read(memory, FRACTIONS + 4 * row)))
            for index in range(3)) for row in range(2))

    def test_01_guarded_owner_image_and_registry_closure(self):
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.report["words"], self.report["frame"],
                          self.report["natural_frame"],
                          self.report["natural_positional_differences"],
                          self.report["guards"], self.report["relocations"]),
                         (63, 64, 72, 11, 11, 2))
        self.assertEqual(self.report["neighbors"], 36)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(self.report["registry"]["aligned_pointers"],
                         [hex(match.TABLE_ROM)])
        self.assertEqual(self.report["registry"]["direct_jal_calls"], 0)
        self.assertEqual((self.report["strict_exclusions"],
                          self.report["game_data"]["different_bytes"]), (0, 0))
        self.receipt["closure"] = self.report

    def test_02_guest_routes_aliases_helpers_and_word_coverage(self):
        helpers = self.helpers()
        seen = set()
        cases = 0
        for route, axis, phase, actor_id, yaw in itertools.product(
                ("inactive", "stale", "same", "changed"), range(3),
                (0, 8), (0, 0xFF), (0x8123, 0xFE45)):
            case = Case(yaw=yaw, pitch=(yaw * 7 + 0x1234) & 0xFFFF,
                        phase=phase, actor_id=actor_id,
                        point=OWNER + 20, optional=False)
            initial = self.tables(fixture(case))
            put(initial, OWNER + 0x60, LINK)
            put(initial, LINK, ACTOR)
            put(initial, ACTOR, 0 if route == "inactive" else 1)
            initial[LINK + 4] = 0xA6 if route == "stale" else 0xA7
            initial[ACTOR + 0x3B] = 0xA7
            put(initial, LINK + 6, case.yaw, 2)
            put(initial, LINK + 8, case.pitch, 2)
            initial[CHANGED] = 0xA5
            expected, point, _ = oracle.actual_reference(initial, case)
            for index, value in enumerate(point):
                if route == "changed" and index == axis:
                    value = oracle.add(value, oracle.bits(1.0))
                put(initial, OWNER + 20 + 4 * index, value)
            end = (oracle.bits(50), oracle.bits(-60), oracle.bits(70))
            for index, value in enumerate(end):
                put(initial, OWNER + 0x38 + 4 * index, value)
            models = [DirectionOracle(
                words, initial, case, entry=match.ENTRY,
                arguments=(OWNER, CHANGED), connected=helpers).run()
                for words in (self.retail, self.words)]
            model = models[0]
            self.assertEqual(complete(model), complete(models[1]))
            seen.update(pc for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            valid = route in ("same", "changed")
            self.assertEqual((model.r[2], model.memory[CHANGED]),
                             (int(valid), 1 if route == "changed" else
                              0 if valid else 0xA5))
            wanted = dict(initial)
            if valid:
                self.assertEqual(model.target_entries, [(
                    ACTOR, oracle.sign(case.yaw) & 0xFFFFFFFF,
                    oracle.sign(case.pitch) & 0xFFFFFFFF, OWNER + 20, 0)])
                for index, value in enumerate(point):
                    put(wanted, OWNER + 20 + 4 * index, value)
                if route == "changed":
                    first, second = self.fractions(initial, point, end)
                    for destination, values in ((OWNER + 0x20, first),
                                                (OWNER + 0x2C, second)):
                        for index, value in enumerate(values):
                            put(wanted, destination + 4 * index, value)
                wanted[CHANGED] = int(route == "changed")
            else:
                self.assertFalse(model.calls)
            self.assertEqual(public(model.memory), public(wanted))
            cases += 1
        missing = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - seen
        self.assertEqual(missing, {match.ENTRY + 0x4C})
        self.receipt["guest"] = {
            "cases": cases, "covered_words": len(seen),
            "unreachable_compiler_words": ["+0x4C"],
            "stack_phases": 2, "signed_angle_patterns": 2,
            "actor_id_boundaries": 2, "all_return_routes": True,
            "real_child_origin_direction_trig_fraction_helpers": True,
            "complete_state_and_trace": True,
        }

    def test_03_native32_defined_domain_and_compiled_controls(self):
        selected = self.fresh / "native-selected.c"
        selected.write_text(native_harness(match.SELECTED))
        rows = []
        for profile in ("-O0", "-O2", "-O3"):
            target = self.fresh / ("native-selected" + profile)
            build = subprocess.run(
                native_command(profile) + ["-fno-strict-aliasing", str(selected),
                                           "-o", str(target)],
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
            build = subprocess.run(
                native_command("-O2", valid=False) + ["-fno-strict-aliasing",
                    str(source), "-o", str(target)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0,
                             (name, build.stdout, build.stderr))
            run = subprocess.run([str(target)], capture_output=True)
            self.assertNotEqual(run.returncode, 0, name)
            effective.append(name)
        self.receipt["native"] = {
            "profiles": rows, "effective_controls": effective,
            "canonical_32bit_pointers": True,
        }

    def test_04_natural_payload_guards_and_complete_image_rejections(self):
        raw, bindings = match.payload(
            self.out / "qualified-compact.o", match.FUNCTION)
        match.checked_candidate(ROOT, self.out / "qualified-compact.o")
        with self.assertRaises(ValueError):
            match.checked_candidate(ROOT, self.out / "predecessor-compact.o")
        natural = list(struct.unpack(">%dI" % match.WORDS, raw))
        for offset, expected, replacement in match.GUARD_WORDS:
            self.assertEqual(natural[offset // 4], expected)
            self.assertEqual(self.retail[offset // 4], replacement)
        self.assertEqual(bindings, match.BINDINGS)
        before = self.before_elf.read_bytes()
        retail = match.retail_bytes(ROOT)
        expected = match.expected_image(before, retail)
        self.assertEqual(expected, self.after_elf.read_bytes())
        positions = [elf_slot_offset(before, match.ENTRY, match.SIZE),
                     next(at for at, name, _, _ in match.symbol_rows(before)
                          if name == match.FUNCTION) + 8]
        for position in positions:
            bad = bytearray(expected)
            bad[position] ^= 1
            with self.assertRaises(ValueError):
                match.check_image(before, bytes(bad), retail)
        with self.assertRaises(ValueError):
            match.check_image(before, expected[:-1], retail)
        self.receipt["rejections"] = {
            "natural_payload_hash_and_bindings": True,
            "guard_words": len(match.GUARD_WORDS),
            "image_corruptions": len(positions) + 1,
            "strict_exclusions": 0,
        }


if __name__ == "__main__":
    unittest.main()
