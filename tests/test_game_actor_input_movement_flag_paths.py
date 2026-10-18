"""Qualify complete movement C and a private branch-sensitive role proof."""
import ctypes
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

from tools.experiments import game_actor_input_movement_recovery as source
from tools.experiments import game_actor_input_movement_flag_paths as recovery
from tools.tests import test_game_actor_input_movement_turn_argument as prior

model = prior.model


class KernelStop(Exception):
    pass


class KernelOracle(model.Oracle):
    def hook(self, target):
        if target != 0x1505A3A8:
            raise AssertionError('Unexpected flag-kernel provider')
        raise KernelStop


class MovementFlagPathTests(unittest.TestCase):
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
        cls.harness = prior.prior.original.MovementRecoveryTests('test_02_all_three_paths_and_numeric_boundaries')
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

    def test_01_sources_actual_padder_neighbors_relocations_and_credit(self):
        self.assertEqual(tuple(self.row[k] for k in ('words', 'frame', 'differences', 'normalized_differences')),
                         (959, 128, 389, 361))
        self.assertEqual((self.row['normalized_exact_opening_words'], self.row['normalized_first_PC']), (469, 0x150F3C48))
        self.assertEqual(self.words[:469], self.truth[:469])
        self.assertEqual((self.row['research_guards'], self.row['normalized_target_changed_bytes']), (28, 36))
        self.assertEqual((self.row['production_guards_added'], self.row['matching_credit'], self.row['installed']), (0, 0, False))
        self.assertEqual(self.row['normalized_raw_sha'], recovery.NORMALIZED_SHA)
        before = (self.out / 'before-record_gate_owner').read_text()
        rows = []
        for name, body in recovery.all_forms():
            self.assertEqual((self.out / (name + '.c')).read_text(), source.recovered_owner(before, body))
            raw, _ = source.parts(self.out / (name + '.o'))
            audit = json.loads((self.out / (name + '-audit.json')).read_text())
            words = list(struct.unpack_from('>%dI' % (len(raw) // 4), source.projection.sections(self.out / (name + '-linked.elf'))['.text'][1]))
            self.assertEqual(hashlib.sha256(raw).hexdigest(), audit['raw_sha'])
            self.assertEqual((len(words), (-words[0]) & 65535, sum(a != b for a, b in zip(words, self.truth))),
                             tuple(audit[k] for k in ('words', 'frame', 'differences')))
            self.assertEqual(audit['raw_neighbors'], 11)
            if len(words) > 959:
                self.assertTrue(audit['padder_rejected'])
            else:
                self.assertEqual(audit['padded_neighbors'], 11)
            rows.append(dict(name=name, words=len(words), differences=audit['differences']))
        self.assertEqual((len(rows), sum(r['words'] > 959 for r in rows)), (9, 1))
        self.assertEqual(source.parts(self.padded)[1], self.bindings)
        old = (self.out / 'before-guards').read_bytes()
        generated = (self.out / 'expected-flag-guards.csv').read_bytes()
        self.assertTrue(generated.startswith(old))
        appended = list(csv.DictReader(io.StringIO(generated.decode())))[len(list(csv.DictReader(io.StringIO(old.decode())))):]
        self.assertEqual((len(appended), sum(r['expected_relocations'] != '-' for r in appended)), (28, 4))
        for r in appended:
            self.assertEqual(r['expected_relocations'], r['replacement_relocations'])
        self.receipt('source-controls', complete_forms=9, overflow_rejections=1, rows=rows,
                     natural_C_word_improvements=3, research_only_rewrites=28, relocated_GPR_rewrites=4)

    def test_02_effective_CFG_livein_liveout_delay_and_binding_controls(self):
        recovery.prove_roles(self.raw_words, self.truth, self.bindings)
        count = 0
        for index in range(recovery.START, recovery.END):
            bad = list(self.raw_words)
            bad[index] ^= 1
            with self.assertRaises(ValueError):
                recovery.prove_roles(bad, self.truth, self.bindings)
            count += 1
        for offset in (*recovery.RELOCATED_CHANGES, (recovery.END - 2) * 4):
            for changed in ([], [('R_MIPS_32', 'bad')], [(self.bindings[offset][0][0], 'wrong')]):
                with self.assertRaises(ValueError):
                    recovery.prove_roles(self.raw_words, self.truth, self.bindings | {offset: changed})
                count += 1
        for mapping in ({}, {**recovery.ROLE_MAP, 13: 11}, {**recovery.ROLE_MAP, 13: 16}):
            with self.assertRaises(ValueError):
                recovery.prove_roles(self.raw_words, self.truth, self.bindings, mapping)
            count += 1
        for index, word, message in (
            (100, (4 << 26) | (410 - 100 - 1), 'Incoming'),
            (100, (2 << 21) | (31 << 11) | 9, 'computed'),
            (0, self.raw_words[0] ^ 4, 'frame'),
            (recovery.END - 2, self.raw_words[recovery.END - 2] ^ 1, 'callback'),
        ):
            bad = list(self.raw_words)
            bad[index] = word
            with self.assertRaisesRegex(ValueError, message):
                recovery.prove_roles(bad, self.truth, self.bindings)
            count += 1
        # Exercise path reasoning directly so a retail-byte mismatch cannot
        # hide a missing live-in, annulment or post-call definition check.
        for index, word in (
            (406, 0),                         # controller live-in
            (409, 0),                         # annulled flag definition
            (418, (4 << 26) | (421 - 418 - 1)), # lower path enters undefined upper flag
            (438, 0),                         # remove reloaded controller LUI
            (469, 0),                         # remove first post-call heading definition
        ):
            bad = list(self.raw_words)
            bad[index] = word
            with self.assertRaisesRegex(ValueError, 'before definition'):
                recovery.path_definitions(bad, recovery.START if index < recovery.END else recovery.END,
                                          recovery.END if index < recovery.END else len(bad), recovery.ROLE_MAP,
                                          index < recovery.END)
            count += 1
        bad = list(self.raw_words)
        bad[439] = (13 << 26) | (15 << 16) | 7
        with self.assertRaisesRegex(ValueError, 'correspondence'):
            recovery.prove_roles(bad, self.truth, self.bindings)
        count += 1
        for index, word in ((408, (4 << 26) | (405 - 408 - 1) & 65535),
                            (409, self.raw_words[408])):
            bad = list(self.raw_words)
            bad[index] = word
            with self.assertRaises(ValueError):
                recovery.path_definitions(bad, recovery.START, recovery.END, recovery.ROLE_MAP, True)
            count += 1
        bad = list(self.raw_words)
        bad[408] = 4 << 26
        with self.assertRaisesRegex(ValueError, 'delay slot'):
            recovery.prove_roles(bad, self.truth, self.bindings)
        count += 1
        with self.assertRaises(ValueError):
            recovery.prove_roles(self.raw_words[:-1], self.truth, self.bindings)
        count += 1
        self.receipt('CFG-controls', effective_controls=count, literal_words_including_dead_duplicate=63,
                     branch_states=self.row['proof']['paths']['states'], post_call_states=self.row['proof']['post_call_liveness']['states'],
                     no_ABI_clobber_used_to_excuse_liveout_reads=True)

    def test_02b_actual_padder_rejects_stale_words_and_relocations(self):
        path = self.out / 'expected-flag-guards.csv'
        rows = list(csv.DictReader(io.StringIO(path.read_text())))
        fieldnames = list(rows[0])
        target = next(i for i, r in enumerate(rows) if r['function'] == source.FUNCTION and int(r['offset'], 0) == 0x658)
        controls = (('expected', '0x00000000'), ('expected_relocations', '-'),
                    ('expected_relocations', 'R_MIPS_HI16:wrong'))
        for n, (key, value) in enumerate(controls):
            bad = copy.deepcopy(rows)
            bad[target][key] = value
            text = io.StringIO(newline='')
            writer = csv.DictWriter(text, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(bad)
            table = self.out / ('negative-flag-guards-%d.csv' % n)
            table.write_text(text.getvalue())
            with self.assertRaises(ValueError):
                source.literal.padded_object(self.root, self.out, self.obj, 'negative-flag-guard-%d' % n, table)
        self.receipt('padder-controls', actual_rejections=len(controls), stale_word_and_relocation_controls=True)

    def test_03_kernel_poison_branch_likely_and_alias_cases(self):
        seeds = (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xA5A5A5A5, 0xDEADBEEF, 0x01020304)
        buttons = (0, 0x10, 0x8000, 0x4000, 0xC000, 0x8010, 0x4010, 0xC010)
        actors = (model.ACTOR, 0x800A19A4 - 0xC0)
        count, coverage, outcomes = 0, set(), set()
        for actor, seed, button, condition, flag, velocity, phase in itertools.product(
                actors, seeds, buttons, (False, True), (0, 1), (-4., 0., 9.), (0, 8)):
            memory, case = model.fixture(self.rom, actor=actor, phase=phase, pattern=phase // 8,
                                         below=flag, buttons=button, velocity=velocity)
            # Whole-function entry normally selects INPUT from the slot. This
            # kernel starts later, so install that same controller selection.
            model.put(memory, 0x800CC284, model.INPUT)
            pair = [KernelOracle(w, memory, case, self.connected) for w in (self.raw_words, self.words)]
            for machine in pair:
                machine.r = [0, *((seed ^ (i * 0x1234567)) & 0xFFFFFFFF for i in range(1, 32))]
                machine.r[1], machine.r[4], machine.r[16], machine.r[29] = 0x800A0000, actor, actor, model.STACK + phase
                machine.f = [(seed ^ (i * 0x01010101)) & 0xFFFFFFFF for i in range(32)]
                machine.f[0], machine.f[14], machine.f[16] = model.bits(1.), model.bits(1.5), model.bits(0.)
                machine.lo, machine.condition = seed, condition
                machine.entry = source.ENTRY + recovery.START * 4
                with self.assertRaises(KernelStop):
                    machine.run()
                self.assertEqual(machine.r[31], source.ENTRY + recovery.END * 4)
            left, right = pair
            coverage.update((pc - source.ENTRY) // 4 for pc in left.visits)
            for pc in (0x150F3B54, 0x150F3BEC):
                index = (pc - source.ENTRY) // 4
                outcomes.add((pc, source.ENTRY + (index + 1) * 4 in left.visits))
            self.assertEqual((left.memory, left.f, left.calls, left.observations, left.events),
                             (right.memory, right.f, right.calls, right.observations, right.events))
            self.assertEqual((left.lo, left.condition, left.all_accesses), (right.lo, right.condition, right.all_accesses))
            self.assertEqual([left.r[i] for i in range(32) if i not in recovery.ROLE_MAP],
                             [right.r[i] for i in range(32) if i not in recovery.ROLE_MAP])
            defined = {self.raw_words[i] >> s & 31 for i in range(recovery.START, recovery.END)
                       if source.ENTRY + i * 4 in left.visits for s in recovery.operands(self.raw_words[i])[1]}
            for register, replacement in recovery.ROLE_MAP.items():
                if register in defined:
                    self.assertEqual(left.r[register], right.r[replacement])
            count += 1
        self.assertEqual(count, 3072)
        self.assertEqual(sorted(set(range(recovery.START, recovery.END)) - coverage), [420])
        self.assertEqual(len(outcomes), 4)
        self.receipt('kernel', complete_cases=count, poisoned_seeds=8, actor_bases=2, button_combinations=8,
                     flag_values=2, condition_values=2, vertical_values=3, stack_phases=2,
                     both_likely_delay_slots_executed_and_annulled=True,
                     visited_words=62, actual_callback_packet_and_complete_memory_FP_events_equal=True)

    test_04_complete_three_way_public_and_cap_boundaries = prior.MovementTurnArgumentTests.test_04_complete_three_way_public_and_cap_boundaries
    pair_at = prior.MovementTurnArgumentTests.pair_at
    complete_prefixes = prior.MovementTurnArgumentTests.complete_prefixes

    def test_05_new_private_frontier_and_complete_disabled_and_mode_zero(self):
        total, frontiers, states = 0, {}, 0
        for phase, pattern, gate in itertools.product((0, 8), (0, 1), range(5)):
            for position in (100., 2200.):
                for velocity in ((-4.,) if position == 100. else (-40., -30., -29.999998, 30.)):
                    memory, case = model.fixture(self.rom, phase=phase, pattern=pattern, gate=gate,
                                                 held=101, position=position, velocity=velocity)
                    for cut in range(150):
                        pair, fired = self.pair_at(memory, case, cut)
                        self.assertTrue(fired)
                        if model.point.state(pair[0]) != model.point.state(pair[1]):
                            key = ','.join(hex(x.current_pc) for x in pair)
                            frontiers[key] = frontiers.get(key, 0) + 1
                            self.assertGreater(cut, (55, 63, 54, 56, 57)[gate])
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
        self.assertEqual((states, ds, dp, zs, zp), (100, 80, 2700, 160, 8320))
        self.receipt('private', active_states=states, equal_fault_prefixes=total, frontier_PC_pairs=frontiers,
                     disabled_complete_states=ds, disabled_fault_prefixes=dp, mode_zero_complete_states=zs,
                     mode_zero_fault_prefixes=zp, full_private_opaque_or_hardware_acceptance_not_claimed=True)

    test_06_native_rebases_and_aliases = prior.MovementTurnArgumentTests.test_06_native_and_actual_normalized_rebases_and_aliases

    def test_07_fresh_owned_compiler_capture_and_effective_layout_controls(self):
        backend = recovery.previous.previous
        record, words, binary = backend.finish_trace(self.root, self.out, recovery.SELECTED_NAME, self.body)
        self.assertEqual(words, self.raw_words)
        self.assertEqual((record['correlated_events'], len(binary)), (74, 684))
        work = self.out / 'traces' / recovery.SELECTED_NAME
        self.assertEqual(source.parts(work / 'baseline.o'), source.parts(self.obj))
        content = backend.frame.isolated(self.body)
        layout = recovery.check_layout(record, words, content)
        controls = 0
        for phase, store in layout['button_stores'].items():
            for key, value in (('offset', store['offset'] + 4), ('dtype', 'J'), ('length', 8)):
                bad = copy.deepcopy(record)
                next(r for r in bad['records'][phase] if r['byte_offset'] == store['byte_offset'])[key] = value
                with self.assertRaises(ValueError):
                    recovery.check_layout(bad, words, content)
                controls += 1
        for pc in (0x150F3BF4, 0x150F3C00, 0x150F3C1C):
            bad = list(words)
            bad[(pc - source.ENTRY) // 4] ^= 64
            with self.assertRaises(ValueError):
                recovery.check_layout(record, bad, content)
            controls += 1
        self.receipt('backend', newly_owned_capture=True, raw_normal_and_observed_objects_identical=True,
                     source_sha=record['source_sha'], compiler_sha256=record['compiler_sha256'],
                     emitter_events=74, AS1_instructions=684, layout=layout, effective_layout_controls=controls,
                     normalized_object_is_post_compile_research_not_AS1_output=True)

    def test_08_production_first_image_and_predecessors_preserved(self):
        recovery.freeze(self.root, self.out)
        for key, path in recovery.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes())
        self.harness.test_07_production_baseline_and_callback_preserved()
        source.checkpoint.freeze_after(self.root)
        self.receipt('protected', entries=len(recovery.PATHS), paths=len(set(recovery.PATHS.values())),
                     immutable_first_image_members=10, installed=False, production_guards_added=0, matching_credit=0)


if __name__ == '__main__':
    unittest.main()
