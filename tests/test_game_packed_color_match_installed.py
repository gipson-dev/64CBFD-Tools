"""Complete independent RGB installation image, old guards and all 52 input states."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_packed_color_match as source
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols, SYMBOL
from tools.check_game_data_layout import audit_layout
from tools.tests import packed_color_match_checkpoint as checkpoint


def apply_symbol_serialization(expected):
    names = ('D_8009CE70', 'D_800AAC80', 'D_800A1370')
    rows = {name: (offset, fields, string) for offset, name, fields, string in symbol_rows(expected) if name in names}
    if set(rows) != set(names):
        raise ValueError('Missing packed-color serialization symbol')
    bindings = {'D_8009CE70': (0x8009CE70, 0, 16, 0, 6),
        'D_800AAC80': (0x800AAC80, 0, 16, 0, 65521),
        'D_800A1370': (0x800A1370, 0, 16, 0, 65521)}
    for name in names:
        offset, fields, string = rows[name]
        if fields[1:] != bindings[name] or expected[string:string + 11] != name.encode() + b'\0':
            raise ValueError('Changed packed-color serialization binding')
    slots = [rows[name] for name in names]
    if ([slot[0] - slots[0][0] for slot in slots] != [0, 16, 32] or
            [slot[2] - slots[0][2] for slot in slots] != [0, 11, 22]):
        raise ValueError('Changed packed-color serialization order')
    symbols = canonical_symbols(expected)
    for slot, name in zip(slots, ('D_800A1370', 'D_8009CE70', 'D_800AAC80')):
        offset, fields, string = slot
        SYMBOL.pack_into(expected, offset, fields[0], *rows[name][1][1:])
        expected[string:string + 11] = name.encode() + b'\0'
    if canonical_symbols(expected) != symbols:
        raise ValueError('Packed-color symbol bindings changed')


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != source.BASELINE['elf']:
        raise ValueError('Unknown packed-color predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12):
        raise ValueError('Unknown packed-color predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, source.ENTRY, 992)
    result[offset:offset + 992] = rom[source.ROM:source.ROM + 992]
    struct.pack_into('>I', result, row[0] + 8, 992)
    apply_symbol_serialization(result)
    return bytes(result)


class PackedColorInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_independent_entire_image_and_all_52_inputs(self):
        before = (self.out / 'before-elf').read_bytes()
        guards = (self.out / 'before-guards').read_bytes()
        expected = dict(elf=expected_image(before, (self.root / 'conker/conker.us.bin').read_bytes()),
            preset_owner=source.recovered_owner((self.out / 'before-preset_owner').read_text()).encode(),
            guards=source.guard_manifest(guards))
        for key, relative in source.PATHS.items():
            self.assertEqual((self.root / relative).read_bytes(), expected.get(key, (self.out / ('before-' + key)).read_bytes()), key)
        self.assertEqual((self.root / source.PATHS['preset_owner']).read_text(), expected['preset_owner'].decode())
        self.assertEqual(expected['guards'][:len(guards)], guards)
        self.assertEqual(len(expected['guards'][len(guards):].splitlines()), 7)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        checkpoint.freeze_after(self.root)
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        self.receipt('installed-image', ELF_bytes=len(before),
            changed_bytes=sum(a != b for a, b in zip(before, expected['elf'])),
            target_slot=[source.ENTRY, 992], symbol_extent=[12, 992],
            exact_named_symbol_order_cycle=['D_800A1370', 'D_8009CE70', 'D_800AAC80'],
            metadata_changed_bytes=21, no_metadata_ranges_ignored=True,
            every_other_ELF_byte_and_other_49_inputs_fixed=True, protected_data=layout,
            complete_old_mixed_EOL_guard_prefix_fixed=True, seven_rows_appended=True,
            progress_rows_and_shared_headers_fixed=True, raw_C_exact=False,
            after={key: hashlib.sha256(value).hexdigest() for key, value in expected.items()})

    def test_02_every_input_source_and_six_physical_corruptions_rejected(self):
        rb, rt = Path.read_bytes, Path.read_text
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_independent_entire_image_and_all_52_inputs()
        path = self.root / source.PATHS['preset_owner']
        with patch.object(Path, 'read_text', lambda p, *args, **kw: rt(p, *args, **kw) + '\n' if p == path else rt(p, *args, **kw)):
            with self.assertRaises(AssertionError):
                self.test_01_independent_entire_image_and_all_52_inputs()
        path = self.root / source.PATHS['elf']
        data = rb(path)
        row = next(row for row in symbol_rows(data) if row[1] == source.FUNCTION)
        for offset in (elf_slot_offset(data, source.ENTRY, 4), row[0] + 8,
                elf_slot_offset(data, 0x1516D678, 4), elf_slot_offset(data, 0x1516972C, 4),
                elf_slot_offset(data, 0x8008CBA0, 4), elf_slot_offset(data, 0x800A6E00, 4)):
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_independent_entire_image_and_all_52_inputs()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')
        self.receipt('installed-controls', input_flips=52, source_text_flip=True,
            physical_code_symbol_updater_cleanup_table_and_data_flips=6, unknown_predecessor_rejected=True)

    def test_03_exact_input_inverse_and_all_before_after_captures(self):
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
                    with self.assertRaisesRegex(AssertionError, 'packed-color fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse', exact_paths=3, corrupt_unknown_inputs_and_all_captures_rejected=True,
            current_full_image_and_connected_callback_use_no_inverse=True)

    def test_04_all_52_immutable_predecessor_capture_corruptions(self):
        rb = Path.read_bytes
        for key in source.PATHS:
            path = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        self.receipt('capture-controls', all_52_before_capture_flips_rejected=True,
            after_captures_independently_checked_by_exact_input_inverse=True)

    def test_05_exact_three_symbol_serialization_and_corruption_controls(self):
        before = (self.out / 'before-elf').read_bytes()
        after = bytearray(before)
        canonical = canonical_symbols(before)
        apply_symbol_serialization(after)
        self.assertEqual(canonical_symbols(after), canonical)
        self.assertEqual(sum(a != b for a, b in zip(before, after)), 21)
        rows = [row for row in symbol_rows(before) if row[1] in ('D_8009CE70', 'D_800AAC80', 'D_800A1370')]
        for offset, name, _, string in rows:
            for at in (offset + 4, offset + 8, offset + 12, offset + 14, string):
                bad = bytearray(before)
                bad[at] ^= 1
                with self.assertRaises(ValueError):
                    apply_symbol_serialization(bad)
        with self.assertRaises(ValueError):
            apply_symbol_serialization(after)
        self.receipt('symbol-serialization', exact_cycle_only=True, all_canonical_bindings_fixed=True,
            changed_metadata_bytes=21, binding_size_type_section_and_name_corruptions_rejected=15,
            already_serialized_or_unknown_orders_rejected=True)


if __name__ == '__main__':
    unittest.main()
