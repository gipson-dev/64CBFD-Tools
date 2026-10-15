"""Independent complete counter-preset image and all input/guard corruption gates."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_counter_preset_match as source
from tools.tests import counter_preset_match_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != source.BASELINE['elf']:
        raise ValueError('Unknown counter-match predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12):
        raise ValueError('Unknown counter-match predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, source.ENTRY, 336)
    result[offset:offset + 336] = rom[source.ROM:source.ROM + 336]
    struct.pack_into('>I', result, row[0] + 8, 336)
    return bytes(result)


class CounterMatchInstalledTests(unittest.TestCase):
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
        expected = dict(elf=expected_image(before, (self.root / 'conker/conker.us.bin').read_bytes()),
            preset_owner=source.recovered_owner((self.out / 'before-preset_owner').read_text()).encode(),
            guards=source.guard_manifest(guards, *source.raw_target(self.out / 'qualified.o')))
        for key, relative in source.PATHS.items():
            self.assertEqual((self.root / relative).read_bytes(), expected.get(key, (self.out / ('before-' + key)).read_bytes()), key)
        self.assertEqual((self.root / source.PATHS['preset_owner']).read_text(), expected['preset_owner'].decode())
        self.assertEqual(expected['guards'][:len(guards)], guards)
        self.assertEqual(len(expected['guards'][len(guards):].splitlines()), 38)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest, key)
        checkpoint.freeze_after(self.root)
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        self.receipt('installed-image', ELF_bytes=len(before), changed_bytes=sum(a != b for a, b in zip(before, expected['elf'])),
            target_slot=[source.ENTRY, 336], symbol_extent=[12, 336], metadata_allowances=0,
            every_other_ELF_byte_and_other_49_inputs_fixed=True, protected_data=layout,
            full_old_guard_prefix_fixed=True, appended_rows=38, progress_and_shared_headers_fixed=True,
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
        rows = list(csv.DictReader(io.StringIO(guards.decode())))
        target = [i for i, row in enumerate(rows) if row['function'] == source.FUNCTION]
        self.assertEqual(len(target), 38)
        for index in target:
            changed = [dict(row) for row in rows]
            row = changed[index]
            if row['omit'] == 'true':
                row['omit'] = 'false'
            else:
                row['replacement'] = '0x%08X' % (int(row['replacement'], 0) ^ 1)
            output = io.StringIO(newline='')
            writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
            writer.writerows(row for row in changed if row['function'] == source.FUNCTION)
            bad = before + output.getvalue().encode()
            with patch.object(Path, 'read_bytes', lambda p: bad if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_independent_image_and_all_52_inputs()
        path = self.root / source.PATHS['elf']
        data = rb(path)
        row = next(row for row in symbol_rows(data) if row[1] == source.FUNCTION)
        counter = next(row for row in symbol_rows(data) if row[1] == 'D_800DD2A0')
        self.assertEqual(counter[2][1], source.TABLE)
        for offset in (elf_slot_offset(data, source.ENTRY, 4), row[0] + 8,
                elf_slot_offset(data, source.CALLEE, 4), elf_slot_offset(data, 0x15167A68, 4),
                counter[0] + 4, elf_slot_offset(data, 0x800A6E00, 4)):
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_entire_independent_image_and_all_52_inputs()
        with self.assertRaisesRegex(ValueError, 'predecessor ELF'):
            expected_image((self.out / 'before-elf').read_bytes() + b'\n', b'')
        self.receipt('installed-controls', input_flips=52, source_text_flip=True, every_appended_guard_row_mutated=38,
            physical_code_symbol_factory_allocator_counter_binding_and_data_flips=6, unknown_predecessor_rejected=True)

    def test_03_exact_input_inverse_and_every_before_after_capture(self):
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
                    with self.assertRaisesRegex(AssertionError, 'counter-match fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        self.receipt('inverse', exact_paths=3, every_unknown_or_corrupt_input_and_capture_rejected=True,
            actual_current_full_image_and_factory_chain_use_no_inverse=True)

    def test_04_all_52_immutable_predecessor_capture_corruptions(self):
        rb = Path.read_bytes
        for key in source.PATHS:
            path = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        self.receipt('capture-controls', all_52_before_capture_flips_rejected=True,
            after_captures_independently_checked_by_exact_input_inverse=True)


if __name__ == '__main__':
    unittest.main()
