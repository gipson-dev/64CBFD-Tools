"""Independent complete table-fade ELF prediction and input/guard corruption gates."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_table_fade_match as source
from tools.tests import table_fade_match_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols, SYMBOL
from tools.check_game_data_layout import audit_layout


SERIAL_PAIRS = (('D_800D2E45', 'D_80089C28'), ('D_8008CBE8', 'func_15007A70'),
    ('D_800E0D9E', 'D_80089C70'), ('func_15070830', 'D_80089BC0'))
SERIAL_BINDINGS = {
    'D_800D2E45': (0x800D2E45, 0, 16, 0, 65521), 'D_80089C28': (0x80089C28, 0, 16, 0, 65521),
    'D_8008CBE8': (0x8008CBE8, 0, 16, 0, 65521), 'func_15007A70': (0x15007A70, 204, 18, 0, 5),
    'D_800E0D9E': (0x800E0D9E, 0, 16, 0, 65521), 'D_80089C70': (0x80089C70, 0, 16, 0, 65521),
    'func_15070830': (0x15070830, 48, 18, 0, 5), 'D_80089BC0': (0x80089BC0, 0, 16, 0, 6),
}


def apply_symbol_serialization(expected):
    names = set(SERIAL_BINDINGS)
    rows = {name: (offset, fields, string) for offset, name, fields, string in symbol_rows(expected) if name in names}
    if set(rows) != names:
        raise ValueError('Missing table-fade serialization symbol')
    symbols = canonical_symbols(expected)
    before = bytes(expected)
    for first, second in SERIAL_PAIRS:
        a, b = rows[first], rows[second]
        for name, row in ((first, a), (second, b)):
            if row[1][1:] != SERIAL_BINDINGS[name] or expected[row[2]:row[2] + len(name) + 1] != name.encode() + b'\0':
                raise ValueError('Changed table-fade serialization binding')
        if b[0] - a[0] != SYMBOL.size or b[2] - a[2] != len(first) + 1:
            raise ValueError('Changed table-fade serialization order')
        SYMBOL.pack_into(expected, a[0], a[1][0], *b[1][1:])
        SYMBOL.pack_into(expected, b[0], a[1][0] + len(second) + 1, *a[1][1:])
        expected[a[2]:b[2] + len(second) + 1] = second.encode() + b'\0' + first.encode() + b'\0'
    if len(expected) != len(before) or canonical_symbols(expected) != symbols or sum(a != b for a, b in zip(before, expected)) != 106:
        raise ValueError('Unclosed table-fade symbol serialization')


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != source.BASELINE['elf']:
        raise ValueError('Unknown table-fade predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12):
        raise ValueError('Unknown table-fade predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, source.ENTRY, 412)
    result[offset:offset + 412] = rom[source.ROM:source.ROM + 412]
    struct.pack_into('>I', result, row[0] + 8, 412)
    apply_symbol_serialization(result)
    return bytes(result)


def expected_inputs(root, out):
    guards = (out / 'before-guards').read_bytes()
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        preset_owner=source.recovered_owner((out / 'before-preset_owner').read_text()).encode(),
        guards=source.guard_manifest(guards, *source.raw_target(out / 'qualified.o')))


class TableFadeInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_entire_independent_image_and_all_52_inputs(self):
        before = (self.out / 'before-elf').read_bytes()
        guards = (self.out / 'before-guards').read_bytes()
        expected = expected_inputs(self.root, self.out)
        for key, relative in source.PATHS.items():
            self.assertEqual((self.root / relative).read_bytes(), expected.get(key, (self.out / ('before-' + key)).read_bytes()), key)
        self.assertEqual((self.root / source.PATHS['preset_owner']).read_text(), expected['preset_owner'].decode())
        self.assertEqual(expected['guards'][:len(guards)], guards)
        self.assertEqual(len(expected['guards'][len(guards):].splitlines()), 27)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        checkpoint.freeze_after(self.root)
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        self.receipt('installed-image', ELF_bytes=len(before), changed_bytes=sum(a != b for a, b in zip(before, expected['elf'])),
            target_slot=[source.ENTRY, 412], symbol_extent=[12, 412], exact_named_symbol_swaps=SERIAL_PAIRS,
            metadata_changed_bytes=106, no_metadata_ranges_ignored=True,
            every_other_ELF_byte_and_other_49_inputs_fixed=True, protected_data=layout,
            full_old_guard_prefix_fixed=True, appended_rows=27, progress_and_shared_headers_fixed=True,
            raw_C_exact=False, after={key: hashlib.sha256(value).hexdigest() for key, value in expected.items()})

    def test_02_every_input_guard_row_source_and_physical_corruption(self):
        rb, rt = Path.read_bytes, Path.read_text
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_independent_image_and_all_52_inputs()
        path = self.root / source.PATHS['preset_owner']
        with patch.object(Path, 'read_text', lambda p, *a, **kw: rt(p, *a, **kw) + '\n' if p == path else rt(p, *a, **kw)):
            with self.assertRaises(AssertionError):
                self.test_01_entire_independent_image_and_all_52_inputs()
        path = self.root / source.PATHS['guards']
        guards = rb(path)
        before = (self.out / 'before-guards').read_bytes()
        fields = next(csv.reader(io.StringIO(before.decode())))
        rows = [r for r in csv.DictReader(io.StringIO(guards.decode())) if r['function'] == source.FUNCTION]
        self.assertEqual(len(rows), 27)
        for index in range(len(rows)):
            changed = [dict(row) for row in rows]
            changed[index]['replacement'] = '0x%08X' % (int(changed[index]['replacement'], 0) ^ 1)
            output = io.StringIO(newline='')
            writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
            writer.writerows(changed)
            with patch.object(Path, 'read_bytes', lambda p: before + output.getvalue().encode() if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_independent_image_and_all_52_inputs()
        path = self.root / source.PATHS['elf']
        data = rb(path)
        rows = {row[1]: row for row in symbol_rows(data)}
        offsets = [elf_slot_offset(data, source.ENTRY, 4), rows[source.FUNCTION][0] + 8,
            elf_slot_offset(data, source.MOVE, 4), elf_slot_offset(data, source.SCALE, 4),
            rows['D_8008CBC4'][0] + 4, elf_slot_offset(data, source.TABLES, 4)]
        for first, second in SERIAL_PAIRS:
            offsets.extend((rows[first][0] + 4, rows[second][3]))
        for offset in offsets:
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_independent_image_and_all_52_inputs()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')
        self.receipt('installed-controls', input_flips=52, source_text_flip=True, appended_guard_mutations=27,
            physical_code_symbol_helper_binding_data_flips=6, exact_serialization_flips=8, unknown_predecessor_rejected=True)

    def test_03_all_52_immutable_predecessor_capture_corruptions(self):
        rb = Path.read_bytes
        for key in source.PATHS:
            path = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        self.receipt('capture-controls', all_52_before_capture_flips_rejected=True)

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
                    with self.assertRaisesRegex(AssertionError, 'table-fade fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse', exact_paths=3, every_unknown_input_and_before_after_flip_rejected=True,
            actual_current_whole_image_and_helper_chain_use_no_inverse=True)

    def test_05_serialization_binding_order_and_canonical_symbols(self):
        before = (self.out / 'before-elf').read_bytes()
        after = expected_image(before, (self.root / 'conker/conker.us.bin').read_bytes())
        target_only = bytearray(before)
        row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
        struct.pack_into('>I', target_only, row[0] + 8, 412)
        self.assertEqual(canonical_symbols(after), canonical_symbols(target_only))
        rows = {r[1]: r for r in symbol_rows(before)}
        for name in SERIAL_BINDINGS:
            bad = bytearray(before)
            bad[rows[name][0] + 4] ^= 1
            with self.assertRaisesRegex(ValueError, 'serialization binding'):
                apply_symbol_serialization(bad)
        with self.assertRaisesRegex(ValueError, 'binding|order'):
            apply_symbol_serialization(bytearray(after))
        self.receipt('serialization', exact_swaps=4, exact_metadata_bytes=106, named_definitions_preserved_except_target_size=True,
            eight_binding_mutations_and_wrong_order_rejected=True, no_whole_metadata_exclusions=True)


if __name__ == '__main__':
    unittest.main()
