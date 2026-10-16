"""Full first-predicted ELF, all physical metadata bytes and fixed live inputs."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_table_debris_match as source
from tools.tests import table_debris_match_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout


class TableDebrisInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def test_01_complete_initial_prediction_all_inputs_and_protected_layout(self):
        expected = source.expected_inputs(self.root, self.out)
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), checkpoint.AFTER)
        for key, relative in source.PATHS.items():
            actual = (self.root / relative).read_bytes()
            wanted = expected.get(key, (self.out / ('before-' + key)).read_bytes())
            self.assertEqual(hashlib.sha256(actual).digest(), hashlib.sha256(wanted).digest(), key)
            self.assertEqual(actual, wanted, key)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest)
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        checkpoint.freeze_after(self.root)
        (self.out / 'installed-image.json').write_text(json.dumps(dict(
            changed_ELF_bytes=628, target_slot=632, symbol_extent=[12, 632],
            slot_extent_changed_bytes=507, exact_preinstall_serialization_bytes=121,
            every_other_ELF_byte_and_75_inputs_fixed=True, target_word_guards=0,
            first_complete_preinstall_prediction_matches=True, metadata_exclusions=0,
            protected_layout=layout, after=checkpoint.AFTER), indent=2) + '\n')

    def test_02_live_inputs_and_physical_code_data_metadata_corruptions(self):
        rb = Path.read_bytes
        for relative in source.PATHS.values():
            target = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_complete_initial_prediction_all_inputs_and_protected_layout()
        target = self.root / source.PATHS['elf']
        data = rb(target)
        for address in (source.ENTRY, source.ENTRY + 124, source.ENTRY + 160, source.ENTRY + 240,
                source.ENTRY + 332, source.ENTRY + 532, source.ENTRY + 628,
                source.SUBMIT, source.RANDOM, source.LOOKUP, source.TABLE, 0x800A6FA4,
                0x800A6FA8, 0x800A6FAC, 0x15170B90, 0x15170EC4, 0x151718F0):
            bad = bytearray(data)
            bad[elf_slot_offset(data, address, 4)] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_complete_initial_prediction_all_inputs_and_protected_layout()
        names = {n for original, _ in source.SERIALIZATION_GROUPS for n in original}
        for at, name, fields, name_at in source.symbol_rows(data):
            if name in names:
                for position in (at, at + 4, name_at):
                    bad = bytearray(data)
                    bad[position] ^= 1
                    with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == target else rb(p)):
                        with self.assertRaises(AssertionError):
                            self.test_01_complete_initial_prediction_all_inputs_and_protected_layout()

    def test_03_capture_initial_manifest_and_successor_corruptions(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key in source.PATHS:
            target = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        for filename in ('baseline.json', 'initial-prediction.json'):
            target = self.out / filename
            with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == target else rt(p, *a, **kw)):
                if filename == 'baseline.json':
                    with self.assertRaisesRegex(ValueError, 'manifest'):
                        source.freeze(self.root, self.out)
                else:
                    with self.assertRaises(AssertionError):
                        self.test_01_complete_initial_prediction_all_inputs_and_protected_layout()
        checkpoint.freeze_after(self.root)
        for relative, key in checkpoint.PATHS.items():
            current = (self.root / relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(current, relative, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(current + b'\n', relative, self.root), current + b'\n')
            self.assertEqual(checkpoint.previous_input(current, 'unowned', self.root), current)
            for stage in ('before', 'after'):
                target = self.out / (stage + '-' + key)
                with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                    with self.assertRaisesRegex(AssertionError, 'fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
