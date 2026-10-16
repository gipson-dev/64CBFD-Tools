"""Close every installed ELF/input byte, including the body/padding size distinction."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_scaled_random_spray as source
from tools.tests import scaled_random_spray_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout


class ScaledSprayInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def test_01_every_ELF_byte_all_69_inputs_and_protected_layout(self):
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
            target_slot=476, symbol_extent=[12, 472], body_words=118, padding_words=1,
            metadata_exclusions=0, all_other_ELF_bytes_and_66_inputs_fixed=True,
            protected_layout=layout, after=checkpoint.AFTER), indent=2) + '\n')

    def test_02_every_live_input_and_target_neighbor_helper_corruption(self):
        rb = Path.read_bytes
        for relative in source.PATHS.values():
            target = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_every_ELF_byte_all_69_inputs_and_protected_layout()
        target = self.root / source.PATHS['elf']
        data = rb(target)
        for address in (source.ENTRY, source.ENTRY + 144, source.ENTRY + 168, source.ENTRY + 408,
                source.ENTRY + 468, source.ENTRY + 472, 0x151707E0, 0x15170B90,
                source.DIRECTION, source.FACTORY, 0x15167A68, 0x8009A220):
            bad = bytearray(data)
            bad[elf_slot_offset(data, address, 4)] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_every_ELF_byte_all_69_inputs_and_protected_layout()
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
