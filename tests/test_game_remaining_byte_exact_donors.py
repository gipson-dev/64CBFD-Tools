"""Direct retail bodies, complete owner isolation, and closed linked transition."""
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_remaining_donor_candidates as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_one_shot_timer_match import canonical_symbols, symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout
from tools.tests import remaining_donor_checkpoint as checkpoint
from tools.tests import unlinked_donor_checkpoint

REMOVED = ('func_15042D94', 'func_15079228', 'func_151F2E88')


class RemainingByteExactDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_all_nineteen_complete_raw_bodies_and_742_neighbors(self):
        records = []
        for owner in sorted({value[0] for value in source.TARGETS.values()}):
            flags = ('-g',) if owner.startswith('libultra/audio') else ('-O2', '-g3')
            before = checkpoint.fixture(self.root, 'before', owner).decode()
            current = unlinked_donor_checkpoint.previous_input((self.root / source.owner_path(owner)).read_bytes(), source.owner_path(owner), self.root).decode()
            self.assertEqual(current.encode(), checkpoint.fixture(self.root, 'after', owner))
            old, w0 = source.compile_owner(self.root, self.out, before, 'audit-before-' + owner.replace('/', '_'), flags)
            new, w1 = source.compile_owner(self.root, self.out, current, 'audit-after-' + owner.replace('/', '_'), flags)
            t0, f0, r0 = parse_object(old)
            t1, f1, r1 = parse_object(new)
            selected = {name for name, spec in source.TARGETS.items() if spec[0] == owner}
            self.assertEqual(set(f0), set(f1))
            for name in set(f0) - selected:
                a, b = f0[name], f1[name]
                self.assertEqual(a['size'], b['size'], name)
                self.assertEqual(t0[a['value']:a['value'] + a['size']], t1[b['value']:b['value'] + b['size']], name)
                relative = lambda table, info: {at - info['value']: value for at, value in table.items()
                    if info['value'] <= at < info['value'] + info['size']}
                self.assertEqual(relative(r0, a), relative(r1, b), name)
            self.assertEqual(normalized_pools(old), normalized_pools(new), owner)
            self.assertLessEqual(w1.count('cfe: Warning'), w0.count('cfe: Warning'))
            if owner == 'game_221290':
                new, w1 = source.compile_owner(self.root, self.out, current, 'audit-codec-g', ('-g',))
            emitted, functions = source.link_owner(self.root, self.out, new, owner)
            for name in sorted(selected):
                spec = source.TARGETS[name]
                info = functions[name]
                count, entry = spec[1], int(name[5:], 16)
                expected = self.rom[entry - 0x15000000 + 0x2D4B0:entry - 0x15000000 + 0x2D4B0 + count * 4]
                self.assertGreaterEqual(info['size'], count * 4)
                self.assertEqual(emitted[info['value']:info['value'] + count * 4], expected, name)
                self.assertFalse(any(emitted[info['value'] + count * 4:info['value'] + info['size']]), name)
            records.append(dict(owner=owner, neighbors=len(f0) - len(selected), targets=len(selected)))
        self.assertEqual(sum(record['neighbors'] for record in records), 742)
        self.receipt('direct-and-owners', owners=records, new_guards=0, all_raw_words_exact=True,
            neighbor_words_relocations_pools_fixed=True)

    def test_02_all_linked_slots_protected_data_and_closed_overflow_repacking(self):
        before = checkpoint.fixture(self.root, 'before', 'elf')
        after = unlinked_donor_checkpoint.previous_input((self.root / 'conker/build/conker.us.elf').read_bytes(), 'conker/build/conker.us.elf', self.root)
        self.assertEqual(after, checkpoint.fixture(self.root, 'after', 'elf'))
        expected = bytearray(before)
        for name, (_, words, _) in source.TARGETS.items():
            entry = int(name[5:], 16)
            at = elf_slot_offset(before, entry, words * 4)
            rom = entry - 0x15000000 + 0x2D4B0
            expected[at:at + words * 4] = self.rom[rom:rom + words * 4]
            self.assertEqual(after[elf_slot_offset(after, entry, words * 4):][:words * 4], self.rom[rom:rom + words * 4], name)
        rows0 = {name: fields for _, name, fields, _ in symbol_rows(before) if name.startswith('__retail_overflow_func_')}
        rows1 = {name: fields for _, name, fields, _ in symbol_rows(after) if name.startswith('__retail_overflow_func_')}
        self.assertEqual(set(rows0) - set(rows1), {'__retail_overflow_' + name for name in REMOVED})
        self.assertFalse(set(rows1) - set(rows0))
        retained = sorted(rows1, key=lambda name: rows0[name][1])
        for name in retained:
            old, new = rows0[name], rows1[name]
            self.assertEqual(old[2:], new[2:], name)
            self.assertEqual(before[elf_slot_offset(before, old[1], old[2]):][:old[2]],
                after[elf_slot_offset(after, new[1], new[2]):][:new[2]], name)
            public = name.replace('__retail_overflow_', '')
            entry = int(public[5:], 16)
            at = elf_slot_offset(before, entry, 8)
            jump = 0x08000000 | (old[1] >> 2 & 0x3FFFFFF)
            if struct.unpack_from('>I', before, at)[0] == jump:
                struct.pack_into('>I', expected, at, 0x08000000 | (new[1] >> 2 & 0x3FFFFFF))
        old_sections = sections(self.out / 'before-elf')
        new_sections = sections(self.out / 'after-elf')
        game0 = old_sections['.game']
        offset = elf_slot_offset(before, game0[0], len(game0[1]))
        self.assertEqual(new_sections['.game'][1], expected[offset:offset + len(game0[1])])
        for name in set(old_sections) - {'.game', '.game_overflow', '.symtab', '.strtab'}:
            self.assertEqual(new_sections[name], old_sections[name], name)
        removed_bytes = sum(rows0['__retail_overflow_' + name][2] for name in REMOVED)
        self.assertEqual(removed_bytes, 3360)
        self.assertEqual(len(old_sections['.game_overflow'][1]) - len(new_sections['.game_overflow'][1]), removed_bytes)
        self.assertEqual(new_sections['.game_overflow'][1], b''.join(
            before[elf_slot_offset(before, rows0[name][1], rows0[name][2]):][:rows0[name][2]]
            for name in retained))
        original_symbols = canonical_symbols(before)
        new_symbols = canonical_symbols(after)
        expected_symbols = original_symbols.copy()
        for name, (_, words, _) in source.TARGETS.items():
            old = next(row for row in expected_symbols if row[0] == name)
            new = (old[0], old[1], words * 4, *old[3:])
            expected_symbols[old] -= 1
            expected_symbols[new] += 1
        for name, old in rows0.items():
            expected_symbols[(name, *old[1:])] -= 1
            if name in rows1:
                expected_symbols[(name, *rows1[name][1:])] += 1
        for filename in ('game_70200.c.o', 'game_21FC90.c.o'):
            expected_symbols[(filename, 0, 0, 4, 0, 65521)] -= 1
        for name in ('__romPos', 'debugger_overflow_ROM_START'):
            old = next(row for row in expected_symbols if row[0] == name)
            expected_symbols[old] -= 1
            expected_symbols[(name, old[1] - removed_bytes, *old[2:])] += 1
        self.assertEqual(+expected_symbols, new_symbols)
        data = audit_layout(self.root / 'conker/build/conker.us.elf', self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('image-transition', targets=19, retail_words=sum(spec[1] for spec in source.TARGETS.values()),
            removed_overflow_bytes=removed_bytes, retained_overflow_bodies=len(retained),
            changed_game_bytes=sum(a != b for a, b in zip(old_sections['.game'][1], new_sections['.game'][1])),
            every_other_executable_and_data_section_fixed=True, symbol_definitions_closed=True,
            literal_ELF_serialization_pinned=True, protected_data=data)

    def test_03_progress_guards_and_retained_input_history(self):
        for key, path in (('progress', 'conker/progress.csv'), ('guards', 'conker/retail_word_patches.us.csv')):
            self.assertEqual(unlinked_donor_checkpoint.previous_input((self.root / path).read_bytes(), path, self.root), checkpoint.fixture(self.root, 'before', key))
        self.assertEqual(unlinked_donor_checkpoint.previous_input((self.root / 'conker/Makefile').read_bytes(), 'conker/Makefile', self.root), checkpoint.fixture(self.root, 'after', 'makefile'))
        self.receipt('history', all_old_guard_bytes_fixed=True, all_progress_rows_fixed=True)

    def test_04_effective_word_and_immutable_input_controls(self):
        read_bytes = Path.read_bytes
        for name, (_, words, _) in source.TARGETS.items():
            path = self.root / 'conker/build/conker.us.elf'
            changed = bytearray(read_bytes(path))
            changed[elf_slot_offset(changed, int(name[5:], 16), words * 4) + 3] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(changed) if p == path else read_bytes(p)):
                with self.assertRaises(AssertionError):
                    self.test_02_all_linked_slots_protected_data_and_closed_overflow_repacking()
        for key, path in (('progress', 'conker/progress.csv'), ('guards', 'conker/retail_word_patches.us.csv')):
            path = self.root / path
            changed = read_bytes(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p: changed if p == path else read_bytes(p)):
                with self.assertRaises(AssertionError):
                    self.test_03_progress_guards_and_retained_input_history()
        self.receipt('controls', nineteen_installed_word_corruptions_rejected=True,
            guard_and_progress_corruptions_rejected=True)

    def test_05_three_effective_compiled_source_controls(self):
        mutations = {'func_15008870': ('hi = 0x65', 'hi = 0x64'),
            'func_15079228': ('unk218 -= 1', 'unk218 -= 2'),
            'func_151F8088': ('mask = 0xF0', 'mask = 0xE0')}
        for name, (old, new) in mutations.items():
            owner, count, _ = source.TARGETS[name]
            current = (self.root / source.owner_path(owner)).read_text()
            lo, hi = source.function_span(current, name)
            replacement = current[lo:hi].replace(old, new)
            self.assertNotEqual(replacement, current[lo:hi])
            changed = current[:lo] + replacement + current[hi:]
            flags = ('-g',) if owner == 'game_221290' else ('-O2', '-g3')
            obj, _ = source.compile_owner(self.root, self.out, changed, 'negative-' + name, flags)
            emitted, functions = source.link_owner(self.root, self.out, obj, owner)
            info = functions[name]
            entry = int(name[5:], 16)
            rom = entry - 0x15000000 + 0x2D4B0
            self.assertNotEqual(emitted[info['value']:info['value'] + count * 4], self.rom[rom:rom + count * 4], name)
        self.receipt('compiled-controls', clear_range=True, movement_count=True, codec_sync_mask=True,
            comparison_is_byte_gate_not_audio_runtime_acceptance=True)


if __name__ == '__main__':
    unittest.main()
