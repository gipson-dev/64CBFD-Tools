"""Whole first prediction, both source owners, exact guards and protected input audit."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_sequence_state_reset_installation as installation
from tools.experiments import game_sequence_state_reset as source
from tools.tests import sequence_state_reset_checkpoint as checkpoint
from tools.tests import sequence_record_setup_checkpoint as successor
from tools.tests import test_game_view_overlay_installed as inverse
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols, symbol_rows
from tools.check_game_data_layout import audit_layout


class SequenceStateResetInstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out); cls.expected = installation.expected_inputs(cls.root, cls.out)
        cls.wanted = {k:cls.expected.get(k, (cls.out / ('before-' + k)).read_bytes()) for k in source.PATHS}

    def check_live(self):
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), checkpoint.AFTER)
        self.assertEqual(len(source.PATHS), 136)
        for key, path in source.PATHS.items():
            self.assertTrue(successor.previous_input((self.root / path).read_bytes(), path, self.root) == self.wanted[key], key)

    def test_01_whole651_byte_prediction_both_owners_extent_metadata_and_data(self):
        self.check_live()
        for key, digest in checkpoint.AFTER.items(): self.assertEqual(hashlib.sha256(self.expected[key]).hexdigest(), digest)
        before, data = (self.out / 'before-elf').read_bytes(), self.expected['elf']
        self.assertEqual((len(before), len(data)), (3257636, 3257636)); self.assertEqual(sum(a != b for a, b in zip(before, data)), 651)
        at = elf_slot_offset(data, source.ENTRY, 400)
        self.assertEqual(data[at:at + 400], (self.out / 'before-retail_rom').read_bytes()[source.ROM:source.ROM + 400])
        self.assertEqual(sum(a != b for a, b in zip(before[at:at + 400], data[at:at + 400])), 374)
        old = canonical_symbols(before); wanted = old.copy(); original = next(k for k in old if k[0] == source.FUNCTION)
        self.assertEqual(original[2], 12); successor = list(original); successor[2] = 400
        wanted[original] -= 1; wanted[tuple(successor)] += 1; self.assertEqual(+wanted, canonical_symbols(data))
        self.assertEqual(len(installation.SERIALIZATION), 10)
        for entry, length in ((0x15008248, 132), (0x150233BC, 40), (0x1501CE54, 420), (0x1501CC3C, 388), (0x1501C880, 956)):
            position = elf_slot_offset(data, entry, length); self.assertEqual(before[position:position + length], data[position:position + length])
        guard_before, guard_after = (self.out / 'before-guards').read_bytes(), self.expected['guards']
        self.assertTrue(guard_after.startswith(guard_before)); self.assertEqual(guard_after.count(b'\n') - guard_before.count(b'\n'), 13)
        self.assertEqual(guard_before.count(b'\r\n'), guard_after.count(b'\r\n'))
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        checkpoint.freeze_after(self.root)
        (self.out / 'installed-image.json').write_text(json.dumps(dict(after=checkpoint.AFTER,
            changed_ELF_bytes=651, code_bytes=374, extent_bytes=2, exact_metadata_bytes=275,
            exact_symbol_groups=10, metadata_exclusions=0, raw_C_words=100, normalized_words=100,
            extent=[12, 400], new_guards=13, existing_guard_bytes_unchanged=True,
            unchanged_other_inputs=132, caller_prototype_only=True, no_new_compiler_profile=True, protected_layout=layout), indent=2) + '\n')

    def test_02_all136_live_inputs_and_both_owners_guards_and_all_metadata_groups_fail_closed(self):
        self.check_live(); read = Path.read_bytes
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p:read(p) + b'\n' if p == path else read(p)):
                with self.assertRaises(AssertionError): self.check_live()
        path = self.root / source.PATHS['elf']; data = read(path)
        offsets = [elf_slot_offset(data, va, 4) for va in (source.ENTRY, source.ENTRY + 4, source.ENTRY + 0x16C,
            source.ENTRY + 396, 0x1501CE54, 0x1501CC3C, 0x1501C880, 0x15008248, 0x150233BC)]
        names = {source.FUNCTION} | {name for row in installation.SERIALIZATION for name in row[0]}
        for row in symbol_rows(data):
            if row[1] in names: offsets.extend((row[0], row[0] + 4, row[0] + 8, row[0] + 12, row[3]))
        for at in offsets:
            bad = bytearray(data); bad[at] ^= 1
            with patch.object(Path, 'read_bytes', lambda p:bytes(bad) if p == path else read(p)):
                with self.assertRaises(AssertionError): self.check_live()

    def test_03_only_exact_successor_and_all_four_before_after_fixture_pairs(self):
        with patch.object(inverse, 'checkpoint', checkpoint):
            inverse.ViewOverlayInstalledTests.test_03_only_exact_successor_and_both_fixture_stages(self)


if __name__ == '__main__': unittest.main()
