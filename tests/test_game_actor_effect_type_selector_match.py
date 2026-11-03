"""Actor effect-type selection, fixed jump tables, callers and full image."""

import itertools
import json
import re
import struct
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_actor_effect_type_selector_candidates as screen
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.match_progress import load_elf_functions
from pad_c_object import emit_padded_assembly
from tools.pad_generated_object import parse_object
from tools.tests import test_game_random_curve_record as native
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import put
from tools.tests.test_game_payload_copy_wrapper_match import SignedByteOracle
from tools.tests.test_game_table_range_loader import STACK


ACTOR = 0x21000


class GameActorEffectTypeSelectorMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / screen.BUILD
        cls.output.mkdir(exist_ok=True)
        cls.path = cls.output
        cls.record, cls.words, cls.pool = screen.compile_candidate(
            cls.root, cls.output, "selected")
        cls.rom = (cls.root / "conker/conker.us.bin").read_bytes()
        cls.retail = list(struct.unpack_from(
            ">%dI" % screen.WORDS, cls.rom, screen.ROM))
        game_address, game_bytes = screen.sections(
            cls.root / "conker/build/conker.us.elf")[".game_data"]
        cls.original_pool = game_bytes[
            screen.TABLE - game_address:screen.TABLE - game_address + 0x260]
        cls.answers = [99] * 256
        for value, identities in screen.GROUPS.items():
            for identity in identities:
                cls.answers[identity] = value

        current = (cls.root / screen.SOURCE).read_text()
        cls.installed = screen.SELECTED in current
        cls.baseline_owner, cls.baseline_diagnostics = compile_owner(
            cls.root, cls.output, current, "baseline-owner")
        cls.candidate_owner, cls.candidate_diagnostics = (
            screen.compile_candidate_owner(cls.root, cls.output))
        effects_source = (
            cls.root /
            "conker/src/game/translation_units/161520_actor_point_effects.c"
        ).read_text()
        cls.effects, cls.effects_diagnostics = compile_owner(
            cls.root, cls.output, effects_source, "actor-point-effects")

        qualified_source = cls.output / "qualified-owner.s"
        qualified_source.write_text(emit_padded_assembly(
            cls.candidate_owner,
            cls.root / "conker/retail_layout.us.txt",
            "game_161520",
            rodata_symbol=screen.ANCHOR,
            word_patches_path=(
                cls.root / "conker/retail_word_patches.us.csv"),
            function_objects={"func_15138BC0": cls.effects},
        ))
        cls.owner = cls.output / "qualified-owner.o"
        subprocess.run([
            "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
            "-mabi=32", "-I", str(cls.root / "conker/include"), "-o",
            str(cls.owner), str(qualified_source),
        ], check=True, capture_output=True)

        linker = (cls.root / "conker/build/conker.ld").read_text()
        old = "build/src/game_161520.c.o"
        new = str(cls.owner.relative_to(
            cls.root / "conker")).replace("\\", "/")
        if linker.count(old) != 1:
            raise ValueError("Actor selector owner linker reference changed")
        script = cls.output / "qualified-image.ld"
        script.write_text(linker.replace(old, new))
        cls.elf = cls.output / "qualified-image.elf"
        subprocess.run([
            "mips-linux-gnu-ld", "-T",
            str(script.relative_to(cls.root / "conker")), "-Map",
            str((cls.output / "qualified-image.map").relative_to(
                cls.root / "conker")),
            "-T", "undefined_syms.us.txt", "-T", "undefined_funcs.us.txt",
            "-T", "undefined_syms_auto.txt", "-T",
            "undefined_funcs_auto.txt", "--no-check-sections",
            "--no-warn-mismatch", "-o",
            str(cls.elf.relative_to(cls.root / "conker")),
        ], cwd=cls.root / "conker", check=True, capture_output=True)

    def memory(self, identity, alignment=0, poison=0xA5, pool=None):
        memory = {STACK + offset: poison
                  for offset in range(-0x600, 0x100)}
        memory.update({ACTOR + offset: poison for offset in range(-16, 64)})
        memory[ACTOR + alignment + 4] = identity
        memory.update({
            screen.TABLE + offset: value for offset, value in enumerate(
                self.original_pool if pool is None else pool)
        })
        return memory

    def model(self, words, memory, alignment=0, phase=0):
        return SignedByteOracle(
            words, memory, entry=screen.ENTRY,
            arguments=(ACTOR + alignment,), phase=phase).run()

    def test_01_compiler_controls_direct_words_and_complete_fixed_tables(self):
        self.assertEqual(
            (self.record["body_words"], self.record["differences"],
             self.record["rodata_bytes"], self.record["table_differences"]),
            (63, 0, 608, 0))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.pool, self.original_pool)
        expected = {
            identity: value for value, identities in screen.GROUPS.items()
            for identity in identities
        }
        self.assertEqual(
            self.answers, [expected.get(identity, 99)
                           for identity in range(256)])
        records = []
        for name, body in screen.candidates():
            for profile in screen.PROFILES:
                record, words, pool = screen.compile_candidate(
                    self.root, self.output, name + "-" + profile,
                    body, profile)
                self.assertEqual(record["diagnostics"], "")
                records.append(record)
                if record["differences"] == 0:
                    self.assertEqual(words, self.retail)
                    self.assertEqual(pool, self.original_pool)
        self.assertEqual(sum(item["differences"] == 0 for item in records), 8)
        (self.output / "controls.json").write_text(
            json.dumps(records, indent=2) + "\n")

    def test_02_guest_every_identity_alignment_poison_and_exact_reads(self):
        coverage = [set(), set()]
        cases = 0
        for identity, alignment, poison, phase in itertools.product(
                range(256), range(4), (0, 0x55, 0xA5, 0xFF), (0, 8)):
            memory = self.memory(identity, alignment, poison)
            models = []
            for index, words in enumerate((self.words, self.retail)):
                model = self.model(words, memory, alignment, phase)
                models.append(model)
                self.assertEqual(model.r[2], self.answers[identity])
                self.assertEqual(model.memory, memory)
                self.assertEqual(model.calls, [])
                self.assertEqual(
                    model.events[0],
                    ("R", ACTOR + alignment + 4, 1, identity))
                self.assertFalse([event for event in model.events
                                  if event[0] == "W"])
                coverage[index].update(model.visits)
            self.assertEqual(models[0].events, models[1].events)
            cases += 1
        self.assertEqual(cases, 8192)
        full = set(range(screen.ENTRY, screen.ENTRY + screen.WORDS * 4, 4))
        self.assertEqual(coverage, [full, full])

    def test_03_native_actual_source_and_six_effective_controls(self):
        controls = {
            "placeholder": "s32 func_15134070(u8 *actor) { return 0; }",
            "signed-byte": screen.SELECTED.replace(
                "actor[4]", "((signed char *)actor)[4]"),
            "wrong-field": screen.SELECTED.replace("actor[4]", "actor[3]"),
            "missing-high": screen.SELECTED.replace(
                "        case 0xB0:\n", ""),
            "wrong-default": screen.SELECTED.replace(
                "return 99;", "return 0;"),
            "wrong-category": screen.SELECTED.replace(
                "            return 19;", "            return 18;"),
        }
        receipts = []
        for name, body in controls.items():
            _, words, pool = screen.compile_candidate(
                self.root, self.output, "negative-" + name, body)
            differences = 0
            for identity in range(256):
                model = self.model(
                    words, self.memory(identity, pool=pool))
                differences += (
                    model.r[2] != self.answers[identity] or
                    model.events[:1] != [("R", ACTOR + 4, 1, identity)])
            self.assertGreater(differences, 0, name)
            receipts.append({
                "name": name, "cases": 256,
                "differences": differences,
            })
        (self.output / "negatives.json").write_text(
            json.dumps(receipts, indent=2) + "\n")

        answers = ",".join(map(str, self.answers))
        self.fixture = (
            "typedef unsigned char u8;typedef int s32;\n" +
            screen.SELECTED +
            "\nstatic int answers[256]={" + answers + "};\n")
        self.run_host(r"""
u8 bytes[48],before[48];int identity,alignment,poison,i,cases=0;
int poisons[]={0,0x55,0xA5,0xFF};
if(sizeof(void *)!=4 || sizeof(s32)!=4) return 80;
for(identity=0;identity<256;identity++)
for(alignment=0;alignment<16;alignment++)
for(poison=0;poison<4;poison++) {
    for(i=0;i<48;i++) bytes[i]=(u8)poisons[poison];
    bytes[16+alignment+4]=(u8)identity;
    for(i=0;i<48;i++) before[i]=bytes[i];
    if(func_15134070(bytes+16+alignment)!=answers[identity]) return 81;
    for(i=0;i<48;i++) if(bytes[i]!=before[i]) return 82;
    cases++;
}
if(cases!=16384) return 83;
""")

    def test_04_minimal_storage_invalid_table_and_complete_caller_census(self):
        for identity in range(256):
            memory = self.memory(identity)
            for address in range(ACTOR - 16, ACTOR + 64):
                if address != ACTOR + 4:
                    memory.pop(address)
            for words in (self.words, self.retail):
                self.assertEqual(
                    self.model(words, memory).r[2],
                    self.answers[identity])
        for words in (self.words, self.retail):
            memory = self.memory(0x34)
            del memory[ACTOR + 4]
            with self.assertRaisesRegex(AssertionError, "unmapped read"):
                self.model(words, memory)
            memory = self.memory(0x34)
            put(memory, screen.TABLE, 0x1BAD0000)
            with self.assertRaisesRegex(AssertionError, "unowned jump"):
                self.model(words, memory)

        jal = 0x0C000000 | (screen.ENTRY >> 2 & 0x03FFFFFF)
        locations = [
            offset for offset in range(0, len(self.rom) - 3, 4)
            if struct.unpack_from(">I", self.rom, offset)[0] == jal
        ]
        self.assertEqual(
            locations,
            [0x102FAC, 0x164138, 0x164D04, 0x16608C, 0x166154,
             0x1C1AE0, 0x1C1FD8, 0x1DD6E4, 0x1DDEBC, 0x1E21A4])
        pointer = struct.pack(">I", screen.ENTRY)
        self.assertEqual(
            [offset for offset in range(0, len(self.rom) - 3, 4)
             if self.rom[offset:offset + 4] == pointer], [])

    def test_05_owner_padder_pool_and_existing_diagnostics_are_closed(self):
        normalize = lambda value: re.sub(
            r"build/[^,\n]+\.c, line \d+",
            "build/SOURCE.c, line N", value)
        self.assertEqual(
            normalize(self.candidate_diagnostics),
            normalize(self.baseline_diagnostics))
        self.assertIn("Warning 712", self.candidate_diagnostics)
        self.assertEqual(self.effects_diagnostics, "")
        text, functions, relocations = parse_object(self.candidate_owner)
        info = functions[screen.FUNCTION]
        self.assertEqual((info["value"], info["size"]), (0, 252))
        self.assertEqual({
            offset - info["value"]: rows
            for offset, rows in relocations.items()
            if info["value"] <= offset < info["value"] + info["size"]
        }, {
            0x1C: [("R_MIPS_HI16", ".rodata")],
            0x24: [("R_MIPS_LO16", ".rodata")],
            0x3C: [("R_MIPS_HI16", ".rodata")],
            0x44: [("R_MIPS_LO16", ".rodata")],
        })
        self.assertEqual(
            screen.sections(self.candidate_owner)[".rodata"][1],
            screen.sections(self.output / "selected.o")[".rodata"][1])
        self.assertEqual(
            len(screen.sections(self.candidate_owner)[".rodata"][1]), 608)
        self.assertNotIn(".rodata", screen.sections(self.owner))
        production = self.root / screen.OBJECT
        self.assertGreaterEqual(
            same_functions(production, self.owner, (screen.FUNCTION,)), 60)
        self.assertEqual(
            normalized_pools(production), normalized_pools(self.owner))

    def test_06_strict_full_image_protected_data_and_installed_state(self):
        old, _, old_addresses = load_elf_functions(
            str(self.root / "conker/build/conker.us.elf"),
            "mips-linux-gnu-objdump")
        new, _, new_addresses = load_elf_functions(
            str(self.elf), "mips-linux-gnu-objdump")
        self.assertEqual((old.keys(), old_addresses),
                         (new.keys(), new_addresses))
        changed = [name for name in old if old[name] != new[name]]
        self.assertEqual(
            changed, [] if self.installed else [screen.FUNCTION])
        self.assertEqual(new[screen.FUNCTION], self.retail)
        report = audit_layout(self.elf, self.root / "conker")
        self.assertEqual(
            (report["exact"], report["bytes"], report["owner_count"],
             report["different_bytes"], report["different_owner_count"]),
            (True, 189088, 720, 0, 0))
        game_address, game_bytes = screen.sections(self.elf)[".game_data"]
        self.assertEqual(
            game_bytes[screen.TABLE - game_address:
                       screen.TABLE - game_address + 0x260],
            self.original_pool)
        if self.installed:
            owner = (self.root / screen.SOURCE).read_text()
            self.assertIn(screen.SELECTED, owner)
            self.assertIn(screen.PROTOTYPE, owner)
            makefile = (self.root / "conker/Makefile").read_text()
            self.assertIn(
                "game_161520.c.o: RETAIL_RODATA_SYMBOL := " +
                screen.ANCHOR, makefile)


if __name__ == "__main__":
    unittest.main()
