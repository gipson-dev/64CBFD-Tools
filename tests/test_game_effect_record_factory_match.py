"""Effect-record factory bytes, semantics, callers, owner and whole-image gates."""

from pathlib import Path
import json
import os
import unittest

from tools.experiments import game_effect_record_factory_match as source
from tools.tests import game_effect_record_factory_oracle as oracle
from tools.tests import game_effect_record_factory_integration as integration
from tools.tests import game_effect_record_factory_native as native


ROOT = Path(os.environ.get("CBFD_CONSUMER_ROOT", Path(__file__).resolve().parents[2]))


class EffectRecordFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        source.prepare(ROOT, cls.output)
        cls.is_installed = source.installed(ROOT, cls.output)

    def test_01_fresh_semantic_c_is_direct_byte_match(self):
        obj, diagnostics = source.compile_owner(ROOT, self.output,
            source.HEADERS + source.SELECTED, "public-fresh-selected")
        self.assertFalse(diagnostics)
        self.assertEqual(source.checked_payload(*source.payload(obj, source.FUNCTION)),
                         source.payload(source.before_path(self.output, source.OBJECT),
                                        source.FUNCTION))
        wrong = source.SELECTED.replace("created[0x68] |= (u8)callback",
                                        "created[0x68] = (u8)callback")
        control, diagnostics = source.compile_owner(ROOT, self.output,
            source.HEADERS + wrong, "public-wrong-callback-store")
        self.assertFalse(diagnostics)
        with self.assertRaises(ValueError):
            source.checked_payload(*source.payload(control, source.FUNCTION))
        report = json.loads((self.output / "private-preparation.json").read_text())
        self.assertEqual((report["words"], report["frame"], report["guards"],
                          report["bindings"]), (54, 56, 0, 3))

    def test_02_guest_all_branches_live_reads_and_complete_copy(self):
        report = oracle.qualify(ROOT, self.output, source)
        self.assertEqual((report["cases_per_layout"], report["independent_links"],
                          report["executions"], report["covered_words"],
                          report["unreachable_duplicate_load_words"]),
                         (256, 3, 768, 53, 1))
        self.assertTrue(report["all256_callback_and_slot_bytes"])
        self.assertTrue(report["live_descriptor_mutations_after_helper_and_allocator"])
        self.assertTrue(report["complete_88_byte_copy_checked"])

    def test_03_complete_original_caller_census_and_o32_stack_ABI(self):
        report = integration.qualify(ROOT, self.output)
        self.assertEqual(report["original_callers"], 43)
        self.assertEqual(len(report["aligned_ROM_JALs"]), 43)
        self.assertTrue(report["seven_argument_O32_ABI"])
        self.assertTrue(report["all_callers_materialize_stack_arguments_5_6_7"])
        self.assertFalse(report["complete_parent_execution_claimed"])

    def test_04_native_profiles_and_effective_controls(self):
        report = native.qualify(ROOT, self.output, source.SELECTED)
        self.assertEqual(report["total_executions"], 768)
        self.assertEqual([row["optimization"] for row in report["profiles"]],
                         ["-O0", "-O2", "-O3"])
        for row in report["profiles"]:
            self.assertEqual((row["cases"], row["negative_controls"]), (256, 6))
            self.assertTrue(row["UBSan_clean"])

    def test_05_owner_padder_protected_data_and_strict_image(self):
        report = source.verify_prepared(self.output)
        self.assertEqual(report["neighbors"], 40)
        self.assertTrue(report["padded_owner_object_byte_identical"])
        self.assertTrue(report["normalized_pools_unchanged"])
        audit = source.audit(ROOT, self.output, self.is_installed)
        self.assertEqual((audit["functions"], audit["other_bodies_fixed"],
                          audit["strict_exclusions"]), (6052, 6051, 0))
        self.assertEqual((audit["protected_data"]["exact"],
                          audit["protected_data"]["bytes"],
                          audit["protected_data"]["owner_count"]),
                         (True, 189088, 720))


if __name__ == "__main__":
    unittest.main()
