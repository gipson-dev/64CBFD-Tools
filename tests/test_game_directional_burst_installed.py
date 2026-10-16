"""Check the complete installed burst image without section/metadata exclusions."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_directional_burst_match as source
from tools.tests import directional_burst_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout


class DirectionalBurstInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def test_01_entire_expected_ELF_all_67_inputs_and_protected_layout(self):
        expected = source.expected_inputs(self.root, self.out)
        for key, path in source.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), expected.get(key, (self.out / ('before-' + key)).read_bytes()), key)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        checkpoint.freeze_after(self.root)
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        before = (self.out / 'before-elf').read_bytes()
        (self.out / 'installed-image.json').write_text(json.dumps(dict(
            changed_ELF_bytes=sum(a != b for a, b in zip(before, expected['elf'])),
            target_slot=736, symbol_extent=[12, 736], metadata_exclusions=0,
            all_other_ELF_bytes_and_64_inputs_fixed=True, protected_layout=layout,
            after=checkpoint.AFTER), indent=2) + '\n')

    def test_02_all_live_inputs_and_physical_corruption_controls(self):
        rb = Path.read_bytes
        for relative in source.PATHS.values():
            target = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_expected_ELF_all_67_inputs_and_protected_layout()
        target = self.root / source.PATHS['elf']
        data = rb(target)
        for address in (source.ENTRY, source.ENTRY + 0x80, source.ENTRY + 0x17C, source.ENTRY + 0x2C8,
                source.ENTRY + 732, 0x151700D8, 0x151707E0, 0x151717FC, source.previous.SMALL,
                source.previous.LARGE, source.previous.RANDOM, 0x8009A220):
            bad = bytearray(data)
            bad[elf_slot_offset(data, address, 4)] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_expected_ELF_all_67_inputs_and_protected_layout()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            source.expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')

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
