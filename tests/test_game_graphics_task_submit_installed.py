"""Whole first image, exact caller-guard retirement and protected input successor."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_graphics_task_submit as source
from tools.tests import graphics_task_submit_checkpoint as checkpoint
from tools.tests import test_game_view_overlay_installed as inverse
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols, symbol_rows
from tools.check_game_data_layout import audit_layout


class GraphicsTaskSubmitInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out); cls.expected = source.expected_inputs(cls.root, cls.out)
        cls.wanted = {k:cls.expected.get(k, (cls.out / ('before-' + k)).read_bytes()) for k in source.PATHS}

    def check_live(self):
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), checkpoint.AFTER)
        self.assertEqual(len(source.PATHS), 134)
        for key, path in source.PATHS.items(): self.assertTrue((self.root / path).read_bytes() == self.wanted[key], key)

    def test_01_whole800_byte_prediction_body_extent_metadata_and_retired_guards(self):
        self.check_live()
        for key, digest in checkpoint.AFTER.items(): self.assertEqual(hashlib.sha256(self.expected[key]).hexdigest(), digest)
        before, data = (self.out / 'before-elf').read_bytes(), self.expected['elf']
        self.assertEqual((len(before), len(data)), (3257636, 3257636))
        self.assertEqual(sum(a != b for a, b in zip(before, data)), 800)
        at = elf_slot_offset(data, source.ENTRY, 956)
        self.assertEqual(data[at:at + 956], (self.out / 'before-retail_rom').read_bytes()[source.ROM:source.ROM + 956])
        self.assertEqual(sum(a != b for a, b in zip(before[at:at + 956], data[at:at + 956])), 731)
        old = canonical_symbols(before); wanted = old.copy(); original = next(k for k in old if k[0] == source.FUNCTION)
        self.assertEqual(original[2], 12); successor = list(original); successor[2] = 956
        wanted[original] -= 1; wanted[tuple(successor)] += 1
        self.assertEqual(+wanted, canonical_symbols(data))
        guard_before, guard_after = (self.out / 'before-guards').read_bytes(), self.expected['guards']
        self.assertEqual(len(guard_before.splitlines()) - len(guard_after.splitlines()), 9)
        self.assertEqual((self.root / source.PATHS['makefile']).read_bytes(), (self.out / 'before-makefile').read_bytes())
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        checkpoint.freeze_after(self.root)
        (self.out / 'installed-image.json').write_text(json.dumps(dict(after=checkpoint.AFTER, changed_ELF_bytes=800,
            code_bytes=731, extent_bytes=2, metadata_serialization_bytes=67, exact_symbol_groups=3, body_bytes=956,
            extent=[12, 956], new_guards=0, retired_caller_guards=9, unchanged_other_guard_bytes=True,
            unchanged_other_inputs=130, no_new_compiler_profile=True, metadata_exclusions=0,
            protected_layout=layout), indent=2) + '\n')

    def test_02_all134_live_inputs_and_code_caller_guard_metadata_corruptions(self):
        self.check_live(); read = Path.read_bytes
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p:read(p) + b'\n' if p == path else read(p)):
                with self.assertRaises(AssertionError): self.check_live()
        path = self.root / source.PATHS['elf']; data = read(path)
        offsets = [elf_slot_offset(data, va, 4) for va in (source.ENTRY, source.ENTRY + 0x9C,
            source.ENTRY + 0x148, source.ENTRY + 952, 0x15018CE0, 0x15018CE8, 0x1501A39C, 0x1501CC3C)]
        for row in symbol_rows(data):
            if row[1] in (source.FUNCTION, 'func_1501878C', 'D_800BEAD4', 'D_800BEAD8', 'D_800BE9F4',
                    'D_800BE9F8', 'D_800CBE10', 'D_800A0758', '.L15028860_game_data'):
                offsets.extend((row[0], row[0] + 4, row[0] + 8, row[0] + 12, row[3]))
        for at in offsets:
            bad = bytearray(data); bad[at] ^= 1
            with patch.object(Path, 'read_bytes', lambda p:bytes(bad) if p == path else read(p)):
                with self.assertRaises(AssertionError): self.check_live()

    def test_03_only_exact_successor_and_both_fixture_stages(self):
        with patch.object(inverse, 'checkpoint', checkpoint):
            inverse.ViewOverlayInstalledTests.test_03_only_exact_successor_and_both_fixture_stages(self)


if __name__ == '__main__': unittest.main()
