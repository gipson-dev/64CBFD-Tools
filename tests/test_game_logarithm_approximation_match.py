"""Natural logarithm: semantic C, checked schedule, caller and image closure."""

import csv
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_logarithm_approximation_match as source
from tools import pad_c_object
from tools.match_progress import load_elf_functions
from tools.tests import game_logarithm_approximation_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command


ROOT = Path(__file__).resolve().parents[2]


class GameLogarithmApproximationMatchTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD / ("test-run-" + str(os.getpid()))
        cls.values = source.prepare(ROOT, cls.output)
        cls.predecessor = load_elf_functions(
            str(cls.values["predecessor_elf"]), "mips-linux-gnu-objdump")[0][source.FUNCTION]
        cls.retail = load_elf_functions(
            str(cls.values["qualified_elf"]), "mips-linux-gnu-objdump")[0][source.FUNCTION]
        cls.owner_text = source.source_states((ROOT / source.SOURCE).read_text())[1]
        cls.body = oracle.semantic_body(cls.owner_text)

    @classmethod
    def tearDownClass(cls):
        (cls.output / "test-receipt.json").write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_complete_checked_slot_and_relocations(self):
        report = self.values["report"]
        self.assertEqual(report["function"], source.FUNCTION)
        self.assertEqual(report["words"], 68)
        self.assertEqual(report["natural_frame"], 0)
        self.assertEqual(report["retail_frame"], 0)
        self.assertEqual(report["natural_positional_differences"], 41)
        self.assertEqual(report["guards"], 41)
        self.assertEqual(report["compiler_words"], 65)
        self.assertEqual(report["insertions"], 3)
        self.assertEqual(report["omissions"], 0)
        self.assertEqual(self.retail, list(struct.unpack(
            ">68I", source.retail_bytes(ROOT))))
        raw, bindings = source.function_blob(self.values["qualified_owner"])
        self.assertEqual(len(raw), 272)
        self.assertEqual(bindings, source.RETAIL_BINDINGS)
        self.assertEqual(raw, source.retail_object_bytes(ROOT))
        self.assertEqual(
            sorted(row["offset"] for row in source.PATCH_ROWS if row["insert_after"]),
            ["0x014", "0x02C", "0x0A4"])
        self.receipt["shape"] = {
            "retail_words": 68, "compiler_words": 65, "frame": 0,
            "guards": 41, "insertions": 3, "omissions": 0,
            "natural_relocations": 4, "retail_relocations": 4,
        }

    def test_02_guest_semantics_and_complete_word_coverage(self):
        result = oracle.run_suite(self.predecessor, self.retail)
        self.assertEqual(result["cases"], 1040)
        self.assertEqual(result["executions"], 2080)
        self.assertEqual(result["natural_words_covered"], 63)
        self.assertEqual(result["retail_words_covered"], 66)
        self.receipt["guest"] = result

    def test_03_native32_three_profiles_and_fifteen_controls(self):
        profiles = {}
        fixture = oracle.native_harness(self.body)
        for profile in ("-O0", "-O2", "-O3"):
            path = self.output / ("native" + profile + ".c")
            path.write_text(fixture)
            executable = path.with_suffix("")
            build = subprocess.run(
                native_command(profile) + [str(path), "-o", str(executable)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(executable)], capture_output=True, timeout=15)
            self.assertEqual(run.returncode, 0, (profile, run.stderr))
            profiles[profile] = {"cases": 1040, "exit": 0, "UBSan": True}
        rejected = {}
        for name, body in oracle.controls(self.body).items():
            path = self.output / ("control-" + name + ".c")
            path.write_text(oracle.native_harness(body))
            executable = path.with_suffix("")
            build = subprocess.run(
                native_command("-O2") + [str(path), "-o", str(executable)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, (name, build.stderr))
            try:
                run = subprocess.run([str(executable)], capture_output=True, timeout=3)
                self.assertNotEqual(run.returncode, 0, name)
                rejected[name] = "output mismatch"
            except subprocess.TimeoutExpired:
                rejected[name] = "bounded nontermination"
        self.assertEqual(len(rejected), 15)
        self.receipt["native"] = {"profiles": profiles, "controls": rejected}

    def test_04_raw_binding_and_every_guard_preimage_fail_closed(self):
        raw, bindings = source.function_blob(self.values["qualified_compact"])
        source.checked_payload(ROOT, raw, bindings)
        raw_controls = 0
        for index in range(len(raw)):
            changed = bytearray(raw)
            changed[index] ^= 1
            with self.assertRaises(ValueError):
                source.checked_payload(ROOT, bytes(changed), bindings)
            raw_controls += 1
        for offset in bindings:
            changed = dict(bindings)
            changed[offset] = [("R_MIPS_HI16", "wrong_symbol")]
            with self.assertRaises(ValueError):
                source.checked_payload(ROOT, raw, changed)
            raw_controls += 1
        fields = (
            "filename", "function", "offset", "expected", "replacement",
            "expected_relocations", "replacement_relocations", "note",
            "insert_after", "insert_after_relocations", "omit")
        guard_controls = 0
        expected = [source.complete_row(row) for row in source.PATCH_ROWS]
        for index in range(len(expected)):
            rows = [dict(row) for row in expected]
            rows[index]["expected"] = hex(int(rows[index]["expected"], 0) ^ 1)
            manifest = self.output / ("guard-control-%02d.csv" % index)
            with manifest.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaises(ValueError):
                pad_c_object.emit_padded_assembly(
                    self.values["qualified_compact"], ROOT / source.ASM,
                    source.FILENAME, word_patches_path=manifest)
            guard_controls += 1
        self.assertEqual((raw_controls, guard_controls), (264, 41))
        self.receipt["controls"] = {
            "raw_and_binding_controls": raw_controls,
            "guard_preimage_controls": guard_controls,
        }

    def test_05_caller_owner_image_and_protected_data(self):
        report = self.values["report"]
        self.assertEqual(report["registry"], {
            "direct_jal_calls": ["0x77994"],
            "aligned_pointer_literals": [],
            "caller": "func_1504A400 (retail raw assembly)",
            "current_linked_caller": "zero-return placeholder; no live-call claim",
            "abi": "binary32 input in f12; binary32 result in f0 is multiplied by saved f14",
        })
        self.assertEqual(report["neighbors"], 57)
        self.assertEqual(report["functions"], 6051)
        self.assertEqual(report["changed_bodies"], [source.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(
            (report["game_data"]["exact"], report["game_data"]["bytes"],
             report["game_data"]["owner_count"],
             report["game_data"]["different_bytes"]),
            (True, 189088, 720, 0))
        self.assertEqual(
            report["game_data"]["sha256"],
            "0bbc00e1adfac5ffe6117f5be9c941575f87b341a77d808004603ac1cb87c670")
        self.receipt["closure"] = {
            "retail_caller": "func_1504A400", "direct_calls": 1,
            "current_caller_stub_boundary": True, "neighbors": 57,
            "functions": 6051, "changed_only_target": True,
            "all_addresses_fixed": True, "strict_exclusions": 0,
            "protected_Game_bytes": 189088, "protected_owners": 720,
            "protected_data_exact": True,
        }


if __name__ == "__main__":
    unittest.main()
