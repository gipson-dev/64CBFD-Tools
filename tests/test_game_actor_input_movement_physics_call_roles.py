"""Qualify the bounded movement role map, call ABI and new private frontier."""
import copy
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_physics_call_roles as recovery
from tools.tests import test_game_actor_input_movement_remaining_schedules as prior

source, model, original = recovery.source, prior.model, prior.original


class PhysicsStop(Exception):
    pass


class PhysicsOracle(model.Oracle):
    def __init__(self, *args, **kwargs):
        self.defined_roles, self.call_state = set(), None
        super().__init__(*args, **kwargs)

    def execute(self, word):
        if self.current_pc == source.ENTRY + recovery.END * 4:
            raise PhysicsStop
        _, writes = recovery.flags.operands(word)
        self.defined_roles.update(word >> s & 31 for s in writes if word >> s & 31 in recovery.ROLE_MAP)
        return super().execute(word)

    def record_call(self, target):
        self.call_state = (dict(self.memory), tuple(self.r), tuple(self.f), self.lo, self.condition)
        return super().record_call(target)


class MovementPhysicsCallRoleTests(prior.MovementRemainingScheduleTests):
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
        cls.base31, _ = recovery.previous.previous.previous.normalize(cls.raw_words, cls.truth, cls.bindings)
        cls.base28, _ = recovery.previous.previous.previous.previous.previous.normalize(cls.raw_words, cls.truth, cls.bindings)
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
        self.assertEqual(tuple(self.row[k] for k in ('words', 'frame', 'differences', 'normalized_differences')), (959, 128, 134, 88))
        self.assertEqual((self.row['normalized_exact_opening_words'], self.row['normalized_first_PC']), (633, 0x150F3ED8))
        self.assertEqual(self.words[:633], self.truth[:633])
        self.assertEqual((self.row['research_guards'], self.row['new_research_guards'], self.row['production_guards_added'],
                          self.row['matching_credit'], self.row['installed']), (46, 15, 0, 0, False))
        old = self.root / recovery.previous.BUILD
        self.assertEqual((self.out / (recovery.previous.SELECTED_NAME + '.c')).read_bytes(),
                         (old / (recovery.previous.SELECTED_NAME + '.c')).read_bytes())
        self.assertEqual(source.parts(self.obj), source.parts(old / (recovery.previous.SELECTED_NAME + '.o')))
        self.assertEqual((self.out / 'expected-schedule-guards.csv').read_bytes(), (old / 'expected-schedule-guards.csv').read_bytes())
        before = (self.out / 'expected-schedule-guards.csv').read_bytes()
        after = (self.out / 'expected-physics-call-guards.csv').read_bytes()
        self.assertTrue(after.startswith(before))
        rows = list(csv.DictReader(io.StringIO(after.decode())))
        self.assertEqual(len(rows) - len(list(csv.DictReader(io.StringIO(before.decode())))), 15)
        self.assertEqual([i for i in range(959) if self.base31[i] != self.words[i]], list(recovery.CHANGED))
        self.assertEqual(source.parts(self.obj)[1], source.parts(self.padded)[1])
        proof = self.row['physics_call_proof']
        self.assertEqual((proof['kernel_words'], proof['paths']['states'], proof['post_call_liveness']['states']), (149, 127, 1457))
        self.assertEqual(proof['affected_physical_registers'], [3, 10, 11, 12, 13, 14, 15, 24, 25])
        self.receipt('literal', raw_differences=134, normalized_differences=88, exact_prefix=633,
                     new_research_rows=15, total_research_rows=46, production_rows=0, matching_credit=0,
                     reused_32_source_screens_not_recompiled=True, unchanged_C_and_raw_object=True, proof=proof)

    def test_06_private_prefixes_and_complete_existing_paths(self):
        total, states, frontiers, old_rejections, old_prefixes = 0, 0, {}, 0, 0
        for phase, pattern, gate in itertools.product((0, 8), (0, 1), range(5)):
            for position in (100., 2200.):
                for velocity in ((-4.,) if position == 100. else (-40., -30., -29.999998, 30.)):
                    memory, case = model.fixture(self.rom, phase=phase, pattern=pattern, gate=gate,
                                                 held=101, position=position, velocity=velocity)
                    old_frontier = None
                    for cut in range(150):
                        if old_frontier is None:
                            with patch.object(self, 'words', self.base31):
                                old, old_fired = self.pair_at(memory, case, cut)
                            self.assertTrue(old_fired)
                            if model.point.state(old[0]) != model.point.state(old[1]):
                                self.assertEqual([m.current_pc for m in old], [0x150F3C88] * 2)
                                old_frontier = cut
                                old_rejections += 1
                            else:
                                old_prefixes += 1
                        pair, fired = self.pair_at(memory, case, cut)
                        self.assertTrue(fired)
                        if model.point.state(pair[0]) != model.point.state(pair[1]):
                            self.assertEqual([m.current_pc for m in pair], [0x150F3EE0] * 2)
                            self.assertEqual((pair[0].memory, pair[0].f), (pair[1].memory, pair[1].f))
                            different = tuple(i for i, (a, b) in enumerate(zip(pair[0].r, pair[1].r)) if a != b)
                            frontiers[str(different)] = frontiers.get(str(different), 0) + 1
                            self.assertIsNotNone(old_frontier)
                            self.assertLess(old_frontier, cut)
                            break
                        total += 1
                    else:
                        self.fail('No bounded remaining private frontier')
                    states += 1
        ds, dp = self.complete_prefixes(dict(phase=p, pattern=b, gate=g, held=h, disabled=1)
            for p, b, g, h in itertools.product((0, 8), (0, 1), range(5), (0, 100, 101, 124)))
        zs, zp = self.complete_prefixes(dict(phase=p, pattern=b, gate=g, mode=0, nearby=n, depth=d,
            pressed=a, position=-101. if a else 100.) for p, b, g, n, d, a in itertools.product(
                (0, 8), (0, 1), range(5), (0, 101), (0., 100.00001), (0, 0xC000)))
        self.assertEqual((states, total, old_rejections, ds, dp, zs, zp), (100, 8844, 100, 80, 2700, 160, 8320))
        self.assertEqual(old_prefixes, 6700)
        self.receipt('private', active_states=states, equal_fault_prefixes=total, first_PC='0x150F3EE0',
                     different_GPR_sets=frontiers, old_31_row_rejections=old_rejections,
                     old_31_row_equal_prefixes=old_prefixes,
                     disabled_states=ds, disabled_prefixes=dp, mode_zero_states=zs, mode_zero_prefixes=zp,
                     full_private_or_hardware_acceptance_not_claimed=True)

    def test_13_fresh_backend_homes_and_effective_controls(self):
        old = self.root / recovery.previous.BUILD
        record, words, binary = recovery.previous.backend.finish_trace(self.root, old, recovery.previous.SELECTED_NAME, self.body)
        self.assertEqual(words, self.raw_words)
        self.assertEqual(source.parts(old / 'traces' / recovery.previous.SELECTED_NAME / 'baseline.o'), source.parts(self.obj))
        content = recovery.previous.backend.frame.isolated(self.body)
        layout = recovery.previous.check_layout(record, words, content)
        controls = 0
        for pc, _ in recovery.previous.PITCH_SITES:
            bad = list(words)
            bad[(pc - source.ENTRY) // 4] ^= 1
            with self.assertRaises(ValueError):
                recovery.previous.check_layout(record, bad, content)
            controls += 1
        receipt = json.loads((old / 'backend.json').read_text())
        self.assertEqual((record['source_sha'], record['correlated_events'], len(binary), receipt['effective_controls']),
                         ('0b89776bd3c14abb3f18407fb0f45af318c1803add086c3b60960fdce1b52980', 74, 687, 52))
        self.receipt('backend', reused_completed_capture=True, newly_owned_capture=False,
                     source_sha=record['source_sha'], emitter_events=74, AS1_instructions=687,
                     layout=layout, fresh_pitch_controls=controls, prior_unchanged_controls=52,
                     normal_and_observed_and_fresh_object_identical=True)

    def test_14_stale_guard_and_relocation_controls(self):
        rows = list(csv.DictReader(io.StringIO((self.out / 'expected-physics-call-guards.csv').read_text())))
        index = next(i for i, row in enumerate(rows) if row['function'] == source.FUNCTION and int(row['offset'], 0) == 626 * 4)
        for n, (key, value) in enumerate((('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_LO16:wrong'))):
            bad = copy.deepcopy(rows)
            bad[index][key] = value
            text = io.StringIO(newline='')
            writer = csv.DictWriter(text, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(bad)
            table = self.out / ('negative-physics-call-guards-%d.csv' % n)
            table.write_text(text.getvalue())
            with self.assertRaises(ValueError):
                source.literal.padded_object(self.root, self.out, self.obj, 'negative-physics-call-%d' % n, table)
        self.receipt('padder-controls', effective_actual_rejections=2, relocated_delay_slot=True)

    def test_15_production_predecessors_and_first_images_unchanged(self):
        recovery.freeze(self.root, self.out)
        self.harness.test_07_production_baseline_and_callback_preserved()
        source.checkpoint.freeze_after(self.root)
        self.receipt('protected', entries=len(recovery.PATHS), paths=len(set(recovery.PATHS.values())),
                     immutable_first_image_members=10, installed=False, matching_credit=0, production_guards_added=0)

    def test_17_effective_role_CFG_lifetime_and_binding_controls(self):
        controls = 0
        for i in recovery.CHANGED:
            bad = list(self.base31)
            bad[i] ^= 1
            with self.assertRaises(ValueError):
                recovery.prove_roles(bad, self.truth, self.bindings)
            controls += 1
        for offset in recovery.REGION_BINDINGS:
            for changed in ([], [('R_MIPS_32', 'wrong')]):
                with self.assertRaisesRegex(ValueError, 'relocation binding'):
                    recovery.prove_roles(self.base31, self.truth, self.bindings | {offset: changed})
                controls += 1
        for mapping in ({}, {13: 10}, recovery.ROLE_MAP | {3: 11}, recovery.ROLE_MAP | {3: 13}):
            with self.assertRaisesRegex(ValueError, 'injective role map'):
                recovery.prove_roles(self.base31, self.truth, self.bindings, mapping)
            controls += 1
        for index, word, message in (
            (0, 0x27BDFF78, 'extent/frame'), (625, 0x0D416451, 'target'),
            (10, 0x10000000 | (500 - 11), 'Incoming control'),
            (10, 0x0080F809, 'computed'), (495, 0x10000001, 'delay slot'),
            (541, 0x10000000 | ((500 - 542) & 65535), 'Backward'),
            (541, 0x10000000 | (700 - 542), 'exits region'),
            (541, 0x10000000 | (550 - 542), 'delay slot'),
        ):
            bad, truth = list(self.base31), list(self.truth)
            bad[index] = word
            if index in (541,):
                truth[index] = word
            with self.assertRaisesRegex(ValueError, message):
                recovery.prove_roles(bad, truth, self.bindings)
            controls += 1
        with self.assertRaisesRegex(ValueError, 'extent/frame'):
            recovery.prove_roles(self.base31[:-1], self.truth, self.bindings)
        controls += 1
        # Start with an actual read of each role before any definition. Testing
        # the scanner directly prevents literal-correspondence checks masking it.
        for register in recovery.ROLE_MAP:
            bad = list(self.base31)
            bad[478] = 0xA20000A0 | (register << 16)
            with self.assertRaisesRegex(ValueError, 'read before definition at 478'):
                recovery.flags.path_definitions(bad, recovery.START, recovery.END, recovery.ROLE_MAP, True)
            controls += 1
        for register in set(recovery.ROLE_MAP) | set(recovery.ROLE_MAP.values()):
            bad = list(self.base31)
            bad[627] = 0xA20000A0 | (register << 16)
            with self.assertRaisesRegex(ValueError, 'read before definition at 627'):
                recovery.prove_roles(bad, self.truth, self.bindings)
            controls += 1
        for i in (479, 482, 486, 496, 588, 624):
            bad = list(self.base31)
            bad[i] ^= 0x40
            with self.assertRaises(ValueError):
                recovery.prove_roles(bad, self.truth, self.bindings)
            controls += 1
        for name, value in (('START', 479), ('END', 628), ('CHANGED', recovery.CHANGED[:-1])):
            with patch.object(recovery, name, value), self.assertRaises(ValueError):
                recovery.prove_roles(self.base31, self.truth, self.bindings)
            controls += 1
        self.receipt('role-controls', effective_controls=controls, local_states=127, continuation_states=1457,
                     likely_annulment_modeled=True, injective_not_closed=True,
                     both_sides_defined_before_liveout_read=True, no_ABI_clobber_shortcut=True)

    def test_18_poisoned_kernel_pre_call_roles_and_effective_provider_mutations(self):
        scenarios = (
            (0, 0, 0, -128, -40., 0.), (101, 0, 0x10, -1, -30., 75.),
            (0, 1, 0x10, 0, -4., 100.), (101, 1, 0x10, 1, 0., 201.),
            (0, 0, 0x10, 127, 30., 2200.), (101, 0, 0, 127, 30.00001, 75.),
            (0, 1, 0, -1, -29.999998, 0.), (101, 1, 0x10, -128, 75., 201.),
        )
        cases, fired, visited, defined = 0, 0, set(), set()
        affected = set(recovery.ROLE_MAP) | set(recovery.ROLE_MAP.values())
        for actor, alias, scenario, phase, seed, mutation in itertools.product(
                (model.ACTOR, 0x800A19C4 - 0x20), (False, True), scenarios, (0, 8),
                (0, 0xFFFFFFFF, 0x5A5A5A5A), (0, 2, 8)):
            held, below, buttons, y, velocity, depth = scenario
            memory, case = model.fixture(self.rom, actor=actor, phase=phase, pattern=seed & 1,
                held=held, below=below, buttons=buttons, y=y, velocity=velocity, depth=depth, mutation=mutation)
            pointer = actor + 0x1E if alias else model.INPUT
            model.put(memory, 0x800CC284, pointer)
            model.put(memory, pointer, buttons, 2)
            model.put(memory, pointer + 3, y, 1)
            model.put(memory, model.STACK + phase - 128 + 0x6C, model.bits(2.5 if below else -2.5))
            machines = []
            for words in (self.truth, self.base31, self.words):
                machine = PhysicsOracle(words, memory, case, self.connected)
                machine.r = [0, *((seed ^ (i * 0x1234567)) & 0xFFFFFFFF for i in range(1, 32))]
                machine.r[1], machine.r[16], machine.r[29] = 0x800A0000, actor, model.STACK + phase - 128
                machine.f = [(seed ^ (i * 0x01010101)) & 0xFFFFFFFF for i in range(32)]
                machine.f[8], machine.f[14], machine.f[18] = model.bits(.005493164), model.bits(1.5), model.bits(-123.)
                machine.lo, machine.condition = seed, bool(seed & 1)
                machine.entry = source.ENTRY + recovery.START * 4
                with self.assertRaises(PhysicsStop):
                    machine.run()
                self.assertEqual(machine.calls, [(0x15059140, (actor,))])
                self.assertEqual(machine.fired, [(0x15059140, 1)] if mutation else [])
                self.assertEqual(model.read(machine.call_state[0], 0x800CBDD3, 1), 1)
                if mutation:
                    address = actor + (0x28 if mutation == 2 else 0x25C)
                    self.assertNotEqual(model.read(machine.call_state[0], address), model.read(machine.memory, address))
                machines.append(machine)
            expected, old, normalized = machines
            for machine in (old, normalized):
                self.assertEqual((machine.memory, machine.r, machine.f, machine.events, machine.lo, machine.condition),
                                 (expected.memory, expected.r, expected.f, expected.events, expected.lo, expected.condition))
                self.assertEqual((machine.call_state[0], machine.call_state[2:]),
                                 (expected.call_state[0], expected.call_state[2:]))
            self.assertEqual(normalized.call_state, expected.call_state)
            for r in old.defined_roles:
                self.assertEqual(old.call_state[1][r], expected.call_state[1][recovery.ROLE_MAP[r]])
            for r in set(range(32)) - affected:
                self.assertEqual(old.call_state[1][r], expected.call_state[1][r])
            visited.update(expected.visits)
            defined.update(old.defined_roles)
            fired += bool(mutation)
            cases += 1
        self.assertEqual((cases, fired), (576, 384))
        self.assertEqual(defined, set(recovery.ROLE_MAP))
        self.receipt('physics-kernel', cases=cases, effective_provider_mutations=fired, actor_bases=2,
                     controller_locations=2, scenarios=8, phases=2, poisoned_seeds=3, provider_modes=[0, 2, 8],
                     visited_kernel_words=len(visited), pre_call_full_normalized_state_equal=True,
                     raw_role_correspondence_and_identity_checked_before_clobber=True,
                     complete_post_call_RAM_GPR_FP_events_LO_condition_equal=True,
                     arbitrary_private_FCSR_hardware_or_gameplay_acceptance_not_claimed=True)


if __name__ == '__main__':
    unittest.main()
