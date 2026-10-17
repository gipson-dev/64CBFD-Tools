"""Whole first image, exact guard append and all protected input successor checks."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_record_maximum_installation as installation
from tools.experiments import game_record_maximum_scan as source
from tools.tests import record_maximum_checkpoint as checkpoint
from tools.tests import test_game_view_overlay_installed as inverse
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols, symbol_rows
from tools.check_game_data_layout import audit_layout


class RecordMaximumInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out); cls.expected = installation.expected_inputs(cls.root, cls.out)
        cls.wanted = {k:cls.expected.get(k, (cls.out / ('before-' + k)).read_bytes()) for k in source.PATHS}

    def check_live(self):
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), checkpoint.AFTER)
        self.assertEqual(len(source.PATHS), 136)
        for key, path in source.PATHS.items(): self.assertTrue((self.root / path).read_bytes() == self.wanted[key], key)

    def test_01_whole371_byte_prediction_body_extent_serialization_and_protected_data(self):
        self.check_live()
        for key, digest in checkpoint.AFTER.items(): self.assertEqual(hashlib.sha256(self.expected[key]).hexdigest(), digest)
        before, data = (self.out / 'before-elf').read_bytes(), self.expected['elf']
        self.assertEqual((len(before), len(data)), (3257636, 3257636))
        self.assertEqual(sum(a != b for a, b in zip(before, data)), 371)
        at = elf_slot_offset(data, source.ENTRY, 420)
        self.assertEqual(data[at:at + 420], (self.out / 'before-retail_rom').read_bytes()[source.ROM:source.ROM + 420])
        self.assertEqual(sum(a != b for a, b in zip(before[at:at + 420], data[at:at + 420])), 318)
        old = canonical_symbols(before); wanted = old.copy(); original = next(k for k in old if k[0] == source.FUNCTION)
        self.assertEqual(original[2], 12); successor = list(original); successor[2] = 420
        wanted[original] -= 1; wanted[tuple(successor)] += 1
        self.assertEqual(+wanted, canonical_symbols(data))
        guard_before, guard_after = (self.out / 'before-guards').read_bytes(), self.expected['guards']
        self.assertTrue(guard_after.startswith(guard_before)); self.assertEqual(guard_after.count(b'\n') - guard_before.count(b'\n'), 48)
        self.assertEqual(guard_before.count(b'\r\n'), guard_after.count(b'\r\n'))
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        checkpoint.freeze_after(self.root)
        (self.out / 'installed-image.json').write_text(json.dumps(dict(after=checkpoint.AFTER,
            changed_ELF_bytes=371, code_bytes=318, extent_bytes=2, exact_metadata_bytes=51,
            exact_symbol_groups=1, metadata_exclusions=0, raw_C_words=105, normalized_words=105,
            extent=[12, 420], new_guards=48, existing_guard_bytes_unchanged=True,
            unchanged_other_inputs=133, no_new_compiler_profile=True, protected_layout=layout), indent=2) + '\n')

    def test_02_all136_live_inputs_and_code_caller_guard_metadata_corruptions(self):
        self.check_live(); read = Path.read_bytes
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p:read(p) + b'\n' if p == path else read(p)):
                with self.assertRaises(AssertionError): self.check_live()
        path = self.root / source.PATHS['elf']; data = read(path)
        offsets = [elf_slot_offset(data, va, 4) for va in (source.ENTRY, source.ENTRY + 0x98,
            source.ENTRY + 0x11C, source.ENTRY + 416, 0x1501CC3C, 0x1501C880, 0x1501D348)]
        for row in symbol_rows(data):
            if row[1] in (source.FUNCTION, 'D_800C35D0', '.L15099274_game_data', 'D_800A8D98'):
                offsets.extend((row[0], row[0] + 4, row[0] + 8, row[0] + 12, row[3]))
        for at in offsets:
            bad = bytearray(data); bad[at] ^= 1
            with patch.object(Path, 'read_bytes', lambda p:bytes(bad) if p == path else read(p)):
                with self.assertRaises(AssertionError): self.check_live()

    def test_03_only_exact_successor_and_both_fixture_stages(self):
        with patch.object(inverse, 'checkpoint', checkpoint):
            inverse.ViewOverlayInstalledTests.test_03_only_exact_successor_and_both_fixture_stages(self)


if __name__ == '__main__': unittest.main()
