"""Guarded emission, signed-priority behavior, ABI, caller cut and fail-closed scope."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_maximum_match as fit
from tools.experiments import game_record_maximum_scan as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import game_record_maximum_oracle as model
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_view_list_setup as assembly


class Join(Exception): pass


class CallerCode(faults.TrackedCode):
    def __getitem__(self, pc):
        if pc == 0x1501D9D4: raise Join
        return super().__getitem__(pc)


class CallerCut(model.MaximumOracle):
    def record_call(self, target):
        if target not in (source.ENTRY, 0x15022BA4): raise ValueError('Unexpected caller-cut provider')
        self.calls.append((target, self.arguments(1)))

    def hook(self, target):
        if target != 0x15022BA4: raise ValueError('Unexpected opaque provider')
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register


class RecordMaximumMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw, cls.row = fit.qualify(cls.root, cls.out)
        cls.original = cls.out / 'original-maximum.o'
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>105I', cls.rom, source.ROM))
        data, functions = source.build.link_owner(cls.root, cls.out, cls.padded, source.OWNER)
        cls.normalized = list(struct.unpack_from('>105I', data, functions[source.FUNCTION]['value']))

    def receipt(self, name, **row):
        (self.out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')

    def compare(self, words, memory, slot, phase=0):
        expected = model.reference(memory, slot); m = model.MaximumOracle(words, memory, slot, phase)
        saved = m.r[16:24] + m.r[28:32]; floating = list(m.f); initial = dict(m.memory)
        m.run(); self.assertEqual(m.memory, expected); self.assertEqual(m.calls, [])
        self.assertEqual(m.r[16:24] + m.r[28:32], saved); self.assertEqual(m.f, floating)
        changed = {a for a in m.memory if m.memory[a] != initial[a]}
        self.assertLessEqual(changed, set(range(model.OUTPUT + slot * 4, model.OUTPUT + slot * 4 + 4)))
        return m

    def test_01_exact105_no_frame_no_insertions_and_56_raw_neighbors(self):
        self.assertEqual(self.normalized, self.truth)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['new_guards'], self.row['unchanged_raw_neighbors']), (105, 0, 48, 56))
        self.assertFalse(self.row['direct']); self.assertEqual(self.row['inserted_words'], 0); self.assertEqual(self.row['omitted_words'], 0)
        before = (self.out / 'before-guards').read_bytes(); after = (self.out / 'qualified-guards.csv').read_bytes()
        self.assertTrue(after.startswith(before)); self.assertEqual(after.count(b'\n') - before.count(b'\n'), 48)
        self.assertEqual(before.count(b'\r\n'), after.count(b'\r\n'))
        self.receipt('emission', raw_words=105, normalized_words=105, frame=0, new_guards=48,
            register_only_after_four_word_setup_routing=True, unchanged_raw_neighbors=56, direct=False,
            source_profile_unchanged=True, inserted_words=0, omitted_words=0)

    def test_02_original_raw_C_normalized_all_words_and_signed_priority(self):
        count = 0; visits = [set(), set(), set()]
        for case in model.cases():
            memory = model.fixture(case)
            for phase in (0, 8):
                machines = []
                for index, words in enumerate((self.truth, self.raw, self.normalized)):
                    m = self.compare(words, memory, case[0], phase); visits[index].update(m.visits); machines.append(m)
                self.assertEqual(model.state(machines[0]), model.state(machines[2])); count += 1
        wanted = set(range(source.ENTRY, source.ENTRY + 420, 4))
        for seen in visits: self.assertEqual(seen & wanted, wanted)
        self.receipt('guest', three_way_cases=count, all105_words_visited_in_each=True,
            signed_override_and_maxima=True, preferred_update_suppresses_fallback=True,
            full_u16_enable_and_tail_counts=True, high_byte_count_cases_synthetic=True,
            literal_original_normalized_private_state=True, raw_C_public_state_only=True)

    def test_03_guest_alias_gating_and_all_access_fault_prefixes(self):
        alias_count = fault_count = 0
        fixtures = [(model.fixture(c), c[0]) for c in ((0, 0, 0, 0, -9999), (1, 2, 2, 1, -9999), (2, 1, 4, 0, -32768))]
        for name, memory, slot in model.alias_cases():
            machines = [self.compare(words, memory, slot) for words in (self.truth, self.raw, self.normalized)]
            self.assertEqual(model.state(machines[0]), model.state(machines[2])); alias_count += 1
            fixtures.append((memory, slot))
        for memory, slot in fixtures:
            full = self.compare(self.truth, memory, slot)
            for fault in range(full.all_accesses):
                machines = []
                for words in (self.truth, self.normalized):
                    m = model.MaximumOracle(words, memory, slot); m.access_fault = fault
                    with self.assertRaises(faults.AccessBoundary): m.run()
                    self.assertEqual(m.all_accesses, fault); machines.append(m)
                self.assertEqual(model.state(machines[0]), model.state(machines[1])); fault_count += 1
        # A zero byte count must not dereference any of the pointer tables.
        memory = model.fixture((0, 0, 0, 0, -9999))
        for at in (model.PRIMARY, model.ENABLED, model.COUNTS):
            for n in range(4): del memory[at + n]
        for words in (self.truth, self.raw, self.normalized): self.compare(words, memory, 0)
        memory = model.fixture((0, 2, 6, 0, -9999))
        for at in (model.PREFERRED, model.FALLBACK):
            for n in range(8): del memory[at + n]
        for n in range(4): del memory[model.COUNTS + n]
        for words in (self.truth, self.raw, self.normalized): self.compare(words, memory, 0)
        memory = model.fixture((0, 1, 0, 0, -9999))
        model.put(memory, 0x200000, 1, 2); model.put(memory, 0x210000, 0, 2); model.put(memory, 0x220000, 0, 2)
        for at in (model.PREFERRED, model.FALLBACK):
            for n in range(4): del memory[at + n]
        for words in (self.truth, self.raw, self.normalized): self.compare(words, memory, 0)
        self.receipt('aliases-faults', guest_alias_cases=alias_count, original_normalized_fault_prefixes=fault_count,
            clear_precedes_byte_count=True, zero_count_disabled_and_empty_tail_pointer_gates=True,
            guest_aliases_not_portable_native_C_alias_claims=True, raw_C_fault_equivalence_not_claimed=True)

    def test_04_all_words_bindings_pools_original_and_guard_fields_fail_closed(self):
        text, functions, relocations = parse_object(self.obj); f = functions[source.FUNCTION]
        for index in range(105):
            bad = bytearray(text); bad[f['value'] + index * 4] ^= 1
            with patch.object(fit, 'parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaises(ValueError): fit.checked_object(self.obj)
        for at in (*fit.RELOCATIONS, 8):
            bad = dict(relocations); bad[f['value'] + at] = [('R_MIPS_26', 'wrong')]
            with patch.object(fit, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaises(ValueError): fit.checked_object(self.obj)
        with patch.object(fit, 'sections', return_value={'.data':(0, b'bad')}):
            with self.assertRaises(ValueError): fit.checked_object(self.obj)
        original = parse_object(self.original); g = original[1][source.FUNCTION]; real_parse = fit.parse_object
        for index in range(105):
            bad = bytearray(original[0]); bad[g['value'] + index * 4] ^= 1
            with patch.object(fit, 'parse_object', side_effect=lambda p:(bytes(bad), original[1], original[2]) if p == self.original else real_parse(p)):
                with self.assertRaises(ValueError): fit.normalization(self.obj, self.original)
        bad_relocations = dict(original[2]); bad_relocations[g['value']] = [('R_MIPS_HI16', 'wrong')]
        with patch.object(fit, 'parse_object', side_effect=lambda p:(original[0], original[1], bad_relocations) if p == self.original else real_parse(p)):
            with self.assertRaises(ValueError): fit.normalization(self.obj, self.original)
        self.assertTrue(fit.register_only(0x0105782A, 0x0105082A))
        for bad in (0x0105782B, 0x0100782A, 0x0205782A, 0x0085782A):
            self.assertFalse(fit.register_only(bad, 0x0105082A))
        before = (self.out / 'before-guards').read_bytes(); after = (self.out / 'qualified-guards.csv').read_bytes()
        fields = next(csv.reader(io.StringIO(before.decode())))
        rows = list(csv.DictReader(io.StringIO(after[len(before):].decode()), fieldnames=fields)); count = 0
        for row in rows:
            for field in fields:
                old = row[field]; row[field] = 'bad'; stream = io.StringIO(newline='')
                csv.DictWriter(stream, fieldnames=fields, lineterminator='\n').writerows(rows)
                with self.assertRaises(ValueError): fit.checked_guards(before, before + stream.getvalue().encode(), self.obj, self.original)
                row[field] = old; count += 1
        self.assertEqual(count, 528)
        self.receipt('fail-closed', raw_words=105, original_words=105, bindings=18, added_binding=1,
            private_pool=1, guard_field_corruptions=count, original_binding_map_pinned=True)

    def test_05_three_independent_HI_LO_carry_rebases(self):
        text, functions, relocations = parse_object(self.padded)
        names = sorted({name for rows in fit.RELOCATIONS.values() for _, name in rows})
        for index in range(3):
            entry = 0x15207FF0 + index * 0x100000
            symbols = {name:0x80100000 + n * 0x10000 + (0x7FFC, 0x8004, 0x7FD0)[index] for n, name in enumerate(names)}
            emitted, unresolved = emit_function(text, functions[source.FUNCTION], relocations, source.FUNCTION, symbols)
            self.assertFalse(unresolved); asm = self.out / ('rebase-C-%d.s' % index); asm.write_text(emitted); obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], capture_output=True, check=True)
            images = []
            for label, path in (('original', self.original), ('C', obj)):
                script = self.out / ('rebase-%s-%d.ld' % (label, index)); elf = script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)], capture_output=True, check=True)
                images.append(sections(elf)['.text'][1][:420])
            self.assertEqual(images[0], images[1])
        self.receipt('rebases', independent_original_links=3, independent_guarded_C_links=3, all105_words=True, HI_LO_carries=True)

    def test_06_full_original_caller_and_actual_delay_slot_interface(self):
        context = type('OriginalContext', (), dict(root=self.root, out=self.out))
        original = assembly.ViewListSetupTests.original.__func__(context, 'original-maximum-caller',
            (self.out / 'before-view_list_caller_original').read_text(), 'func_1501D348')
        data, functions = source.build.link_owner(self.root, self.out, original, source.OWNER)
        f = functions['func_1501D348']; body = data[f['value']:f['value'] + f['size']]
        self.assertEqual((len(body), body), (1892, self.rom[0x4A7F8:0x4AF5C]))
        cut = list(struct.unpack_from('>4I', body, 0x1501D9C4 - 0x1501D348))
        self.assertEqual(cut, [0x0D407395, 0x02A02025, 0x0D408AE9, 0x02A02025])
        count = 0
        for case in model.cases():
            if case[1] > 30: continue
            slot = case[0]; memory = model.fixture(case); expected = model.reference(memory, slot); machines = []
            for words in (self.truth, self.raw, self.normalized):
                helper = dict(zip(range(source.ENTRY, source.ENTRY + 420, 4), words))
                m = CallerCut(cut, memory, 0xDEADBEEF, helpers=helper, entry=0x1501D9C4)
                m.r[21] = slot; m.code = CallerCode(m.code, m); initial_sp = m.r[29]
                with self.assertRaises(Join): m.run()
                self.assertEqual(m.memory, expected); self.assertEqual(m.calls, [(source.ENTRY, (slot,)), (0x15022BA4, (slot,))])
                self.assertEqual((m.r[21], m.r[29], m.r[31]), (slot, initial_sp, 0x1501D9D4)); machines.append(m)
            self.assertEqual(model.state(machines[0]), model.state(machines[2])); count += 1
        self.receipt('caller', full_original_words=473, three_way_actual_call_cuts=count,
            slot_from_S5_in_both_JAL_delay_slots=True, no_interpreted_return_value=True,
            following_provider_opaque_ABI_only=True, full_caller_gameplay_not_claimed=True)


if __name__ == '__main__': unittest.main()
