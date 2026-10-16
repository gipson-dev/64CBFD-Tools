"""Complete debris image/input prediction and physical corruption gates, with no exclusions."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_six_piece_debris_match as source
from tools.tests import six_piece_debris_match_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout


class SixPieceDebrisInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def test_01_entire_first_predicted_ELF_all_inputs_and_protected_layout(self):
        expected = source.expected_inputs(self.root, self.out)
        self.assertEqual(json.loads((self.out / 'qualified-prediction.json').read_text()), checkpoint.AFTER)
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text())['elf'],
            'b0429fedef05f574cc9e06c7ab12621564ee7e6d37fda29fa2bce33a6895c682')
        for key, path in source.PATHS.items():
            actual = (self.root / path).read_bytes()
            wanted = expected.get(key, (self.out / ('before-' + key)).read_bytes())
            self.assertEqual(hashlib.sha256(actual).digest(), hashlib.sha256(wanted).digest(), key)
            self.assertEqual(actual, wanted, key)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        checkpoint.freeze_after(self.root)
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        before = (self.out / 'before-elf').read_bytes()
        (self.out / 'installed-image.json').write_text(json.dumps(dict(
            changed_ELF_bytes=sum(a != b for a, b in zip(before, expected['elf'])), target_slot=820,
            symbol_extent=[12, 820], metadata_exclusions=0, initial_slot_only_changes=675,
            accounted_symbol_serialization_changes=84, all_other_ELF_bytes_and_72_inputs_fixed=True,
            protected_layout=layout, after=checkpoint.AFTER), indent=2) + '\n')

    def test_02_all_live_input_and_physical_corruption_controls(self):
        rb = Path.read_bytes
        for relative in source.PATHS.values():
            target = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_first_predicted_ELF_all_inputs_and_protected_layout()
        target = self.root / source.PATHS['elf']
        data = rb(target)
        for address in (source.ENTRY, source.ENTRY + 100, source.ENTRY + 292, source.ENTRY + 448,
                source.ENTRY + 620, source.ENTRY + 816, source.SUBMIT, source.RING,
                0x151717FC, 0x151709B4, 0x15170EC4, source.RANDOM, source.LOOKUP,
                0x800A6F80, 0x800A6E90, 0x800A6F94):
            bad = bytearray(data)
            bad[elf_slot_offset(data, address, 4)] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_first_predicted_ELF_all_inputs_and_protected_layout()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            source.expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')
        names = {'func_150CBCE0', 'D_800A3E2C', 'D_800A6E90', 'D_800A2460', 'osCreateThread'}
        for at, name, fields, string_at in source.symbol_rows(data):
            if name in names:
                for position in (at, at + 4, string_at):
                    bad = bytearray(data)
                    bad[position] ^= 1
                    with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == target else rb(p)):
                        with self.assertRaises(AssertionError):
                            self.test_01_entire_first_predicted_ELF_all_inputs_and_protected_layout()

    def test_03_frozen_manifest_and_successor_corruptions(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key in source.PATHS:
            target = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        target = self.out / 'baseline.json'
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == target else rt(p, *a, **kw)):
            with self.assertRaisesRegex(ValueError, 'manifest'):
                source.freeze(self.root, self.out)
        checkpoint.freeze_after(self.root)
        for path, key in checkpoint.PATHS.items():
            current = (self.root / path).read_bytes()
            self.assertEqual(checkpoint.previous_input(current, path, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(current + b'\n', path, self.root), current + b'\n')
            self.assertEqual(checkpoint.previous_input(current, 'unowned', self.root), current)
            for stage in ('before', 'after'):
                target = self.out / (stage + '-' + key)
                with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                    with self.assertRaisesRegex(AssertionError, 'fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, path, self.root)
                        else:
                            checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
