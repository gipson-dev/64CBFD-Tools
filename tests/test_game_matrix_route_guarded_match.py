"""Close the qualified matrix route with twelve checked compiler-layout rows."""

import csv
import shutil
import subprocess
import sys
from pathlib import Path

from tools.pad_c_object import emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.experiments import game_matrix_route_branch_candidates as branch
from tools.experiments import game_matrix_route_candidates as route
from tools.experiments import game_matrix_route_layout_candidates as layout
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests import test_game_matrix_route_branch_recovery as recovery
from tools.tests.game_owner_pool import normalized_pools


PATCH_ROWS = (
    dict(offset="0x044", expected="0x1000005D", replacement="0x1000005E",
         note="Retarget early failure branch across the inserted primary preload"),
    dict(offset="0x054", expected="0x9605001E", replacement="0x9602001E",
         note="Keep lookup key in retail V0 during attachment fallthrough"),
    dict(offset="0x068", expected="0x10000054", replacement="0x10000055",
         note="Retarget attachment failure branch across the inserted primary preload"),
    dict(offset="0x084", expected="0x1000002F", replacement="0x10000030",
         note="Retarget attachment success branch across the inserted primary preload"),
    dict(offset="0x08C", expected="0x9605001E", replacement="0x9602001E",
         note="Reload lookup key into retail V0 before the keyed route"),
    dict(offset="0x094", expected="0x50A0001B", replacement="0x1040001B",
         note="Use the retail normal zero-key branch through V0"),
    dict(offset="0x098", expected="0x8E020034", replacement="0x00402825",
         note="Move the nonzero lookup key into A1 in the branch delay slot"),
    dict(offset="0x0AC", expected="0x10000043", replacement="0x10000044",
         note="Retarget keyed lookup failure branch across the inserted primary preload"),
    dict(offset="0x0D0", expected="0x1000003A", replacement="0x1000003B",
         note="Retarget resolver failure branch across the inserted primary preload"),
    dict(offset="0x0D8", expected="0x8E2A0048", replacement="0x8E2A0048",
         note="Load resolved primary before testing the post-resolver attachment",
         insert_after="0x8FA50090"),
    dict(offset="0x0FC", expected="0x8FA50090", replacement="0x00000000",
         note="Retire the duplicate late primary reload after the eager preload"),
    dict(offset="0x138", expected="0x03233021", replacement="0x00793021",
         note="Use retail commutative delegated bank and index operand order"),
)


def complete_row(row):
    return {
        "filename": "game_16EE20",
        "function": route.FUNCTION,
        "offset": row["offset"],
        "expected": row["expected"],
        "replacement": row["replacement"],
        "expected_relocations": "-",
        "replacement_relocations": "-",
        "note": row["note"],
        "insert_after": row.get("insert_after", ""),
        "insert_after_relocations": "-" if row.get("insert_after") else "",
        "omit": "false",
    }


class GameMatrixRouteGuardedMatchTests(
        recovery.GameMatrixRouteBranchRecoveryTests):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guarded_output = (
            cls.root / "conker/build/game-matrix-route-guarded-match")
        cls.guarded_output.mkdir(exist_ok=True)
        cls.installed_source = (
            cls.root / "conker/src/game_16EE20.c").read_text()
        cls.installed = branch.SELECTED in cls.installed_source
        if cls.installed:
            candidate_source = cls.installed_source
        else:
            if cls.installed_source.count(layout.SELECTED) != 1:
                raise ValueError("Installed matrix-route source changed")
            candidate_source = cls.installed_source.replace(
                layout.SELECTED, branch.SELECTED)

        cls.owner_diagnostics = []
        cls.compact_owners = []
        for name, source in (
                ("baseline", cls.installed_source),
                ("candidate", candidate_source)):
            obj, diagnostics = recovery.prior.compile_owner(
                cls.root, cls.guarded_output, source, name + "-owner")
            cls.owner_diagnostics.append(
                [(item[0], item[2]) for item in diagnostics])
            processed = cls.guarded_output / (name + "-owner-processed.o")
            shutil.copyfile(obj, processed)
            subprocess.run([
                sys.executable,
                str(cls.root / "tools/asm-processor/asm_processor.py"),
                "-O2", "-g3",
                str((cls.guarded_output / (name + "-owner.c")).relative_to(
                    cls.root / "conker")),
                "--post-process",
                str(processed.relative_to(cls.root / "conker")),
                "--assembler",
                "mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 "
                "-mabi=32 -I include",
                "--asm-prelude", "include/asm_processor_prelude.inc",
            ], cwd=cls.root / "conker", check=True, capture_output=True)
            cls.compact_owners.append(processed)
        cls.candidate_owner = cls.compact_owners[1]

        source_patches = cls.root / "conker/retail_word_patches.us.csv"
        with source_patches.open(newline="") as stream:
            reader = csv.DictReader(stream)
            cls.patch_fields = reader.fieldnames
            cls.base_patch_rows = list(reader)
        existing = [row for row in cls.base_patch_rows
                    if row["function"] == route.FUNCTION]
        if cls.installed:
            if existing != [complete_row(row) for row in PATCH_ROWS]:
                raise ValueError("Installed matrix-route guards changed")
            cls.qualified_patch_rows = cls.base_patch_rows
        else:
            if existing:
                raise ValueError("Unexpected preexisting matrix-route guards")
            cls.qualified_patch_rows = (
                cls.base_patch_rows + [complete_row(row) for row in PATCH_ROWS])
        cls.patch_file = cls.guarded_output / "qualified-patches.csv"
        cls.write_patches(cls.patch_file, cls.qualified_patch_rows)

        qualified_source = cls.guarded_output / "qualified-owner.s"
        qualified_source.write_text(emit_padded_assembly(
            cls.candidate_owner,
            cls.root / "conker/retail_layout.us.txt",
            "game_16EE20",
            rodata_symbol="jtbl_800A5218_game",
            word_patches_path=cls.patch_file,
        ))
        cls.owner = cls.guarded_output / "qualified-owner.o"
        subprocess.run([
            "mips-linux-gnu-as", "-EB", "-mtune=vr4300",
            "-march=vr4300", "-mabi=32", "-I",
            str(cls.root / "conker/include"), "-o", str(cls.owner),
            str(qualified_source),
        ], check=True, capture_output=True)

        linker = (cls.root / "conker/build/conker.ld").read_text()
        old = "build/src/game_16EE20.c.o"
        new = str(cls.owner.relative_to(
            cls.root / "conker")).replace("\\", "/")
        if linker.count(old) != 1:
            raise ValueError("Matrix-route owner linker reference changed")
        script = cls.guarded_output / "qualified-image.ld"
        script.write_text(linker.replace(old, new))
        cls.elf = cls.guarded_output / "qualified-image.elf"
        subprocess.run([
            "mips-linux-gnu-ld", "-T",
            str(script.relative_to(cls.root / "conker")), "-Map",
            str((cls.guarded_output / "qualified-image.map").relative_to(
                cls.root / "conker")),
            "-T", "undefined_syms.us.txt", "-T", "undefined_funcs.us.txt",
            "-T", "undefined_syms_auto.txt", "-T",
            "undefined_funcs_auto.txt", "--no-check-sections",
            "--no-warn-mismatch", "-o",
            str(cls.elf.relative_to(cls.root / "conker")),
        ], cwd=cls.root / "conker", check=True, capture_output=True)

    @classmethod
    def write_patches(cls, path, rows):
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=cls.patch_fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_guarded_phase_is_exact_and_all_twelve_rows_fail_closed(self):
        self.assertEqual(
            (self.record["body_words"], self.record["frame"],
             self.record["differences"]),
            (119, 160, 74))
        self.assertEqual(self.owner_diagnostics[0], self.owner_diagnostics[1])
        self.assertEqual(len(self.owner_diagnostics[0]), 2)

        _, functions, relocations = parse_object(self.owner)
        target = functions[route.FUNCTION]
        self.assertEqual(target["size"], 480)
        target_relocations = {
            offset - target["value"]: rows
            for offset, rows in relocations.items()
            if target["value"] <= offset < target["value"] + target["size"]
        }
        self.assertEqual(target_relocations, {
            0x05C: [("R_MIPS_HI16", "D_800BE9C0")],
            0x070: [("R_MIPS_LO16", "D_800BE9C0")],
            0x09C: [("R_MIPS_26", "func_1503195C")],
            0x0C0: [("R_MIPS_26", "func_15031070")],
            0x10C: [("R_MIPS_HI16", "D_800BE9C0")],
            0x118: [("R_MIPS_LO16", "D_800BE9C0")],
            0x138: [("R_MIPS_26", "func_15145EA4")],
            0x150: [("R_MIPS_26", "guMtxL2F")],
            0x194: [("R_MIPS_26", "func_150A7960")],
        })
        self.assertEqual(
            same_functions(
                self.root / "conker/build/src/game_16EE20.c.o",
                self.owner, (route.FUNCTION,)),
            88)
        self.assertEqual(
            normalized_pools(self.root / "conker/build/src/game_16EE20.c.o"),
            normalized_pools(self.owner))

        qualified, _, _ = load_elf_functions(
            str(self.elf), "mips-linux-gnu-objdump")
        self.assertEqual(qualified[route.FUNCTION], self.retail)

        target_indices = [
            index for index, row in enumerate(self.qualified_patch_rows)
            if row["function"] == route.FUNCTION
        ]
        self.assertEqual(len(target_indices), 12)
        for sequence, index in enumerate(target_indices):
            stale = [dict(row) for row in self.qualified_patch_rows]
            stale[index]["expected"] = "0xDEADBEEF"
            path = self.guarded_output / ("stale-%d.csv" % sequence)
            self.write_patches(path, stale)
            with self.assertRaisesRegex(ValueError, "stale .*word patch"):
                emit_padded_assembly(
                    self.candidate_owner,
                    self.root / "conker/retail_layout.us.txt",
                    "game_16EE20",
                    rodata_symbol="jtbl_800A5218_game",
                    word_patches_path=path,
                )

    def test_strict_image_protected_data_and_installed_state(self):
        old, _, old_addresses = load_elf_functions(
            str(self.root / "conker/build/conker.us.elf"),
            "mips-linux-gnu-objdump")
        new, _, new_addresses = load_elf_functions(
            str(self.elf), "mips-linux-gnu-objdump")
        self.assertEqual((old.keys(), old_addresses),
                         (new.keys(), new_addresses))
        changed = [name for name in old if old[name] != new[name]]
        self.assertEqual(changed, [] if self.installed else [route.FUNCTION])
        self.assertEqual(new[route.FUNCTION], self.retail)
        report = audit_layout(self.elf, self.root / "conker")
        self.assertEqual(
            (report["exact"], report["bytes"], report["owner_count"],
             report["different_bytes"], report["different_owner_count"]),
            (True, 189088, 720, 0, 0))
        if self.installed:
            self.assertIn(branch.SELECTED, self.installed_source)
            with (self.root / "conker/retail_word_patches.us.csv").open(
                    newline="") as stream:
                rows = [row for row in csv.DictReader(stream)
                        if row["function"] == route.FUNCTION]
            self.assertEqual(rows, [complete_row(row) for row in PATCH_ROWS])


if __name__ == "__main__":
    import unittest
    unittest.main()
