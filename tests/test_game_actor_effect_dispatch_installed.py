"""Entire completed 19E040 owner and no-exclusion installed image proof."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_effect_dispatch as source
from tools.tests import actor_effect_dispatch_checkpoint as checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import parse_retail_slice


class ActorEffectInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)

    def test_01_full_image_first_prediction_inputs_and_all_nine_owner_slots(self):
        expected = source.expected_inputs(self.root, self.out)
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), checkpoint.AFTER)
        for key, relative in source.PATHS.items():
            wanted = expected.get(key, (self.out / ('before-'+key)).read_bytes())
            self.assertEqual((self.root / relative).read_bytes(), wanted, key)
        for key, digest in checkpoint.AFTER.items():
            self.assertEqual(hashlib.sha256(expected[key]).hexdigest(), digest)
        before, data = (self.out / 'before-elf').read_bytes(), expected['elf']
        self.assertEqual(sum(a != b for a, b in zip(before, data)), 127)
        lo, hi, funcs, _ = parse_retail_slice(self.root / source.PATHS['edge_wrapper_original'])
        at = elf_slot_offset(data, lo, hi-lo)
        self.assertEqual(data[at:at+hi-lo], (self.out / 'before-retail_rom').read_bytes()[0x19E040:0x19E040+hi-lo])
        self.assertEqual((len(funcs), hi-lo), (9, 4368))
        owner = expected['edge_wrapper_owner'].decode()
        self.assertNotIn('return 0;', owner)
        self.assertNotIn('Non-matching placeholders', owner)
        row = next(r for r in symbol_rows(data) if r[1] == source.FUNCTION)
        self.assertEqual(row[2][1:3], (source.ENTRY, 168))
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        checkpoint.freeze_after(self.root)
        (self.out / 'installed-image.json').write_text(json.dumps(dict(changed_ELF_bytes=127,
            body_bytes=168, slot_bytes=172, terminal_padding=4, symbol_extent=[12, 168],
            complete_owner_functions=9, complete_owner_bytes=4368, all_owner_slots_byte_exact=True,
            every_other_ELF_byte_and_87_inputs_fixed=True, metadata_exclusions=0,
            target_guards=0, protected_layout=layout, after=checkpoint.AFTER), indent=2)+'\n')

    def test_02_all_live_inputs_physical_code_callees_padding_and_metadata_corruptions(self):
        rb = Path.read_bytes
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p)+b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_full_image_first_prediction_inputs_and_all_nine_owner_slots()
        path = self.root / source.PATHS['elf']
        data = rb(path)
        positions = [elf_slot_offset(data, at, 4) for at in (source.ENTRY, source.ENTRY+80, source.ENTRY+108,
            source.ENTRY+124, source.ENTRY+140, source.ENTRY+164, source.ENTRY+168, source.SOUND,
            source.FIRST, source.SECOND, source.THIRD, 0x15171600, 0x15171200, 0x800A6FA4)]
        row = next(r for r in symbol_rows(data) if r[1] == source.FUNCTION)
        positions.extend((row[0], row[0]+4, row[0]+8, row[3]))
        for at in positions:
            bad = bytearray(data)
            bad[at] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_01_full_image_first_prediction_inputs_and_all_nine_owner_slots()

    def test_03_initial_prediction_capture_and_successor_corruptions(self):
        rb, rt = Path.read_bytes, Path.read_text
        path = self.out / 'initial-prediction.json'
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == path else rt(p, *a, **kw)):
            with self.assertRaises(AssertionError):
                self.test_01_full_image_first_prediction_inputs_and_all_nine_owner_slots()
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
