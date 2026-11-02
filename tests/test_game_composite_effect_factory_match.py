"""Composite-effect factory direct bytes, semantics, callers and strict image."""
from pathlib import Path
import json
import os
import struct
import unittest

from tools.experiments import game_composite_effect_factory_match as source
from tools.tests import game_composite_effect_factory_oracle as oracle
from tools.tests import game_composite_effect_factory_integration as integration
from tools.tests import game_composite_effect_factory_native as native


ROOT = Path(os.environ.get("CBFD_CONSUMER_ROOT", Path(__file__).resolve().parents[2]))


class CompositeEffectFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        source.verify_prepared(cls.output)
        cls.installed = os.environ.get("CBFD_COMPOSITE_EFFECT_FACTORY_INSTALLED") == "1"
        cls.values = source.check_inputs(ROOT, cls.output, cls.installed)

    def test_01_direct_payload_bindings_extents_and_independent_links(self):
        obj, diagnostics = source.compile_owner(
            ROOT, self.output, source.HEADERS + source.SELECTED, "public-fresh-" + source.FUNCTION
        )
        self.assertFalse(diagnostics)
        raw, refs = source.checked_payload(*source.payload(obj, source.FUNCTION))
        original, bindings = source.payload(self.output / ("original-" + source.FUNCTION + ".o"), source.FUNCTION)
        self.assertEqual((raw, refs), (original, bindings))
        self.assertEqual(struct.unpack_from(">I", raw)[0], 0x27BDFF50)
        proposed = (self.output / ("proposed-" + source.OWNER + ".c")).read_text()
        self.assertIn("void " + source.FUNCTION + "(CompositeEffectInput *input, u8 mode, s32 extra)", proposed)
        self.assertIn("complete private scratch extents", proposed)
        with self.assertRaises(ValueError):
            source.checked_payload(raw[:-4], refs)
        with self.assertRaises(ValueError):
            source.checked_payload(raw, {})
        q = json.loads((self.output / "private-layout-v5.json").read_text())
        self.assertEqual((q["words"], q["frame"], q["guards"], len(q["layouts"])), (270, 176, 0, 3))
        self.assertEqual(
            (q["input_bytes"], q["packet_private_extent_bytes"], q["header_private_extent_bytes"], q["complete_scratch_bytes"], q["private_tail_bytes"]),
            (116, 60, 24, 88, 6),
        )
        for index in range(3):
            entry = q["layouts"][index]["entry"]
            original_image = (self.output / ("layout-%d-original.elf" % index)).read_bytes()
            c_image = (self.output / ("layout-%d-C.elf" % index)).read_bytes()
            original_at = source.elf_slot_offset(original_image, entry, source.SIZE)
            c_at = source.elf_slot_offset(c_image, entry, source.SIZE)
            self.assertEqual(original_image[original_at:original_at + source.SIZE], c_image[c_at:c_at + source.SIZE])

    def test_02_guest_full_state_payloads_traces_and_access_prefixes(self):
        q = oracle.qualify(ROOT, self.output)
        self.assertEqual((q["cases"], q["executions"], q["covered_nontrap_words"], q["unreachable_divisor_traps"]), (256, 512, 256, 14))
        self.assertEqual((q["semantic_layouts"], q["independent_GNU_links"], q["access_prefix_pairs"]), (1, 3, 261))
        self.assertTrue(q["original_and_C_full_state_calls_payloads_and_traces_equal"])
        self.assertTrue(q["live_input_after_first_RNG_and_after_submit"])

    def test_03_all_original_callers_and_o32_abi(self):
        q = integration.qualify(ROOT, self.output)
        self.assertEqual((q["original_callers"], q["unique_parents"], q["required_input_bytes"]), (13, 13, 110))
        self.assertEqual(len(q["aligned_ROM_JALs"]), 13)
        self.assertFalse(q["aligned_ROM_Js"])
        self.assertFalse(q["aligned_ROM_pointer_literals"])
        self.assertTrue(q["all_required_input_bytes_have_pre_call_store_evidence"])
        self.assertIn("six callers use LW", q["argument_contract"]["extra"])
        self.assertFalse(q["full_parent_execution_claimed"])

    def test_04_native_layout_live_reads_full_extra_and_effective_controls(self):
        q = native.qualify(ROOT, self.output, source.SELECTED, source.HEADERS)
        self.assertEqual((q["cases_per_profile"], q["effective_controls_each"]), (256, 11))
        self.assertEqual(q["profiles"], ["O0", "O2", "O3"])
        self.assertEqual((q["input_size"], q["packet_private_extent"], q["header_private_extent"], q["complete_scratch_bytes"]), (116, 60, 24, 88))
        self.assertTrue(q["UBSan"])
        self.assertTrue(q["all256_mode_bytes"])
        self.assertTrue(q["full_32bit_extra"])
        self.assertTrue(q["live_input_after_first_RNG_and_submit"])

    def test_05_actual_make_neighbors_protected_data_and_strict_image(self):
        for before, after in (
            ("before-" + source.OWNER + ".o", "after-" + source.OWNER + ".o"),
            ("before-padded-" + source.OWNER + ".o", "qualified-" + source.OWNER + ".o"),
        ):
            self.assertEqual(source.same_functions(self.output / before, self.output / after, (source.FUNCTION,)), 40)
            self.assertEqual(source.normalized_pools(self.output / before), source.normalized_pools(self.output / after))
        self.assertEqual(
            (self.output / ("qualified-" + source.OWNER + ".o")).read_bytes(),
            (self.output / ("make-shadow-" + source.OWNER + "/src/game/" + source.OWNER + ".c.o")).read_bytes(),
        )
        self.assertEqual(len(json.loads((self.output / ("Make-commands-" + source.OWNER + ".json")).read_text())), 5)
        q = source.audit(ROOT, self.output, self.installed)
        self.assertEqual((q["functions"], q["other_bodies_fixed"], q["strict_exclusions"], q["closed_metadata_groups"]), (6052, 6051, 0, 0))
        self.assertTrue(q["all_function_addresses_fixed"])
        self.assertEqual(source.expected_map(self.output), self.values["conker/build/conker.us.map"])
        before = self.values["conker/build/conker.us.elf"]
        rom = (ROOT / "conker/conker.us.bin").read_bytes()
        actual = ((ROOT / "conker/build/conker.us.elf") if self.installed else (self.output / "private-joint-linked.elf")).read_bytes()
        for at in (0x100, len(actual) - 1, source.elf_slot_offset(actual, source.ENTRY, source.SIZE) + 24):
            bad = bytearray(actual)
            bad[at] ^= 1
            with self.assertRaises(ValueError):
                source.check_image(before, bytes(bad), rom)


if __name__ == "__main__":
    unittest.main()
