"""Qualify complete movement matching, call-invalidated roles and address rebases."""
import copy
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_tail_match as recovery
from tools.tests import test_game_actor_input_movement_physics_call_roles as prior
from tools.tests.test_game_actor_input_movement_scalar_lifetimes import CountOracle

source, model, original = recovery.source, prior.model, prior.original


class TailStop(Exception):
    pass


class TailOracle(CountOracle):
    def __init__(self, *args, seed=0, stop=954, **kwargs):
        self.seed, self.stop, self.boundaries = seed, stop, []
        super().__init__(*args, **kwargs)

    def execute(self, word):
        if self.current_pc == source.ENTRY + self.stop * 4:
            raise TailStop
        return super().execute(word)

    def record_call(self, target):
        self.boundaries.append((target, dict(self.memory), tuple(self.f), self.lo, self.condition))
        return super().record_call(target)

    def hook(self, target):
        super().hook(target)
        for r in recovery.ROLE_MAP:
            self.r[r] = (self.seed ^ target ^ (r * 0x1234567) ^ len(self.calls)) & 0xFFFFFFFF


class MovementTailMatchTests(prior.MovementPhysicsCallRoleTests):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / recovery.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = recovery.qualify(cls.root, cls.out)
        cls.body = recovery.previous.previous.selected_body()
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>959I', cls.rom, source.ROM))
        cls.connected = {0x150F34A0 + i * 4: w for i, w in enumerate(struct.unpack_from('>21I', cls.rom, 0x120950))}
        cls.bindings = source.parts(cls.obj)[1]
        normalization = prior.recovery.previous.previous.previous
        cls.base31, _ = normalization.normalize(cls.raw_words, cls.truth, cls.bindings)
        cls.base28, _ = normalization.previous.previous.normalize(cls.raw_words, cls.truth, cls.bindings)
        cls.base46, _ = recovery.previous.prove_roles(cls.base31, cls.truth, cls.bindings)
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
        self.assertEqual(tuple(self.row[k] for k in ('words', 'frame', 'differences', 'normalized_differences')), (959, 128, 134, 0))
        self.assertEqual(self.words, self.truth)
        self.assertEqual((self.row['normalized_exact_opening_words'], self.row['normalized_first_PC']), (959, None))
        self.assertEqual((self.row['research_guards'], self.row['new_research_guards'], self.row['installed'], self.row['matching_credit']), (134, 88, False, 0))
        old = self.root / recovery.previous.BUILD
        self.assertEqual(source.parts(self.obj), source.parts(old / 'dataflow-423.o'))
        self.assertEqual((self.out / 'dataflow-423.c').read_bytes(), (old / 'dataflow-423.c').read_bytes())
        before = (self.out / 'expected-physics-call-guards.csv').read_bytes()
        after = (self.out / 'expected-tail-guards.csv').read_bytes()
        self.assertTrue(after.startswith(before))
        self.assertEqual(len(list(csv.DictReader(io.StringIO(after.decode())))) - len(list(csv.DictReader(io.StringIO(before.decode())))), 88)
        expected_bindings = dict(self.bindings)
        expected_bindings[2980], expected_bindings[2984] = self.bindings[2984], self.bindings[2980]
        self.assertEqual(source.parts(self.padded)[1], expected_bindings)
        self.assertEqual(self.row['normalized_raw_sha'], '48bbb4778e4843846a24a556baf564bd5634aad2ab19e9bb88648d24b98c88a0')
        self.assertEqual(self.row['normalized_target_changed_bytes'], 163)
        proof = self.row['tail_proof']
        self.assertEqual((proof['kernel_words'], proof['paths']['states'], proof['post_call_liveness']['states']), (327, 1860, 4))
        self.receipt('literal', raw_differences=134, normalized_differences=0, exact_words=959,
                     total_research_rows=134, new_research_rows=88, production_rows=0, matching_credit=0,
                     unchanged_C_and_raw=True, previous_32_screens_reused=True, proof=proof)

    def complete_prefixes(self, specs):
        finished, prefixes = 0, 0
        for spec in specs:
            memory, case = model.fixture(self.rom, **spec)
            for cut in range(512):
                pair, fired = self.pair_at(memory, case, cut)
                self.assertEqual(model.point.state(pair[0]), model.point.state(pair[1]), (spec, cut))
                if not fired:
                    finished += 1
                    break
                prefixes += 1
            else:
                self.fail('Complete movement path exceeds fault bound')
        return finished, prefixes

    def test_06_private_prefixes_and_complete_existing_paths(self):
        active = []
        old_total, rejections = 0, 0
        for phase, pattern, gate in itertools.product((0, 8), (0, 1), range(5)):
            for position in (100., 2200.):
                for velocity in ((-4.,) if position == 100. else (-40., -30., -29.999998, 30.)):
                    spec = dict(phase=phase, pattern=pattern, gate=gate, held=101, position=position, velocity=velocity)
                    active.append(spec)
                    memory, case = model.fixture(self.rom, **spec)
                    with patch.object(self, 'words', self.base46):
                        for cut in range(150):
                            pair, fired = self.pair_at(memory, case, cut)
                            self.assertTrue(fired)
                            if model.point.state(pair[0]) != model.point.state(pair[1]):
                                self.assertEqual([m.current_pc for m in pair], [0x150F3EE0] * 2)
                                rejections += 1
                                break
                            old_total += 1
                        else:
                            self.fail('Old tail mismatch not exercised')
        states, total = self.complete_prefixes(active)
        ds, dp = self.complete_prefixes(dict(phase=p, pattern=b, gate=g, held=h, disabled=1)
            for p, b, g, h in itertools.product((0, 8), (0, 1), range(5), (0, 100, 101, 124)))
        zs, zp = self.complete_prefixes(dict(phase=p, pattern=b, gate=g, mode=0, nearby=n, depth=d,
            pressed=a, position=-101. if a else 100.) for p, b, g, n, d, a in itertools.product(
                (0, 8), (0, 1), range(5), (0, 101), (0., 100.00001), (0, 0xC000)))
        extra = [dict(held=0, pressed=0x2000, count=n, depth=0., mutation=m, phase=p)
                 for n, m, p in itertools.product((0, 4, 5, 6), (0, 3, 6, 9), (0, 8))]
        extra.extend(dict(held=101, control=2, depth=d, mutation=m) for d, m in itertools.product((0., 75.), range(10)))
        es, ep = self.complete_prefixes(extra)
        self.assertEqual((states, total, rejections, old_total, ds, dp, zs, zp, es, ep),
                         (100, 11276, 100, 8844, 80, 2700, 160, 8320, 52, 8333))
        self.receipt('private', active_states=states, active_equal_prefixes=total, complete_active=True,
                     old_46_row_rejections=rejections, old_46_row_equal_prefixes=old_total,
                     disabled_states=ds, disabled_prefixes=dp, mode_zero_states=zs, mode_zero_prefixes=zp,
                     extra_spawn_release_states=es, extra_prefixes=ep, arbitrary_FCSR_or_hardware_not_claimed=True)

    def test_14_stale_guard_and_relocation_controls(self):
        rows = list(csv.DictReader(io.StringIO((self.out / 'expected-tail-guards.csv').read_text())))
        index = next(i for i, row in enumerate(rows) if row['function'] == source.FUNCTION and int(row['offset'], 0) == 745 * 4)
        for n, (key, value) in enumerate((('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_LO16:wrong'))):
            bad = copy.deepcopy(rows)
            bad[index][key] = value
            text = io.StringIO(newline='')
            writer = csv.DictWriter(text, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(bad)
            table = self.out / ('negative-tail-guards-%d.csv' % n)
            table.write_text(text.getvalue())
            with self.assertRaises(ValueError):
                source.literal.padded_object(self.root, self.out, self.obj, 'negative-tail-%d' % n, table)
        self.receipt('padder-controls', effective_actual_rejections=2, address_pair_row=True)

    def test_15_production_predecessors_and_first_images_unchanged(self):
        recovery.freeze(self.root, self.out)
        self.harness.test_07_production_baseline_and_callback_preserved()
        source.checkpoint.freeze_after(self.root)
        self.receipt('protected', entries=len(recovery.PATHS), paths=len(set(recovery.PATHS.values())),
                     immutable_first_image_members=10, installed=False, matching_credit=0, production_guards_added=0)

    def test_19_tail_permutation_call_reset_loop_and_effective_controls(self):
        controls = 0
        for i in range(recovery.START, recovery.END):
            if self.base46[i] == self.truth[i]:
                continue
            bad = list(self.base46)
            bad[i] ^= 1
            with self.assertRaises(ValueError):
                recovery.prove_tail(bad, self.truth, self.bindings)
            controls += 1
        for offset in (k for k in self.bindings if recovery.START * 4 <= k < recovery.END * 4):
            for changed in ([], [('R_MIPS_32', 'wrong')]):
                with self.assertRaisesRegex(ValueError, 'relocation binding'):
                    recovery.prove_tail(self.base46, self.truth, self.bindings | {offset: changed})
                controls += 1
        for mapping in ({}, {8: 9}, recovery.ROLE_MAP | {11: 10}, recovery.ROLE_MAP | {11: 16}):
            with self.assertRaisesRegex(ValueError, 'closed permutation'):
                recovery.prove_tail(self.base46, self.truth, self.bindings, mapping)
            controls += 1
        for index, word, message in (
            (0, 0x27BDFF78, 'extent/frame'), (100, 0x10000000 | (650 - 101), 'Incoming control'),
            (100, 0x0080F809, 'computed'), (633, 0x10000001, 'delay slot'),
            (638, 0x10000000 | ((630 - 639) & 65535), 'backedge'),
            (638, 0x10000000 | (955 - 639), 'exits region'),
            (638, 0x10000000 | (747 - 639), 'splits independent'),
            (638, 0x10000000 | (746 - 639), 'splits independent'),
            (745, 0x24A2C5FC, 'independent address'), (746, 0x2445121C, 'independent address'),
        ):
            bad = list(self.base46)
            bad[index] = word
            with self.assertRaisesRegex(ValueError, message):
                recovery.prove_tail(bad, self.truth, self.bindings)
            controls += 1
        for i in recovery.CALLS:
            bad = list(self.base46)
            bad[i] ^= 1
            with self.assertRaisesRegex(ValueError, 'call target'):
                recovery.prove_tail(bad, self.truth, self.bindings)
            controls += 1
        for i in (627, *(i + 2 for i in recovery.CALLS if i != 952)):
            for register in recovery.ROLE_MAP:
                bad = list(self.base46)
                bad[i] = 0xA20000A0 | (register << 16)
                with self.assertRaisesRegex(ValueError, 'read before definition at %d' % i):
                    recovery.paths(bad, recovery.ROLE_MAP)
                controls += 1
        for register in recovery.ROLE_MAP:
            bad = list(self.base46)
            bad[954] = 0xA20000A0 | (register << 16)
            truth = list(self.truth)
            truth[954] = bad[954]
            with self.assertRaisesRegex(ValueError, 'before definition'):
                recovery.prove_tail(bad, truth, self.bindings)
            controls += 1
        for name, value in (('START', 628), ('END', 955), ('PAIR', (744, 745))):
            with patch.object(recovery, name, value), self.assertRaisesRegex(ValueError, 'proof boundaries'):
                recovery.prove_tail(self.base46, self.truth, self.bindings)
            controls += 1
        with self.assertRaisesRegex(ValueError, 'extent/frame'):
            recovery.prove_tail(self.base46[:-1], self.truth, self.bindings)
        controls += 1
        self.receipt('tail-controls', effective_controls=controls, roles=10, bindings=55, calls=9,
                     post_call_read_controls=80, source_livein_controls=10, liveout_controls=10,
                     loop_backedge=[756, 749], paths=1860, continuation_states=4)

    def test_20_tail_poisoned_callee_clobbers_and_full_ABI_packets(self):
        specs = [dict(), dict(nearby=101, held=0), dict(held=101, control=2),
                 dict(held=0, pressed=0x2000, count=4), dict(held=0, pressed=0x2000, count=5),
                 dict(held=101, depth=-1., velocity=-40.), dict(held=0, depth=-1., position=-101.),
                 dict(held=101, below=1, buttons=0x10), dict(held=0, below=0, depth=-1., buttons=0x4000)]
        cases, calls, visited, fired = 0, set(), set(), set()
        for spec, phase, pattern, seed, mutation in itertools.product(specs, (0, 8), (0, 1),
                (0, 0xFFFFFFFF, 0x5A5A5A5A), (0, 6, 7)):
            memory, case = model.fixture(self.rom, **dict(spec, phase=phase, pattern=pattern, mutation=mutation))
            model.put(memory, 0x800CC284, model.INPUT)
            model.put(memory, 0x800CC288, case['pressed'])
            model.put(memory, model.STACK + phase - 128 + 0x58, model.bits(0.))
            machines = []
            for words in (self.truth, self.base46, self.words):
                machine = TailOracle(words, memory, case, self.connected, seed=seed)
                machine.r = [0, *((seed ^ (i * 0x1234567)) & 0xFFFFFFFF for i in range(1, 32))]
                machine.r[16], machine.r[29] = case['actor'], model.STACK + phase - 128
                machine.f = [model.bits((i - 16) * .125) for i in range(32)]
                machine.lo, machine.condition = seed, bool(seed & 1)
                machine.entry = source.ENTRY + recovery.START * 4
                with self.assertRaises(TailStop):
                    machine.run()
                machines.append(machine)
            expected = machines[0]
            for machine in machines[1:]:
                self.assertEqual((machine.memory, machine.r, machine.f, machine.events, machine.lo, machine.condition,
                                  machine.calls, machine.boundaries, machine.fired),
                                 (expected.memory, expected.r, expected.f, expected.events, expected.lo, expected.condition,
                                  expected.calls, expected.boundaries, expected.fired))
            calls.update(target for target, _ in expected.calls)
            fired.update(case['mutation'] for _ in expected.fired)
            visited.update(expected.visits)
            cases += 1
        self.assertEqual(cases, 324)
        self.assertEqual(calls, {int(name[5:], 16) for name in recovery.CALLS.values()})
        self.assertEqual(fired, {6, 7})
        self.receipt('tail-kernel', cases=cases, effective_provider_modes=sorted(fired), calls=sorted(calls),
                     visited_words=len(visited), poisoned_caller_saved_roles_after_every_call=True,
                     complete_RAM_GP_FP_events_LO_condition_and_pre_call_ABI_boundaries=True,
                     FCSR_hardware_or_arbitrary_unpassed_callee_register_acceptance_not_claimed=True)

    def test_21_independent_bound_symbol_rebases_and_actual_counter_loop(self):
        cases = 0
        for base, count, phase in itertools.product((0x80107FFC, 0x80518000, 0x800FF000), (1, 3, 24, 25), (0, 8)):
            symbols = source.nm_anchors(self.root / 'conker/build/conker.us.elf')
            end = base + count * 0x32C
            symbols.update(D_800CC5FC=base, D_800D121C=end)
            memory, case = model.fixture(self.rom, phase=phase)
            wanted = 0
            for i in range(count):
                active, kind = int(i % 2 == 0), 0x25 if i % 3 != 1 else 0x24
                model.put(memory, base + i * 0x32C, active)
                model.put(memory, base + i * 0x32C + 4, kind, 1)
                wanted += active and kind == 0x25
            machines = []
            for label, obj in (('raw', self.obj), ('normalized', self.padded)):
                words = source.linked(self.root, self.out, obj, 'bounds-%d-%s' % (cases, label), symbols=symbols)
                machine = TailOracle(words, memory, case, self.connected, stop=758)
                machine.r[3], machine.r[16], machine.r[29] = 0, case['actor'], model.STACK + phase - 128
                machine.entry = source.ENTRY + 743 * 4
                with self.assertRaises(TailStop):
                    machine.run()
                self.assertEqual((machine.r[3], machine.r[2], machine.r[5]), (wanted, end, end))
                self.assertEqual(machine.active_reads, [base + i * 0x32C for i in range(count)])
                self.assertFalse(machine.calls)
                machines.append(machine)
            self.assertEqual((machines[0].memory, machines[0].events, machines[0].lo, machines[0].condition),
                             (machines[1].memory, machines[1].events, machines[1].lo, machines[1].condition))
            cases += 1
        self.assertEqual(cases, 24)
        self.receipt('bound-rebases', cases=cases, linked_objects=48, high_carry_and_signed_low_halves=True,
                     record_counts=[1, 3, 24, 25], counter_outputs_and_access_order=True,
                     actual_relocation_moves_not_literal_address_patches=True,
                     complete_data_or_hardware_rebase_acceptance_not_claimed=True)


if __name__ == '__main__':
    unittest.main()
