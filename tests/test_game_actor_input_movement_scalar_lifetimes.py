"""Qualify the movement zero comparison, counter pointer and final sample."""
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

from tools.experiments import game_actor_input_movement_scalar_lifetimes as recovery
from tools.tests import test_game_actor_input_movement_pitch_surface_order as prior

source, model, original = recovery.source, prior.model, prior.original
release, heading = prior.prior, prior.prior.prior


class CountOracle(model.Oracle):
    def __init__(self, *args, **kwargs):
        self.active_reads = []
        super().__init__(*args, **kwargs)

    def execute(self, word):
        if 0x150F40A4 <= self.current_pc <= 0x150F40C8 and word >> 26 == 35 and word & 65535 == 0:
            self.active_reads.append(self.r[word >> 21 & 31])
        return super().execute(word)


class MovementScalarLifetimeTests(unittest.TestCase):
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
        cls.base28, _ = recovery.previous.previous.previous.normalize(cls.raw_words, cls.truth, cls.bindings)
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

    def test_01_complete_source_controls_and_literal_gain(self):
        self.assertEqual(tuple(self.row[k] for k in ('words', 'frame', 'differences', 'normalized_differences')), (959, 128, 139, 108))
        self.assertEqual((self.row['normalized_exact_opening_words'], self.row['normalized_first_PC']), (478, 0x150F3C6C))
        self.assertEqual(self.words[:478], self.truth[:478])
        self.assertEqual(self.row['normalized_raw_sha'], 'e78c78662ddcf369e8aaa8fbdcc0946c92b57fbc2ade58c5c023f8474f931987')
        self.assertEqual((self.row['research_guards'], self.row['new_research_guards'], self.row['production_guards_added'],
                          self.row['matching_credit'], self.row['installed']), (31, 0, 0, 0, False))
        self.assertEqual((self.out / 'expected-scalar-guards.csv').read_bytes(),
                         (self.root / recovery.previous.BUILD / 'expected-surface-guards.csv').read_bytes())
        self.assertEqual(source.parts(self.obj)[1], source.parts(self.padded)[1])
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
            self.assertEqual((audit['raw_neighbors'], audit['padded_neighbors']), (11, 11))
            rows.append(dict(name=name, words=len(words), differences=audit['differences']))
        self.assertEqual((len(rows), {r['words'] for r in rows}), (27, {959}))
        old = list(struct.unpack_from('>959I', source.projection.sections(
            self.root / recovery.previous.BUILD / (recovery.previous.SELECTED_NAME + '-linked.elf'))['.text'][1]))
        changed = [i for i, (a, b) in enumerate(zip(old, self.raw_words)) if a != b]
        gained = [i for i in changed if self.raw_words[i] == self.truth[i]]
        lost = [i for i in changed if old[i] == self.truth[i]]
        self.assertEqual((len(changed), len(gained), len(lost)), (19, 13, 0))
        for pc in (0x150F3D44, 0x150F434C, 0x150F4350):
            self.assertEqual(self.raw_words[(pc - source.ENTRY) // 4], self.truth[(pc - source.ENTRY) // 4])
        self.receipt('source-controls', complete_forms=27, overflow_rejections=0, shorter_controls=0, rows=rows,
                     raw_changed_words=19, newly_exact=13, formerly_exact_lost=0, research_table_byte_identical=True)

    def test_02_zero_comparison_AST_dominance_and_effective_controls(self):
        proof = recovery.check_zero_lifetime(self.body)
        self.assertEqual((proof['identifier_uses'], proof['writes']), (5, 2))
        self.assertLess(proof['comparison_line'], proof['pitch_line'])
        initial = '    contactHeight = 0.0f;'
        pitch = '            pitchValue = (actor->verticalVelocity - contactHeight) * -2.0f;'
        loop = recovery.replace(self.body, '        if (contactHeight == acceleration) {',
                                '        while (1) {\n        if (contactHeight == acceleration) {')
        loop = recovery.replace(loop, '        actor->flagAD = 10;', '        }\n        actor->flagAD = 10;')
        variants = (
            recovery.replace(self.body, initial, '    contactHeight = 1.0f;'),
            recovery.replace(self.body, initial, '    if (actor->held) { contactHeight = 0.0f; }'),
            recovery.replace(self.body, pitch, '            contactHeight = 0.0f;\n' + pitch),
            recovery.replace(self.body, pitch, '            func_15059140((MovementActor34F4 *)&contactHeight);\n' + pitch),
            recovery.replace(self.body, pitch, '            while (1) {\n' + pitch + '\n            }'),
            recovery.replace(self.body, pitch, pitch + '\n            goto disabled_done;'),
            recovery.replace(self.body, '            contactHeight = 50.0f;', '            contactHeight = 25.0f;'),
            recovery.replace(self.body, 'actor->verticalVelocity - contactHeight', 'actor->verticalVelocity - (&contactHeight)'),
            loop,
            recovery.replace(self.body, '        acceleration = actor->acceleration;', '        acceleration = 0.0f;'),
            recovery.replace(self.body, '        velocity = actor->verticalVelocity;\n        if (contactHeight',
                             '        velocity = 0.0f;\n        if (contactHeight'),
            recovery.replace(self.body, 'contactHeight == acceleration', 'acceleration == contactHeight'),
        )
        for body in variants:
            with self.assertRaises(ValueError):
                recovery.check_zero_lifetime(body)
        self.receipt('zero-lifetime', proof=proof, effective_AST_controls=len(variants),
                     old_eight_controls_rerun=True, added_comparison_scope_inputs_and_order_controls=4,
                     cpp_and_C_parser_used=True, arbitrary_caller_stack_alias_not_claimed=True)

    test_03_existing_heading_role_controls = prior.MovementPitchSurfaceOrderTests.test_02_existing_effective_heading_role_controls
    test_04_existing_heading_kernel = prior.MovementPitchSurfaceOrderTests.test_03_existing_non_call_heading_kernel
    test_05_complete_public_FP_and_cap = prior.MovementPitchSurfaceOrderTests.test_04_complete_public_FP_and_cap
    pair_at = prior.MovementPitchSurfaceOrderTests.pair_at
    complete_prefixes = prior.MovementPitchSurfaceOrderTests.complete_prefixes
    test_06_private_prefixes_and_complete_existing_paths = prior.MovementPitchSurfaceOrderTests.test_05_private_prefixes_and_existing_complete_paths
    test_07_release_indices_and_old_speed_read_rejections = prior.MovementPitchSurfaceOrderTests.test_06_release_indices_speed_aliases_and_old_read_rejection
    test_08_signed_Y_alias_controls = prior.MovementPitchSurfaceOrderTests.test_07_signed_Y_alias_controls
    test_09_clamp_boundaries_and_compiled_wrong_limits = prior.MovementPitchSurfaceOrderTests.test_08_clamp_boundaries_and_compiled_wrong_limits

    def test_10_native32_UBSan_rebases_and_count_thresholds(self):
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
        specs.extend(dict(held=h, velocity=v) for h, v in itertools.product((0, 101), heading.CLAMP_VALUES))
        specs.extend(release.address_specs())
        specs.extend(dict(count=c, phase=p, pressed=a) for c, p, a in itertools.product(range(7), (0, 8), (0, 0x2000)))
        with patch.object(model, 'fixture', fixture), patch.object(source, 'SELECTED', self.body):
            row = release.native.qualify(self.root, self.out, self.rom, specs)
        self.assertEqual((row['cases_per_profile'], row['effective_controls']), (397, 8))
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
        self.receipt('native-rebases-aliases', native_cases_per_profile=397, profiles=['O2', 'O0'], UBSan=True,
                     native_controls=8, new_native_count_cases=28, text_rebases=2, rebase_cases=12,
                     established_guest_aliases=aliases, partial_struct_overlaps_kept_guest_only=True)

    def test_11_counter_reads_exactly_24_records_and_effective_wrong_bounds(self):
        cases, fired = 0, 0
        expected_reads = [model.TABLE + i * 0x32C for i in range(1, 25)]
        for slot, active, kind, phase, pattern in itertools.product(range(25), (0, 1), (0x24, 0x25), (0, 8), (0, 1)):
            memory, case = model.fixture(self.rom, count=4, pressed=0x2000, phase=phase, pattern=pattern)
            model.put(memory, model.TABLE + slot * 0x32C, active)
            model.put(memory, model.TABLE + slot * 0x32C + 4, kind, 1)
            count = 4 + ((active and kind == 0x25) - 1 if 1 <= slot <= 4 else int(active and kind == 0x25) if slot else 0)
            machines = [CountOracle(w, memory, case, self.connected).run() for w in (self.truth, self.raw_words, self.words)]
            expected = machines[0]
            for machine in machines:
                self.assertEqual(machine.active_reads, expected_reads)
                self.assertIn(0x150F40A8, machine.visits)
                self.assertEqual(any(t == 0x15073FA0 for t, _ in machine.calls), count < 5)
                self.assertEqual(model.public(machine.memory), model.public(expected.memory))
                self.assertEqual((machine.calls, machine.observations, machine.fired),
                                 (expected.calls, expected.observations, expected.fired))
            cases += 1
            fired += count < 5
        for name, before, after in (
            ('negative-count-player-slot', 'countRecord = (MovementActor34F4 *)D_800CC5FC;',
             'countRecord = (MovementActor34F4 *)D_800CC2D0;'),
            ('negative-count-limit-four', 'if (count < 5)', 'if (count < 4)'),
        ):
            _, words, _ = recovery.measure(self.root, self.out, name, recovery.replace(self.body, before, after))
            memory, case = model.fixture(self.rom, count=4, pressed=0x2000)
            model.put(memory, model.TABLE, 1)
            model.put(memory, model.TABLE + 4, 0x25, 1)
            expected = CountOracle(self.truth, memory, case, self.connected).run()
            actual = CountOracle(words, memory, case, self.connected).run()
            self.assertIn(0x150F40A8, actual.visits)
            self.assertTrue(any(t == 0x15073FA0 for t, _ in expected.calls))
            self.assertFalse(any(t == 0x15073FA0 for t, _ in actual.calls), name)
            self.assertNotEqual(model.public(actual.memory), model.public(expected.memory))
        self.assertEqual((cases, fired), (400, 320))
        self.receipt('count-records', cases=cases, fired_spawn_cases=fired, active_reads_per_run=24,
                     scanned_slots=list(range(1, 25)), player_slot_excluded=True, compiled_effective_controls=2,
                     actual_retail_RAM_and_packets=True)

    def test_12_existing_surface_kernel_and_old_global_read_rejections(self):
        recovery.measure(self.root, self.out, 'surface-base', recovery.previous.previous.selected_body())
        prior.MovementPitchSurfaceOrderTests.test_10_surface_branch_packets_FP_and_global_overlap(self)

    def test_13_fresh_backend_homes_and_effective_controls(self):
        record, words, binary = recovery.backend.finish_trace(self.root, self.out, recovery.SELECTED_NAME, self.body)
        self.assertEqual(words, self.raw_words)
        self.assertEqual((record['correlated_events'], len(binary)), (74, 687))
        self.assertEqual(source.parts(self.out / 'traces' / recovery.SELECTED_NAME / 'baseline.o'), source.parts(self.obj))
        content = recovery.backend.frame.isolated(self.body)
        layout = recovery.check_layout(record, words, content)
        summary = recovery.backend.frame.summary(record, content, recovery.backend.MARKERS)
        controls = 0
        for phase in ('frontend', 'optimizer'):
            bad = copy.deepcopy(record)
            next(r for r in bad['records'][phase] if r['name'] == 'def' and r['storage'] == 'M')['length'] += 4
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, words, content)
            controls += 1
        for name in recovery.backend.HOMES:
            store = next(r for r in summary['phases']['frontend']['markers'][name] if r['name'] == 'str' and r['storage'] == 'M')
            bad = copy.deepcopy(record)
            next(r for r in bad['records']['frontend'] if r['byte_offset'] == store['byte_offset'])['offset'] += 4
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, words, content)
            controls += 1
        for profiles in layout['homes'].values():
            for phase, store in profiles.items():
                for key, value in (('offset', store['offset'] + 4), ('dtype', 'J' if store['dtype'] == 'A' else 'A'), ('length', 8)):
                    bad = copy.deepcopy(record)
                    next(r for r in bad['records'][phase] if r['byte_offset'] == store['byte_offset'])[key] = value
                    with self.assertRaises(ValueError):
                        recovery.check_layout(bad, words, content)
                    controls += 1
        for i in range(4):
            for key in ('host_pc', 'frame'):
                bad = copy.deepcopy(record)
                bad['events'][i][key] ^= 4
                with self.assertRaises(ValueError):
                    recovery.check_layout(bad, words, content)
                controls += 1
        for key in ('saved', 'outgoing', 'locals'):
            bad = copy.deepcopy(record)
            bad['events'][-1][key] += 4
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, words, content)
            controls += 1
        for i in layout['sites']:
            bad = list(words)
            bad[i] ^= 4
            with self.assertRaises(ValueError):
                recovery.check_layout(record, bad, content)
            controls += 1
        self.assertEqual(controls, 47)
        self.receipt('backend', newly_owned_capture=True, normal_and_observed_raw_identical=True,
                     source_sha=record['source_sha'], emitter_events=74, AS1_instructions=687,
                     layout=layout, effective_controls=controls, normalized_output_not_AS1_output=True)

    def test_14_stale_guard_and_relocation_controls(self):
        rows = list(csv.DictReader(io.StringIO((self.out / 'expected-scalar-guards.csv').read_text())))
        fields = list(rows[0])
        index = next(i for i, row in enumerate(rows) if row['function'] == source.FUNCTION and int(row['offset'], 0) == 0x754)
        for n, (key, value) in enumerate((('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_32:wrong'))):
            bad = copy.deepcopy(rows)
            bad[index][key] = value
            text = io.StringIO(newline='')
            writer = csv.DictWriter(text, fieldnames=fields)
            writer.writeheader()
            writer.writerows(bad)
            table = self.out / ('negative-scalar-guards-%d.csv' % n)
            table.write_text(text.getvalue())
            with self.assertRaises(ValueError):
                source.literal.padded_object(self.root, self.out, self.obj, 'negative-scalar-guard-%d' % n, table)
        self.receipt('padder-controls', effective_actual_rejections=2)

    def test_15_production_predecessors_and_first_images_unchanged(self):
        recovery.freeze(self.root, self.out)
        for key, path in recovery.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes())
        self.harness.test_07_production_baseline_and_callback_preserved()
        source.checkpoint.freeze_after(self.root)
        self.receipt('protected', entries=len(recovery.PATHS), paths=len(set(recovery.PATHS.values())),
                     immutable_first_image_members=10, installed=False, matching_credit=0, production_guards_added=0)


if __name__ == '__main__':
    unittest.main()
