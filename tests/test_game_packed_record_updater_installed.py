"""Literal complete-image closure, guard history, input controls and archive hashes."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_packed_record_updater as source
from tools.tests import packed_record_updater_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != source.BASELINE['elf']:
        raise ValueError('Unknown packed-updater predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12):
        raise ValueError('Unknown packed-updater predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, source.ENTRY, 192)
    result[offset:offset + 192] = rom[source.ROM:source.ROM + 192]
    struct.pack_into('>I', result, row[0] + 8, 192)
    return bytes(result)


class PackedRecordUpdaterInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_independent_complete_image_guard_history_and_46_inputs(self):
        before = (self.out / 'before-elf').read_bytes()
        old_guards = (self.out / 'before-guards').read_bytes()
        expected = dict(elf=expected_image(before, (self.root / 'conker/conker.us.bin').read_bytes()),
            preset_owner=source.recovered_owner((self.out / 'before-preset_owner').read_text()).encode(),
            guards=source.guard_manifest(old_guards))
        for key, path in source.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), expected.get(key, (self.out / ('before-' + key)).read_bytes()), key)
        self.assertEqual((self.root / source.PATHS['preset_owner']).read_text(), expected['preset_owner'].decode())
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        self.assertEqual(expected['guards'][:len(old_guards)], old_guards)
        self.assertEqual(len(expected['guards'][len(old_guards):].splitlines()), 3)
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']),
            (True, 189088, 720, 0))
        self.assertEqual(sum(a != b for a, b in zip(before, expected['elf'])), 140)
        checkpoint.freeze_after(self.root)
        self.receipt('installed-image', ELF_sha256=checkpoint.AFTER['elf'], ELF_bytes=len(before),
            changed_bytes=140, target_slot=[source.ENTRY, 192], symbol_extent=[12, 192], metadata_allowances=0,
            every_other_ELF_byte_and_other_43_inputs_fixed=True, protected_data=layout,
            complete_old_guard_prefix_fixed=True, only_three_guard_rows_added=True,
            progress_rows_and_shared_header_contents_unchanged=True)

    def test_02_all_inputs_source_text_and_real_in_file_corruptions_are_detected(self):
        rb, rt = Path.read_bytes, Path.read_text
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_independent_complete_image_guard_history_and_46_inputs()
        path = self.root / source.PATHS['preset_owner']
        with patch.object(Path, 'read_text', lambda p, *a, **kw: rt(p, *a, **kw) + '\n' if p == path else rt(p, *a, **kw)):
            with self.assertRaises(AssertionError):
                self.test_01_independent_complete_image_guard_history_and_46_inputs()
        path = self.root / source.PATHS['elf']
        data = rb(path)
        row = next(row for row in symbol_rows(data) if row[1] == source.FUNCTION)
        for offset in (elf_slot_offset(data, source.ENTRY, 4), row[0] + 8,
                elf_slot_offset(data, source.REMOVE, 4), elf_slot_offset(data, 0x1516D4E8, 4),
                elf_slot_offset(data, source.TABLE, 4), elf_slot_offset(data, 0x8009F6C0, 4)):
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_independent_complete_image_guard_history_and_46_inputs()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')
        self.receipt('installed-controls', all_input_flips=46, source_text_flip=True,
            six_physical_code_symbol_constructor_cleanup_table_constant_flips=True, unknown_predecessor_rejected=True)

    def test_03_exact_input_inverse_rejects_unknown_corrupt_and_modified_captures(self):
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
                    with self.assertRaisesRegex(AssertionError, 'packed-updater fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse', exact_paths=3, unknown_and_corrupt_inputs_and_captures_rejected=True,
            current_image_and_actual_connected_lifecycle_use_no_inverse=True)

    def test_04_all_original_801_archive_fingerprints(self):
        manifest = self.root / 'conker/build/alternative-source-byte-audit-20261014/source-before.json'
        self.assertEqual(hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'd8a07543bcd17a19096e744a66f67a2bf36ba153b51c81e569ae76b95e6581e1')
        rows = json.loads(manifest.read_text(encoding='utf-8-sig'))['files']
        self.assertEqual(len(rows), 801)
        archive = self.root / '../Another Source/CBFD-Recompiled/conker'
        for path, digest in rows.items():
            self.assertEqual(hashlib.sha256((archive / path).read_bytes()).hexdigest().upper(), digest, path)
        self.receipt('archive', all_original_fingerprints=801, original_manifest_fixed=True)


if __name__ == '__main__':
    unittest.main()
