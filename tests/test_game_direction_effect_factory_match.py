"""Directional-effect factory bytes, semantics, caller, native control and image."""
from pathlib import Path
import json
import os
import struct
import unittest

from tools.experiments import game_direction_effect_factory_match as source
from tools.tests import game_direction_effect_factory_oracle as oracle
from tools.tests import game_direction_effect_factory_integration as integration
from tools.tests import game_direction_effect_factory_native as native


ROOT = Path(os.environ.get("CBFD_CONSUMER_ROOT", Path(__file__).resolve().parents[2]))


class DirectionEffectFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        source.verify_prepared(cls.output)
        cls.installed = os.environ.get("CBFD_DIRECTION_EFFECT_FACTORY_INSTALLED") == "1"
        cls.values = source.check_inputs(ROOT, cls.output, cls.installed)

    def test_01_raw_payload_bindings_closed_words_extents_and_links(self):
        obj, diagnostics = source.compile_owner(
            ROOT, self.output, source.HEADERS + source.SELECTED, "public-fresh-" + source.FUNCTION
        )
        self.assertFalse(diagnostics)
        raw, refs = source.checked_payload(*source.payload(obj, source.FUNCTION))
        original, original_refs = source.payload(
            self.output / ("original-" + source.FUNCTION + ".o"), source.FUNCTION)
        normalized, normalized_refs = source.payload(self.output / "normalized.o", source.FUNCTION)
        self.assertEqual(refs, source.RAW_BINDINGS)
        self.assertEqual(original_refs, source.RETAIL_BINDINGS)
        self.assertEqual((normalized, normalized_refs), (original, original_refs))
        self.assertEqual(sum(a != b for a, b in zip(
            struct.unpack(">128I", raw), struct.unpack(">128I", original))), 31)
        self.assertEqual((struct.unpack_from(">I", raw)[0], struct.unpack_from(">I", normalized)[0]),
                         (0x27BDFF68, 0x27BDFF70))
        proposed = (self.output / ("proposed-" + source.OWNER + ".c")).read_text()
        self.assertIn("void " + source.FUNCTION + "(DirectionEffectInput *arg0, s32 arg1, s32 arg2)",
                      proposed)
        self.assertIn("randomized directional effects from a complete live configuration", proposed)
        with self.assertRaises(ValueError):
            source.checked_payload(raw[:-4], refs)
        with self.assertRaises(ValueError):
            source.checked_payload(raw, {})
        q = json.loads((self.output / "private-layout-v1.json").read_text())
        self.assertEqual((q["words"], q["retail_frame"], q["raw_frame"],
                          q["proposed_closed_normalizations"], len(q["layouts"])),
                         (128, 144, 152, 31, 3))
        for index in range(3):
            entry = q["layouts"][index]["entry"]
            images = {}
            for label in ("original", "C", "raw"):
                image = (self.output / ("layout-%d-%s.elf" % (index, label))).read_bytes()
                at = source.elf_slot_offset(image, entry, source.SIZE)
                images[label] = image[at:at + source.SIZE]
            self.assertEqual(images["original"], images["C"])
            self.assertEqual(sum(a != b for a, b in zip(
                struct.unpack(">128I", images["original"]),
                struct.unpack(">128I", images["raw"]))), 31)

    def test_02_guest_state_calls_complete_payloads_and_coverage(self):
        q = oracle.qualify(ROOT, self.output)
        self.assertEqual((q["cases_per_layout"], q["independent_GNU_links"], q["executions"],
                          q["covered_nontrap_words"], q["unreachable_unsigned_divisor_traps"]),
                         (256, 3, 2304, 124, 4))
        self.assertEqual(q["request_counts"], [0, 1, 2])
        self.assertTrue(q["all256_target_channel_bytes"])
        self.assertTrue(q["all11_provider_arguments_and_complete_input_scratch_snapshots"])
        self.assertTrue(q["live_input_after_count_RNG_direction_and_provider"])
        self.assertTrue(q["original_and_normalized_full_state_trace_equal"])
        self.assertTrue(q["raw_C_public_memory_calls_complete_payloads_equal"])

    def test_03_complete_original_caller_census_and_o32_abi(self):
        q = integration.qualify(ROOT, self.output)
        self.assertEqual((q["original_callers"], q["unique_parents"]), (1, 1))
        self.assertEqual((q["input_natural_bytes"], q["input_required_bytes"],
                          q["caller_written_bytes"]), (60, 54, 58))
        self.assertEqual(len(q["aligned_ROM_JALs"]), 1)
        self.assertFalse(q["aligned_ROM_Js"])
        self.assertEqual(q["caller_unwritten_bytes"], ["0x2A", "0x2B"])
        self.assertTrue(q["all_required_input_bytes_have_pre_call_store_evidence"])
        self.assertFalse(q["full_parent_execution_claimed"])

    def test_04_native_o0_o2_o3_live_reads_layouts_and_ubsan(self):
        q = native.qualify(self.output)
        self.assertEqual((q["cases_per_profile"], q["total_executions"]), (256, 768))
        self.assertEqual([row["optimization"] for row in q["profiles"]], ["O0", "O2", "O3"])
        self.assertTrue(all(row["UBSan_clean"] for row in q["profiles"]))
        self.assertEqual((q["input_natural_bytes"], q["input_required_bytes"],
                          q["scratch_visible_bytes"]), (60, 54, 12))
        self.assertTrue(q["all11_provider_arguments_and_complete_input_scratch_snapshots"])
        self.assertTrue(q["post_count_RNG_live_read_delegated_to_guest_oracle"])

    def test_05_actual_make_neighbors_guards_protected_data_and_strict_image(self):
        self.assertEqual(source.same_functions(
            self.output / ("before-" + source.OWNER + ".o"),
            self.output / ("after-" + source.OWNER + ".o"), (source.FUNCTION,)), 40)
        self.assertEqual(source.normalized_pools(self.output / ("before-" + source.OWNER + ".o")),
                         source.normalized_pools(self.output / ("after-" + source.OWNER + ".o")))
        self.assertEqual((self.output / ("qualified-" + source.OWNER + ".o")).read_bytes(),
                         (self.output / ("make-shadow-" + source.OWNER + "/src/game/" +
                                         source.OWNER + ".c.o")).read_bytes())
        self.assertEqual(len(json.loads(
            (self.output / ("Make-commands-" + source.OWNER + ".json")).read_text())), 5)
        self.assertEqual((self.output / "proposed-guards.csv").read_bytes().count(
            b"," + source.FUNCTION.encode() + b","), 31)
        q = source.audit(ROOT, self.output, self.installed)
        self.assertEqual((q["functions"], q["other_bodies_fixed"], q["strict_exclusions"]),
                         (6052, 6051, 0))
        self.assertTrue(q["all_function_addresses_fixed"])
        self.assertEqual(source.expected_map(self.output), self.values["conker/build/conker.us.map"])
        before = self.values["conker/build/conker.us.elf"]
        rom = (ROOT / "conker/conker.us.bin").read_bytes()
        actual = ((ROOT / "conker/build/conker.us.elf") if self.installed else
                  (self.output / "private-joint-linked.elf")).read_bytes()
        for at in (0x100, len(actual) - 1,
                   source.elf_slot_offset(actual, source.ENTRY, source.SIZE) + 24):
            bad = bytearray(actual)
            bad[at] ^= 1
            with self.assertRaises(ValueError):
                source.check_image(before, bytes(bad), rom)


if __name__ == "__main__":
    unittest.main()
