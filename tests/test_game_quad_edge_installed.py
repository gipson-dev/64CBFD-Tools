"""Close every installed byte to the slot prediction and exact symbol cycles."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_quad_edge_match as source
from tools.tests import quad_edge_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout


class QuadEdgeInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def test_01_entire_predicted_ELF_all_63_inputs_and_protected_layout(self):
        expected = source.expected_inputs(self.root, self.out)
        for key, path in source.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), expected.get(key, (self.out / ('before-' + key)).read_bytes()), key)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        checkpoint.freeze_after(self.root)
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        before = (self.out / 'before-elf').read_bytes()
        self.assertEqual(sum(a != b for a, b in zip(before, expected['elf'])), 898)
        (self.out / 'installed-image.json').write_text(json.dumps(dict(changed_ELF_bytes=898,
            target_slot=1064, symbol_extent=[12, 1064], all_other_ELF_bytes_and_60_inputs_fixed=True,
            target_and_extent_changes=834, exact_symbol_serialization_changes=64, metadata_exclusions=0,
            old_guard_prefix_unchanged=True, protected_layout=layout,
            after=checkpoint.AFTER), indent=2) + '\n')

    def test_02_all_live_inputs_and_physical_corruption_controls(self):
        rb = Path.read_bytes
        for relative in source.PATHS.values():
            target = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_predicted_ELF_all_63_inputs_and_protected_layout()
        target = self.root / source.PATHS['elf']
        data = rb(target)
        for address in (source.ENTRY, source.ENTRY + 0x104, source.ENTRY + 0x238, source.ENTRY + 0x270,
                source.ENTRY + 1060, 0x15170034, 0x15170500, 0x151717FC, 0x1516D4E8, 0x15167A68, 0x8009A220):
            changed = bytearray(data)
            changed[elf_slot_offset(data, address, 4)] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(changed) if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_predicted_ELF_all_63_inputs_and_protected_layout()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            source.expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')

    def test_03_frozen_manifest_and_successor_corruption_controls(self):
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
            self.assertEqual(checkpoint.previous_input(current, 'unowned-path', self.root), current)
            for stage in ('before', 'after'):
                target = self.out / (stage + '-' + key)
                with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                    with self.assertRaisesRegex(AssertionError, 'fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, path, self.root)
                        else:
                            checkpoint.freeze_after(self.root)

    def test_04_two_independent_relinks_and_closed_symbol_cycles(self):
        initial = (self.out / 'initial-expected-elf').read_bytes()
        self.assertEqual(hashlib.sha256(initial).hexdigest(), 'c76743afb954c3fcbf9b1537f84e2ec0c8f04be594c3cf22534194b26af250e4')
        expected = source.serialize_symbols(initial)
        self.assertEqual(source.canonical_symbols(initial), source.canonical_symbols(expected))
        self.assertEqual(sum(a != b for a, b in zip(initial, expected)), 64)
        for name in ('relink-one.elf', 'relink-two.elf'):
            self.assertEqual((self.out / name).read_bytes(), expected)
        for location in (0, 0x2A19B4, 0x2DAB26, 0x2E7C56, 0x316C7E):
            bad = bytearray(initial)
            bad[location] ^= 1
            with self.assertRaisesRegex(ValueError, 'initial emitter image'):
                source.serialize_symbols(bytes(bad))


if __name__ == '__main__':
    unittest.main()
