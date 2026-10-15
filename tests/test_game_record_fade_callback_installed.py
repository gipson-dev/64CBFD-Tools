"""Independent whole-image adoption, live inputs and strict fade successor controls."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_record_fade_callback as source
from tools.tests import record_fade_callback_checkpoint as checkpoint
from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout


class FadeInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_whole_independent_image_and_all_57_states(self):
        before = (self.out / 'before-elf').read_bytes()
        expected = source.expected_inputs(self.root, self.out)
        for key, relative in source.PATHS.items():
            self.assertEqual((self.root / relative).read_bytes(), expected.get(key, (self.out / ('before-' + key)).read_bytes()), key)
        self.assertEqual((self.root / source.PATHS['preset_owner']).read_text(), expected['preset_owner'].decode())
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        checkpoint.freeze_after(self.root)
        size_only = bytearray(before)
        row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
        struct.pack_into('>I', size_only, row[0] + 8, 196)
        self.assertEqual(canonical_symbols(expected['elf']), canonical_symbols(size_only))
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        self.receipt('installed-image', ELF_bytes=len(before), changed_bytes=sum(a != b for a, b in zip(before, expected['elf'])),
            target_slot=[source.ENTRY, 196], symbol_extent=[12, 196], metadata_allowances=0,
            every_other_ELF_byte_and_other_55_inputs_fixed=True, protected_data=layout,
            old_guards_profiles_progress_and_callback_table_fixed=True,
            after={key: hashlib.sha256(value).hexdigest() for key, value in expected.items()})

    def test_02_all_live_inputs_text_and_physical_corruptions(self):
        rb, rt = Path.read_bytes, Path.read_text
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_whole_independent_image_and_all_57_states()
        path = self.root / source.PATHS['preset_owner']
        with patch.object(Path, 'read_text', lambda p, *a, **kw: rt(p, *a, **kw) + '\n' if p == path else rt(p, *a, **kw)):
            with self.assertRaises(AssertionError):
                self.test_01_whole_independent_image_and_all_57_states()
        path = self.root / source.PATHS['elf']
        data = rb(path)
        row = next(row for row in symbol_rows(data) if row[1] == source.FUNCTION)
        offsets = [elf_slot_offset(data, source.ENTRY, 4), row[0] + 8,
            elf_slot_offset(data, source.CALLER, 4), elf_slot_offset(data, source.TABLE + 12, 4),
            elf_slot_offset(data, source.MOVE, 4), elf_slot_offset(data, source.SCALE, 4),
            elf_slot_offset(data, source.REMOVE, 4), elf_slot_offset(data, 0x1516F8EC, 4)]
        for offset in offsets:
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_whole_independent_image_and_all_57_states()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            source.expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')
        self.receipt('installed-controls', live_input_flips=57, source_text_flip=True, physical_flips=len(offsets),
            target_symbol_caller_table_move_scale_remove_axis_checked=True, unknown_predecessor_rejected=True)

    def test_03_all_57_before_capture_and_manifest_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key in source.PATHS:
            path = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        path = self.out / 'baseline.json'
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == path else rt(p, *a, **kw)):
            with self.assertRaisesRegex(ValueError, 'manifest'):
                source.freeze(self.root, self.out)
        self.receipt('capture-controls', immutable_before_flips=57, changed_manifest_rejected=True)

    def test_04_exact_successor_and_all_before_after_controls(self):
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
                    with self.assertRaisesRegex(AssertionError, 'record-fade fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse', exact_owned_paths=2, unknown_inputs_and_all_before_after_flips_rejected=True,
            actual_current_image_and_dispatch_chain_use_no_inverse=True)


if __name__ == '__main__':
    unittest.main()
