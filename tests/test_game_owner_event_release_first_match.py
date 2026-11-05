"""Command identity, aliases, real dispatcher, private faults and relocation gates."""

from dataclasses import dataclass
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_owner_event_release_first_candidates as candidate
from tools.experiments import game_owner_event_release_first_match as match
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import test_game_owner_event_dispatch_match as base
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults


ROOT = candidate.ROOT
RECORD, EVENT = base.RECORD, base.EVENT
RELEASE, FORWARD = base.RELEASE, base.FORWARD
PARENT, PARENT_ROM, PARENT_WORDS = 0x15149434, 0x1768E4, 23
TABLE, TABLE_ROM = 0x8008A8D8, 0x22F398


@dataclass(frozen=True)
class Case:
    command: int = 0
    match_mode: int = 0
    phase: int = 0
    upper: int = 0
    seed: int = 0
    layout: int = -1000


def event_at(case):
    return EVENT if case.layout == -1000 else RECORD + case.layout


def fixture(case):
    event = event_at(case)
    memory = {STACK + i: (i * 17 + case.seed + 0xA5) & 255 for i in range(-2048, 512)}
    for address, size in ((RECORD - 32, 128), (event - 32, 80)):
        memory.update({address + i: (i * 13 + case.seed * 19 + 0x59) & 255 for i in range(size)})
    put(memory, RECORD + 0x28, base.OWNER_A)
    memory[RECORD + 0x2C] = 0x31
    put(memory, RECORD + 0xE, case.seed * 257 + 0x1234, 2)
    memory[RECORD + 0xD] = (case.seed * 19 + 0xA4) & 255
    put(memory, event, base.OWNER_A if case.match_mode in (1, 3) else base.OWNER_B)
    memory[event + 4] = 0x31 if case.match_mode in (2, 3) else 0x72
    return memory


def reference(initial, case):
    memory, calls = dict(initial), []
    event, command = event_at(case), case.command & 255
    if command in (0xC, 0xE, 0x50, 0xD):
        matched = read(memory, RECORD + 0x28) == read(memory, event)
        if not matched:
            matched = memory[RECORD + 0x2C] == memory[event + 4]
        if matched:
            if command == 0xD:
                flags = memory[RECORD + 0xD]
                put(memory, RECORD + 0xE, 100, 2)
                memory[RECORD + 0xD] = flags | 1
            else:
                calls.append((RELEASE, (RECORD,)))
    elif command == 0x4E:
        calls.append((RELEASE, (RECORD,)))
    else:
        calls.append((FORWARD, (event, command, RECORD + 0x28, RECORD + 0x2C, RECORD)))
    return memory, calls


class Oracle(base.OwnerEventDispatchOracle):
    def __init__(self, words, memory, case=Case(), fault=None, entry=match.ENTRY,
                 connected=None, arguments=None, release=RELEASE, forward=FORWARD,
                 providers=()):
        TimingOracle.__init__(self, words, memory, phase=case.phase, entry=entry,
            arguments=arguments or (RECORD, event_at(case), (case.upper << 8) | (case.command & 255)),
            connected=connected)
        self.root_fault = fault
        self.release, self.forward, self.providers = release, forward, set(providers)

    def record_call(self, target):
        if target == self.release:
            args = tuple(self.arguments(1))
        elif target == self.forward:
            args = tuple(self.arguments(5))
        elif target == match.ENTRY or target in self.providers:
            args = tuple(self.arguments(3))
        else:
            raise AssertionError("Unbounded release-first helper %08X" % target)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target not in (self.release, self.forward) and target not in self.providers:
            raise AssertionError("Unexpected release-first provider")
        # The inherited hook has no target-specific memory effects.
        super().hook(RELEASE)


def controls():
    b = candidate.SELECTED
    rows = {
        "wrong-arm-command": b.replace("== 0x0D", "== 0x0B", 1),
        "wrong-match-gates": b.replace(" && ", " || "),
        "wrong-timer": b.replace("record->timer = 100;", "record->timer = 99;"),
        "wrong-flag": b.replace("record->flags = flags | 1;", "record->flags = flags | 2;"),
        "wrong-release-C": b.replace("== 0x0C", "== 0x0B", 1),
        "wrong-release-E": b.replace("== 0x0E", "== 0x0F", 1),
        "wrong-release-50": b.replace("== 0x50", "== 0x51", 1),
        "wrong-unconditional-release": b.replace("== 0x4E", "== 0x4F", 1),
        "wrong-forward-command": b.replace("((volatile u8 *)&rawCommand)[3],", "0,"),
        "wrong-forward-owner": b.replace("(s32)&record->owner,", "(s32)&record->ownerId,"),
        "wrong-forward-id": b.replace("(s32)&record->ownerId,", "(s32)&record->owner,"),
        "wrong-release-record": b.replace("func_1516972C(record);", "func_1516972C((void *)event);"),
    }
    if any(body == b for body in rows.values()):
        raise ValueError("Ineffective release-first control")
    return rows


def native_source(body):
    text = base.native_source(body)
    old = """typedef struct {
    u8 retained00[0x10];
    u8 *owner;
    u8 ownerId;
    u8 retained15;
    s16 timer;
    u8 flags;
} OwnerEventRecord15191980;"""
    if text.count(old) != 1:
        raise ValueError("Shared native owner-event record changed")
    text = text.replace(old, candidate.DECLARATIONS.strip()).replace(
        "OwnerEventRecord15191980", "OwnerEventRecord15191A84").replace(
        "record.retained15", "record.retained10[0]").replace(
        "func_15191980(&record, &event, raw);", "func_15191A84(&record, &event, raw);")
    for field, before, after in (("owner", "0x10", "0x28"), ("timer", "0x16", "0xE"), ("flags", "0x18", "0xD")):
        text = text.replace(
            "__builtin_offsetof(OwnerEventRecord15191A84, %s) != %s" % (field, before),
            "__builtin_offsetof(OwnerEventRecord15191A84, %s) != %s" % (field, after))
    return text


class GameOwnerEventReleaseFirstMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = ROOT / match.BUILD
        cls.prepared = match.prepare(ROOT)
        cls.rom = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.retail = list(struct.unpack_from(">66I", cls.rom, match.ROM))
        text, functions, relocations = parse_object(cls.prepared["qualified_compact"])
        info = functions[match.FUNCTION]
        cls.raw_blob = text[info["value"]:info["value"] + match.SIZE]
        linked, _ = link_owner(ROOT, cls.out, cls.prepared["qualified_compact"], match.FILENAME)
        cls.raw = list(struct.unpack_from(">66I", linked, info["value"]))
        cls.fitted_blob = match.normalized(cls.raw_blob, match.BINDINGS, cls.rom[match.ROM:match.ROM + match.SIZE])
        fitted, functions = link_owner(ROOT, cls.out, cls.prepared["qualified_owner"], match.FILENAME)
        cls.fitted = list(struct.unpack_from(">66I", fitted, functions[match.FUNCTION]["value"]))

    def receipt(self, name, value):
        (self.out / (name + ".json")).write_text(json.dumps(value, indent=2) + "\n")

    def compare(self, case, images=None, entry=match.ENTRY, release=RELEASE, forward=FORWARD):
        initial = fixture(case)
        wanted, calls = reference(initial, case)
        calls = [(release if t == RELEASE else forward, args) for t, args in calls]
        models = [Oracle(words, initial, case, entry=entry, release=release, forward=forward).run()
                  for words in images or (self.retail, self.raw, self.fitted)]
        for model in models:
            self.assertEqual((base.public(model.memory), model.calls), (base.public(wanted), calls), case)
        self.assertEqual(complete(models[0]), complete(models[2]))
        return models

    def test_01_owner_bindings_literal_image_and_guard_controls(self):
        report = self.prepared["report"]
        self.assertEqual((report["words"], report["guards"], report["neighbors"], report["relocations"]), (66, 39, 60, 3))
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertTrue(report["literal_full_image_prediction"])
        truth = self.rom[match.ROM:match.ROM + match.SIZE]
        for at in range(match.SIZE):
            bad = bytearray(self.raw_blob)
            bad[at] ^= 1
            with self.assertRaises(ValueError):
                match.normalized(bytes(bad), match.BINDINGS, truth)
        for bindings in ({}, {**match.BINDINGS, 0x60: [("R_MIPS_26", "func_15169850")]}, {**match.BINDINGS, 0x64: match.BINDINGS[0x60]}):
            with self.assertRaises(ValueError):
                match.normalized(self.raw_blob, bindings, truth)
        for index in (0, 19, 38):
            rows = [dict(r) for r in self.prepared["predecessor_rows"]] + [match.complete_row(r) for r in match.PATCH_ROWS]
            rows[len(self.prepared["predecessor_rows"]) + index]["expected"] = "0x%08X" % (match.GUARD_WORDS[index][1] ^ 1)
            path = self.out / ("bad-guard-%d.csv" % index)
            harness.write_patches(path, self.prepared["fields"], rows)
            with self.assertRaises(ValueError):
                emit_padded_assembly(self.prepared["qualified_compact"], ROOT / match.ASM, word_patches_path=path, filename=match.FILENAME)
        before, after = self.prepared["predecessor_elf"].read_bytes(), self.prepared["qualified_elf"].read_bytes()
        for at in (0x80, len(after) - 1, match.elf_slot_offset(before, match.ENTRY, match.SIZE)):
            bad = bytearray(after)
            bad[at] ^= 1
            with self.assertRaises(ValueError):
                match.strict_image(before, bytes(bad), truth)

    def test_02_all_commands_identity_modes_upper_bits_and_stack_phases(self):
        visits, count = set(), 0
        for command, mode, phase, pattern in itertools.product(range(256), range(4), (0, 8), (0, 255)):
            case = Case(command, mode, phase, (command * 0x12345 + mode) & 0xFFFFFF, command ^ pattern)
            models = self.compare(case)
            visits.update(models[0].visits)
            count += 1
        unreachable = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - visits
        self.assertEqual(unreachable, {match.ENTRY + 0x8C})
        self.receipt("guest-contract", {"cases_per_body": count, "covered_retail_words": len(visits),
            "unreachable_scheduling_words": list(map(hex, sorted(unreachable))), "callback_clobber": True})

    def test_03_aligned_event_overlaps(self):
        count = 0
        for layout, command, mode, phase in itertools.product(range(-16, 65, 4), (0xC, 0xD, 0xE, 0x4E, 0x50, 0x33), range(4), (0, 8)):
            self.compare(Case(command, mode, phase, 0xA50000, layout & 255, layout))
            count += 1
        self.receipt("aliases", {"cases_per_body": count, "aligned_event_offsets": list(range(-16, 65, 4)), "complete_public_bytes": True})

    def test_04_native32_profiles_and_semantic_controls(self):
        output = self.out / "native"
        output.mkdir(exist_ok=True)
        rows = [("positive-" + opt[1:], candidate.SELECTED, opt, 0) for opt in ("-O0", "-O2", "-O3")]
        rows += [(label, body, "-O2", 1) for label, body in controls().items()]
        for label, body, opt, expected in rows:
            source, binary = output / (label + ".c"), output / (label + ".elf")
            source.write_text(native_source(body))
            compiled = subprocess.run(["gcc", "-m32", "-std=c99", opt, "-fno-pie", "-no-pie", "-ffreestanding",
                "-fno-strict-aliasing", "-fno-stack-protector", "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
                "-Wall", "-Wextra", "-Werror", "-nostdlib", str(source), "-o", str(binary)], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            self.assertEqual(subprocess.run([str(binary)], capture_output=True, timeout=30).returncode, expected, label)
        self.receipt("native-contract", {"profiles": ["O0", "O2", "O3"], "cases_per_profile": 4096,
            "controls": sorted(controls()), "trap_UBSan": True, "byte_home_fixture_encodes_big_endian_command": True})

    def test_05_real_complete_74_entry_dispatcher(self):
        parent = list(struct.unpack_from(">23I", self.rom, PARENT_ROM))
        registry = struct.unpack_from(">74I", self.rom, TABLE_ROM)
        self.assertEqual(registry[8], match.ENTRY)
        count, visits = 0, set()
        providers = set(registry) - {0, match.ENTRY}
        for selector, command, mode, phase in itertools.product((-128, -1, 0, 1, 8, 17, 73, 74, 127), (0xC, 0xD, 0xE, 0x4E, 0x50, 0x33), range(4), (0, 8)):
            case = Case(command, mode, phase, 0xA50000, command)
            initial = fixture(case)
            initial[RECORD + 0x13] = selector & 255
            for i, target in enumerate(registry):
                put(initial, TABLE + i * 4, target)
            selected = selector if 0 <= selector < 74 else 0
            target = registry[selected]
            wanted, calls = reference(initial, case) if target == match.ENTRY else (initial, [])
            expected_calls = ([(target, (RECORD, event_at(case), command))] + calls) if target == match.ENTRY else (
                [(target, (RECORD, event_at(case), command))] if target else [])
            models = []
            for words in (self.retail, self.raw, self.fitted):
                connected = {match.ENTRY + i * 4: w for i, w in enumerate(words)}
                model = Oracle(parent, initial, case, entry=PARENT, connected=connected,
                    arguments=(RECORD, event_at(case), (case.upper << 8) | command), providers=providers).run()
                self.assertEqual((base.public(model.memory), model.calls), (base.public(wanted), expected_calls))
                visits.update(model.visits)
                models.append(model)
            self.assertEqual(complete(models[0]), complete(models[2]))
            count += 1
        self.assertTrue(set(range(PARENT, PARENT + 23 * 4, 4)) <= visits)
        self.receipt("caller", {"phases_per_body": count, "words": 23, "registry_entries": 74,
            "signed_selector_clamp_and_NULL": True, "other_callbacks_are_bounded_providers": True})

    def test_06_literal_private_fault_prefixes(self):
        count = 0
        for command, mode, phase in itertools.product((0xC, 0xD, 0x4E, 0x33), (0, 1, 2), (0, 8)):
            case = Case(command, mode, phase)
            initial = fixture(case)
            baseline = Oracle(self.retail, initial, case).run()
            for cut in range(baseline.root_accesses):
                models = [Oracle(words, initial, case, fault=cut) for words in (self.retail, self.fitted)]
                for model in models:
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                self.assertEqual(complete(models[0]), complete(models[1]))
                count += 1
        self.receipt("fault-prefixes", {"fired_prefixes": count, "complete_fitted_private_state_equal": True,
            "raw_fault_access_order_or_PC_not_equated": True})

    def test_07_independent_GNU_links_and_helper_rebases(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context = type("ReleaseFirstOriginal", (), dict(root=ROOT, out=self.out))
        original = ViewListSetupTests.original.__func__(context, "original-release-first", (ROOT / match.ASM).read_text(), match.FUNCTION)
        objects = (original, self.prepared["qualified_compact"], self.prepared["qualified_owner"])
        count = links = 0
        for index, (entry, release, forward) in enumerate(((match.ENTRY, RELEASE, FORWARD),
                (0x18017FFC, 0x18FF7FFC, 0x18008000), (0x1A028000, 0x1A007FFC, 0x1AFF8000))):
            images = []
            anchors = {"func_1516972C": release, "func_15169850": forward}
            for ordinal, obj in enumerate(objects):
                text, functions, relocations = parse_object(obj)
                assembly, unknown = emit_function(text, functions[match.FUNCTION], relocations, match.FUNCTION, anchors)
                self.assertFalse(unknown)
                path = self.out / ("rebase-%d-%d" % (index, ordinal))
                path.with_suffix(".s").write_text(assembly)
                path.with_suffix(".ld").write_text("SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n" % entry)
                subprocess.run(["mips-linux-gnu-as", "-EB", "-march=vr4300", "-o", str(path.with_suffix(".o")), str(path.with_suffix(".s"))], capture_output=True, check=True)
                subprocess.run(["mips-linux-gnu-ld", "-m", "elf32btsmip", "-T", str(path.with_suffix(".ld")), "-e", match.FUNCTION,
                    *["--defsym=%s=0x%X" % pair for pair in anchors.items()], "-o", str(path.with_suffix(".elf")), str(path.with_suffix(".o"))], capture_output=True, check=True)
                images.append(list(struct.unpack_from(">66I", sections(path.with_suffix(".elf"))[".text"][1])))
                links += 1
            self.assertEqual(images[0], images[2])
            for command, mode in itertools.product((0xC, 0xD, 0xE, 0x4E, 0x50, 0x33), range(4)):
                self.compare(Case(command, mode), images, entry, release, forward)
                count += 1
        self.receipt("rebases", {"GNU_links": links, "cases_per_body": count, "independent_entry_and_J26_targets": True})

    def test_08_actual_compiled_wrong_C_controls(self):
        results = {}
        witnesses = {"wrong-match-gates": Case(0xD, 1), "wrong-timer": Case(0xD, 1),
            "wrong-flag": Case(0xD, 1), "wrong-release-record": Case(0x4E)}
        for label in ("wrong-match-gates", "wrong-timer", "wrong-flag", "wrong-release-record"):
            obj, _ = compile_owner(ROOT, self.out, candidate.source_with(controls()[label]), "control-" + label)
            text, functions = link_owner(ROOT, self.out, obj, candidate.OWNER)
            info = functions[match.FUNCTION]
            words = list(struct.unpack_from(">%dI" % (info["size"] // 4), text, info["value"]))
            case = witnesses[label]
            wanted, calls = reference(fixture(case), case)
            actual = Oracle(words, fixture(case), case).run()
            self.assertNotEqual((base.public(actual.memory), actual.calls), (base.public(wanted), calls), label)
            results[label] = {"words": len(words), "guest_counterexample": True}
        self.receipt("compiled-controls", results)


if __name__ == "__main__":
    unittest.main()
