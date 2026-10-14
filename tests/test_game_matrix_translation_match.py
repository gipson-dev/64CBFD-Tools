"""Qualify translation scheduling without changing its recovered C arithmetic."""
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import game_matrix_translation_candidates as source
from tools.experiments import game_matrix_translation_matching as matching
from tools.tests import test_game_matrix_translation_recovery as previous
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools import pad_c_object


def state(model):
    return (model.memory, model.r, model.f, model.condition, getattr(model, 'fcsr', None),
        getattr(model, 'lo', None), getattr(model, 'hi', None), model.events, model.calls)


class AccessFault(Exception):
    pass


class FaultOracle(TriangleOracle):
    def __init__(self, *args, fault=None, **kwargs):
        self.fault, self.accesses = fault, 0
        super().__init__(*args, **kwargs)

    def execute(self, word):
        self.dispatched_word = word
        super().execute(word)

    def get(self, address, size):
        if self.fault == self.accesses:
            raise AccessFault
        self.accesses += 1
        return super().get(address, size)

    def put(self, address, value, size):
        if self.recording:
            if self.fault == self.accesses:
                raise AccessFault
            self.accesses += 1
        return super().put(address, value, size)


class GameMatrixTranslationMatchTests(previous.GameMatrixTranslationRecoveryTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-matrix-translation-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source='conker/src/game_16EE20.c', elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            makefile='conker/Makefile', layout='conker/retail_layout.us.txt',
            assembly='conker/asm/nonmatchings/game_16EE20/func_15142314.s')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == '7acc24c75dc922e9aa72027a030b4c8e43b0d2a2d9bc5f8c2a17fccb3dba7810'
        assert cls.baseline['elf'] == 'fd188cd74393988f34b462987b50082856707d02e5b729e7a119ba3f100890ee'
        assert cls.baseline['guards'] == '586bbe75d4b9fbee2fb3429e15ca8bf9822449177fb53bdb2e1ca786d435f110'
        cls.record, cls.raw = source.compile_candidate(cls.root, cls.out, 'selected')
        cls.words = matching.normalize(cls.raw)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>49I', cls.rom, source.ROM))
        cls.parent = list(struct.unpack_from('>98I', cls.rom, previous.PARENT_ROM))
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.guard_before = (cls.out / 'before-guards').read_bytes()
        cls.guard_after = matching.guard_bytes(cls.guard_before, cls.out / 'selected.o')
        cls.rows = matching.guard_rows(cls.out / 'selected.o')
        cls.test_guards = cls.out / 'derived-guards.csv'
        cls.test_guards.write_bytes(cls.guard_after)
        cls.isolated_guards = cls.out / 'isolated-guards.csv'
        cls.write_rows(cls.isolated_guards, cls.rows)
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    @classmethod
    def write_rows(cls, path, rows):
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=next(csv.reader(cls.guard_before.decode('ascii').splitlines())),
            lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        path.write_text(stream.getvalue())

    def check_case(self, memory, args, phase=0, coverage=None):
        pair = super().check_case(memory, args, phase, coverage)
        self.assertEqual(state(pair[0]), state(pair[1]))
        raw = self.model(self.raw, memory, args, phase)
        self.assertEqual(raw.memory, pair[0].memory)
        self.assertEqual(previous.public_events(raw), previous.public_events(pair[0]))
        return pair

    def run_host(self, body):
        run = subprocess.run
        path = self.path
        for profile in ('-O2', '-O0'):
            self.path = path / profile[1:]
            self.path.mkdir(exist_ok=True)

            def compile_profile(command, *args, **kwargs):
                if isinstance(command, list) and '-m32' in command and '-O2' in command:
                    command = [profile if item == '-O2' else item for item in command]
                return run(command, *args, **kwargs)

            with patch.object(subprocess, 'run', compile_profile):
                previous.GameMatrixTranslationRecoveryTests.run_host(self, body)
        self.path = path

    def test_actual_native_32bit_body_with_wrapped_indices_and_complete_alias_storage(self):
        super().test_actual_native_32bit_body_with_wrapped_indices_and_complete_alias_storage()
        record = json.loads((self.out / 'native.json').read_text())
        record['profiles'] = ['O2', 'O0']
        record['cases_per_profile'] = record['cases']
        self.receipt('native', record)

    def test_complete_original_parent_on_null_and_zero_routes_connects_both_translation_bodies(self):
        cases = 0
        for flag, n, point_mode, phase, output in itertools.product((0, 1, 255), range(16), range(3),
                (0, 8), (previous.OUTPUT, previous.MATRIX + 0x18, previous.STATUS, previous.POINT)):
            memory, args = previous.fixture(flag, previous.edge_pairs(n), previous.float_words(n), output=output)
            point = 0 if point_mode == 0 else previous.POINT
            for axis in range(3):
                previous.put(memory, previous.POINT + axis * 4, 0x80000000 if point_mode == 2 else 0)
            expected = dict(memory)
            previous.put(expected, previous.STATUS, 7)
            expected, _ = previous.reference(expected, args)
            previous.put(expected, previous.STATUS, 0)
            models = []
            for words in (self.words, self.retail):
                connected = {source.ENTRY + i * 4: word for i, word in enumerate(words)}
                model = previous.ConnectedTranslationOracle(self.parent, memory, phase=phase, entry=previous.PARENT,
                    arguments=(point, output, args[0]), connected=connected).run()
                self.assertEqual(previous.external_memory(model.memory), previous.external_memory(expected))
                self.assertEqual(model.calls, [(source.ENTRY, args[0], 0, output)])
                models.append(model)
            self.assertEqual(state(models[0]), state(models[1]))
            cases += 1
        self.assertEqual(cases, 1152)
        self.receipt('parent', dict(cases=cases, complete_original_parent_words=98,
            full_modeled_states_equal=True, scope='null/positive-zero/negative-zero routes only'))

    def test_complete_slot_and_all_152_source_controls_remain_nonmatching(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences'],
            self.record['pool_bytes'], self.record['diagnostics']), (49, 0, 34, 0, ''))
        self.assertEqual(self.words, self.retail)
        self.assertNotEqual(self.raw, self.retail)
        self.assertEqual(len(self.rows), 34)
        self.assertEqual(self.words[4] >> 26, 4)
        self.assertEqual(self.raw[4] >> 26, 20)
        self.assertEqual(self.words[5], self.raw[3])
        self.assertEqual(self.words[40], 0)
        self.assertEqual(self.words[41:], self.raw[41:])
        self.receipt('shape', dict(words=49, frame=0, raw_differences=34, guards=34,
            normalized_differences=0, ordinary_branch_and_return_delay_recovered=True,
            old_152_source_controls_unchanged_and_not_rerun=True, direct_C_match=False))

    def test_copied_owner_actual_padder_retains_complete_unguarded_body_and_flag_relocation(self):
        owner = (self.root / self.paths['source']).read_text()
        obj, diagnostics = previous.compile_owner(self.root, self.out, owner, 'owner')
        self.assertEqual(len(diagnostics), 2)
        processed = self.out / 'owner-postprocessed.o'
        shutil.copyfile(obj, processed)
        subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
            str((self.out / 'owner.c').relative_to(self.root / 'conker')), '--post-process',
            str(processed.relative_to(self.root / 'conker')), '--assembler',
            'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
            '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
        self.assertEqual(matching.guard_rows(processed), self.rows)
        with (self.root / self.paths['layout']).open(newline='') as stream:
            layout_rows = [r for r in csv.DictReader(stream) if r['filename'] == 'game_16EE20']
        # The generated-padder inventory uses pristine addressed words only for slot bounds.
        inventory = self.out / 'owner-retail.s'
        lines = []
        for row in layout_rows:
            start, end = int(row['address'], 16), int(row['end'], 16)
            lines.append('glabel ' + row['function'])
            for address in range(start, end, 4):
                rom = address - 0x15000000 + 0x2D4B0
                word = struct.unpack_from('>I', self.rom, rom)[0]
                lines.append('/* %X %08X %08X */ .word 0x%08X' % (rom, address, word, word))
            lines.append('endlabel ' + row['function'])
        inventory.write_text('\n'.join(lines) + '\n')
        objects = []
        for tag, guards in (('before', self.out / 'before-guards'), ('after', self.test_guards)):
            for kind in ('layout', 'slice'):
                kwargs = dict(rodata_symbol='jtbl_800A5218_game', word_patches_path=guards)
                assembly = pad_c_object.emit_padded_assembly(processed, self.root / self.paths['layout'], 'game_16EE20', **kwargs) if kind == 'layout' else emit_padded_assembly(
                    processed, inventory, filename='game_16EE20', **kwargs)
                path = self.out / ('owner-' + tag + '-' + kind + '.s')
                path.write_text(assembly)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
                    '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
                objects.append(parse_object(path.with_suffix('.o')))
        self.assertEqual(objects[0], objects[1])
        self.assertEqual(objects[2], objects[3])
        pools = [normalized_pools(self.out / ('owner-' + tag + '-' + kind + '.o'))
            for tag in ('before', 'after') for kind in ('layout', 'slice')]
        self.assertTrue(all(pool == pools[0] for pool in pools))
        before, after = objects[0], objects[2]
        self.assertEqual(len(before[1]), 89)
        self.assertEqual(before[1], after[1])
        self.assertEqual(before[2], after[2])
        expected = bytearray(before[0])
        target = before[1][matching.FUNCTION]
        start = target['value']
        expected[start:start + 196] = struct.pack('>49I', *matching.normalize(list(struct.unpack_from('>49I', before[0], start))))
        self.assertEqual(bytes(expected), after[0])
        self.receipt('owner', dict(functions=89, unchanged_neighbors=88, both_complete_padders=True,
            raw_object_guard_rows_equal=True, only_target_text_changed=True, all_relocations_fixed=True))

    def test_installed_source_complete_linked_slot_and_unchanged_guard_history(self):
        guards = (self.root / self.paths['guards']).read_bytes()
        installed = guards == self.guard_after
        self.assertIn(guards, (self.guard_before, self.guard_after))
        expected = bytearray(self.before)
        if installed:
            offset = elf_slot_offset(self.before, source.ENTRY, 196)
            expected[offset:offset + 196] = struct.pack('>49I', *self.words)
        current = (self.root / self.paths['elf']).read_bytes()
        self.assertEqual(current, bytes(expected))
        for name in set(self.paths) - {'elf', 'guards'}:
            data = (self.out / ('before-' + name)).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), self.baseline[name])
            self.assertEqual((self.root / self.paths[name]).read_bytes(), data, name)
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('linked-audit', dict(installed=installed,
            changed_bytes=sum(a != b for a, b in zip(self.before, current)),
            entire_ELF_except_target_fixed=True, every_symbol_field_fixed=True, protected_data=data,
            historical_guard_bytes_exact_prefix=True, C_source_profile_layout_conversion_rows_fixed=True))

    def test_fired_fault_cuts_match_and_raw_schedule_negative_is_effective(self):
        cases = pairs = raw_different = 0
        for flag, n, alias, phase in itertools.product((0, 1, 255), range(4), (None, 0x18, 0x30, 0x38), (0, 8)):
            memory, args = previous.fixture(flag, previous.edge_pairs(n), previous.float_words(n), alias=alias)
            complete = [FaultOracle(w, memory, phase=phase, entry=source.ENTRY, arguments=args).run()
                for w in (self.retail, self.words, self.raw)]
            self.assertEqual([m.accesses for m in complete], [7 if flag == 0 else 10] * 3)
            self.assertEqual(state(complete[0]), state(complete[1]))
            for cut in range(complete[0].accesses):
                models = []
                for w in (self.retail, self.words, self.raw):
                    m = FaultOracle(w, memory, phase=phase, entry=source.ENTRY, arguments=args, fault=cut)
                    with self.assertRaises(AccessFault):
                        m.run()
                    self.assertEqual(m.accesses, cut)
                    models.append(m)
                self.assertEqual(state(models[0]), state(models[1]))
                self.assertEqual(models[0].dispatched_word, models[1].dispatched_word)
                raw_different += state(models[0]) != state(models[2])
                pairs += 1
            cases += 1
        self.assertEqual((cases, pairs), (96, 864))
        self.assertGreater(raw_different, 0)
        self.receipt('faults', dict(domains=cases, fired_triplets=pairs, all_normalized_states_equal=True,
            raw_state_negative_count=raw_different, PC_BD_full_FCSR_hardware_not_claimed=True))

    def test_independent_original_guarded_links_and_signed_low_carry(self):
        original = self.out / 'original.s'
        slot = self.root / self.paths['assembly']
        original.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + slot.read_text())
        guarded = self.out / 'guarded.s'
        guarded.write_text(emit_padded_assembly(self.out / 'selected.o', slot,
            word_patches_path=self.isolated_guards, filename='game_16EE20'))
        for path in (original, guarded):
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
                '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        cases = 0
        for index, (entry, flag) in enumerate(((source.ENTRY, source.FLAG), (0x15342314, 0x80107FFC), (0x15542314, 0x80318004))):
            script = self.out / ('rebase-' + str(index) + '.ld')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            linked = []
            for name, obj in (('original', original.with_suffix('.o')), ('guarded', guarded.with_suffix('.o')), ('raw', self.out / 'selected.o')):
                elf = self.out / (name + '-' + str(index) + '.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=D_800C3E90=0x%X' % flag, '-o', str(elf), str(obj)], check=True, capture_output=True)
                linked.append(list(struct.unpack_from('>49I', source.sections(elf)['.text'][1])))
            self.assertEqual(linked[0], linked[1])
            self.assertEqual(matching.normalize(linked[2]), linked[0])
            with patch.multiple(source, ENTRY=entry, FLAG=flag):
                for mode, n, alias, phase in itertools.product((0, 1, 255), range(4), (None, 0x18, 0x38), (0, 8)):
                    memory, args = previous.fixture(mode, previous.edge_pairs(n), previous.float_words(n), alias=alias)
                    models = [self.model(w, memory, args, phase) for w in linked[:2]]
                    self.assertEqual(state(models[0]), state(models[1]))
                    expected, events = previous.reference(memory, args)
                    self.assertEqual(previous.public_events(models[1]), events)
                    cases += 1
        self.receipt('rebases', dict(original_guarded_and_raw_links=3, cases=cases,
            complete_words_and_modeled_states_equal=True, signed_LO16_carry=True))

    def test_all_stale_source_words_and_relocations_fail_closed(self):
        obj = self.out / 'selected.o'
        text, functions, relocations = parse_object(obj)
        start = functions[source.FUNCTION]['value']
        for index in range(49):
            bad = bytearray(text)
            bad[start + index * 4 + 3] ^= 1
            with patch.object(matching, 'parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaisesRegex(ValueError, 'Stale'):
                    matching.guard_rows(obj)
        slot = self.root / self.paths['assembly']
        layout = self.out / 'isolated-layout.txt'
        layout.write_text('section,filename,function,address,end\n'
            'game,game_16EE20,func_15142314,0x15142314,0x151423D8\n')
        self.assertTrue(emit_padded_assembly(obj, slot, filename='game_16EE20', word_patches_path=self.isolated_guards))
        self.assertTrue(pad_c_object.emit_padded_assembly(obj, layout, 'game_16EE20', word_patches_path=self.isolated_guards))
        for row in self.rows:
            index = int(row['offset'], 0) // 4
            bad = bytearray(text)
            bad[start + index * 4 + 3] ^= 1
            fake = (bytes(bad), functions, relocations)
            with patch('tools.pad_generated_object.parse_object', return_value=fake):
                with self.assertRaisesRegex(ValueError, 'word patch'):
                    emit_padded_assembly(obj, slot, filename='game_16EE20', word_patches_path=self.isolated_guards)
            with patch.object(pad_c_object, 'parse_object', return_value=fake):
                with self.assertRaisesRegex(ValueError, 'word patch'):
                    pad_c_object.emit_padded_assembly(obj, layout, 'game_16EE20', word_patches_path=self.isolated_guards)
            dropped = list(self.words)
            dropped[index] = self.raw[index]
            self.assertNotEqual(dropped, self.retail)
        for at in matching.RELOCATIONS:
            bad = dict(relocations)
            del bad[start + at]
            with patch.object(matching, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaisesRegex(ValueError, 'relocation map'):
                    matching.guard_rows(obj)
        for word, displacement in ((0, 1), (self.raw[4], -1), (self.raw[4], 32768)):
            with self.assertRaises(ValueError):
                matching.ordinary_branch(word, displacement)
        with self.assertRaises(ValueError):
            matching.normalize(self.raw[:-1])
        with self.assertRaises(ValueError):
            matching.guard_bytes(self.guard_after, obj)
        self.receipt('guard-controls', dict(stale_source_words=49, both_padder_stale_words=34,
            missing_relocations=2, every_dropped_guard_breaks_identity=True, all_fail_closed=True))

    def test_whole_image_source_and_guard_integrity_controls_are_effective(self):
        read = Path.read_bytes
        elf = self.root / self.paths['elf']
        data = elf.read_bytes()
        target = elf_slot_offset(data, source.ENTRY, 196)
        parent = elf_slot_offset(data, previous.PARENT, 392)
        for offset in (0, target, target + 195, parent, len(data) - 1):
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p, *a, **k: bytes(bad) if p == elf else read(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_installed_source_complete_linked_slot_and_unchanged_guard_history()
        for name in ('source', 'guards'):
            path = self.root / self.paths[name]
            bad = path.read_bytes() + b'\n'
            with patch.object(Path, 'read_bytes', lambda p, *a, **k: bad if p == path else read(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_installed_source_complete_linked_slot_and_unchanged_guard_history()
        self.receipt('image-controls', dict(ELF_header_target_first_last_parent_and_tail_corruptions_effective=True,
            source_and_guard_mutations_detected=True, no_blanket_metadata_exclusion=True))


if __name__ == '__main__':
    unittest.main()
