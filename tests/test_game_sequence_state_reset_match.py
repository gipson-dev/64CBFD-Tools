"""Reset emission, original helper, ordered effects, both callers and bounded faults."""
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_sequence_state_reset as source
from tools.experiments import game_sequence_state_reset_match as fit
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import game_sequence_state_reset_oracle as model
from tools.tests import test_game_actor_burst_consumer_match as faults


class Join(Exception): pass


class CutCode(faults.TrackedCode):
    def __getitem__(self, pc):
        if pc == 0x1501D458: raise Join
        return super().__getitem__(pc)


class CutOracle(model.ResetOracle):
    def record_call(self, target):
        if target != 0x1501D1D4: return super().record_call(target)
        packet = self.arguments(3); self.calls.append((target, packet)); self.events.append(('CALL', target, packet))

    def hook(self, target):
        if target != 0x1501D1D4: return super().hook(target)
        for reg in (1, 2, 3, *range(4, 16), 24, 25): self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0x11223344


class SequenceStateResetMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw, cls.row = fit.qualify(cls.root, cls.out)
        cls.original = cls.out / 'original-reset.o'; cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>100I', cls.rom, source.ROM))
        data, functions = source.build.link_owner(cls.root, cls.out, cls.padded, source.OWNER)
        cls.normalized = list(struct.unpack_from('>100I', data, functions[source.FUNCTION]['value']))
        cls.helper = dict(zip(range(model.HELPER, model.HELPER + 40, 4), struct.unpack_from('>10I', cls.rom, 0x5086C)))
        cls.helper_body = data[functions['func_150233BC']['value']:functions['func_150233BC']['value'] + 40]

    def receipt(self, name, **row): (self.out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')

    def compare(self, words, memory, slot, phase=0, mode=0, connected=False):
        expected, before, fired = model.reference(memory, slot, mode)
        m = model.ResetOracle(words, memory, slot, phase, mode, self.helper if connected else {})
        m.run(); self.assertEqual(model.public(m.memory), model.public(expected))
        self.assertEqual(m.observations, [before]); self.assertEqual(m.fired, fired)
        calls = [(model.HELPER, ())] + ([(model.ZERO, (model.TABLE, 168))] if connected else [])
        self.assertEqual(m.calls, calls)
        for reg in (*range(16, 24), 28, 29, 30, 31): self.assertEqual(m.r[reg], m.before[reg])
        return m

    def test_01_exact100_original_frame_delay_store_and_all_neighbors(self):
        self.assertEqual(self.normalized, self.truth); self.assertEqual(self.helper_body, struct.pack('>10I', *self.helper.values()))
        self.assertEqual((self.row['words'], self.row['frame'], self.row['new_guards'], self.row['unchanged_raw_neighbors'],
            self.row['unchanged_caller_functions']), (100, 24, 13, 56, 6))
        self.assertFalse(self.row['direct']); self.assertEqual((self.row['inserted_words'], self.row['omitted_words']), (0, 0))
        self.assertEqual(self.truth[90:92], [0x0D408CEF, 0xA4233C9E])
        before = (self.out / 'before-guards').read_bytes(); after = (self.out / 'qualified-guards.csv').read_bytes()
        self.assertTrue(after.startswith(before)); self.assertEqual(after.count(b'\n') - before.count(b'\n'), 13)
        self.assertEqual(before.count(b'\r\n'), after.count(b'\r\n'))
        self.receipt('emission', raw_words=100, normalized_words=100, frame=24, new_guards=13, direct=False,
            unchanged_raw_neighbors=56, unchanged_caller_functions=6, original_RA14_and_call_delay_SH=True,
            no_profile_frame_save_slot_or_call_boundary_repair=True, real_helper10_preserved=True)

    def test_02_original_raw_and_guarded_ordered_resets_mutations_aliases_and_real_helper(self):
        count = connected_count = 0; visits = [set(), set(), set()]; fired_modes = set(); overwritten_constant = False
        for slot, limit, pattern, mode in model.cases():
            memory = model.fixture(slot, limit, pattern)
            for phase in (0, 8):
                machines = []
                for i, words in enumerate((self.truth, self.raw, self.normalized)):
                    m = self.compare(words, memory, slot, phase, mode); visits[i].update(m.visits); machines.append(m)
                self.assertEqual(model.state(machines[0]), model.state(machines[2])); count += 1
                fired_modes.update(machines[0].fired)
                if slot in (-45822, -45820):
                    overwritten_constant |= model.read(memory, model.LIMIT) != model.read(machines[0].memory, model.LIMIT)
                if mode == 0:
                    machines = [self.compare(words, memory, slot, phase, 0, True) for words in (self.truth, self.raw, self.normalized)]
                    self.assertEqual(model.state(machines[0]), model.state(machines[2])); connected_count += 1
        wanted = set(range(source.ENTRY, source.ENTRY + 400, 4))
        for seen in visits: self.assertEqual(seen & wanted, wanted)
        self.assertEqual(fired_modes, {1, 2, 4, 8}); self.assertTrue(overwritten_constant)
        self.receipt('guest', three_way_opaque_cases=count, three_way_real_helper_cases=connected_count,
            all100_words_visited_each=True, positive_mutation_gates=sorted(fired_modes),
            captured_limit_survives_indexed_guest_alias=True, real_helper10_executed=True,
            real_bzero_bounded_to_168_bytes=True, high_slots_and_nonretail_float_bits_synthetic=True,
            diagnostic_mutations_not_retail_bzero=True)

    def test_03_literal_original_guarded_instruction_access_fault_prefixes(self):
        count = 0
        for slot, phase, mode, connected in ((0, 0, 15, False), (1, 8, 0, True), (-45822, 0, 0, False)):
            memory = model.fixture(slot); full = self.compare(self.truth, memory, slot, phase, mode, connected)
            for fault in range(full.all_accesses):
                machines = []
                for words in (self.truth, self.normalized):
                    m = model.ResetOracle(words, memory, slot, phase, mode, self.helper if connected else {})
                    m.access_fault = fault
                    with self.assertRaises(faults.AccessBoundary): m.run()
                    self.assertEqual(m.all_accesses, fault); machines.append(m)
                self.assertEqual(model.state(machines[0]), model.state(machines[1])); count += 1
        self.receipt('faults', original_guarded_fault_prefixes=count, actual_helper_and_opaque_boundary_both=True,
            literal_memory_GPR_FPR_events_PC_delay_and_access_state=True, raw_C_fault_equivalence_not_claimed=True,
            opaque_provider_and_bzero_bytes_not_instruction_fault_emulation=True)

    def test_04_raw_original_bindings_pools_and_all_guard_fields_fail_closed(self):
        text, functions, relocations = parse_object(self.obj); f = functions[source.FUNCTION]
        for index in range(100):
            bad = bytearray(text); bad[f['value'] + index * 4] ^= 1
            with patch.object(fit, 'parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaises(ValueError): fit.checked_object(self.obj)
        bindings = fit.object_parts(self.obj)[1]
        for at in (*bindings, 0):
            bad = dict(relocations); bad[f['value'] + at] = [('R_MIPS_26', 'wrong')]
            with patch.object(fit, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaises(ValueError): fit.checked_object(self.obj)
        with patch.object(fit, 'sections', return_value={'.data':(0, b'bad')}):
            with self.assertRaises(ValueError): fit.checked_object(self.obj)
        original = parse_object(self.original); g = original[1][source.FUNCTION]; real_parse = fit.parse_object
        for index in range(100):
            bad = bytearray(original[0]); bad[g['value'] + index * 4] ^= 1
            with patch.object(fit, 'parse_object', side_effect=lambda p:(bytes(bad), original[1], original[2]) if p == self.original else real_parse(p)):
                with self.assertRaises(ValueError): fit.normalization(self.obj, self.original)
        bad_bindings = dict(original[2]); bad_bindings[g['value'] + 4] = [('R_MIPS_HI16', 'wrong')]
        with patch.object(fit, 'parse_object', side_effect=lambda p:(original[0], original[1], bad_bindings) if p == self.original else real_parse(p)):
            with self.assertRaises(ValueError): fit.normalization(self.obj, self.original)
        with patch.dict(fit.ROUTING, {4:4}):
            with self.assertRaises(ValueError): fit.normalization(self.obj, self.original)
        with self.assertRaises(ValueError): fit.swap_float_register(0x44802000)
        before = (self.out / 'before-guards').read_bytes(); after = (self.out / 'qualified-guards.csv').read_bytes()
        fields = next(csv.reader(io.StringIO(before.decode())))
        rows = list(csv.DictReader(io.StringIO(after[len(before):].decode()), fieldnames=fields)); count = 0
        for row in rows:
            for field in fields:
                old = row[field]; row[field] = 'bad'; stream = io.StringIO(newline='')
                csv.DictWriter(stream, fieldnames=fields, lineterminator='\n').writerows(rows)
                with self.assertRaises(ValueError): fit.checked_guards(before, before + stream.getvalue().encode(), self.obj, self.original)
                row[field] = old; count += 1
        self.assertEqual(count, 143)
        self.receipt('fail-closed', raw_words=100, original_words=100, bindings=75, extra_binding=True,
            private_pool=True, guard_field_corruptions=count, original_binding_map_pinned=True)

    def test_05_three_independent_HI_LO_carry_rebases(self):
        text, functions, relocations = parse_object(self.padded)
        names = sorted({name for rows in fit.object_parts(self.obj)[1].values() for _, name in rows})
        for index in range(3):
            entry = 0x15207FF0 + index * 0x100000
            symbols = {name:(entry + 0x10000 if name.startswith('func_') else 0x80100000 + n * 0x10000 + (0x7FFC, 0x8004, 0x7FD0)[index]) for n, name in enumerate(names)}
            emitted, unresolved = emit_function(text, functions[source.FUNCTION], relocations, source.FUNCTION, symbols)
            self.assertFalse(unresolved); asm = self.out / ('rebase-C-%d.s' % index); asm.write_text(emitted); obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], capture_output=True, check=True)
            images = []
            for label, path in (('original', self.original), ('C', obj)):
                script = self.out / ('rebase-%s-%d.ld' % (label, index)); elf = script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)], capture_output=True, check=True)
                images.append(sections(elf)['.text'][1][:400])
            self.assertEqual(images[0], images[1])
        self.receipt('rebases', independent_original_links=3, independent_guarded_C_links=3, all100_words=True, HI_LO_carries=True)

    def test_06_whole33_word_current_caller_and_actual_two_reset_chain(self):
        data, functions = source.build.link_owner(self.root, self.out, self.out / 'caller-after-padded.o', 'game_34F20')
        f = functions['func_15008248']; body = data[f['value']:f['value'] + f['size']]
        self.assertEqual((len(body), body), (132, self.rom[0x356F8:0x3577C])); words = list(struct.unpack('>33I', body)); count = 0
        for limit, pattern, phase, style in itertools.product(model.LIMITS, (0, 1, 255), (0, 8), ((False, 0), (False, 15), (True, 0))):
            connected, mode = style; memory = model.fixture(0, limit, pattern); expected = dict(memory)
            for a in (0x800C3638, 0x800C3671, 0x800C3670): model.put(expected, a, 0, 1)
            snapshots = []
            for slot in (0, 1): expected, before, _ = model.reference(expected, slot, mode); snapshots.append(before)
            for a in (0x800C3663, 0x800C3681, 0x800C3682, 0x800C3683): model.put(expected, a, 0, 1)
            for i in range(3): model.put(expected, model.TABLE + i * 56, 0, 2); model.put(expected, model.TABLE + i * 56 + 12, 0, 1)
            machines = []
            for target in (self.truth, self.raw, self.normalized):
                helper = dict(self.helper) if connected else {}; helper.update(zip(range(source.ENTRY, source.ENTRY + 400, 4), target))
                m = model.ResetOracle(words, memory, 0, phase, mode, helper, entry=0x15008248,
                    arguments=(0xDEADBEEF, 0x80000000, 0x10000, 0xFFFFFFFF)).run()
                self.assertEqual(model.public(m.memory), model.public(expected)); self.assertEqual(m.observations, snapshots)
                wanted = []
                for slot in (0, 1):
                    wanted.extend([(source.ENTRY, (slot,)), (model.HELPER, ())])
                    if connected: wanted.append((model.ZERO, (model.TABLE, 168)))
                self.assertEqual(m.calls, wanted); machines.append(m)
            self.assertEqual(model.state(machines[0]), model.state(machines[2])); count += 1
        self.receipt('wrapper', complete_current_caller_words=33, three_way_full_caller_cases=count,
            both_reset_bodies_and_real_helper_chain=True, incoming_argument_ignored=True,
            actual_bzero_is_bounded=True, natural_gameplay_not_claimed=True)

    def test_07_original473_word_other_caller_and_real_argument_spill_reload_cut(self):
        original = fit.original(self.root, self.out, 'original-reset-caller', 'func_1501D348')
        data, functions = source.build.link_owner(self.root, self.out, original, source.OWNER)
        f = functions['func_1501D348']; body = data[f['value']:f['value'] + f['size']]
        self.assertEqual((len(body), body), (1892, self.rom[0x4A7F8:0x4AF5C]))
        cut = list(struct.unpack_from('>13I', body, 0x1501D424 - 0x1501D348)); count = 0
        self.assertEqual((cut[1], cut[7], cut[8]), (0x02A02025, 0x0D407411, 0xAFB10078))
        for slot, take, phase, mode in itertools.product((0, 1, 2), (False, True), (0, 8), (0, 15)):
            memory = model.fixture(slot); initial = dict(memory)
            if not take:
                model.put(initial, 0x800C35A8, 0x78, 1); model.put(initial, 0x800C3C98, 0x40, 1)
            expected, before, _ = model.reference(initial, slot, mode); machines = []
            for target in (self.truth, self.raw, self.normalized):
                helper = dict(zip(range(source.ENTRY, source.ENTRY + 400, 4), target))
                m = CutOracle(cut, memory, 0, phase, mode, helper, entry=0x1501D424)
                m.r[1], m.r[2], m.r[3] = 2, 2 if take else 1, 0x12345678
                m.r[16], m.r[17], m.r[21] = 0x10203040, 0x30000400, slot; m.code = CutCode(m.code, m)
                with self.assertRaises(Join): m.run()
                self.assertEqual(model.public(m.memory), model.public(expected)); self.assertEqual(m.observations, [before])
                self.assertEqual(m.calls, [(source.ENTRY, (slot,)), (model.HELPER, ()), (0x1501D1D4, (0x30000400, 0x10203040, slot))])
                self.assertEqual((m.r[16], m.r[17], m.r[21], m.r[29], m.r[31]), (0x10203040, 0x30000400, slot, model.STACK + phase, 0x1501D458)); machines.append(m)
            self.assertEqual(model.state(machines[0]), model.state(machines[2])); count += 1
        self.receipt('other-caller', full_original_words=473, three_way_real_call_cuts=count,
            actual_argument_branch_delay_and_two_stack_spills=True, actual_post_call_reloads=True,
            next_three_word_provider_packet=True, full_original_caller_and_next_provider_not_claimed=True)


if __name__ == '__main__': unittest.main()
