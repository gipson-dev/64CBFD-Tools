"""func_150CB0E0: exact C, callback semantics, caller route, and image closure."""

import json
import os
from pathlib import Path
import struct
import unittest

from tools.experiments import game_transformed_height_probe_match as source
from tools.tests import game_transformed_height_probe_oracle as oracle


ROOT = Path(__file__).resolve().parents[2]


class TransformedHeightProbeTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD / ("test-run-" + str(os.getpid()))
        cls.values = source.prepare(ROOT, cls.output)
        oracle.ROOT = ROOT
        oracle.OUTPUT = cls.output

    @classmethod
    def tearDownClass(cls):
        (cls.output / "test-receipt.json").write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_fresh_source_is_direct_exact_C(self):
        report = self.values["report"]
        self.assertEqual(report["function"], source.FUNCTION)
        self.assertEqual(report["words"], 64)
        self.assertEqual(report["natural_frame"], 56)
        self.assertEqual(report["retail_frame"], 56)
        self.assertEqual(report["natural_positional_differences"], 0)
        self.assertEqual(report["guards"], 0)
        self.assertEqual(report["relocations"], 7)
        self.assertEqual(report["changed_bodies"], [source.FUNCTION])
        self.assertEqual(report["strict_exclusions"], 0)
        self.receipt["fresh_C"] = {
            "words": 64, "bytes": 256, "frame": 56,
            "raw_C_byte_exact": True, "guards": 0,
            "relocations": 7, "neighbors": report["neighbors"],
        }

    def test_02_guest_callbacks_aliases_live_height_and_coverage(self):
        result = oracle.run_suite()
        self.assertEqual(result["cases"], 15360)
        self.assertEqual(result["executions"], 46080)
        self.assertEqual(result["covered_reachable_words"], 63)
        self.assertEqual(result["unreachable_duplicate_word"], "0x150cb178")
        self.receipt["guest"] = result

    def test_03_native32_UBSan_and_twelve_controls(self):
        result = oracle.run_native(source.candidate.SELECTED)
        self.assertEqual(result["cases"], 15360)
        self.assertEqual(result["negative_controls"], 12)
        self.assertEqual(set(result["profiles"]), {"-O0", "-O2", "-O3"})
        self.receipt["native"] = result

    def test_04_frame_homes_and_unreachable_duplicate_load(self):
        raw, bindings = source.function_blob(self.values["qualified_compact"])
        words = struct.unpack(">64I", raw)
        self.assertEqual(
            (words[0], words[1], words[2], words[6], words[61], words[62]),
            (0x27BDFFC8, 0xAFB00018, 0xAFA70044,
             0xAFBF001C, 0x27BD0038, 0x03E00008))
        self.assertEqual(words[34], 0x54800004)
        self.assertEqual(words[35], 0xC6040000)
        self.assertEqual(words[38], 0xC6040000)
        stores = {(word >> 16 & 31, word & 0xFFFF)
                  for word in words
                  if word >> 26 == 43 and word >> 21 & 31 == 29}
        self.assertEqual(stores, {(16, 24), (31, 28), (7, 68),
                                  (5, 60), (6, 64)})
        self.assertEqual(bindings, source.BINDINGS)
        self.receipt["frame"] = {
            "frame": 56, "RA_offset": 28, "S0_offset": 24,
            "local_ray_offset": 44, "local_ray_bytes": 12,
            "incoming_home_offsets": [60, 64, 68],
            "reachable_words": 63, "body_words": 64,
            "unreachable_word_offset": 152,
        }

    def test_05_raw_binding_and_semantic_source_controls(self):
        raw, bindings = source.function_blob(self.values["qualified_compact"])
        controls = 0
        for index in range(len(raw)):
            changed = bytearray(raw)
            changed[index] ^= 1
            with self.assertRaises(ValueError):
                source.checked_payload(ROOT, bytes(changed), bindings)
            controls += 1
        for offset in bindings:
            changed = dict(bindings)
            changed[offset] = [("R_MIPS_26", "wrong_symbol")]
            with self.assertRaises(ValueError):
                source.checked_payload(ROOT, raw, changed)
            controls += 1
        for old, new in (
                ("mode != 1 && mode != 2", "mode != 1 && mode != 3"),
                ("+ 0xA00", "+ 0xA04"),
                ("+ 0xBC0", "+ 0xBC4"),
                ("+ 100.0f", "+ 99.0f"),
                ("- 500.0f", "- 499.0f")):
            changed = source.candidate.SELECTED.replace(old, new, 1)
            self.assertNotEqual(changed, source.candidate.SELECTED)
            predecessor, _, _ = source.source_states(
                (ROOT / source.SOURCE).read_text())
            control_source = predecessor.replace(
                source.candidate.ANCHOR,
                source.candidate.ANCHOR + source.candidate.DECLARATIONS,
                1).replace(source.candidate.PLACEHOLDER, changed, 1)
            candidate_object, diagnostics = source.candidate.compile_owner(
                ROOT, self.output, control_source,
                "source-control-" + str(controls))
            self.assertFalse(diagnostics)
            with self.assertRaises(ValueError):
                source.checked_candidate(ROOT, candidate_object)
            controls += 1
        self.receipt["controls"] = {
            "raw_and_binding_controls": controls - 5,
            "fresh_source_controls": 5,
        }

    def test_06_caller_route_image_and_protected_data(self):
        report = self.values["report"]
        self.assertEqual(report["registry"], {
            "direct_jal_calls": ["0xf86d4"],
            "aligned_pointer_literals": [],
            "caller": "func_150CB1F4",
            "abi": "position output, actor, optional height result, unsigned mode",
        })
        self.assertEqual(report["functions"], 6051)
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(
            (report["game_data"]["exact"], report["game_data"]["bytes"],
             report["game_data"]["owner_count"],
             report["game_data"]["different_bytes"]),
            (True, 189088, 720, 0))
        self.assertEqual(
            report["game_data"]["sha256"],
            "0bbc00e1adfac5ffe6117f5be9c941575f87b341a77d808004603ac1cb87c670")
        self.receipt["closure"] = {
            "functions": 6051, "changed_only_target": True,
            "addresses_fixed": True, "strict_exclusions": 0,
            "protected_Game_bytes": 189088, "protected_owners": 720,
            "protected_data_exact": True,
        }


if __name__ == "__main__":
    unittest.main()
