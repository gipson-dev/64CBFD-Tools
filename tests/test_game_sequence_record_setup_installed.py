"""Whole first prediction and all 140 protected inputs, with no metadata exclusions."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_sequence_record_setup as setup
from tools.experiments import game_sequence_record_setup_installation as source
from tools.tests import sequence_record_setup_checkpoint as checkpoint
from tools.tests import test_game_view_overlay_installed as inverse
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols, symbol_rows
from tools.check_game_data_layout import audit_layout


class SequenceRecordSetupInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out); cls.expected = source.expected_inputs(cls.root, cls.out)
        cls.wanted = {k:cls.expected.get(k, (cls.out / ('before-' + k)).read_bytes()) for k in source.PATHS}

    def check_live(self):
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), checkpoint.AFTER)
        self.assertEqual(len(source.PATHS), 140)
        for key, path in source.PATHS.items(): self.assertTrue((self.root / path).read_bytes() == self.wanted[key], key)

    def test_01_first_whole_image_prediction_all_473_words_extent_and_data(self):
        self.check_live()
        for key, digest in checkpoint.AFTER.items(): self.assertEqual(source.digest(self.expected[key]), digest)
        before, data = (self.out / 'before-elf').read_bytes(), self.expected['elf']
        self.assertEqual((len(before), len(data)), (3257636, 3257636))
        self.assertEqual(sum(a != b for a, b in zip(before, data)), 1637)
        self.assertEqual((self.out / 'prelink-prediction.elf').read_bytes(), data)
        at = elf_slot_offset(data, setup.ENTRY, 1892)
        self.assertEqual(data[at:at + 1892], (self.out / 'before-retail_rom').read_bytes()[setup.ROM:setup.ROM + 1892])
        self.assertEqual(sum(a != b for a, b in zip(before[at:at + 1892], data[at:at + 1892])), 1468)
        old = canonical_symbols(before); wanted = old.copy(); original = next(k for k in old if k[0] == setup.FUNCTION)
        self.assertEqual(original[2], 12); successor = list(original); successor[2] = 1892
        wanted[original] -= 1; wanted[tuple(successor)] += 1; self.assertEqual(+wanted, canonical_symbols(data))
        self.assertEqual(len(source.SERIALIZATION), 7)
        for entry, length in ((0x150082CC,116),(0x151E83E8,200),(0x150233BC,40),
                (0x1501D044,400),(0x1501CE54,420),(0x1501CFF8,76),(0x1501CDC0,148),(0x1501D1D4,132)):
            position = elf_slot_offset(data, entry, length)
            self.assertEqual(before[position:position + length], data[position:position + length])
        guard_before, guard_after = (self.out / 'before-guards').read_bytes(), self.expected['guards']
        self.assertTrue(guard_after.startswith(guard_before))
        self.assertEqual(guard_after.count(b'\n') - guard_before.count(b'\n'), 165)
        self.assertEqual(guard_before.count(b'\r\n'), guard_after.count(b'\r\n'))
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']), (True,189088,720,0))
        checkpoint.freeze_after(self.root)
        (self.out / 'installed-image.json').write_text(json.dumps(dict(after=checkpoint.AFTER,
            changed_ELF_bytes=1637,code_bytes=1468,extent_bytes=2,metadata_bytes=167,
            exact_symbol_groups=7,metadata_exclusions=0,raw_words=474,normalized_words=473,
            extent=[12,1892],new_guards=165,old_guard_bytes_and_298_CRLF_lines_preserved=True,
            unchanged_other_inputs=135,two_caller_prototypes_only=True,no_new_compiler_profile=True,
            protected_layout=layout),indent=2)+'\n')

    def test_02_all140_live_inputs_and_every_changed_symbol_definition_fail_closed(self):
        self.check_live(); read = Path.read_bytes
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p == path else read(p)):
                with self.assertRaises(AssertionError): self.check_live()
        path = self.root / source.PATHS['elf']; data = read(path)
        offsets = [elf_slot_offset(data, va, 4) for va in (setup.ENTRY,setup.ENTRY+0x45C,setup.ENTRY+1888,0x150082CC,0x151E83E8)]
        names = {setup.FUNCTION} | {name for row in source.SERIALIZATION for name in row[0]}
        for row in symbol_rows(data):
            if row[1] in names: offsets.extend((row[0],row[0]+4,row[0]+8,row[0]+12,row[3]))
        for at in offsets:
            bad = bytearray(data); bad[at] ^= 1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p == path else read(p)):
                with self.assertRaises(AssertionError): self.check_live()

    def test_03_only_exact_successor_and_all_five_before_after_fixture_pairs(self):
        with patch.object(inverse,'checkpoint',checkpoint):
            inverse.ViewOverlayInstalledTests.test_03_only_exact_successor_and_both_fixture_stages(self)


if __name__ == '__main__': unittest.main()
