"""Qualify the movement coefficient's actual retail read/store ordering."""
import copy
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_remaining_schedules as recovery
from tools.tests import test_game_actor_input_movement_scalar_lifetimes as prior

source, model, original = recovery.source, prior.model, prior.original


class PitchStop(Exception):
    pass


class PitchOracle(model.Oracle):
    def execute(self, word):
        if self.current_pc == 0x150F3EBC:
            raise PitchStop
        return super().execute(word)


class MovementRemainingScheduleTests(prior.MovementScalarLifetimeTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / recovery.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = recovery.qualify(cls.root, cls.out)
        cls.body = recovery.selected_body()
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>959I', cls.rom, source.ROM))
        cls.connected = {0x150F34A0 + i * 4: w for i, w in enumerate(struct.unpack_from('>21I', cls.rom, 0x120950))}
        cls.bindings = source.parts(cls.obj)[1]
        cls.base28, _ = recovery.previous.previous.previous.previous.normalize(cls.raw_words, cls.truth, cls.bindings)
        cls.harness = original.MovementRecoveryTests('test_02_all_three_paths_and_numeric_boundaries')
        for name in ('root', 'out', 'rom', 'words', 'truth', 'connected'):
            setattr(cls.harness, name, getattr(cls, name))
        cls.harness.obj = cls.padded
        cls.harness.coverage, cls.harness.providers = set(), set()
        compare = cls.harness.compare

        def three_way(spec, images=None, entry=source.ENTRY):
            return compare(spec, images or (cls.truth, cls.raw_words, cls.words), entry)

        cls.harness.compare = three_way

    def test_01_complete_source_controls_and_literal_gain(self):
        self.assertEqual(tuple(self.row[k] for k in ('words', 'frame', 'differences', 'normalized_differences')), (959, 128, 134, 103))
        self.assertEqual((self.row['normalized_exact_opening_words'], self.row['normalized_first_PC']), (478, 0x150F3C6C))
        self.assertEqual(self.words[:478], self.truth[:478])
        self.assertEqual(self.row['normalized_raw_sha'], '0e13d4c7659efcacf847a1f0abc249b0e24eeaecb851a2fee1586a642aa3445b')
        self.assertEqual((self.row['research_guards'], self.row['new_research_guards'], self.row['production_guards_added'],
                          self.row['matching_credit'], self.row['installed']), (31, 0, 0, 0, False))
        self.assertEqual((self.out / 'expected-schedule-guards.csv').read_bytes(),
                         (self.root / recovery.previous.BUILD / 'expected-scalar-guards.csv').read_bytes())
        self.assertEqual(source.parts(self.obj)[1], source.parts(self.padded)[1])
        before = (self.out / 'before-record_gate_owner').read_text()
        rows = []
        for name, body in recovery.all_forms():
            with patch.object(source, 'TYPE', recovery.owner_types(name)):
                self.assertEqual((self.out / (name + '.c')).read_text(), source.recovered_owner(before, body), name)
            raw, _ = source.parts(self.out / (name + '.o'))
            audit = json.loads((self.out / (name + '-audit.json')).read_text())
            self.assertEqual(hashlib.sha256(raw).hexdigest(), audit['raw_sha'])
            words = list(struct.unpack_from('>%dI' % (len(raw) // 4), source.projection.sections(self.out / (name + '-linked.elf'))['.text'][1]))
            self.assertEqual((len(words), (-words[0]) & 65535, sum(a != b for a, b in zip(words, self.truth))),
                             tuple(audit[k] for k in ('words', 'frame', 'differences')))
            self.assertEqual((audit['raw_neighbors'], audit['padded_neighbors']), (11, 11))
            rows.append(dict(name=name, words=len(words), differences=audit['differences']))
        self.assertEqual((len(rows), {r['words'] for r in rows}), (32, {959}))
        old = list(struct.unpack_from('>959I', source.projection.sections(
            self.root / recovery.previous.BUILD / (recovery.previous.SELECTED_NAME + '-linked.elf'))['.text'][1]))
        changes = [i for i in range(959) if old[i] != self.raw_words[i]]
        self.assertEqual([source.ENTRY + i * 4 for i in changes], [pc for pc, _ in recovery.PITCH_SITES])
        self.assertTrue(all(self.raw_words[i] == self.truth[i] for i in changes))
        self.assertTrue(all(old[i] != self.truth[i] for i in changes))
        self.receipt('source-controls', complete_forms=32, overflow_rejections=0, shorter_controls=0, rows=rows,
                     raw_changed_words=5, newly_exact=5, formerly_exact_lost=0, research_table_byte_identical=True)

    def test_13_fresh_backend_homes_and_effective_controls(self):
        with patch.object(prior.recovery, 'SELECTED_NAME', recovery.SELECTED_NAME):
            super().test_13_fresh_backend_homes_and_effective_controls()
        record, words, _ = recovery.backend.finish_trace(self.root, self.out, recovery.SELECTED_NAME, self.body)
        content = recovery.backend.frame.isolated(self.body)
        layout = recovery.check_layout(record, words, content)
        controls = 0
        for pc, _ in recovery.PITCH_SITES:
            bad = list(words)
            bad[(pc - source.ENTRY) // 4] ^= 1
            with self.assertRaises(ValueError):
                recovery.check_layout(record, bad, content)
            controls += 1
        previous_receipt = json.loads((self.out / 'backend.json').read_text())
        self.assertEqual(previous_receipt['effective_controls'], 47)
        self.receipt('backend', **dict(previous_receipt, layout=layout,
            effective_controls=47 + controls, new_pitch_order_controls=controls,
            coefficient_is_inline_expression_not_extra_FP_local=True))

    def test_14_stale_guard_and_relocation_controls(self):
        rows = list(csv.DictReader(io.StringIO((self.out / 'expected-schedule-guards.csv').read_text())))
        fields = list(rows[0])
        index = next(i for i, row in enumerate(rows) if row['function'] == source.FUNCTION and int(row['offset'], 0) == 0x754)
        for n, (key, value) in enumerate((('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_32:wrong'))):
            bad = copy.deepcopy(rows)
            bad[index][key] = value
            text = io.StringIO(newline='')
            writer = csv.DictWriter(text, fieldnames=fields)
            writer.writeheader()
            writer.writerows(bad)
            table = self.out / ('negative-schedule-guards-%d.csv' % n)
            table.write_text(text.getvalue())
            with self.assertRaises(ValueError):
                source.literal.padded_object(self.root, self.out, self.obj, 'negative-schedule-guard-%d' % n, table)
        self.receipt('padder-controls', effective_actual_rejections=2)

    def test_15_production_predecessors_and_first_images_unchanged(self):
        recovery.freeze(self.root, self.out)
        for key, path in recovery.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes())
        self.harness.test_07_production_baseline_and_callback_preserved()
        source.checkpoint.freeze_after(self.root)
        self.receipt('protected', entries=len(recovery.PATHS), paths=len(set(recovery.PATHS.values())),
                     immutable_first_image_members=10, installed=False, matching_credit=0, production_guards_added=0)

    def test_16_coefficient_before_zero_stores_guest_alias_and_old_rejection(self):
        old = list(struct.unpack_from('>959I', source.projection.sections(
            self.root / recovery.previous.BUILD / (recovery.previous.SELECTED_NAME + '-linked.elf'))['.text'][1]))
        actors = (model.ACTOR, 0x800A19C4 - 0x20, 0x800A19C4 - 0x24, 0x800A19C4 - 0xB8)
        cases, rejected = 0, 0
        for actor, controller_alias, y, phase, pattern, seed in itertools.product(
                actors, (False, True), (-128, -1, 0, 1, 127), (0, 8), (0, 1),
                (0, 0xFFFFFFFF, 0x7FC12345, 0x5A5A5A5A)):
            memory, case = model.fixture(self.rom, actor=actor, phase=phase, pattern=pattern, buttons=0x10, y=y)
            for off, value in ((0x20, -4.), (0x24, -3.), (0xB8, 11.5)):
                model.put(memory, actor + off, model.bits(value))
            pointer = actor + 0x1E if controller_alias else model.INPUT
            model.put(memory, 0x800CC284, pointer)
            model.put(memory, pointer, 0x10, 2)
            model.put(memory, 0x800A19C4, model.bits(-.5 if pattern else .2))
            model.put(memory, pointer + 3, y, 1)
            machines = []
            for words in (self.truth, self.raw_words, self.words, old):
                machine = PitchOracle(words, memory, case, self.connected)
                machine.r = [0, *((seed ^ (i * 0x1234567)) & 0xFFFFFFFF for i in range(1, 32))]
                machine.r[2], machine.r[16], machine.r[29] = 0x800D0000, actor, model.STACK + phase - 128
                machine.f = [(seed ^ (i * 0x01010101)) & 0xFFFFFFFF for i in range(32)]
                machine.f[16] = model.bits(0.)
                machine.lo, machine.condition = seed, bool(seed & 1)
                machine.entry = 0x150F3E00
                with self.assertRaises(PitchStop):
                    machine.run()
                self.assertEqual((machine.current_pc, machine.all_accesses), (0x150F3EBC, 10))
                self.assertFalse(machine.calls)
                machines.append(machine)
            expected = machines[0]
            for machine in machines[1:3]:
                self.assertEqual((machine.memory, machine.f, machine.events, machine.lo, machine.condition),
                                 (expected.memory, expected.f, expected.events, expected.lo, expected.condition))
                self.assertEqual((machine.r[16], machine.r[29]), (actor, model.STACK + phase - 128))
            mismatch = machines[3].memory != expected.memory
            self.assertEqual(mismatch, actor in actors[1:3])
            rejected += mismatch
            cases += 1
        self.assertEqual((cases, rejected), (640, 320))
        self.receipt('coefficient-kernel', cases=cases, old_late_coefficient_read_rejections=rejected,
                     actor_bases=4, aligned_controller_locations=2, signed_Y_values=5, phases=2, RAM_patterns=2, poisoned_seeds=4,
                     access_count_each=10, stopped_before_callback_delay_store=True,
                     actual_retail_complete_RAM_FP_events_LO_condition=True,
                     arbitrary_private_GPR_FCSR_native_alias_or_hardware_acceptance_not_claimed=True)


if __name__ == '__main__':
    unittest.main()
