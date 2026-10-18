"""Complete movement qualification for a bounded, uninstalled turn-role map."""
import ctypes
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_recovery as source
from tools.experiments import game_actor_input_movement_turn_argument as recovery
from tools.tests import test_game_actor_input_movement_float_lifetimes as prior

model = prior.model


class KernelStop(Exception):
    pass


class KernelOracle(model.Oracle):
    def hook(self, target):
        if target != 0x150599C8:
            raise AssertionError('Unexpected turn-kernel provider')
        raise KernelStop


class MovementTurnArgumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / recovery.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = recovery.qualify(cls.root, cls.out)
        cls.body = recovery.previous.selected_body()
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>959I', cls.rom, source.ROM))
        cls.connected = {0x150F34A0 + i * 4: w for i, w in enumerate(struct.unpack_from('>21I', cls.rom, 0x120950))}
        cls.bindings = source.parts(cls.obj)[1]
        cls.harness = prior.original.MovementRecoveryTests('test_02_all_three_paths_and_numeric_boundaries')
        for name in ('root', 'out', 'rom', 'words', 'truth', 'connected'):
            setattr(cls.harness, name, getattr(cls, name))
        cls.harness.obj = cls.padded
        cls.harness.coverage, cls.harness.providers = set(), set()
        compare = cls.harness.compare

        def three_way(spec, images=None, entry=source.ENTRY):
            return compare(spec, images or (cls.truth, cls.raw_words, cls.words), entry)

        cls.harness.compare = three_way

    def receipt(self, name, **data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def test_01_complete_controls_real_padder_and_no_production_guard(self):
        self.assertEqual((len(self.words), self.row['frame'], self.row['differences'], self.row['normalized_differences']),
                         (959, 128, 392, 385))
        self.assertEqual((self.row['normalized_exact_opening_words'], self.row['normalized_first_PC']), (406, 0x150F3B4C))
        self.assertEqual(self.words[:406], self.truth[:406])
        self.assertEqual(self.row['normalized_raw_sha'], recovery.NORMALIZED_SHA)
        self.assertEqual(self.row['normalized_target_changed_bytes'], 10)
        self.assertTrue(self.row['target_relocations_unchanged'])
        self.assertEqual([(i * 4, a, b) for i, (a, b) in enumerate(zip(self.raw_words, self.words)) if a != b], list(recovery.GUARDS))
        self.assertEqual((self.row['research_guards'], self.row['production_guards_added'], self.row['matching_credit']), (7, 0, 0))
        before = (self.out / 'before-record_gate_owner').read_text()
        rows = []
        for name, body in recovery.all_forms():
            self.assertEqual((self.out / (name + '.c')).read_text(), source.recovered_owner(before, body), name)
            raw, _ = source.parts(self.out / (name + '.o'))
            audit = json.loads((self.out / (name + '-audit.json')).read_text())
            words = list(struct.unpack_from('>%dI' % (len(raw) // 4),
                         source.projection.sections(self.out / (name + '-linked.elf'))['.text'][1]))
            self.assertEqual((len(words), (-words[0]) & 65535, sum(a != b for a, b in zip(words, self.truth))),
                             tuple(audit[k] for k in ('words', 'frame', 'differences')))
            self.assertEqual(audit['raw_neighbors'], 11)
            if len(words) > 959:
                self.assertTrue(audit['padder_rejected'])
            else:
                self.assertEqual(audit['padded_neighbors'], 11)
            rows.append(dict(name=name, words=len(words), differences=audit['differences'], raw_sha=audit['raw_sha']))
        self.assertEqual((len(rows), sum(r['words'] > 959 for r in rows)), (10, 4))
        old = (self.out / 'before-guards').read_bytes()
        generated = (self.out / 'expected-turn-guards.csv').read_bytes()
        self.assertTrue(generated.startswith(old))
        self.assertEqual(len(list(csv.DictReader(io.StringIO(generated.decode())))) - len(list(csv.DictReader(io.StringIO(old.decode())))), 7)
        self.receipt('source-controls', complete_forms=10, overflow_rejections=4, rows=rows,
                     raw_C_unchanged=True, research_only_normalization_words=7, no_trimming=True)

    def test_02_effective_role_entry_opcode_and_guard_table_controls(self):
        recovery.prove_roles(self.raw_words, self.truth, self.bindings)
        count = 0
        for offset, _, replacement in recovery.GUARDS:
            bad = list(self.raw_words)
            bad[offset // 4] ^= 1
            with self.assertRaises(ValueError):
                recovery.prove_roles(bad, self.truth, self.bindings)
            count += 1
            with self.assertRaises(ValueError):
                recovery.prove_roles(self.raw_words, self.truth, self.bindings | {offset: [('R_MIPS_32', 'bad')]})
            count += 1
            guards = tuple((o, a, replacement ^ 1 if o == offset else b) for o, a, b in recovery.GUARDS)
            with patch.object(recovery, 'GUARDS', guards):
                with self.assertRaises(ValueError):
                    recovery.prove_roles(self.raw_words, self.truth, self.bindings)
            count += 1
        for mapping in ({10: 24}, {10: 24, 24: 24, 14: 15, 15: 25},
                        {10: 16, 24: 11, 14: 15, 15: 25}, {10: 24, 24: 11, 14: 15, 15: 8}):
            with self.assertRaises(ValueError):
                recovery.prove_roles(self.raw_words, self.truth, self.bindings, mapping)
            count += 1
        mutations = (
            (100, (4 << 26) | (recovery.START + 2 - 100 - 1), 'Incoming control'),
            (100, (2 << 21) | (31 << 11) | 9, 'computed'),
            (363, (14 << 21) | (4 << 11) | 37, 'before definition'),
            (363, (16 << 21) | (11 << 11) | 37, 'collides'),
            (363, 12, 'Unsupported'),
            (364, self.raw_words[364] ^ 64, 'correspondence'),
            (365, self.raw_words[365] ^ 64, 'correspondence'),
            (recovery.END - 2, self.raw_words[recovery.END - 2] ^ 1, 'callback'),
            (0, self.raw_words[0] ^ 4, 'frame'),
        )
        for index, word, message in mutations:
            bad = list(self.raw_words)
            bad[index] = word
            with self.assertRaisesRegex(ValueError, message):
                recovery.prove_roles(bad, self.truth, self.bindings)
            count += 1
        with self.assertRaises(ValueError):
            recovery.prove_roles(self.raw_words[:-1], self.truth, self.bindings)
        count += 1
        before = (self.out / 'before-guards').read_bytes().decode()
        for text in (before.rstrip('\r\n'), recovery.guard_text(before), before.replace('filename,', 'wrong,')):
            with self.assertRaises(ValueError):
                recovery.guard_text(text)
            count += 1
        self.assertGreaterEqual(count, 35)
        self.receipt('role-controls', effective_controls=count, structural_role_and_actual_retail_checks=True)

    def test_03_kernel_poison_values_aliases_and_actual_callback_boundary(self):
        affected = set(recovery.ROLE_MAP) | set(recovery.ROLE_MAP.values())
        protected = [i for i in range(32) if i not in affected]
        actors = (model.ACTOR, 0x800D1550 - 0xC4, 0x800A1994 - 0xC4)
        seeds = (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xA5A5A5A5, 0x5A5A5A5A, 0x01020304,
                 0xDEADBEEF, 0x10000, 0xFFFF, 0x8000, 0x7FC12345, 0xFF800000, 0x00800000, 0x3F800000)
        count = 0
        for actor, seed, stick, pattern in itertools.product(actors, seeds, (-128, -1, 0, 1, 127), (0, 1)):
            memory, case = model.fixture(self.rom, actor=actor, phase=pattern * 8, pattern=pattern)
            pair = [KernelOracle(w, memory, case, self.connected) for w in (self.raw_words, self.words)]
            for machine in pair:
                machine.r = [0, *((seed ^ (i * 0x1234567)) & 0xFFFFFFFF for i in range(1, 32))]
                machine.r[1], machine.r[4], machine.r[16], machine.r[29] = 0x800D0000, actor, actor, model.STACK + pattern * 8
                machine.f = [(seed ^ (i * 0x01010101)) & 0xFFFFFFFF for i in range(32)]
                machine.f[18] = stick & 0xFFFFFFFF
                machine.lo, machine.condition = seed, bool(pattern)
                machine.entry = source.ENTRY + recovery.START * 4
                with self.assertRaises(KernelStop):
                    machine.run()
                self.assertEqual(machine.calls[-1][0], 0x150599C8)
                self.assertEqual(machine.r[31], source.ENTRY + recovery.END * 4)
            left, right = pair
            self.assertEqual(left.memory, right.memory)
            self.assertEqual(left.f, right.f)
            self.assertEqual(left.calls, right.calls)
            self.assertEqual(left.observations, right.observations)
            self.assertEqual(left.events, right.events)
            self.assertEqual((left.lo, left.condition, left.all_accesses), (right.lo, right.condition, right.all_accesses))
            self.assertEqual([left.r[i] for i in protected], [right.r[i] for i in protected])
            for register, replacement in recovery.ROLE_MAP.items():
                self.assertEqual(left.r[register], right.r[replacement])
            count += 1
        self.assertEqual(count, 480)
        self.receipt('kernel', complete_cases=count, aligned_actor_aliases=3, poisoned_GPR_FPR_seeds=16,
                     signed_stick_values=5, stack_phases=2, actual_call_entry_observed=True,
                     complete_memory_FP_events_and_declared_packet_equal=True,
                     raw_private_GPR_or_hardware_FCSR_equivalence_not_claimed=True)

    test_04_complete_three_way_public_and_cap_boundaries = prior.MovementFloatLifetimeTests.test_04_complete_public_corpus_and_fired_cap_boundaries
    pair_at = prior.MovementFloatLifetimeTests.pair_at
    complete_prefixes = prior.MovementFloatLifetimeTests.complete_prefixes

    def test_05_extended_normalized_prefixes_and_earlier_raw_rejection(self):
        cuts = (55, 63, 54, 56, 57)
        totals = {100.: 0, 2200.: 0}
        states = 0
        for phase, pattern, gate in itertools.product((0, 8), (0, 1), range(5)):
            for position in (100., 2200.):
                velocities = (-4.,) if position == 100. else (-40., -30., -29.999998, 30.)
                for velocity in velocities:
                    memory, case = model.fixture(self.rom, phase=phase, pattern=pattern, gate=gate,
                                                 held=101, position=position, velocity=velocity)
                    extra = 0 if position == 100. else 2 if velocity <= -30. else 3
                    limit = cuts[gate] + extra
                    for cut in range(limit + 1):
                        pair, fired = self.pair_at(memory, case, cut)
                        self.assertTrue(fired)
                        same = model.point.state(pair[0]) == model.point.state(pair[1])
                        self.assertEqual(same, cut < limit)
                        if same:
                            totals[position] += 1
                        else:
                            self.assertEqual(pair[0].memory, pair[1].memory)
                            self.assertEqual(pair[0].f, pair[1].f)
                            self.assertEqual([x.current_pc for x in pair], [0x150F3B58] * 2)
                            self.assertEqual([i for i, (a, b) in enumerate(zip(pair[0].r, pair[1].r)) if a != b], [10, 13])
                    with patch.object(self, 'words', self.raw_words):
                        pair, fired = self.pair_at(memory, case, limit - 13)
                        self.assertTrue(fired)
                        self.assertNotEqual(model.point.state(pair[0]), model.point.state(pair[1]))
                        self.assertEqual([x.current_pc for x in pair], [0x150F3AB8] * 2)
                    states += 1
        self.assertEqual((states, totals), (100, {100.: 1140, 2200.: 4760}))
        disabled = (dict(phase=p, pattern=b, gate=g, held=h, disabled=1)
                    for p, b, g, h in itertools.product((0, 8), (0, 1), range(5), (0, 100, 101, 124)))
        ds, dp = self.complete_prefixes(disabled)
        zero = (dict(phase=p, pattern=b, gate=g, mode=0, nearby=n, depth=d, pressed=a, position=-101. if a else 100.)
                for p, b, g, n, d, a in itertools.product((0, 8), (0, 1), range(5), (0, 101), (0., 100.00001), (0, 0xC000)))
        zs, zp = self.complete_prefixes(zero)
        self.assertEqual((ds, dp, zs, zp), (80, 2700, 160, 8320))
        self.receipt('private', normalized_active_states=100, equal_normalized_prefixes=5900,
                     earlier_raw_rejections=100, low_position_prefixes=1140, high_position_prefixes=4760,
                     first_PC='0x150F3B58', different_GPRs=[10, 13], all_FPR_memory_PC_LO_condition_agree_at_gap=True,
                     disabled_complete_states=ds, disabled_fault_prefixes=dp,
                     mode_zero_complete_states=zs, mode_zero_fault_prefixes=zp,
                     full_opaque_provider_or_hardware_acceptance_not_claimed=True)

    test_06_native_and_actual_normalized_rebases_and_aliases = prior.MovementFloatLifetimeTests.test_06_native32_rebases_aliases_and_cap_boundaries

    def test_07_revalidate_unchanged_raw_compiler_capture_not_a_new_trace(self):
        record, words, binary = recovery.previous.finish_trace(self.root, self.root / recovery.previous.BUILD)
        self.assertEqual(words, self.raw_words)
        work = self.root / recovery.previous.BUILD / 'traces' / recovery.previous.SELECTED_NAME
        self.assertEqual(source.parts(work / 'baseline.o'), source.parts(self.obj))
        layout = recovery.previous.check_layout(record, words, recovery.previous.frame.isolated(self.body))
        self.assertEqual((record['correlated_events'], len(binary)), (74, 684))
        self.receipt('backend', reused_and_revalidated_prior_capture=True, newly_owned_capture=False,
                     raw_compiler_output_identical=True, raw_layout=layout, emitter_events=74, AS1_instructions=684,
                     normalized_object_is_post_compile_research_not_claimed_AS1_output=True)

    def test_08_all_production_data_guards_and_checkpoints_unchanged(self):
        recovery.freeze(self.root, self.out)
        for key, path in recovery.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes())
        self.harness.test_07_production_baseline_and_callback_preserved()
        source.checkpoint.freeze_after(self.root)
        self.receipt('protected', entries=len(recovery.PATHS), paths=len(set(recovery.PATHS.values())),
                     immutable_first_image_members=10, installed=False, production_guards_added=0, matching_credit=0)


if __name__ == '__main__':
    unittest.main()
