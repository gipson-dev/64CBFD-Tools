"""Literal current image, protected inputs, corruption controls and exact history."""
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_world_matrix as source
from tools.tests import actor_world_matrix_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != source.BASELINE['elf']:
        raise ValueError('Unknown world-matrix predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12):
        raise ValueError('Unknown world-matrix predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, source.ENTRY, 160)
    result[offset:offset + 160] = rom[source.ROM:source.ROM + 160]
    struct.pack_into('>I', result, row[0] + 8, 160)
    return bytes(result)


class ActorWorldMatrixInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_independent_current_image_source_and_all_protected_inputs(self):
        before = (self.out / 'before-elf').read_bytes()
        expected = dict(elf=expected_image(before, (self.root / 'conker/conker.us.bin').read_bytes()),
            builder_owner=source.recover((self.out / 'before-builder_owner').read_text()).encode())
        for key, path in source.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), expected.get(key, (self.out / ('before-' + key)).read_bytes()), key)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        self.assertEqual((self.root / source.PATHS['builder_owner']).read_text(), expected['builder_owner'].decode())
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        self.assertEqual(sum(a != b for a, b in zip(before, expected['elf'])), 123)
        checkpoint.freeze_after(self.root)
        self.receipt('installed-image', ELF_sha256=checkpoint.AFTER['elf'], ELF_bytes=len(before),
            changed_bytes=123, target_slot=[source.ENTRY, 160], symbol_extent=[12, 160],
            every_other_ELF_byte_fixed=True, metadata_allowances=0, protected_data=layout,
            guards_layout_headers_profiles_progress_and_all_32_other_inputs_fixed=True)

    def test_02_current_input_and_literal_ELF_corruption_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_independent_current_image_source_and_all_protected_inputs()
        path = self.root / source.PATHS['builder_owner']
        with patch.object(Path, 'read_text', lambda p, *a, **kw: rt(p, *a, **kw) + '\n' if p == path else rt(p, *a, **kw)):
            with self.assertRaises(AssertionError):
                self.test_01_independent_current_image_source_and_all_protected_inputs()
        path = self.root / source.PATHS['elf']
        data = rb(path)
        row = next(row for row in symbol_rows(data) if row[1] == source.FUNCTION)
        offsets = (elf_slot_offset(data, source.ENTRY, 4), row[0] + 8,
            elf_slot_offset(data, 0x1511F31C, 4), elf_slot_offset(data, 0x151148A8, 4),
            elf_slot_offset(data, 0x150A7CB0, 4), elf_slot_offset(data, 0x150A7A48, 4),
            elf_slot_offset(data, 0x8009B884, 4))
        for at in offsets:
            bad = bytearray(data)
            bad[at] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_independent_current_image_source_and_all_protected_inputs()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')
        self.receipt('installed-controls', all_current_input_flips=34, source_text_flip=True,
            target_symbol_caller_angle_scale_product_data_in_file_flips=len(offsets), unknown_predecessor_rejected=True)

    def test_03_exact_inverse_and_every_frozen_input_control(self):
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
                    with self.assertRaisesRegex(AssertionError, 'world-matrix fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse', exact_known_paths=2, unknown_and_every_before_after_corruption_control=True,
            current_image_and_actual_consumer_chain_independently_checked_without_normalization=True)

    def test_04_previous_image_history_archive_and_explicit_old_caller_boundary(self):
        rb, rt = Path.read_bytes, Path.read_text
        def old_text(path, *args, **kwargs):
            current = rb(path)
            previous = checkpoint.previous_input(current, path, self.root)
            return previous.decode('utf-8') if previous != current else rt(path, *args, **kwargs)
        output = io.StringIO()
        with patch.object(Path, 'read_bytes', lambda p: checkpoint.previous_input(rb(p), p, self.root)), \
                patch.object(Path, 'read_text', old_text):
            suite = unittest.defaultTestLoader.loadTestsFromNames([
                'tools.tests.test_game_special_object_position_installed',
                'tools.tests.test_game_special_object_position.SpecialObjectPositionTests.test_06_actual_point_transform_connection_and_matrix_stub_boundary'])
            result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
        self.assertEqual(result.testsRun, 5, output.getvalue())
        self.assertTrue(result.wasSuccessful(), output.getvalue())
        self.receipt('history', previous_position_installed_tests=4, explicit_historical_caller_stub_boundary_tests=1,
            embedded_capture_view_actor_matrix_gates=True, all_original_archive_fingerprints=801,
            exact_input_inverse_only_not_used_for_current_body_or_actual_consumer_chain=True)


if __name__ == '__main__':
    unittest.main()
