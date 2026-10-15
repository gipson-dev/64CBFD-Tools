"""Independent full dual-preset image, all input states and corruption gates."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_dual_factory_preset as source
from tools.tests import dual_factory_preset_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols
from tools.check_game_data_layout import audit_layout


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != source.BASELINE['elf']:
        raise ValueError('Unknown dual-preset predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12):
        raise ValueError('Unknown dual-preset predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, source.ENTRY, 592)
    result[offset:offset + 592] = rom[source.ROM:source.ROM + 592]
    struct.pack_into('>I', result, row[0] + 8, 592)
    return bytes(result)


def expected_inputs(root, out):
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        preset_owner=source.recovered_owner((out / 'before-preset_owner').read_text()).encode())


class DualPresetInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_entire_independent_image_and_all_55_inputs(self):
        before = (self.out / 'before-elf').read_bytes()
        expected = expected_inputs(self.root, self.out)
        for key, relative in source.PATHS.items():
            self.assertEqual((self.root / relative).read_bytes(), expected.get(key, (self.out / ('before-' + key)).read_bytes()), key)
        self.assertEqual((self.root / source.PATHS['preset_owner']).read_text(), expected['preset_owner'].decode())
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        checkpoint.freeze_after(self.root)
        target_size = bytearray(before)
        row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
        struct.pack_into('>I', target_size, row[0] + 8, 592)
        self.assertEqual(canonical_symbols(expected['elf']), canonical_symbols(target_size))
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        self.receipt('installed-image', ELF_bytes=len(before), changed_bytes=sum(a != b for a, b in zip(before, expected['elf'])),
            target_slot=[source.ENTRY, 592], symbol_extent=[12, 592], metadata_allowances=0,
            every_other_ELF_byte_and_other_53_inputs_fixed=True, protected_data=layout,
            all_old_guards_and_progress_rows_and_both_caller_owners_fixed=True,
            after={key: hashlib.sha256(value).hexdigest() for key, value in expected.items()})

    def test_02_every_input_source_and_physical_corruption(self):
        rb, rt = Path.read_bytes, Path.read_text
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_independent_image_and_all_55_inputs()
        path = self.root / source.PATHS['preset_owner']
        with patch.object(Path, 'read_text', lambda p, *a, **kw: rt(p, *a, **kw) + '\n' if p == path else rt(p, *a, **kw)):
            with self.assertRaises(AssertionError):
                self.test_01_entire_independent_image_and_all_55_inputs()
        path = self.root / source.PATHS['elf']
        data = rb(path)
        rows = {r[1]: r for r in symbol_rows(data)}
        offsets = [elf_slot_offset(data, source.ENTRY, 4), rows[source.FUNCTION][0] + 8,
            elf_slot_offset(data, source.CALLEE, 4), elf_slot_offset(data, 0x15167A68, 4),
            elf_slot_offset(data, 0x15028650, 4), elf_slot_offset(data, 0x1506DFE4, 4)]
        for offset in offsets:
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_independent_image_and_all_55_inputs()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')
        self.receipt('installed-controls', input_flips=55, source_text_flip=True,
            physical_target_symbol_factory_allocator_and_two_caller_flips=6, unknown_predecessor_rejected=True)

    def test_03_all_55_immutable_predecessor_capture_corruptions(self):
        rb = Path.read_bytes
        for key in source.PATHS:
            path = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        self.receipt('capture-controls', all_55_before_capture_flips_rejected=True)

    def test_04_exact_successor_and_every_before_after_capture(self):
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
                    with self.assertRaisesRegex(AssertionError, 'dual-preset fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse', exact_paths=2, every_unknown_input_and_before_after_flip_rejected=True,
            actual_current_whole_image_and_real_factory_chain_use_no_inverse=True)


if __name__ == '__main__':
    unittest.main()
