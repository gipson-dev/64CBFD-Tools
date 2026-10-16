"""Full qualified ELF, explicit metadata cycle and every unaffected input."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_rectangle_preset_dispatch as source
from tools.tests import rectangle_preset_dispatch_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols, symbol_rows
from tools.check_game_data_layout import audit_layout


class RectangleDispatchInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def test_01_complete_preinstall_prediction_every_live_input_and_layout(self):
        expected = source.expected_inputs(self.root, self.out)
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), checkpoint.AFTER)
        for key, relative in source.PATHS.items():
            wanted = expected.get(key, (self.out / ('before-'+key)).read_bytes())
            self.assertEqual((self.root / relative).read_bytes(), wanted, key)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest)
        before, rejected = (self.out / 'before-elf').read_bytes(), (self.out / 'slot-only-rejected.elf').read_bytes()
        self.assertEqual(source.serialize_symbols(rejected), expected['elf'])
        self.assertEqual(canonical_symbols(rejected), canonical_symbols(expected['elf']))
        self.assertEqual(sum(a != b for a, b in zip(before, expected['elf'])), 449)
        self.assertEqual(sum(a != b for a, b in zip(before, rejected)), 396)
        self.assertEqual(sum(a != b for a, b in zip(rejected, expected['elf'])), 53)
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        checkpoint.freeze_after(self.root)
        (self.out / 'installed-image.json').write_text(json.dumps(dict(changed_ELF_bytes=449, target_slot=508,
            symbol_extent=[12, 508], slot_extent_changed_bytes=396, exact_serialization_bytes=53,
            every_other_ELF_byte_and_80_inputs_fixed=True, no_exclusions=True, target_guards=0,
            protected_layout=layout, after=checkpoint.AFTER), indent=2)+'\n')

    def test_02_all_live_inputs_and_physical_code_data_cycle_corruptions(self):
        rb = Path.read_bytes
        for relative in source.PATHS.values():
            target = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p)+b'\n' if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_complete_preinstall_prediction_every_live_input_and_layout()
        target = self.root / source.PATHS['elf']
        data = rb(target)
        positions = [elf_slot_offset(data, at, 4) for at in (source.ENTRY, source.ENTRY+80, source.ENTRY+160,
            source.ENTRY+288, source.ENTRY+484, source.ENTRY+504, source.CALLEE, 0x15171200, 0x800A6FC0, 0x800A6FC4)]
        for row in symbol_rows(data):
            if row[1] in (source.FUNCTION, 'D_800A6FC0', '.L1513145C_game_data', 'D_80098D90'):
                positions.extend((row[0], row[0]+4, row[0]+8, row[3]))
        for at in positions:
            bad = bytearray(data)
            bad[at] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_complete_preinstall_prediction_every_live_input_and_layout()

    def test_03_capture_prediction_and_successor_corruptions(self):
        rb, rt = Path.read_bytes, Path.read_text
        path = self.out / 'initial-prediction.json'
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == path else rt(p, *a, **kw)):
            with self.assertRaises(AssertionError):
                self.test_01_complete_preinstall_prediction_every_live_input_and_layout()
        path = self.out / 'slot-only-rejected.elf'
        with patch.object(Path, 'read_bytes', lambda p: rb(p)+b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(ValueError, 'structural'):
                source.serialize_symbols(path.read_bytes())
        checkpoint.freeze_after(self.root)
        for relative, key in checkpoint.PATHS.items():
            data = (self.root / relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(data, relative, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(data+b'\n', relative, self.root), data+b'\n')
            self.assertEqual(checkpoint.previous_input(data, 'unowned', self.root), data)
            for stage in ('before', 'after'):
                path = self.out / (stage+'-'+key)
                with patch.object(Path, 'read_bytes', lambda p: rb(p)+b'\n' if p == path else rb(p)):
                    with self.assertRaisesRegex(AssertionError, 'fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(data, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
