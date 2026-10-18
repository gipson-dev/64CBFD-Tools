"""Qualify movement release addressing and a non-call heading-role boundary."""
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
from tools.experiments import game_actor_input_movement_release_addressing as recovery
from tools.tests import test_game_actor_input_movement_heading_continuation as prior

model, original, native = prior.model, prior.original, prior.native


def address_specs():
    for slot, control, buttons, phase in itertools.product(range(25), (0, 2), (0, 0x10), (0, 8)):
        yield dict(held=100 + slot, control=control, buttons=buttons, phase=phase, depth=75.)


class KernelStop(Exception):
    pass


class HeadingOracle(model.Oracle):
    def execute(self, word):
        if self.current_pc == source.ENTRY + recovery.END * 4:
            raise KernelStop
        return super().execute(word)


class MovementReleaseAddressingTests(unittest.TestCase):
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
        cls.base28, _ = recovery.previous.normalize(cls.raw_words, cls.truth, cls.bindings)
        cls.harness = original.MovementRecoveryTests('test_02_all_three_paths_and_numeric_boundaries')
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

    def test_01_complete_sources_real_padder_extent_and_no_production_credit(self):
        self.assertEqual(tuple(self.row[k] for k in ('words', 'frame', 'differences', 'normalized_differences')), (959, 128, 200, 169))
        self.assertEqual((self.row['normalized_exact_opening_words'], self.row['normalized_first_PC']), (478, 0x150F3C6C))
        self.assertEqual(self.words[:478], self.truth[:478])
        self.assertEqual(self.row['normalized_raw_sha'], recovery.NORMALIZED_SHA)
        self.assertEqual((self.row['research_guards'], self.row['new_research_guards'], self.row['normalized_target_changed_bytes']), (31, 3, 39))
        self.assertEqual((self.row['production_guards_added'], self.row['matching_credit'], self.row['installed']), (0, 0, False))
        self.assertEqual(source.parts(self.obj)[1], source.parts(self.padded)[1])
        old_table = (self.root / recovery.previous.BUILD / 'expected-continuation-guards.csv').read_bytes()
        table = (self.out / 'expected-release-guards.csv').read_bytes()
        self.assertTrue(table.startswith(old_table))
        added = list(csv.DictReader(io.StringIO(table.decode())))[len(list(csv.DictReader(io.StringIO(old_table.decode())))):]
        self.assertEqual([(int(r['offset'], 0), int(r['expected'], 0), int(r['replacement'], 0)) for r in added], list(recovery.GUARDS))
        self.assertTrue(all(r['expected_relocations'] == r['replacement_relocations'] == '-' for r in added))
        before = (self.out / 'before-record_gate_owner').read_text()
        rows = []
        for name, body in recovery.all_forms():
            self.assertEqual((self.out / (name + '.c')).read_text(), source.recovered_owner(before, body), name)
            raw, _ = source.parts(self.out / (name + '.o'))
            audit = json.loads((self.out / (name + '-audit.json')).read_text())
            self.assertEqual(hashlib.sha256(raw).hexdigest(), audit['raw_sha'])
            words = list(struct.unpack_from('>%dI' % (len(raw) // 4), source.projection.sections(self.out / (name + '-linked.elf'))['.text'][1]))
            self.assertEqual((len(words), (-words[0]) & 65535, sum(a != b for a, b in zip(words, self.truth))),
                             tuple(audit[k] for k in ('words', 'frame', 'differences')))
            self.assertEqual(audit['raw_neighbors'], 11)
            if len(words) > 959:
                self.assertTrue(audit['padder_rejected'])
            else:
                self.assertEqual(audit['padded_neighbors'], 11)
            rows.append(dict(name=name, words=len(words), differences=audit['differences']))
        self.assertEqual((len(rows), sum(r['words'] > 959 for r in rows), sum(r['words'] < 959 for r in rows)), (46, 4, 17))
        self.receipt('source-controls', complete_forms=46, overflow_rejections=4, shorter_controls=17, rows=rows,
                     new_research_rows=3, production_rows_added=0, no_trimming_or_inert_locals=True)

    def test_02_effective_heading_role_deadout_entry_and_literal_controls(self):
        recovery.prove_heading(self.base28, self.truth, self.bindings)
        count = 0
        for i in range(recovery.START, recovery.END):
            bad = list(self.base28)
            bad[i] ^= 1
            with self.assertRaises(ValueError):
                recovery.prove_heading(bad, self.truth, self.bindings)
            count += 1
        for offset, _, _ in recovery.GUARDS:
            with self.assertRaises(ValueError):
                recovery.prove_heading(self.base28, self.truth, self.bindings | {offset: [('R_MIPS_32', 'wrong')]})
            count += 1
        for mapping in ({}, {11: 13, 12: 13}, {11: 16, 12: 14}, {13: 11, 14: 12}):
            with self.assertRaises(ValueError):
                recovery.prove_heading(self.base28, self.truth, self.bindings, mapping)
            count += 1
        for index, word in ((100, (4 << 26) | (recovery.START + 1 - 100 - 1)),
                            (100, (2 << 21) | (31 << 11) | 9), (474, 4 << 26),
                            (470, (15 << 26) | (13 << 16) | 0x3FC0),
                            (476, self.base28[476] ^ 64), (0, self.base28[0] ^ 4)):
            bad = list(self.base28)
            bad[index] = word
            with self.assertRaises(ValueError):
                recovery.prove_heading(bad, self.truth, self.bindings)
            count += 1
        with self.assertRaises(ValueError):
            recovery.prove_heading(self.base28[:-1], self.truth, self.bindings)
        count += 1
        for offset, _, _ in recovery.GUARDS:
            changed = tuple((o, a, b ^ 1 if o == offset else b) for o, a, b in recovery.GUARDS)
            with patch.object(recovery, 'GUARDS', changed), self.assertRaises(ValueError):
                recovery.prove_heading(self.base28, self.truth, self.bindings)
            count += 1
        affected = {11, 12, 13, 14}
        for register in affected:
            bad = list(self.base28)
            bad[recovery.END] = (register << 21) | (2 << 11) | 33
            with self.assertRaisesRegex(ValueError, 'before definition'):
                recovery.flags.path_definitions(bad, recovery.END, len(bad), {r: r for r in affected})
            count += 1
        for name, value in (('START', 470), ('END', 479)):
            with patch.object(recovery, name, value), self.assertRaises(ValueError):
                recovery.prove_heading(self.base28, self.truth, self.bindings)
            count += 1
        self.receipt('heading-controls', effective_controls=count, non_call_boundary=True,
                     all_four_physical_registers_checked=True,
                     continuation_states=self.row['heading_proof']['continuation_first_definitions']['states'],
                     no_ABI_clobber_used_to_excuse_read=True)

    def test_03_non_call_kernel_poison_yaws_and_guest_aliases(self):
        actors = (model.ACTOR, model.TABLE + 12 * 0x32C, 0x800A1930)
        seeds = (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xA5A5A5A5, 0x5A5A5A5A, 0x01020304,
                 0xDEADBEEF, 0x10000, 0xFFFF, 0x8000, 0x7FC12345, 0xFF800000, 0x00800000, 0x3F800000)
        count = 0
        affected = {11, 12, 13, 14}
        for actor, seed, yaw, phase in itertools.product(actors, seeds, (-32768, -1, 0, 1, 32767), (0, 8)):
            memory, case = model.fixture(self.rom, actor=actor, phase=phase)
            model.put(memory, actor + 0x7A, yaw, 2)
            pair = [HeadingOracle(w, memory, case, self.connected) for w in (self.base28, self.words)]
            for machine in pair:
                machine.r = [0, *((seed ^ (i * 0x1234567)) & 0xFFFFFFFF for i in range(1, 32))]
                machine.r[16], machine.r[29] = actor, model.STACK + phase
                machine.f = [(seed ^ (i * 0x01010101)) & 0xFFFFFFFF for i in range(32)]
                machine.lo, machine.condition = seed, bool(phase)
                machine.entry = source.ENTRY + recovery.START * 4
                with self.assertRaises(KernelStop):
                    machine.run()
                self.assertEqual((machine.current_pc, machine.all_accesses), (source.ENTRY + recovery.END * 4, 1))
                self.assertFalse(machine.calls)
            left, right = pair
            self.assertEqual((left.memory, left.f, left.events, left.lo, left.condition),
                             (right.memory, right.f, right.events, right.lo, right.condition))
            self.assertEqual([left.r[i] for i in range(32) if i not in affected],
                             [right.r[i] for i in range(32) if i not in affected])
            for register, replacement in recovery.ROLE_MAP.items():
                self.assertEqual(left.r[register], right.r[replacement])
            count += 1
        self.assertEqual(count, 480)
        self.receipt('heading-kernel', complete_cases=count, poisoned_seeds=16, signed_yaws=5,
                     guest_actor_bases=3, stack_phases=2, stopped_before_next_flag_load=True,
                     complete_memory_FP_events_and_identity_registers_equal=True,
                     arbitrary_raw_private_register_or_opaque_provider_equivalence_not_claimed=True)

    test_04_complete_public_FP_and_cap = prior.MovementHeadingContinuationTests.test_04_complete_public_FP_and_cap_corpus
    pair_at = prior.MovementHeadingContinuationTests.pair_at
    complete_prefixes = prior.MovementHeadingContinuationTests.complete_prefixes

    def test_05_extended_private_prefixes_and_complete_existing_paths(self):
        total, states, frontiers = 0, 0, {}
        for phase, pattern, gate in itertools.product((0, 8), (0, 1), range(5)):
            for position in (100., 2200.):
                for velocity in ((-4.,) if position == 100. else (-40., -30., -29.999998, 30.)):
                    memory, case = model.fixture(self.rom, phase=phase, pattern=pattern, gate=gate,
                                                 held=101, position=position, velocity=velocity)
                    for cut in range(150):
                        pair, fired = self.pair_at(memory, case, cut)
                        self.assertTrue(fired)
                        if model.point.state(pair[0]) != model.point.state(pair[1]):
                            self.assertEqual([m.current_pc for m in pair], [0x150F3C88] * 2)
                            self.assertEqual((pair[0].memory, pair[0].f), (pair[1].memory, pair[1].f))
                            different = tuple(i for i, (a, b) in enumerate(zip(pair[0].r, pair[1].r)) if a != b)
                            frontiers[str(different)] = frontiers.get(str(different), 0) + 1
                            with patch.object(self, 'words', self.base28):
                                old, old_fired = self.pair_at(memory, case, cut - 1)
                                self.assertTrue(old_fired)
                                self.assertNotEqual(model.point.state(old[0]), model.point.state(old[1]))
                                self.assertEqual([m.current_pc for m in old], [0x150F3C6C] * 2)
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
        self.assertEqual((states, total, ds, dp, zs, zp), (100, 6700, 80, 2700, 160, 8320))
        self.receipt('private', active_states=states, equal_fault_prefixes=total, first_PC='0x150F3C88',
                     different_GPR_sets=frontiers, old_28_row_rejections=100,
                     disabled_states=ds, disabled_prefixes=dp, mode_zero_states=zs, mode_zero_prefixes=zp,
                     full_private_or_hardware_acceptance_not_claimed=True)

    def test_06_record_indices_speed_order_and_old_candidate_guest_rejection(self):
        cases, entered = 0, 0
        for spec in address_specs():
            self.harness.compare(spec)
            memory, case = model.fixture(self.rom, **spec)
            for words in (self.truth, self.raw_words, self.words):
                machine = model.Oracle(words, memory, case, self.connected).run()
                self.assertEqual(0x150F3FF0 in machine.visits, bool(spec['control'] and not spec['buttons']))
            cases += 1
            entered += bool(spec['control'] and not spec['buttons'])
        old_obj = self.out / 'copy-base.o'
        self.assertEqual(hashlib.sha256(source.parts(old_obj)[0]).hexdigest(),
                         'f96f8e13c2ff31de5266ad84bfcca7150cc8eb2bab30b7336184c8a1d5b02f02')
        old_words = source.linked(self.root, self.out, old_obj, 'qualified-copy-base-linked')
        aliases = 0
        for slot, phase, pattern in itertools.product(range(25), (0, 8), (0, 1)):
            record = model.TABLE + slot * 0x32C
            memory, case = model.fixture(self.rom, actor=record + 0xBC, held=100 + slot, control=2,
                                         phase=phase, pattern=pattern, depth=75.)
            model.put(memory, record + 0xF8, 0x41F00400)
            machines = [model.Oracle(w, memory, case, self.connected).run() for w in (self.truth, self.raw_words, self.words)]
            expected = machines[0]
            for machine in machines:
                self.assertIn(0x150F3FF0, machine.visits)
                self.assertEqual(model.public(machine.memory), model.public(expected.memory))
                self.assertEqual((machine.calls, machine.observations, machine.fired),
                                 (expected.calls, expected.observations, expected.fired))
            old = model.Oracle(old_words, memory, case, self.connected).run()
            self.assertTrue(model.public(old.memory) != model.public(expected.memory), 'Old late speed read was not rejected')
            aliases += 1
        self.assertEqual((cases, entered, aliases), (200, 50, 100))
        self.receipt('record-addresses', complete_cases=cases, release_gate_entered=entered, table_slots=25,
                     actual_retail_speed_alias_cases=aliases, effective_old_late_read_rejections=aliases,
                     prior_high_level_model_not_used_for_new_overlap=True,
                     portable_C_partial_struct_alias_not_claimed=True)

    test_07_existing_signed_Y_alias_controls = prior.MovementHeadingContinuationTests.test_03_signed_Y_read_before_zero_stores_guest_alias_and_old_rejection
    test_08_existing_clamp_boundaries_and_wrong_limits = prior.MovementHeadingContinuationTests.test_06_clamp_boundaries_and_effective_compiled_wrong_limits

    def test_09_native32_UBSan_rebases_and_aliases(self):
        self.harness.test_05_two_independent_text_rebases()
        specs = [*list(original.core_specs())[::7], *list(original.mutation_specs())[::5], *original.targeted_specs()]
        fixture_before = model.fixture

        def fixture(rom, **spec):
            memory, case = fixture_before(rom, **spec)
            if 'headingOffset' in spec:
                model.put(memory, 0x800CC280, spec['headingOffset'])
            return memory, case

        for angle, offset in itertools.product((0, 1, 65535), (0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)):
            specs.append(dict(mode=0, angle=angle, magnitude=2., headingOffset=offset))
        for held, velocity in itertools.product((0, 101), (-40., -30., -29.999998, 0., 30.)):
            specs.append(dict(held=held, position=2200., velocity=velocity))
        specs.extend(dict(held=h, velocity=v) for h, v in itertools.product((0, 101), prior.CLAMP_VALUES))
        specs.extend(address_specs())
        with patch.object(model, 'fixture', fixture), patch.object(source, 'SELECTED', self.body):
            row = native.qualify(self.root, self.out, self.rom, specs)
        self.assertEqual((row['cases_per_profile'], row['effective_controls']), (369, 8))
        aliases = 0
        for alias, gate, mode in itertools.product((0x800CC284, 0x800CC288, model.SLOT), (0, 1), (0, 1)):
            memory, case = model.fixture(self.rom, gate=gate, mode=mode, pattern=1, pressed=0x8000)
            model.put(memory, model.SLOT, alias)
            memory.update({0x800C0080 + i: 0xA5 for i in range(32)})
            expected = model.reference(memory, case)
            for words in (self.truth, self.words):
                actual = model.Oracle(words, memory, case, self.connected).run()
                self.assertEqual(model.public(actual.memory), model.public(expected[0]))
                self.assertEqual((actual.calls, actual.observations), (expected[1], expected[2]))
            aliases += 1
        self.receipt('native-rebases-aliases', native_cases_per_profile=369, profiles=['O2', 'O0'], UBSan=True,
                     native_controls=8, new_native_release_cases=200, text_rebases=2, rebase_cases=12,
                     established_guest_aliases=aliases, new_partial_struct_overlaps_kept_guest_only=True)

    def test_10_owned_backend_real_index_home_and_effective_controls(self):
        record, words, binary = recovery.backend.finish_trace(self.root, self.out, recovery.SELECTED_NAME, self.body)
        self.assertEqual(words, self.raw_words)
        self.assertEqual((record['correlated_events'], len(binary)), (74, 687))
        work = self.out / 'traces' / recovery.SELECTED_NAME
        self.assertEqual(source.parts(work / 'baseline.o'), source.parts(self.obj))
        content = recovery.backend.frame.isolated(self.body)
        layout = recovery.check_layout(record, words, content)
        frame = recovery.backend.frame
        summary = frame.summary(record, content, recovery.backend.MARKERS)
        count = 0
        for phase in ('frontend', 'optimizer'):
            bad = copy.deepcopy(record)
            next(r for r in bad['records'][phase] if r['name'] == 'def' and r['storage'] == 'M')['length'] += 4
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, words, content)
            count += 1
        for name in recovery.backend.HOMES:
            store = next(r for r in summary['phases']['frontend']['markers'][name] if r['name'] == 'str' and r['storage'] == 'M')
            bad = copy.deepcopy(record)
            next(r for r in bad['records']['frontend'] if r['byte_offset'] == store['byte_offset'])['offset'] += 4
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, words, content)
            count += 1
        for phase, store in layout['release_index'].items():
            for key, value in (('offset', store['offset'] + 4), ('dtype', 'R'), ('length', 8)):
                bad = copy.deepcopy(record)
                next(r for r in bad['records'][phase] if r['byte_offset'] == store['byte_offset'])[key] = value
                with self.assertRaises(ValueError):
                    recovery.check_layout(bad, words, content)
                count += 1
        for i in range(4):
            for key in ('host_pc', 'frame'):
                bad = copy.deepcopy(record)
                bad['events'][i][key] ^= 4
                with self.assertRaises(ValueError):
                    recovery.check_layout(bad, words, content)
                count += 1
        for key in ('saved', 'outgoing', 'locals'):
            bad = copy.deepcopy(record)
            bad['events'][-1][key] += 4
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, words, content)
            count += 1
        for i in layout['sites']:
            bad = list(words)
            bad[i] ^= 4
            with self.assertRaises(ValueError):
                recovery.check_layout(record, bad, content)
            count += 1
        self.receipt('backend', newly_owned_capture=True, normal_and_observed_raw_identical=True,
                     source_sha=record['source_sha'], emitter_events=74, AS1_instructions=687,
                     layout=layout, effective_controls=count, normalized_output_not_AS1_output=True)

    def test_11_actual_padder_rejects_stale_heading_word_and_relocation(self):
        rows = list(csv.DictReader(io.StringIO((self.out / 'expected-release-guards.csv').read_text())))
        fields = list(rows[0])
        index = next(i for i, r in enumerate(rows) if r['function'] == source.FUNCTION and int(r['offset'], 0) == 0x754)
        for n, (key, value) in enumerate((('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_32:wrong'))):
            bad = copy.deepcopy(rows)
            bad[index][key] = value
            text = io.StringIO(newline='')
            writer = csv.DictWriter(text, fieldnames=fields)
            writer.writeheader()
            writer.writerows(bad)
            table = self.out / ('negative-heading-guards-%d.csv' % n)
            table.write_text(text.getvalue())
            with self.assertRaises(ValueError):
                source.literal.padded_object(self.root, self.out, self.obj, 'negative-heading-guard-%d' % n, table)
        self.receipt('padder-controls', effective_actual_rejections=2)

    def test_12_all_production_data_predecessors_and_first_images_unchanged(self):
        recovery.freeze(self.root, self.out)
        for key, path in recovery.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes())
        self.harness.test_07_production_baseline_and_callback_preserved()
        source.checkpoint.freeze_after(self.root)
        self.receipt('protected', entries=len(recovery.PATHS), paths=len(set(recovery.PATHS.values())),
                     immutable_first_image_members=10, installed=False, matching_credit=0, production_guards_added=0)


if __name__ == '__main__':
    unittest.main()
