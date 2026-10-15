"""Independent complete image, all 50 inputs, corruption gates and archive preservation."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_packed_coordinate_expression_fit as source
from tools.tests import packed_coordinate_match_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests import test_game_packed_record_updater_installed as previous
from tools.check_game_data_layout import audit_layout


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != source.BASELINE['elf']:
        raise ValueError('Unknown coordinate-match predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12):
        raise ValueError('Unknown coordinate-match predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, source.ENTRY, 340)
    result[offset:offset + 340] = rom[source.ROM:source.ROM + 340]
    struct.pack_into('>I', result, row[0] + 8, 340)
    return bytes(result)


class PackedCoordinateInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_independent_complete_image_and_all_50_inputs(self):
        before = (self.out / 'before-elf').read_bytes()
        expected = dict(elf=expected_image(before, (self.root / 'conker/conker.us.bin').read_bytes()),
            preset_owner=source.recovered_owner((self.out / 'before-preset_owner').read_text()).encode())
        for key, path in source.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), expected.get(key, (self.out / ('before-' + key)).read_bytes()), key)
        self.assertEqual((self.root / source.PATHS['preset_owner']).read_text(), expected['preset_owner'].decode())
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        checkpoint.freeze_after(self.root)
        self.receipt('installed-image', ELF_bytes=len(before),
            changed_bytes=sum(a != b for a, b in zip(before, expected['elf'])),
            target_slot=[source.ENTRY, 340], symbol_extent=[12, 340], metadata_allowances=0,
            every_other_ELF_byte_and_other_48_inputs_fixed=True, protected_data=layout,
            all_guard_bytes_and_progress_rows_fixed=True, direct_C=True,
            after={key: hashlib.sha256(value).hexdigest() for key, value in expected.items()})

    def test_02_all_input_source_and_physical_site_corruptions_rejected(self):
        rb, rt = Path.read_bytes, Path.read_text
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_independent_complete_image_and_all_50_inputs()
        path = self.root / source.PATHS['preset_owner']
        with patch.object(Path, 'read_text', lambda p, *a, **kw: rt(p, *a, **kw) + '\n' if p == path else rt(p, *a, **kw)):
            with self.assertRaises(AssertionError):
                self.test_01_independent_complete_image_and_all_50_inputs()
        path = self.root / source.PATHS['elf']
        data = rb(path)
        row = next(row for row in symbol_rows(data) if row[1] == source.FUNCTION)
        for offset in (elf_slot_offset(data, source.ENTRY, 4), row[0] + 8,
                elf_slot_offset(data, source.CALLEE, 4), elf_slot_offset(data, 0x15167A68, 4),
                elf_slot_offset(data, 0x8008CBA0, 4), elf_slot_offset(data, 0x8009F6C0, 4)):
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_independent_complete_image_and_all_50_inputs()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')
        self.receipt('installed-controls', all_input_flips=50, source_text_flip=True,
            six_physical_code_symbol_factory_allocator_table_constant_flips=True, unknown_predecessor_rejected=True)

    test_03_all_original_801_archive_fingerprints = previous.PackedRecordUpdaterInstalledTests.test_04_all_original_801_archive_fingerprints

    def test_04_exact_input_inverse_and_all_capture_corruptions(self):
        checkpoint.freeze_after(self.root)
        rb = Path.read_bytes
        for relative, key in checkpoint.PATHS.items():
            current = (self.root / relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(current, relative, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(current, self.root / relative, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(current + b'\n', relative, self.root), current + b'\n')
            self.assertEqual(checkpoint.previous_input(current, 'unowned-path', self.root), current)
            for stage in ('before', 'after'):
                path = self.out / (stage + '-' + key)
                with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                    with self.assertRaisesRegex(AssertionError, 'coordinate-match fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse', exact_paths=2, unknown_and_corrupt_inputs_and_captures_rejected=True,
            current_image_and_actual_factory_chain_use_no_inverse=True)


if __name__ == '__main__':
    unittest.main()
