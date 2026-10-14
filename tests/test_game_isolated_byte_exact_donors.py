"""Active-owner proof for byte-exact bodies rescued from failed draft files."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_isolated_donor_candidates as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import test_game_unlinked_byte_exact_donors as owners
from tools.tests.test_game_one_shot_timer_match import canonical_symbols
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout
from tools.tests import isolated_donor_checkpoint as checkpoint


class IsolatedByteExactDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.out.mkdir(exist_ok=True)
        source.freeze(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()

    def test_01_complete_owners_neighbors_pools_and_both_padders(self):
        with patch.object(owners, 'source', source):
            owners.UnlinkedByteExactDonorTests.test_01_complete_owner_neighbors_pools_and_both_production_padders(self)

    def test_02_independent_original_and_rebased_links(self):
        with patch.object(owners, 'source', source):
            owners.UnlinkedByteExactDonorTests.test_06_independent_original_links_and_HI_LO_carries(self)

    def test_03_effective_compiled_preset_and_category_controls(self):
        for name, old, new in (('func_150F0938', '0x25', '0x24'), ('func_150B003C', '== 6', '== 7')):
            spec = source.TARGETS[name]
            before = (self.out / ('before-' + spec['owner'])).read_text()
            after = source.recover(before, spec['owner'])
            lo, hi = build.function_span(after, name)
            changed = after[lo:hi].replace(old, new)
            self.assertNotEqual(changed, after[lo:hi])
            obj, _ = build.compile_owner(self.root, self.out, after[:lo] + changed + after[hi:], 'negative-' + name)
            emitted, functions = build.link_owner(self.root, self.out, obj, spec['owner'])
            entry, count = int(name[5:], 16), spec['words']
            info = functions[name]
            rom = entry - 0x15000000 + 0x2D4B0
            self.assertNotEqual(emitted[info['value']:info['value'] + count * 4], self.rom[rom:rom + count * 4])

    def test_04_installed_sources_and_independent_closed_image(self):
        for owner in {spec['owner'] for spec in source.TARGETS.values()}:
            self.assertEqual((self.root / source.path(owner)).read_text(),
                source.recover((self.out / ('before-' + owner)).read_text(), owner))
        before = (self.out / 'before-elf').read_bytes()
        self.assertEqual(hashlib.sha256(before).hexdigest(), source.BASELINE_ELF)
        after_path = self.root / 'conker/build/conker.us.elf'
        after = after_path.read_bytes()
        expected = bytearray(before)
        symbols = canonical_symbols(before)
        for name, spec in source.TARGETS.items():
            entry, count = int(name[5:], 16), spec['words']
            rom = entry - 0x15000000 + 0x2D4B0
            truth = self.rom[rom:rom + count * 4]
            offset = elf_slot_offset(before, entry, count * 4)
            expected[offset:offset + count * 4] = truth
            self.assertEqual(after[elf_slot_offset(after, entry, count * 4):][:count * 4], truth, name)
            old = next(row for row in symbols if row[0] == name)
            symbols[old] -= 1
            symbols[(name, old[1], count * 4, *old[3:])] += 1
        self.assertEqual(+symbols, canonical_symbols(after))
        previous, current = sections(self.out / 'before-elf'), sections(after_path)
        self.assertEqual(set(previous), set(current))
        base, game = previous['.game']
        offset = elf_slot_offset(before, base, len(game))
        self.assertEqual(current['.game'], (base, bytes(expected[offset:offset + len(game)])))
        for name in set(previous) - {'.game', '.symtab', '.strtab'}:
            self.assertEqual(previous[name], current[name], name)
        for key, path in (('guards', 'conker/retail_word_patches.us.csv'), ('makefile', 'conker/Makefile')):
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes())
        progress = (self.out / 'before-progress').read_bytes()
        row = next(line for line in progress.splitlines(keepends=True) if b',func_150B003C,' in line)
        self.assertTrue(row.endswith(b',asm\n'))
        progress = progress.replace(row, row.replace(b',asm\n', b',c\n'))
        self.assertEqual((self.root / 'conker/progress.csv').read_bytes(), progress)
        data = audit_layout(after_path, self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        (self.out / 'image-transition.json').write_text(json.dumps(dict(
            targets=len(source.TARGETS), words=sum(spec['words'] for spec in source.TARGETS.values()),
            changed_game_bytes=sum(a != b for a, b in zip(game, current['.game'][1])),
            ELF_sha256=hashlib.sha256(after).hexdigest(), new_C_rows=1, new_guards=0,
            all_other_executable_data_overflow_sections_fixed=True, symbol_changes_closed=True,
            protected_data=data), indent=2) + '\n')

    def test_05_effective_installed_words_and_immutable_inputs(self):
        read_bytes = Path.read_bytes
        path = self.root / 'conker/build/conker.us.elf'
        for name, spec in source.TARGETS.items():
            changed = bytearray(read_bytes(path))
            changed[elf_slot_offset(changed, int(name[5:], 16), spec['words'] * 4) + 3] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(changed) if p == path else read_bytes(p)):
                with self.assertRaises(AssertionError):
                    self.test_04_installed_sources_and_independent_closed_image()

        for filename in ('conker/progress.csv', 'conker/Makefile', 'conker/retail_word_patches.us.csv'):
            path = self.root / filename
            changed = read_bytes(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p: changed if p == path else read_bytes(p)):
                with self.assertRaises(AssertionError):
                    self.test_04_installed_sources_and_independent_closed_image()

    def test_06_literal_serialization_and_pinned_inverse(self):
        self.test_04_installed_sources_and_independent_closed_image()
        checkpoint.freeze_after(self.root)
        for path, key in checkpoint.PATHS.items():
            data = (self.root / path).read_bytes()
            self.assertEqual(checkpoint.previous_input(data, path, self.root), checkpoint.fixture(self.root, 'before', key))
            bad = data[:-1] + bytes([data[-1] ^ 1])
            self.assertEqual(checkpoint.previous_input(bad, path, self.root), bad)


if __name__ == '__main__':
    unittest.main()
