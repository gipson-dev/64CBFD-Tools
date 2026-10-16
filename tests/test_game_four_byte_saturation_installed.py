"""No-exclusion installed-image and precise two-input successor gate."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_four_byte_saturation as source
from tools.tests import four_byte_saturation_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


class FourByteSaturationInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def test_01_complete_image_inputs_layout_and_accessor_unchanged(self):
        expected = source.expected_inputs(self.root, self.out)
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), checkpoint.AFTER)
        for key, relative in source.PATHS.items():
            wanted = expected.get(key, (self.out / ('before-'+key)).read_bytes())
            self.assertEqual((self.root / relative).read_bytes(), wanted, key)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest)
        before, data = (self.out / 'before-elf').read_bytes(), expected['elf']
        self.assertEqual(len(before), len(data))
        self.assertEqual(sum(a != b for a, b in zip(before, data)), 164)
        at = elf_slot_offset(data, source.ENTRY, 232)
        self.assertEqual(data[at:at+232], (self.out / 'before-retail_rom').read_bytes()[source.ROM:source.ROM+232])
        row = next(r for r in symbol_rows(data) if r[1] == source.FUNCTION)
        self.assertEqual(row[2][1:3], (source.ENTRY, 232))
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        checkpoint.freeze_after(self.root)
        (self.out / 'installed-image.json').write_text(json.dumps(dict(changed_ELF_bytes=164, slot_bytes=232,
            symbol_extent=[12, 232], every_other_ELF_byte_and_90_inputs_fixed=True, metadata_exclusions=0,
            target_guards=0, protected_layout=layout, after=checkpoint.AFTER), indent=2)+'\n')

    def test_02_all_live_input_and_complete_image_corruptions_rejected(self):
        rb = Path.read_bytes
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p)+b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_complete_image_inputs_layout_and_accessor_unchanged()
        path = self.root / source.PATHS['elf']
        data = rb(path)
        row = next(r for r in symbol_rows(data) if r[1] == source.FUNCTION)
        positions = [elf_slot_offset(data, a, 4) for a in (source.ENTRY, source.ENTRY+228, source.ENTRY+232,
            source.DRIVER, source.TABLE, 0x1516EED4)] + [row[0], row[0]+4, row[0]+8, row[3]]
        for at in positions:
            bad = bytearray(data)
            bad[at] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_complete_image_inputs_layout_and_accessor_unchanged()

    def test_03_exact_checkpoint_mapping_and_both_fixture_stages(self):
        checkpoint.freeze_after(self.root)
        rb = Path.read_bytes
        for relative, key in checkpoint.PATHS.items():
            current = (self.root / relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(current, relative, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(current+b'\n', relative, self.root), current+b'\n')
            self.assertEqual(checkpoint.previous_input(current, 'unowned', self.root), current)
            for stage in ('before', 'after'):
                path = self.out / (stage+'-'+key)
                with patch.object(Path, 'read_bytes', lambda p: rb(p)+b'\n' if p == path else rb(p)):
                    with self.assertRaisesRegex(AssertionError, 'fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
