"""Independent exact current image, honest progress, corruptions and history."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_rotation_matrix_leaf as source
from tools.tests import rotation_matrix_leaf_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != source.BASELINE['elf']:
        raise ValueError('Unknown rotation-leaf predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 24):
        raise ValueError('Unknown rotation-leaf predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, source.ENTRY, 336)
    result[offset:offset + 336] = rom[source.ROM:source.ROM + 336]
    struct.pack_into('>I', result, row[0] + 8, 336)
    return bytes(result)


class RotationMatrixLeafInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_literal_image_adapter_progress_and_all_protected_inputs(self):
        before = (self.out / 'before-elf').read_bytes()
        expected = dict(elf=expected_image(before, (self.root / 'conker/conker.us.bin').read_bytes()),
            angles_owner=source.original_owner((self.out / 'before-angles_owner').read_text()).encode(),
            progress=source.restored_progress((self.out / 'before-progress').read_bytes()))
        for key, path in source.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), expected.get(key, (self.out / ('before-' + key)).read_bytes()), key)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        self.assertEqual((self.root / source.PATHS['angles_owner']).read_text(), expected['angles_owner'].decode())
        before_rows = list(csv.reader((self.out / 'before-progress').read_text().splitlines()))
        after_rows = list(csv.reader(expected['progress'].decode().splitlines()))
        self.assertEqual(len(before_rows), len(after_rows))
        changed = [(a, b) for a, b in zip(before_rows, after_rows) if a != b]
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0][0][:-1], changed[0][1][:-1])
        self.assertEqual((changed[0][0][-1], changed[0][1][-1]), ('c', 'asm'))
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        self.assertEqual(sum(a != b for a, b in zip(before, expected['elf'])), 280)
        checkpoint.freeze_after(self.root)
        self.receipt('installed-image', ELF_sha256=checkpoint.AFTER['elf'], ELF_bytes=len(before), changed_bytes=280,
            target_slot=[source.ENTRY, 336], symbol_extent=[24, 336], metadata_allowances=0,
            every_other_ELF_byte_and_35_other_inputs_fixed=True, protected_data=layout,
            only_progress_change_is_one_false_C_stub_to_assembly=True, new_C_match_credit=0)

    def test_02_current_input_text_and_real_ELF_corruption_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_literal_image_adapter_progress_and_all_protected_inputs()
        path = self.root / source.PATHS['angles_owner']
        with patch.object(Path, 'read_text', lambda p, *a, **kw: rt(p, *a, **kw) + '\n' if p == path else rt(p, *a, **kw)):
            with self.assertRaises(AssertionError):
                self.test_01_literal_image_adapter_progress_and_all_protected_inputs()
        path = self.root / source.PATHS['elf']
        data = rb(path)
        row = next(row for row in symbol_rows(data) if row[1] == source.FUNCTION)
        offsets = (elf_slot_offset(data, source.ENTRY, 4), row[0] + 8,
            elf_slot_offset(data, 0x1511490C, 4), elf_slot_offset(data, 0x150AD780, 4),
            elf_slot_offset(data, 0x150AD78C, 4), elf_slot_offset(data, 0x8009F6C0, 4))
        for offset in offsets:
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_literal_image_adapter_progress_and_all_protected_inputs()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')
        self.receipt('installed-controls', all_current_input_flips=38, source_text_flip=True,
            target_symbol_caller_both_math_and_coefficient_in_file_flips=6, unknown_predecessor_rejected=True)

    def test_03_exact_inverse_and_all_before_after_input_controls(self):
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
                    with self.assertRaisesRegex(AssertionError, 'rotation-leaf fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse', exact_known_paths=3, unknown_inputs_and_all_frozen_corruptions_rejected=True,
            not_used_for_current_image_or_actual_connected_chains=True)

    def test_04_historical_image_and_explicit_old_provider_boundary(self):
        rb = Path.read_bytes
        output = io.StringIO()
        with patch.object(Path, 'read_bytes', lambda p: checkpoint.previous_input(rb(p), p, self.root)):
            suite = unittest.defaultTestLoader.loadTestsFromNames([
                'tools.tests.test_game_actor_world_matrix_installed',
                'tools.tests.test_game_actor_world_matrix.ActorWorldMatrixTests.test_06_actual_position_consumer_builder_and_point_chain'])
            result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
        self.assertEqual(result.testsRun, 5, output.getvalue())
        self.assertTrue(result.wasSuccessful(), output.getvalue())
        self.receipt('history', previous_builder_installed_checks=4, explicit_historical_provider_boundary_checks=1,
            earlier_capture_view_actor_matrix_and_caller_gates=True, all_original_archive_files=801,
            exact_input_inverse_only=True)


if __name__ == '__main__':
    unittest.main()
