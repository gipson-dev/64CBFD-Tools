"""Literal guarded counter-preset ABI, faults, relocations and real factory chain."""
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_counter_preset_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools import pad_generated_object as padder
from tools.tests import test_game_counter_preset as previous
from tools.tests import test_game_factory_preset_wrapper as wrapper
from tools.tests import test_game_record_factory as factory
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.tests.test_game_owner_actor_update_match import read
from tools.tests.test_game_record_constructor_match import elf_slot_offset

CounterOracle, packet, address = previous.CounterOracle, previous.packet, previous.address


def state(model):
    return (wrapper.state(model), model.lo, model.condition, model.callbacks,
        model.writes, model.visits, getattr(model, 'observed', []))


class ChainOracle(factory.FactoryOracle):
    def record_call(self, target):
        if not hasattr(self, 'observed'):
            self.observed = []
        if target == source.CALLEE:
            self.observed.append(read(self.memory, self.counter, 1))
        super().record_call(target)


class CounterMatchCandidateTests(unittest.TestCase):
    def test_scope_and_fail_closed_compiler_gate(self):
        self.assertEqual(len(source.PATHS), 52)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        self.assertEqual(source.build.body(source.SELECTED, source.FUNCTION),
            source.build.body(source.previous.SELECTED, source.FUNCTION))
        for count, differences, diagnostics in ((84, 0, ''), (85, 75, ''), (85, 76, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=count, differences=differences, diagnostics=diagnostics))):
                with self.assertRaisesRegex(ValueError, 'compiler shape'):
                    source.qualify(Path('.'), Path('.'))
        with self.assertRaisesRegex(ValueError, 'words or relocations'):
            source.normalize(b'', source.RELOCATIONS)


class CounterMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>84I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_05_native32_O2_O0_and_all_ten_effective_controls = previous.CounterPresetRecoveryTests.test_04_native32_backed_array_signed_boundaries_and_controls
    test_08_all_original_801_archive_fingerprints = previous.CounterPresetRecoveryTests.test_08_all_original_801_archive_fingerprints

    def test_01_raw_shape_guards_and_all_owner_neighbors(self):
        self.assertEqual((len(self.raw_words), self.row['differences'], self.row['guards_added']), (85, 76, 38))
        self.assertEqual(self.words, self.truth)
        raw, rel = source.raw_target(self.obj)
        normalized, moved = source.normalize(raw, rel)
        self.assertEqual(len(normalized), 336)
        self.assertEqual(moved, {24: rel[24], 28: rel[28], 312: rel[316]})
        for index in range(85):
            bad = bytearray(raw)
            bad[index * 4] ^= 1
            with self.assertRaisesRegex(ValueError, 'words or relocations'):
                source.normalize(bytes(bad), rel)
        for offset in rel:
            for action in ('missing', 'symbol', 'kind'):
                bad = dict(rel)
                if action == 'missing':
                    del bad[offset]
                else:
                    kind, name = bad[offset][0]
                    bad[offset] = [(kind + '_bad', name)] if action == 'kind' else [(kind, name + '_bad')]
                with self.assertRaisesRegex(ValueError, 'words or relocations'):
                    source.normalize(raw, bad)
        obj, diagnostics = source.build.compile_owner(self.root, self.out, (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostics, '')
        old, new = padder.parse_object(obj), padder.parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda o, f: [(p - f['value'], r) for p, r in o[2].items() if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(obj), normalized_pools(self.obj))
        before = (self.out / 'before-guards').read_bytes()
        guards = source.guard_manifest(before, raw, rel)
        self.assertTrue(guards.startswith(before))
        rows = list(csv.DictReader(io.StringIO(guards.decode())))
        target = [row for row in rows if row['function'] == source.FUNCTION]
        self.assertEqual(len(target), 38)
        self.assertEqual(sum(row['omit'] == 'true' for row in target), 1)
        self.assertEqual(sum(row['expected'] == row['replacement'] and row['omit'] == 'false' for row in target), 1)
        with self.assertRaisesRegex(ValueError, 'guard predecessor'):
            source.guard_manifest(guards, raw, rel)
        self.receipt('owner', raw_words=85, raw_differences=76, guarded_words=84, guarded_differences=0,
            guards=38, register_replacements=35, branch_adjustments=1, omitted_loads=1, identity_call_binding_guards=1,
            raw_word_corruptions_rejected=85, relocation_corruptions_rejected=9,
            unchanged_neighbors=29, pools_and_relative_relocations_fixed=True, frame=208, raw_C_exact=False)

    def test_02_all_private_registers_stack_events_and_branch_delay_lifetimes(self):
        counts, visits = dict(cases=0, accepted=0, rejected=0), set()
        for index in (0x80000000, 0xFFFFFFC0, 0xFFFFFFFF, 0, 1, 2, 3, 4, 0x7FFFFFFF):
            for value in (0, 1, 127, 128, 254, 255):
                for threshold in (0x80000000, 0xFFFFFFFF, 0, 1, 127, 128, 254, 255, 256, 0x7FFFFFFF):
                    args = (index, threshold, 0xFFFFFF80 | value, (index * 1664525 + threshold) & 0xFFFFFFFF)
                    for phase in (0, 8):
                        for mode in range(3):
                            pair = [CounterOracle(w, args, value, phase, mode).run() for w in (self.words, self.truth)]
                            self.assertEqual(state(pair[0]), state(pair[1]))
                            live = signed(index) < 4
                            called = live and value >= signed(threshold)
                            model = pair[0]
                            self.assertEqual(model.calls, [(source.CALLEE, *packet(args))] if called else [])
                            self.assertEqual(model.observed, [0] if called else [])
                            self.assertEqual(model.r[29], wrapper.STACK + phase)
                            self.assertEqual(read(model.memory, address(args), 1), 0x5A if called and mode == 2 else 0 if called else value)
                            if not called:
                                self.assertEqual(model.r[2], address(args))
                            else:
                                call = next(i for i, event in enumerate(model.events) if event[0] == 'CALL')
                                self.assertEqual(model.events[call - 1], ('W', wrapper.STACK + phase - 72, 4, index))
                            self.assertEqual(len([e for e in model.events if e[:3] == ('R', address(args), 1)]), int(live))
                            visits |= model.visits
                            counts['cases'] += 1
                            counts['accepted' if called else 'rejected'] += 1
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 336, 4)))
        self.receipt('abi', **counts, all_84_words_visited=True, full_literal_private_state_equal=True,
            rejected_V0_is_pointer_from_branch_delay=True, final_actor_word_store_in_call_delay=True,
            incoming_outgoing_home_clobbers_and_counter_provider_write=True,
            backed_guest_indices_not_arbitrary_runtime_or_native_domain=True)

    def test_03_all_fired_private_fault_prefixes(self):
        count = 0
        for args in ((0, 0, 0xFFFFFF80, 0x12345678), (0, 256, 0xFFFFFF80, 0x12345678), (4, 0, 0xFFFFFF80, 0x12345678)):
            for phase in (0, 8):
                whole = CounterOracle(self.words, args, phase=phase, mode=2).run()
                for fault in range(whole.accesses):
                    pair = [CounterOracle(w, args, phase=phase, mode=2, fault=fault) for w in (self.words, self.truth)]
                    for model in pair:
                        with self.assertRaises(AccessFault):
                            model.run()
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    count += 1
        self.receipt('prefixes', paired_fired_guest_faults=count, all_literal_private_prefixes_equal=True,
            not_portable_C_fault_or_hardware_acceptance=True)

    def test_04_all_ten_compiled_negatives_reject_normalization(self):
        failures = {}
        for name, body in previous.controls().items():
            obj, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            with self.assertRaisesRegex(ValueError, 'words or relocations'):
                source.normalize(*source.raw_target(obj))
            count = 0
            for args in ((0xFFFFFFFF, 0, 0xFFFFFF80, 0x12345678), (0, 0xFFFFFFFF, 0xFFFFFF80, 0x12345678), (0, 255, 0xFFFFFF80, 0x12345678)):
                a, b = [CounterOracle(w, args, 255, mode=2).run() for w in (words, self.truth)]
                count += (a.calls, a.observed, read(a.memory, address(args), 1)) != (b.calls, b.observed, read(b.memory, address(args), 1))
            self.assertGreater(count, 0, name)
            failures[name] = count
        self.receipt('controls', effective_unguarded_guest_negatives=failures,
            every_mutant_rejected_by_normalization=True, no_guards_applied_to_semantic_changes=True)

    def test_06_original_and_normalized_rebases_and_full_home_aliases(self):
        normalized, rel = source.normalize(*source.raw_target(self.obj))
        text, missing = emit_function(normalized, dict(value=0, size=336), rel, source.FUNCTION,
            {'func_1516D99C': source.CALLEE, 'D_800DD2A0': source.TABLE})
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for label, body in dict(selected=text, original='glabel ' + source.FUNCTION + '\n' + original).items():
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        aliases = 0
        for i, (delta, table) in enumerate(((0, source.TABLE), (0x10000, 0x00317FFC), (-0x10000, 0x00528004))):
            entry, callee = source.ENTRY + delta, source.CALLEE - delta
            script = self.out / ('rebase-%d.ld' % i)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            outputs = []
            for label in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (label, i))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=func_1516D99C=0x%X' % callee, '--defsym=D_800DD2A0=0x%X' % table,
                    '-o', str(elf), str(self.out / (label + '-reloc.o'))], check=True, capture_output=True)
                outputs.append(list(struct.unpack_from('>84I', sections(elf)['.text'][1])))
            self.assertEqual(outputs[0], outputs[1])
            for args in ((0, 0, 0xFFFFFF80, 0x12345678), (0xFFFFFFFF, 255, 0xFF123456, 0x98765432), (0, 256, 0, 0), (4, 0, 0, 0)):
                pair = [CounterOracle(w, args, entry=entry, callee=callee, table=table).run() for w in outputs]
                self.assertEqual(state(pair[0]), state(pair[1]))
            if i == 0:
                continue
            for phase in (0, 8):
                for offset in (3, 7, 11, 15, -208 + 0x4C, -1):
                    slot = (wrapper.STACK + phase + offset - table) & 0xFFFFFFFF
                    self.assertLess(signed(slot), 4)
                    args = (slot, 0, 0x12345680, 0x765432FF)
                    pair = [CounterOracle(w, args, phase=phase, mode=0 if offset == -1 else 2,
                        entry=entry, callee=callee, table=table).run() for w in outputs]
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    self.assertEqual(pair[0].calls, [(callee, *packet(args))])
                    aliases += 1
        self.receipt('rebases', independent_original_normalized_text_table_call_pairs=3,
            all_84_words_equal=True, full_private_backed_home_outgoing_RA_aliases=aliases,
            low_carry_boundaries=True, synthetic_guest_not_portable_C_alias_claim=True)

    def test_07_current_real_factory_allocator_chain(self):
        image = (self.root / source.PATHS['elf']).read_bytes()
        connected = {}
        for entry, rom, count in ((source.CALLEE, 0x19AE4C, 125), (0x15167A68, 0x194F18, 28)):
            words = list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        counts = dict(rejected=0, null=0, registered=0)
        for i in range(128):
            args = tuple(a & 0xFFFFFFFF for a in (i % 6, 0 if i % 3 else 256, 0xFFFF0080 | i, i * 1664525 + 1013904223))
            called, result = args[0] < 4 and args[1] <= 255, 0 if i % 4 == 0 else factory.RECORD
            pair = []
            for words in (self.words, self.truth):
                model = ChainOracle(words, args, result, phase=(i & 1) * 8, entry=source.ENTRY, connected=connected, chain=True)
                model.counter = address(args)
                model.memory.update({model.counter + j: v for j, v in enumerate((255, 0xA5, 0x5A, 0xC3))})
                pair.append(model.run())
            self.assertEqual(state(pair[0]), state(pair[1]))
            model = pair[0]
            self.assertEqual(getattr(model, 'observed', []), [0] if called else [])
            self.assertEqual(read(model.memory, address(args), 1), 0 if called else 255)
            if called:
                self.assertEqual(model.calls[0], (source.CALLEE, *packet(args)))
                self.assertEqual(model.calls[1], (0x15167A68, 17, args[3], 76, 0, args[2] & 255, 1))
                self.assertEqual(model.calls[2], (factory.ALLOCATE, 76, 1, 0, 0, 1))
                self.assertEqual(len(model.calls), 4 if result else 3)
                if result:
                    expected = factory.reference(factory.fixture(packet(args)), packet(args), result)[0]
                    for at in range(factory.RECORD + 14, factory.RECORD + 76):
                        self.assertEqual(model.memory[at], expected[at])
                    self.assertEqual(model.memory[factory.RECORD], 17)
                    self.assertEqual(model.memory[factory.RECORD + 1], args[3] & 255)
                    self.assertEqual(model.memory[factory.RECORD + 12], args[2] & 255)
            else:
                self.assertEqual(model.calls, [])
            counts['rejected' if not called else 'registered' if result else 'null'] += 1
        self.assertTrue(all(counts.values()))
        self.receipt('chain', paired_cases=128, **counts, actual_current_callee_words=[125, 28],
            all_private_states_equal=True, provider_observes_clear_before_null_or_success=True,
            actual_current_image_uses_no_inverse=True, lower_heap_and_registration_opaque=True)

    def test_09_every_physical_guard_word_and_binding_is_checked(self):
        original = padder.parse_object(self.obj)
        start = original[1][source.FUNCTION]['value']
        guards = self.out / 'qualified-guards.csv'
        rows = [r for r in csv.DictReader(io.StringIO(guards.read_text())) if r['function'] == source.FUNCTION]
        for row in rows:
            bad = bytearray(original[0])
            bad[start + int(row['offset'], 0)] ^= 1
            with patch.object(padder, 'parse_object', return_value=(bytes(bad), original[1], original[2])):
                with self.assertRaisesRegex(ValueError, 'stale word patch'):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'], filename=source.OWNER, word_patches_path=guards)
        for offset in source.RELOCATIONS:
            rel = dict(original[2])
            kind, name = rel[start + offset][0]
            rel[start + offset] = [(kind, name + '_bad')]
            with patch.object(padder, 'parse_object', return_value=(original[0], original[1], rel)):
                with self.assertRaisesRegex(ValueError, 'stale relocations'):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'], filename=source.OWNER, word_patches_path=guards)
        self.receipt('physical-guards', stale_word_controls=len(rows), stale_binding_controls=3,
            original_compiler_body_not_literal_retail_copy=True, old_guard_history_unchanged=True)


if __name__ == '__main__':
    unittest.main()
