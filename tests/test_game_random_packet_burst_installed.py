"""No-exclusion installed ELF and all frozen/live input corruption checks."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_random_packet_burst as source
from tools.tests import random_packet_burst_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout


class BurstInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def test_01_complete_first_prediction_and_all_live_inputs(self):
        expected = source.expected_inputs(self.root, self.out)
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), checkpoint.AFTER)
        for key, relative in source.PATHS.items():
            actual = (self.root / relative).read_bytes()
            wanted = expected.get(key, (self.out / ('before-' + key)).read_bytes())
            self.assertEqual(actual, wanted, key)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest)
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        checkpoint.freeze_after(self.root)
        (self.out / 'installed-image.json').write_text(json.dumps(dict(changed_ELF_bytes=793,
            target_slot=1024, symbol_extent=[12, 1024], metadata_exclusions=0,
            first_complete_preinstall_prediction_matches=True, target_guards=0,
            every_other_ELF_byte_and_80_inputs_fixed=True, protected_layout=layout, after=checkpoint.AFTER), indent=2) + '\n')

    def test_02_all_live_inputs_and_physical_code_data_metadata_corruptions(self):
        rb = Path.read_bytes
        for relative in source.PATHS.values():
            target = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_complete_first_prediction_and_all_live_inputs()
        target, data = self.root / source.PATHS['elf'], (self.root / source.PATHS['elf']).read_bytes()
        positions = [elf_slot_offset(data, at, 4) for at in (source.ENTRY, source.ENTRY+108,
            source.ENTRY+288, source.ENTRY+944, source.ENTRY+1020, source.RANDOM,
            source.LOOKUP, source.SUBMIT, 0x800A6FB0, 0x800A6FBC, 0x15170F4C, 0x15171600)]
        row = next(r for r in symbol_rows(data) if r[1] == source.FUNCTION)
        positions += [row[0], row[0]+4, row[0]+8, row[3]]
        for at in positions:
            bad = bytearray(data)
            bad[at] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == target else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_complete_first_prediction_and_all_live_inputs()

    def test_03_prediction_capture_and_successor_corruptions(self):
        rb, rt = Path.read_bytes, Path.read_text
        path = self.out / 'initial-prediction.json'
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == path else rt(p, *a, **kw)):
            with self.assertRaises(AssertionError):
                self.test_01_complete_first_prediction_and_all_live_inputs()
        checkpoint.freeze_after(self.root)
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
