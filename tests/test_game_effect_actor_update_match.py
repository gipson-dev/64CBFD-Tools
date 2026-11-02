"""Effect-actor update bytes, guest/native semantics, registration and complete image."""
from pathlib import Path
import json
import os
import subprocess
import unittest

from tools.experiments import game_effect_actor_update_match as source
from tools.tests import game_effect_actor_update_oracle as oracle
from tools.tests import game_effect_actor_update_native as native
from tools.tests import game_effect_actor_update_integration as integration
from tools.pad_generated_object import emit_padded_assembly


ROOT = Path(os.environ.get("CBFD_CONSUMER_ROOT", Path(__file__).resolve().parents[2]))


class EffectActorUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        source.verify_prepared(cls.output)
        cls.installed = (ROOT / source.SOURCE).read_bytes() == (
            cls.output / "proposed-generated_17CAF0.c").read_bytes()

    def test_01_fresh_semantic_c_is_direct_byte_match(self):
        obj, diagnostics = source.compile_owner(ROOT, self.output,
            source.HEADERS + source.SELECTED, "public-fresh-selected")
        self.assertFalse(diagnostics)
        self.assertEqual(source.checked_payload(*source.payload(obj)),
                         source.payload(ROOT / source.OBJECT))
        bad = source.SELECTED.replace("payload[0] -= D_800BE9A4",
                                      "payload[0] += D_800BE9A4")
        control, diagnostics = source.compile_owner(ROOT, self.output,
            source.HEADERS + bad, "public-wrong-lifetime")
        self.assertFalse(diagnostics)
        with self.assertRaises(ValueError):
            source.checked_payload(*source.payload(control))
        self.assertEqual(source.NEW_GUARDS, [])

    def test_02_guest_state_branches_live_reads_and_rebases(self):
        report = oracle.qualify(ROOT, self.output, source)
        self.assertEqual((report["cases_per_layout"], report["independent_links"],
                          report["executions"], report["words"], report["covered_words"]),
                         (256, 3, 768, 130, 90))
        self.assertTrue(report["positive_zero_negative_lifetime"])
        self.assertTrue(report["all256_opacity_inputs"])
        self.assertTrue(report["live_sine_mutations"])
        self.assertTrue(report["original_and_raw_C_words_equal"])

    def test_03_native_profiles_and_original_registration(self):
        report = native.qualify(ROOT, self.output, source.SELECTED)
        self.assertEqual(report["total_executions"], 768)
        self.assertEqual([row["optimization"] for row in report["profiles"]],
                         ["-O0", "-O2", "-O3"])
        for row in report["profiles"]:
            self.assertEqual((row["cases"], row["negative_controls"]), (256, 5))
            self.assertTrue(row["UBSan_clean"] and row["canaries"])
        caller = integration.qualify(ROOT, self.output)
        self.assertEqual(caller["aligned_ROM_pointer_literals"], ["0x22e3b8"])
        self.assertEqual((caller["registration_index"], caller["ABI"]),
                         (18, "s32(u8 *actor)"))
        self.assertFalse(caller["aligned_ROM_JALs"] or caller["aligned_ROM_Js"])

    def test_04_complete_owner_padder_and_actual_make_object(self):
        before = source.before_path(self.output, source.SOURCE).read_text()
        obj, diagnostics = source.compile_owner(ROOT, self.output,
            source.recovered_owner(before), "public-fresh-owner")
        self.assertFalse(diagnostics)
        assembly = emit_padded_assembly(obj, ROOT / source.ASM,
            word_patches_path=ROOT / "conker/retail_word_patches.us.csv",
            filename=source.OWNER)
        path = self.output / "public-fresh-padded.s"
        path.write_text(assembly)
        built = self.output / "public-fresh-padded.o"
        subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300",
            "-march=vr4300", "-mabi=32", "-I", str(ROOT / "conker/include"),
            "-o", str(built), str(path)], check=True)
        qualified = self.output / "qualified-padded.o"
        self.assertEqual(built.read_bytes(), qualified.read_bytes())
        actual = self.output / "make-shadow-generated_17CAF0/src/game/generated_17CAF0.c.o"
        self.assertEqual(actual.read_bytes(), qualified.read_bytes())
        self.assertEqual(source.guard_manifest(source.before_path(
            self.output, "conker/retail_word_patches.us.csv").read_bytes()),
            source.before_path(self.output, "conker/retail_word_patches.us.csv").read_bytes())

    def test_05_strict_complete_image_protected_data_and_inputs(self):
        source.check_inputs(ROOT, self.output, self.installed)
        report = source.audit(ROOT, self.output, self.installed)
        self.assertTrue(report["entire_linked_image_byte_identical"])
        self.assertEqual((report["strict_exclusions"], report["functions"],
                          report["other_bodies_fixed"]), (0, 6052, 6051))
        self.assertEqual((report["protected_data"]["exact"],
                          report["protected_data"]["bytes"],
                          report["protected_data"]["owner_count"]),
                         (True, 189088, 720))


if __name__ == "__main__":
    unittest.main()
