"""Independent exact image closure, corrupt-input controls and historical gates."""
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_special_object_position as source
from tools.tests import special_object_position_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != source.BASELINE['elf']:
        raise ValueError('Unknown attachment-position predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12):
        raise ValueError('Unknown attachment-position predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, source.ENTRY, 204)
    result[offset:offset + 204] = rom[source.ROM:source.ROM + 204]
    struct.pack_into('>I', result, row[0] + 8, 204)
    return bytes(result)


class SpecialObjectPositionInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_independent_current_image_source_guards_and_protected_inputs(self):
        before = (self.out / 'before-elf').read_bytes()
        expected = dict(elf=expected_image(before, (self.root / 'conker/conker.us.bin').read_bytes()),
            position_owner=source.recover((self.out / 'before-position_owner').read_text()).encode(),
            guards=source.guard_manifest((self.out / 'before-guards').read_bytes()))
        for key, path in source.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), expected.get(key, (self.out / ('before-' + key)).read_bytes()), key)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        self.assertEqual((self.root / source.PATHS['position_owner']).read_text(), expected['position_owner'].decode())
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        self.assertEqual(sum(a != b for a, b in zip(before, expected['elf'])), 152)
        checkpoint.freeze_after(self.root)
        self.receipt('installed-image', ELF_sha256=checkpoint.AFTER['elf'], ELF_bytes=len(before),
            changed_bytes=152, target_slot=[source.ENTRY, 204], symbol_extent=[12, 204],
            every_other_ELF_byte_fixed=True, metadata_allowances=0, protected_data=layout,
            guard_prefix_fixed_and_exactly_two_rows_appended=True, unchanged_other_inputs=len(source.PATHS) - 3)

    def test_02_current_and_frozen_corruption_is_effectively_rejected(self):
        rb, rt = Path.read_bytes, Path.read_text
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_independent_current_image_source_guards_and_protected_inputs()
        path = self.root / source.PATHS['position_owner']
        with patch.object(Path, 'read_text', lambda p, *a, **kw: rt(p, *a, **kw) + '\n' if p == path else rt(p, *a, **kw)):
            with self.assertRaises(AssertionError):
                self.test_01_independent_current_image_source_guards_and_protected_inputs()
        path = self.root / source.PATHS['elf']
        data = rb(path)
        row = next(row for row in symbol_rows(data) if row[1] == source.FUNCTION)
        for at in (elf_slot_offset(data, source.ENTRY, 4), row[0] + 8,
                   elf_slot_offset(data, 0x151745F0, 4), elf_slot_offset(data, 0x151149AC, 4),
                   elf_slot_offset(data, 0x8009B884, 4)):
            bad = bytearray(data)
            bad[at] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_independent_current_image_source_guards_and_protected_inputs()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')
        self.receipt('installed-controls', all_current_input_flips=len(source.PATHS),
            source_text_flip=True, target_symbol_previous_match_lookup_table_in_file_flips=5,
            unknown_predecessor_rejected=True)

    def test_03_exact_inverse_and_all_frozen_input_controls(self):
        checkpoint.freeze_after(self.root)
        rb = Path.read_bytes
        for relative, key in checkpoint.PATHS.items():
            current = (self.root / relative).read_bytes()
            before = checkpoint.fixture(self.root, 'before', key)
            self.assertEqual(checkpoint.previous_input(current, relative, self.root), before)
            self.assertEqual(checkpoint.previous_input(current, self.root / relative, self.root), before)
            self.assertEqual(checkpoint.previous_input(current + b'\n', relative, self.root), current + b'\n')
            self.assertEqual(checkpoint.previous_input(current, 'unowned-path', self.root), current)
            for stage in ('before', 'after'):
                path = self.out / (stage + '-' + key)
                with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                    with self.assertRaisesRegex(AssertionError, 'attachment-position fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse', exact_known_paths=3, unknown_and_all_before_after_corruption_controls=True,
            current_image_independently_checked_without_normalization=True)

    def test_04_previous_image_history_and_original_archive_hashes(self):
        rb = Path.read_bytes
        output = io.StringIO()
        with patch.object(Path, 'read_bytes', lambda p: checkpoint.previous_input(rb(p), p, self.root)):
            suite = unittest.defaultTestLoader.loadTestsFromName('tools.tests.test_game_capture_request_match_installed')
            result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
        self.assertEqual(result.testsRun, 5, output.getvalue())
        self.assertTrue(result.wasSuccessful(), output.getvalue())
        self.receipt('history', previous_capture_request_tests=5, embedded_previous_view_tests=5,
            embedded_earlier_actor_and_matrix_tests=8, all_original_archive_fingerprints=801,
            exact_input_inverse_only=True)


if __name__ == '__main__':
    unittest.main()
