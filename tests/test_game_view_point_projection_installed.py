"""Whole first projection image, exact source successor and protected inputs."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_view_point_projection as source
from tools.tests import view_point_projection_checkpoint as checkpoint
from tools.tests import test_game_view_overlay_installed as previous
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols, symbol_rows
from tools.check_game_data_layout import audit_layout


class ViewPointProjectionInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out); cls.expected = source.expected_inputs(cls.root, cls.out)
        cls.wanted = {k:cls.expected.get(k, (cls.out / ('before-' + k)).read_bytes()) for k in source.PATHS}

    def check_live(self):
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), checkpoint.AFTER)
        self.assertEqual(len(source.PATHS), 128)
        for key, path in source.PATHS.items(): self.assertTrue((self.root / path).read_bytes() == self.wanted[key], key)

    def test_01_whole276byte_prediction_body_extent_and_protected_data(self):
        self.check_live()
        for key, digest in checkpoint.AFTER.items(): self.assertEqual(hashlib.sha256(self.expected[key]).hexdigest(), digest)
        before, data = (self.out / 'before-elf').read_bytes(), self.expected['elf']
        self.assertEqual((len(before), len(data)), (3257636, 3257636))
        self.assertEqual(sum(a != b for a, b in zip(before, data)), 276)
        at = elf_slot_offset(data, source.ENTRY, 348)
        self.assertEqual(data[at:at + 348], (self.out / 'before-retail_rom').read_bytes()[source.ROM:source.ROM + 348])
        self.assertEqual(sum(a != b for a, b in zip(before[at:at + 348], data[at:at + 348])), 274)
        old = canonical_symbols(before); wanted = old.copy()
        original = next(k for k in old if k[0] == source.FUNCTION)
        self.assertEqual(original[2], 12)
        successor = list(original); successor[2] = 348
        wanted[original] -= 1; wanted[tuple(successor)] += 1
        self.assertEqual(+wanted, canonical_symbols(data))
        self.assertEqual((self.root / source.PATHS['guards']).read_bytes(), (self.out / 'before-guards').read_bytes())
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        checkpoint.freeze_after(self.root)
        (self.out / 'installed-image.json').write_text(json.dumps(dict(after=checkpoint.AFTER,
            changed_ELF_bytes=276, code_bytes=274, extent_bytes=2, metadata_serialization_bytes=0,
            body_bytes=348, extent=[12, 348], new_guards=0, no_new_compiler_profile=True,
            metadata_exclusions=0, unchanged_other_inputs=126, guards_byte_identical=True, protected_layout=layout), indent=2) + '\n')

    def test_02_all128_live_inputs_helper_callers_and_metadata_fail_closed(self):
        self.check_live(); read = Path.read_bytes
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p:read(p) + b'\n' if p == path else read(p)):
                with self.assertRaises(AssertionError): self.check_live()
        path = self.root / source.PATHS['elf']; data = read(path)
        offsets = [elf_slot_offset(data, a, 4) for a in (source.ENTRY, source.ENTRY + 0x54, source.ENTRY + 344,
            0x150A7960, 0x150A7A00, 0x150A7A14, 0x1516CD8C, 0x1512ADF8, 0x151744D8)]
        for row in symbol_rows(data):
            if row[1] in (source.FUNCTION, 'func_150A7A00', 'func_151742EC', 'D_800BE628'):
                offsets.extend((row[0], row[0] + 4, row[0] + 8, row[0] + 12, row[3]))
        for at in offsets:
            bad = bytearray(data); bad[at] ^= 1
            with patch.object(Path, 'read_bytes', lambda p:bytes(bad) if p == path else read(p)):
                with self.assertRaises(AssertionError): self.check_live()

    def test_03_only_exact_successor_and_both_fixture_stages(self):
        with patch.object(previous, 'checkpoint', checkpoint):
            previous.ViewOverlayInstalledTests.test_03_only_exact_successor_and_both_fixture_stages(self)


if __name__ == '__main__': unittest.main()
