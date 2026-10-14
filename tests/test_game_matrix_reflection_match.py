"""Qualify reflection C and source-derived guards against the complete retail slot."""
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_matrix_reflection_loop_setup as source
from tools.experiments import game_matrix_reflection_matching as matching
from tools.tests import test_game_matrix_reflection_recovery as recovery
from tools.tests import test_game_matrix_reflection_saved_index as saved
from tools.tests.test_game_matrix_reflection_roles import state
from tools.tests.test_game_record_constructor_match import elf_slot_offset, elf_symbol_size_offset
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools import pad_c_object
from tools.check_game_data_layout import audit_layout


def reflection_symbol_size_offset(data):
    with patch('tools.tests.test_game_record_constructor_match.screen.ENTRY', recovery.screen.ENTRY):
        return elf_symbol_size_offset(data, matching.FUNCTION)


class GameMatrixReflectionMatchTests(recovery.GameMatrixReflectionRecoveryTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-matrix-reflection-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=recovery.screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            makefile='conker/Makefile', assembly='conker/asm/61D10.s', layout='conker/retail_layout.us.txt')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['elf'] == '38ac5d5272b5800ff666bb1d284ccfa12409f3a25fa06b38068cd9d337973561'
        assert cls.baseline['source'] == 'ce9efbb40671a56699d587183f31b9c72cfa835441af6809dfe729ad2d0402ee'
        assert cls.baseline['guards'] == 'cb084753c4a5b27cd425a8eddd4f906c457d4feeaf5a66e7ac0e987518550358'
        cls.body = source.qualified_body()
        cls.meta, cls.raw = source.previous.compile_candidate(cls.root, cls.out, 'selected', cls.body)
        cls.words = matching.normalize(cls.raw)
        cls.retail = list(struct.unpack_from('>486I', (cls.root / 'conker/conker.us.bin').read_bytes(), recovery.screen.ROM))
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_after = recovery.screen.recovered_owner(cls.owner_before, cls.body)
        cls.guard_before = (cls.out / 'before-guards').read_bytes()
        cls.rows = matching.guard_rows(cls.out / 'selected.o')
        cls.guard_after = matching.guard_bytes(cls.guard_before, cls.out / 'selected.o')
        cls.test_guards = cls.out / 'derived-guards.csv'
        cls.test_guards.write_bytes(cls.guard_after)
        cls.isolated_guards = cls.out / 'isolated-guards.csv'
        cls.write_rows(cls.isolated_guards, cls.rows)

    @classmethod
    def write_rows(cls, path, rows):
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=next(csv.reader(cls.guard_before.decode('ascii').splitlines())),
            lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        path.write_text(stream.getvalue())

    def compare(self, memory, args, phase=0, distance=30, action=None, words=None):
        pair = super().compare(memory, args, phase, distance, action, words)
        if words is None:
            self.assertEqual(state(pair[0]), state(pair[1]))
            raw = recovery.ReflectionOracle(self.raw, memory, args, phase, distance, action).run()
            self.assertEqual(raw.memory, pair[0].memory)
            self.assertEqual(raw.helpers.calls, pair[0].helpers.calls)
        return pair

    def test_01_shape_is_not_exact_matching(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (486, 400, 238, 0, ''))
        self.assertNotEqual(self.raw, self.retail)
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.raw[:22], self.retail[:22])
        self.assertEqual(len(self.rows), 238)
        for i, (raw, normalized) in enumerate(zip(self.raw, self.words)):
            self.assertEqual(raw >> 26, normalized >> 26, i)
            if raw >> 26 in (0, 17):
                self.assertEqual(raw & 63, normalized & 63, i)
            else:
                self.assertEqual(raw & 65535, normalized & 65535, i)
        for at in matching.RELOCATIONS:
            self.assertEqual(self.raw[at // 4], self.words[at // 4])
        self.receipt('shape', words=486, frame=400, raw_differences=238, guards=238,
            normalized_differences=0, all_opcodes_immediates_and_relocations_fixed=True,
            direct_C_match=False, guarded_byte_exact=True)

    def test_02_complete_modes_flags_counts_falloff_and_callback(self):
        super().test_02_complete_modes_flags_counts_falloff_and_callback()
        record = json.loads((self.out / 'guest.json').read_text())
        self.assertEqual(record['cases'], 4800)
        record.update(full_register_fault_state_not_qualified=False,
            complete_modeled_normalized_return_states_equal=True,
            raw_C_complete_sampled_RAM_and_helper_packets_equal=True,
            hardware_and_provider_implementation_not_claimed=True)
        self.receipt('guest', **record)

    def test_05_all_seven_production_inputs_remain_unchanged(self):
        guards = (self.root / self.paths['guards']).read_bytes()
        installed = guards == self.guard_after
        self.assertIn(guards, (self.guard_before, self.guard_after))
        expected = bytearray(self.before)
        if installed:
            offset = elf_slot_offset(self.before, recovery.screen.ENTRY, 1944)
            expected[offset:offset + 1944] = struct.pack('>486I', *self.words)
            symbol_offset = reflection_symbol_size_offset(self.before)
            self.assertEqual(struct.unpack_from('>I', expected, symbol_offset)[0], 12)
            struct.pack_into('>I', expected, symbol_offset, 1944)
        current = (self.root / self.paths['elf']).read_bytes()
        self.assertEqual(current, bytes(expected))
        self.assertEqual((self.root / self.paths['source']).read_text(), self.owner_after if installed else self.owner_before)
        for name in set(self.paths) - {'source', 'elf', 'guards'}:
            before = (self.out / ('before-' + name)).read_bytes()
            self.assertEqual(hashlib.sha256(before).hexdigest(), self.baseline[name])
            self.assertEqual((self.root / self.paths[name]).read_bytes(), before, name)
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('linked-audit', installed=installed,
            changed_bytes=sum(a != b for a, b in zip(self.before, current)),
            exact_whole_ELF_with_only_target_and_its_size_field_changed=True,
            target_symbol_size_change=[12, 1944] if installed else None,
            no_blanket_metadata_exception=True, historical_guards_exact_prefix=True,
            target_rows_added=238 if installed else 0, protected_data=data)

    def native_source(self, body):
        source_text = super().native_source(body)
        marker = 'v->mode,(u8 *)input,(u8 *)output'
        self.assertEqual(source_text.count(marker), 1)
        return source_text.replace(marker, 'v->mode,(Mtx *)input,(u8 *)output')

    test_07_native32_actual_body_and_effective_controls = saved.GameMatrixReflectionSavedIndexTests.test_07_native32_actual_body_and_effective_controls

    def test_08_complete_owner_neighbors_pools_and_both_padders(self):
        read_text = Path.read_text
        owner_path = self.root / recovery.screen.SOURCE
        with patch.object(Path, 'read_text', lambda p, *a, **k:
                self.owner_before if p == owner_path else read_text(p, *a, **k)):
            with patch.dict(self.paths, guards=str(self.test_guards)):
                super().test_08_complete_owner_neighbors_pools_and_both_padders()
        self.assertEqual(matching.guard_rows(self.out / 'owner-after.o'), self.rows)
        for script in ('pad_c_object.py', 'pad_generated_object.py'):
            text, functions, relocations = parse_object(self.out / (script + '.o'))
            target = functions[matching.FUNCTION]
            start = target['value']
            relative = {at - start: uses for at, uses in relocations.items() if start <= at < start + 1944}
            self.assertEqual(relative, matching.RELOCATIONS)
            payload = list(struct.unpack_from('>486I', text, start))
            raw_text, raw_functions, _ = parse_object(self.out / 'selected.o')
            raw_start = raw_functions[matching.FUNCTION]['value']
            self.assertEqual(payload, matching.normalize(list(struct.unpack_from('>486I', raw_text, raw_start))))

    def test_09_public_agreement_is_not_literal_private_frame_identity(self):
        memory, args = recovery.fixture(0, 1, 1)
        pair = self.compare(memory, args)
        self.assertEqual(state(pair[0]), state(pair[1]))
        raw = recovery.ReflectionOracle(self.raw, memory, args).run()
        self.assertEqual([i for i in range(32) if raw.r[i] != pair[0].r[i]], [9, 13])
        self.assertNotEqual(state(raw), state(pair[0]))
        self.receipt('private', full_modeled_return_state_equal=True,
            raw_GPR9_and13_negative_effective=True, hardware_PC_BD_FCSR_HI_not_claimed=True)

    def test_12_all56_real_local_reorders_emit_the_same_words(self):
        forms = list(source.candidates())
        self.assertEqual(len(forms), 21)
        self.assertEqual(len({name for name, _ in forms}), 21)
        records = []
        for name, body in forms:
            meta, words = source.previous.compile_candidate(self.root, self.out, name, body)
            self.assertEqual((meta['body_words'], meta['frame']), (486, 400), name)
            self.assertNotEqual(words, self.retail, name)
            if name == source.SELECTED_NAME:
                self.assertEqual(words, self.raw)
            records.append(dict(name=name, differences=meta['differences']))
        self.receipt('screens', forms=21, records=records, no_direct_C_match=True)

    def test_14_independent_original_links_and_rebased_semantic_contract(self):
        original = (self.root / 'conker/asm/61D10.s').read_text().split('glabel ' + matching.FUNCTION + '\n', 1)[1]
        slot_text = 'glabel ' + matching.FUNCTION + '\n' + original.split('endlabel ' + matching.FUNCTION, 1)[0] + 'endlabel ' + matching.FUNCTION + '\n'
        slot = self.out / 'original-slot.s'
        slot.write_text(slot_text)
        assembly = self.out / 'original.s'
        assembly.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + slot_text)
        guarded = self.out / 'guarded.s'
        guarded.write_text(emit_padded_assembly(self.out / 'selected.o', slot,
            word_patches_path=self.isolated_guards, filename='generated_61D10'))
        for path in (assembly, guarded):
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
                '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        cases = 0
        for index, delta in enumerate((0, 0x200000, 0x400000)):
            entry = recovery.screen.ENTRY + delta
            symbols = {name: value + delta for name, value in recovery.screen.SYMBOLS.items()}
            script = self.out / ('rebase-' + str(index) + '.ld')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            linked = []
            for label, path in (('original', assembly), ('guarded', guarded)):
                elf = self.out / (label + '-' + str(index) + '.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', matching.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path.with_suffix('.o'))],
                    check=True, capture_output=True)
                linked.append(list(struct.unpack_from('>486I', recovery.screen.compiler.sections(elf)['.text'][1])))
            with patch.multiple(recovery.screen, ENTRY=entry, SYMBOLS=symbols):
                _, raw = source.previous.compile_candidate(self.root, self.out, 'raw-rebase-' + str(index), self.body)
                self.assertEqual(matching.normalize(raw), linked[0])
                self.assertEqual(linked[0], linked[1])
                for mode, fixed, count, phase in itertools.product(range(3), range(4), (0, 1, 2), (0, 8)):
                    memory, args = recovery.fixture(mode, count, fixed)
                    pair = [recovery.ReflectionOracle(w, memory, args, phase, entry=entry).run() for w in linked]
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    cases += 1
        self.receipt('rebases', independently_assembled_links=3, cases=cases,
            complete_words_and_modeled_states_equal=True, unchanged_JAL_relocations=True)

    def test_15_literal_fired_fault_prefix_retains_saved_role_boundary(self):
        domains = itertools.product((0, 1, 2, 3), (0, 1), range(4), (0, 8), (None, 0, 256))
        pairs = cases = 0
        for mode, count, fixed, phase, enabled in domains:
            memory, args = recovery.fixture(mode, count, fixed, enabled=0 if enabled is None else enabled)
            if enabled is None:
                args = (0, *args[1:])
            complete = [recovery.FaultOracle(w, memory, args, phase=phase).run() for w in (self.retail, self.words)]
            self.assertEqual(complete[0].accesses, complete[1].accesses)
            self.assertEqual(state(complete[0]), state(complete[1]))
            for cut in range(complete[0].accesses):
                pair = []
                for words in (self.retail, self.words):
                    model = recovery.FaultOracle(words, memory, args, phase=phase, fault=cut)
                    with self.assertRaises(recovery.AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                    pair.append(model)
                self.assertEqual(pair[0].dispatched_word, pair[1].dispatched_word)
                self.assertEqual(state(pair[0]), state(pair[1]))
                pairs += 1
            cases += 1
        self.assertEqual((cases, pairs), (192, 10260))
        self.receipt('faults', domains=cases, fired_pairs=pairs, all_modeled_states_equal=True,
            arbitrary_inputs_and_hardware_PC_BD_FCSR_HI_not_claimed=True)

    def test_16_each_stale_word_and_relocation_is_rejected(self):
        obj = self.out / 'selected.o'
        text, functions, relocations = parse_object(obj)
        start = functions[matching.FUNCTION]['value']
        slot = self.out / 'negative-slot.s'
        original = (self.root / 'conker/asm/61D10.s').read_text().split('glabel ' + matching.FUNCTION + '\n', 1)[1]
        slot.write_text('glabel ' + matching.FUNCTION + '\n' + original.split('endlabel ' + matching.FUNCTION, 1)[0] +
            'endlabel ' + matching.FUNCTION + '\n')
        layout = self.out / 'negative-layout.txt'
        layout.write_text('section,filename,function,address,end\n'
            'game,generated_61D10,func_15034F30,0x15034F30,0x150356C8\n')
        self.assertTrue(emit_padded_assembly(obj, slot,
            word_patches_path=self.isolated_guards, filename='generated_61D10'))
        self.assertTrue(pad_c_object.emit_padded_assembly(obj, layout,
            'generated_61D10', word_patches_path=self.isolated_guards))
        for row in self.rows:
            bad = bytearray(text)
            bad[start + int(row['offset'], 0) + 3] ^= 1
            fake = (bytes(bad), functions, relocations)
            with patch.object(matching, 'parse_object', return_value=fake):
                with self.assertRaisesRegex(ValueError, 'Stale'):
                    matching.guard_rows(obj)
            with patch('tools.pad_generated_object.parse_object', return_value=fake):
                with self.assertRaisesRegex(ValueError, 'word patch'):
                    emit_padded_assembly(obj, slot, word_patches_path=self.isolated_guards, filename='generated_61D10')
            with patch.object(pad_c_object, 'parse_object', return_value=fake):
                with self.assertRaisesRegex(ValueError, 'word patch'):
                    pad_c_object.emit_padded_assembly(obj, layout, 'generated_61D10', word_patches_path=self.isolated_guards)
            index = int(row['offset'], 0) // 4
            dropped = list(self.words)
            dropped[index] = self.raw[index]
            self.assertNotEqual(dropped, self.retail)
        for at in matching.RELOCATIONS:
            bad = dict(relocations)
            del bad[start + at]
            with patch.object(matching, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaisesRegex(ValueError, 'relocation map'):
                    matching.guard_rows(obj)
        self.receipt('stale-controls', guarded_words=238, relocation_removals=16,
            source_hash_and_both_padders_reject_every_stale_expected_word=True,
            each_dropped_guard_breaks_complete_identity=True)

    def test_17_operand_helpers_fail_closed_and_preserve_reserved_fields(self):
        for fn, word, cycle in ((matching.gpr_cycle, 0xFC000000, {8: 9, 9: 8}),
                (matching.gpr_cycle, 0, {4: 5, 5: 4}), (matching.gpr_cycle, 0, {8: 9}),
                (matching.fpr_cycle, 0, {20: 22, 22: 20}), (matching.fpr_cycle, 0, {0: 2})):
            with self.assertRaises(ValueError):
                fn(word, cycle)
        for fn in (matching.commute_add, matching.commute_multiply):
            with self.assertRaises(ValueError):
                fn(0)
        with self.assertRaises(ValueError):
            matching.subtract_destination(0, 0)
        # REGIMM RT is a subtype, COP1 compare FD is reserved, MTC1 RT is a GPR.
        self.assertEqual(matching.gpr_cycle(0x05010004, {8: 9, 9: 8}) & 0x001FFFFF, 0x00010004)
        for word in (0x45010004, 0x4448F800):
            self.assertEqual(matching.fpr_cycle(word, {0: 2, 2: 0}), word)
        self.assertEqual(matching.fpr_cycle(0x44880800, {0: 2, 2: 0}) >> 16 & 31, 8)
        for cut in (0, 22, 87, 98, 220, 341, 420, 485):
            bad = list(self.raw)
            bad[cut] ^= 1
            with self.assertRaises(ValueError):
                matching.normalize(bad)
        with self.assertRaises(ValueError):
            matching.normalize(self.raw[:-1])
        with self.assertRaises(ValueError):
            matching.guard_bytes(self.guard_after, self.out / 'selected.o')
        self.receipt('helper-controls', protected_argument_and_saved_FP_cycles_rejected=True,
            stale_and_incomplete_source_arrays_rejected=True, reserved_fields_preserved=True)

    def test_18_banked240_and_wrong_profile_keep_effective_private_controls(self):
        meta, banked = source.previous.compile_candidate(self.root, self.out, 'banked240', source.BASE)
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (486, 400, 240))
        memory, args = recovery.fixture(0, 1, 1)
        original, old = [recovery.ReflectionOracle(w, memory, args).run() for w in (self.retail, banked)]
        self.assertEqual(original.memory, old.memory)
        self.assertEqual([i for i in range(32) if original.r[i] != old.r[i]], [9, 14])
        with self.assertRaises(ValueError):
            matching.normalize(banked)
        _, bare = source.previous.compile_candidate(self.root, self.out, 'bare-o2', self.body, 'o2')
        with self.assertRaises(ValueError):
            matching.normalize(bare)
        for words, cut in ((banked, 19), (bare, 1)):
            pair = []
            for w in (self.retail, words):
                model = recovery.FaultOracle(w, memory, args, fault=cut)
                with self.assertRaises(recovery.AccessFault):
                    model.run()
                self.assertEqual(model.accesses, cut)
                pair.append(model)
            self.assertNotEqual(state(pair[0]), state(pair[1]))
        self.receipt('historical-controls', banked240_GPR9_and14_negative_retained=True,
            banked_cut19_and_bare_O2_cut1_fault_negatives_effective=True,
            both_wrong_source_and_wrong_profile_rejected_by_normalizer=True)

    def test_19_whole_image_and_source_integrity_controls_are_effective(self):
        read_bytes, read_text = Path.read_bytes, Path.read_text
        source_path = self.root / self.paths['source']
        source_text = source_path.read_text()
        with patch.object(Path, 'read_text', lambda p, *a, **k:
                source_text + '\n' if p == source_path else read_text(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_05_all_seven_production_inputs_remain_unchanged()
        elf_path = self.root / self.paths['elf']
        data = elf_path.read_bytes()
        target = elf_slot_offset(data, recovery.screen.ENTRY, 1944)
        for offset in (0, target, target + 1943, reflection_symbol_size_offset(data),
                elf_slot_offset(data, 0x15034860, 1620), len(data) - 1):
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p, *a, **k:
                    bytes(bad) if p == elf_path else read_bytes(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_05_all_seven_production_inputs_remain_unchanged()
        guard_path = self.root / self.paths['guards']
        guards = guard_path.read_bytes()
        with patch.object(Path, 'read_bytes', lambda p, *a, **k:
                guards + b'\n' if p == guard_path else read_bytes(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_05_all_seven_production_inputs_remain_unchanged()
        self.receipt('image-controls', source_and_guard_corruptions_effective=True,
            ELF_header_target_first_last_symbol_size_neighbor_and_file_tail_mutations_effective=True)


if __name__ == '__main__':
    unittest.main()
