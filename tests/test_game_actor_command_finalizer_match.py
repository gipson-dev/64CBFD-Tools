"""Qualify source-derived guards without claiming a direct finalizer C match."""
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

from tools.experiments import game_actor_command_finalizer_clamp as source
from tools.experiments import game_actor_command_finalizer_fitting as fitting
from tools.experiments import game_actor_command_finalizer_matching as matching
from tools.experiments import game_actor_command_finalizer_bias as bias
from tools.tests import test_game_actor_command_finalizer_clamp as previous
from tools.tests import test_game_actor_command_finalizer_flow as faults
from tools.tests import test_game_actor_command_finalizer_recovery as recovery
from tools.tests import test_game_actor_command_finalizer_fitting as owner
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.check_game_data_layout import audit_layout


class GameActorCommandFinalizerMatchTests(previous.GameActorCommandFinalizerClampTests):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-command-finalizer-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=recovery.screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            layout='conker/retail_layout.us.txt', makefile='conker/Makefile',
            caller='conker/src/game/generated_61490.c', rodata='conker/asm/data/23C630.rodata.s')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == 'ce9efbb40671a56699d587183f31b9c72cfa835441af6809dfe729ad2d0402ee'
        assert cls.baseline['elf'] == '687cfa25054d239a1a081d23b91b1e199ecf1b595972824cfc32df751319d6e2'
        assert cls.baseline['guards'] == '420eb4c5458868e6b19f5a7eb45f04b38ef96532216f283689eec7e0c5e8d796'
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_after = cls.owner_before
        cls.meta, cls.raw = fitting.compile_candidate(cls.root, cls.out, 'selected', source.SELECTED)
        cls.words = matching.normalize(cls.raw)
        cls.banked_words = cls.raw
        _, cls.old_words = fitting.compile_candidate(cls.root, cls.out, 'old-slot-control', previous.opening.roles.roles.BASE)
        cls.retail = list(struct.unpack_from('>405I', (cls.root / 'conker/conker.us.bin').read_bytes(), 0x61D10))
        cls.guard_before = (cls.out / 'before-guards').read_bytes()
        cls.guard_after = matching.guard_bytes(cls.guard_before, cls.out / 'selected.o')
        cls.test_guards = cls.out / 'derived-guards.csv'
        cls.test_guards.write_bytes(cls.guard_after)
        cls.rows = matching.guard_rows(cls.out / 'selected.o')
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

    def compare(self, memory, args, seed=0, mode=0, phase=0):
        pair = super().compare(memory, args, seed, mode, phase)
        self.assertEqual(faults.state(pair[0]), faults.state(pair[1]))
        self.assertEqual(pair[0].visits, pair[1].visits)
        raw = recovery.FinalizerOracle(self.raw, memory, args, phase, seed, mode).run()
        self.assertEqual((recovery.public(raw.memory), raw.r[2], raw.calls),
            (recovery.public(pair[0].memory), pair[0].r[2], pair[0].calls))
        return pair

    def test_01_original_extent_frame_selector_schedule_and_no_guards(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (405, 72, 76, 0, ''))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.raw, list(struct.unpack_from('>405I', self.before,
            elf_slot_offset(self.before, recovery.screen.ENTRY, 1620))))
        self.assertEqual(sum(a != b for a, b in zip(self.raw, self.words)), 76)
        self.assertEqual(len(self.rows), 76)
        self.assertTrue(self.guard_after.startswith(self.guard_before))
        with self.assertRaisesRegex(ValueError, 'already present'):
            matching.guard_bytes(self.guard_after, self.out / 'selected.o')
        self.receipt('shape', raw_words=405, frame=72, raw_differences=76,
            derived_differences=0, guards=76, direct_C_match=False)

    def test_02_all_types_channels_field_boundaries_and_call_mutations(self):
        super().test_02_all_types_channels_field_boundaries_and_call_mutations()
        path = self.out / 'guest.json'
        record = json.loads(path.read_text())
        record.update(full_modeled_private_state_match=True, private_frame_match=True,
            raw_C_public_contract_checked=True, hardware_execution_not_claimed=True)
        path.write_text(json.dumps(record, indent=2) + '\n')

    def test_07_copied_owner_all_neighbors_pools_and_both_padders(self):
        with patch.dict(self.paths, guards=str(self.test_guards)):
            owner.GameActorCommandFinalizerFittingTests.test_07_owner_neighbors_pools_and_both_padders(self)
        self.assertEqual(matching.guard_rows(self.out / 'owner-after.o'), self.rows)
        for script in ('pad_c_object.py', 'pad_generated_object.py'):
            obj = self.out / (script + '.o')
            text, functions, relocations = parse_object(obj)
            target = functions[matching.FUNCTION]
            start = target['value']
            expected_relocs = matching.normalized_relocations(matching.RELOCATIONS)
            actual_relocs = {at - start: uses for at, uses in relocations.items()
                if start <= at < start + 1620}
            self.assertEqual(actual_relocs, expected_relocs)
            self.assertEqual(list(struct.unpack_from('>405I', text, start)),
                matching.normalize(list(struct.unpack_from('>405I', parse_object(self.out / 'selected.o')[0]))))

    def test_08_literal_image_and_all_protected_inputs(self):
        guards = (self.root / self.paths['guards']).read_bytes()
        installed = guards == self.guard_after
        self.assertIn(guards, (self.guard_before, self.guard_after))
        expected = bytearray(self.before)
        if installed:
            offset = elf_slot_offset(self.before, recovery.screen.ENTRY, 1620)
            expected[offset:offset + 1620] = struct.pack('>405I', *self.words)
        current = (self.root / self.paths['elf']).read_bytes()
        self.assertEqual(current, bytes(expected))
        for name in set(self.paths) - {'elf', 'guards'}:
            self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-' + name)).read_bytes(), name)
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('linked-audit', installed=installed, guard_rows_added=76 if installed else 0,
            changed_bytes=sum(a != b for a, b in zip(self.before, current)),
            exact_whole_ELF_no_metadata_exception=True, data=data)

    def test_09_independent_original_links_and_carry_rebases(self):
        original = (self.root / 'conker/asm/61D10.s').read_text().split('glabel ' + matching.FUNCTION + '\n', 1)[1]
        assembly = self.out / 'original.s'
        assembly.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') +
            '"\nglabel ' + matching.FUNCTION + '\n' + original.split('endlabel ' + matching.FUNCTION, 1)[0] +
            'endlabel ' + matching.FUNCTION + '\n')
        obj = assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(assembly)], check=True, capture_output=True)
        slot = self.out / 'guard-slot.s'
        slot.write_text('glabel ' + matching.FUNCTION + '\n' + original.split('endlabel ' + matching.FUNCTION, 1)[0] +
            'endlabel ' + matching.FUNCTION + '\n')
        padded_assembly = self.out / 'guarded.s'
        padded_assembly.write_text(emit_padded_assembly(self.out / 'selected.o', slot,
            word_patches_path=self.isolated_guards, filename='generated_61D10'))
        padded_obj = padded_assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
            '-o', str(padded_obj), str(padded_assembly)], check=True, capture_output=True)
        layouts = ((recovery.screen.ENTRY, 0x80097D40, recovery.TIMER, recovery.VALUE, recovery.RANDOM),
            (0x15234860, 0x80107FFC, 0x80218004, 0x80227FFC, 0x15307FFC),
            (0x15434860, 0x80318004, 0x80417FFC, 0x80428004, 0x15518004))
        cases = 0
        for index, (entry, constants, timer, value, random) in enumerate(layouts):
            symbols = dict(func_150ADA20=random, D_800BE9E4=timer, D_800C3EF0=value,
                **{'D_%08X' % (0x80097D40 + i * 4): constants + i * 4 for i in range(8)})
            with patch.multiple(recovery.screen, ENTRY=entry, SYMBOLS=symbols):
                _, raw = fitting.compile_candidate(self.root, self.out, 'rebase-' + str(index), source.SELECTED)
            script = self.out / ('original-' + str(index) + '.ld')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            linked = []
            for label, input_obj in (('original', obj), ('guarded', padded_obj)):
                elf = self.out / (label + '-' + str(index) + '.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', matching.FUNCTION,
                    *['--defsym=%s=0x%X' % x for x in symbols.items()], '-o', str(elf), str(input_obj)], check=True, capture_output=True)
                linked.append(list(struct.unpack_from('>405I', recovery.sections(elf)['.text'][1])))
            self.assertEqual(linked[0], linked[1])
            self.assertEqual(matching.normalize(raw), linked[0])
            with patch.multiple(recovery, CONSTANT_BASE=constants, TIMER=timer, VALUE=value, RANDOM=random):
                for kind, pattern, gates, phase in itertools.product((0x42, 0x70, 0x7C, 0x98), range(5), range(4), (0, 8)):
                    memory, args = recovery.fixture(kind, pattern, 255 if gates & 1 else 1, 255 if gates & 2 else 2)
                    expected, cursor, calls = recovery.reference(memory, args, 0xFFFFFFFF, 1)
                    pair = [recovery.FinalizerOracle(w, memory, args, phase, 0xFFFFFFFF, 1, entry).run() for w in linked]
                    self.assertEqual(faults.state(pair[0]), faults.state(pair[1]))
                    self.assertEqual((recovery.public(pair[1].memory), pair[1].r[2], pair[1].calls),
                        (recovery.public(expected), cursor, calls))
                    cases += 1
        self.receipt('rebases', independent_original_and_guarded_links=3, cases=cases,
            full_words_and_states_exact=True, HI16_signed_LO16_carries=True)

    def test_12_all_sampled_fired_access_cuts_keep_the_open_boundary(self):
        domains = [(kind, pattern, 1, 2, phase) for kind, pattern, phase in
            itertools.product((0, 0x42, 0x69, 0x70, 0x7C, 0x87), (0, 1, 3), (0, 8))]
        domains += [(kind, 0, first, second, phase) for kind, first, second, phase in
            itertools.product((0, 0x70), (1, 255), (2, 255), (0, 8))]
        pairs = 0
        for kind, pattern, first, second, phase in domains:
            memory, args = recovery.fixture(kind, pattern, first, second)
            complete = [faults.InstructionOracle(w, memory, args, phase, 0xFFFFFFFF).run() for w in (self.retail, self.words)]
            self.assertEqual(complete[0].accesses, complete[1].accesses)
            self.assertEqual(faults.state(complete[0]), faults.state(complete[1]))
            for cut in range(complete[0].accesses):
                pair = []
                for words in (self.retail, self.words):
                    model = faults.InstructionOracle(words, memory, args, phase, 0xFFFFFFFF)
                    model.fault = cut
                    with self.assertRaises(recovery.stream.AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                    self.assertIn(model.dispatched_word >> 26, (32, 33, 35, 36, 37, 40, 41, 43, 49, 57))
                    pair.append(model)
                self.assertEqual(pair[0].dispatched_word, pair[1].dispatched_word)
                self.assertEqual(faults.state(pair[0]), faults.state(pair[1]))
                pairs += 1
        self.assertEqual((len(domains), pairs), (52, 2938))
        self.receipt('fault-boundary', paths=52, fired_pairs=pairs, equal_states=pairs,
            full_modeled_private_fault_match=True, hardware_PC_BD_FCSR_not_claimed=True)

    def test_14_source_screens_and_effective_overflow_and_fault_controls(self):
        text, functions, relocations = parse_object(self.out / 'selected.o')
        slot = self.out / 'negative-slot.s'
        original = (self.root / 'conker/asm/61D10.s').read_text().split('glabel ' + matching.FUNCTION + '\n', 1)[1]
        slot.write_text('glabel ' + matching.FUNCTION + '\n' + original.split('endlabel ' + matching.FUNCTION, 1)[0] +
            'endlabel ' + matching.FUNCTION + '\n')
        isolated = self.out / 'isolated-guards.csv'
        header = next(csv.reader(self.guard_before.decode('ascii').splitlines()))
        with isolated.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=header)
            writer.writeheader()
            writer.writerows(self.rows)
        for row in self.rows:
            bad = bytearray(text)
            bad[functions[matching.FUNCTION]['value'] + int(row['offset'], 0) + 3] ^= 1
            with patch('tools.pad_generated_object.parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaises(ValueError):
                    emit_padded_assembly(self.out / 'selected.o', slot, word_patches_path=isolated, filename='generated_61D10')
            with patch.object(matching, 'parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaisesRegex(ValueError, 'Stale'):
                    matching.guard_rows(self.out / 'selected.o')
        for at in matching.RELOCATIONS:
            bad = dict(relocations)
            bad.pop(at)
            with patch.object(matching, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaisesRegex(ValueError, 'relocation map'):
                    matching.guard_rows(self.out / 'selected.o')
        with self.assertRaises(ValueError):
            matching.gpr_cycle(0xFC000000, {11: 12, 12: 11})
        for cycle in ({11: 12}, {4: 5, 5: 4}, {29: 30, 30: 29}):
            with self.assertRaisesRegex(ValueError, 'closed finalizer scratch'):
                matching.gpr_cycle(self.raw[31], cycle)
        self.receipt('guard-controls', stale_word_rejections=76, stale_whole_object_rejections=76,
            missing_relocation_rejections=len(matching.RELOCATIONS), unknown_opcode_rejected=True,
            nonclosed_argument_and_saved_register_cycles_rejected=3,
            replacements_derived_without_retail_words=True)

    def test_16_bias_screens_have_no_accepted_source_improvement(self):
        forms = list(bias.candidates())
        self.assertEqual(len(forms), 15)
        self.assertEqual(forms[0][1], source.SELECTED)
        records = []
        for name, body in forms:
            meta, words = fitting.compile_candidate(self.root, self.out, 'bias-' + name, body)
            prefix = words[:14] == self.retail[:14]
            if meta['body_words'] == 405 and prefix:
                self.assertGreaterEqual(meta['differences'], 76, name)
                self.assertEqual(words, self.raw, name)
            records.append(dict(name=name, words=meta['body_words'], frame=meta['frame'],
                differences=meta['differences'], prefix_exact=prefix))
        self.receipt('bias-screens', forms=15, improvement=False, production_unchanged=True, records=records)

    def test_17_all_omitted_guards_fail_linked_byte_identity(self):
        original = (self.root / 'conker/asm/61D10.s').read_text().split('glabel ' + matching.FUNCTION + '\n', 1)[1]
        slot = self.out / 'omitted-slot.s'
        slot.write_text('glabel ' + matching.FUNCTION + '\n' + original.split('endlabel ' + matching.FUNCTION, 1)[0] +
            'endlabel ' + matching.FUNCTION + '\n')
        script = self.out / 'omitted.ld'
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % recovery.screen.ENTRY)
        guards = self.out / 'omitted.csv'
        assembly = self.out / 'omitted.s'
        obj, elf = assembly.with_suffix('.o'), assembly.with_suffix('.elf')
        for index, row in enumerate(self.rows):
            self.write_rows(guards, self.rows[:index] + self.rows[index + 1:])
            assembly.write_text(emit_padded_assembly(self.out / 'selected.o', slot,
                word_patches_path=guards, filename='generated_61D10'))
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
                '-o', str(obj), str(assembly)], check=True, capture_output=True)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', matching.FUNCTION,
                *['--defsym=%s=0x%X' % x for x in recovery.screen.SYMBOLS.items()],
                '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>405I', recovery.sections(elf)['.text'][1]))
            self.assertNotEqual(words, self.retail, row['offset'])
        self.receipt('omitted-guards', independently_linked_omissions=76, all_break_exact_identity=True)

    def test_18_both_full_owner_padders_reject_every_stale_expected_word(self):
        obj, _ = recovery.screen.compile_owner(self.root, self.out, self.owner_before, 'guard-controls-owner')
        guards = self.out / 'stale-expected.csv'
        for index, row in enumerate(self.rows):
            rows = [dict(r) for r in self.rows]
            rows[index]['expected'] = '0x%08X' % (int(row['expected'], 0) ^ 1)
            stream = io.StringIO(newline='')
            csv.DictWriter(stream, fieldnames=next(csv.reader(self.guard_before.decode('ascii').splitlines())),
                lineterminator='\n').writerows(rows)
            guards.write_bytes(self.guard_before + stream.getvalue().encode('ascii'))
            for script in ('pad_c_object.py', 'pad_generated_object.py'):
                output = self.out / ('stale-' + script + '.s')
                args = [str(obj), str(self.root / 'conker/retail_layout.us.txt'), 'generated_61D10', str(output)] if script == 'pad_c_object.py' else [
                    str(obj), str(self.root / 'conker/asm/61D10.s'), str(output), '--filename', 'generated_61D10']
                result = subprocess.run([sys.executable, str(self.root / 'tools' / script), *args,
                    '--word-patches', str(guards)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0, (script, row['offset']))
                self.assertIn('word patch', result.stderr, (script, row['offset'], result.stderr))
        self.receipt('full-owner-guard-controls', both_padders=True, stale_expected_word_rejections=152)


if __name__ == '__main__':
    unittest.main()
