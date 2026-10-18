"""Complete heading/velocity continuation qualification, with no new guards."""
import ctypes
import copy
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_recovery as source
from tools.experiments import game_actor_input_movement_heading_continuation as recovery
from tools.tests import test_game_actor_input_movement_flag_paths as prior

model = prior.model
original, native = prior.prior.prior.original, prior.prior.prior.native
CLAMP_VALUES = (-40., model.floating(model.bits(-34.) + 1), -34., model.floating(model.bits(-34.) - 1),
                -0., 0., model.floating(model.bits(26.) - 1), 26., model.floating(model.bits(26.) + 1), 30.)


class MovementHeadingContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / recovery.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = recovery.qualify(cls.root, cls.out)
        cls.body = recovery.selected_body()
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>959I', cls.rom, source.ROM))
        cls.connected = {0x150F34A0 + i * 4: w for i, w in enumerate(struct.unpack_from('>21I', cls.rom, 0x120950))}
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

    def test_01_complete_sources_actual_padder_and_unchanged_28_research_rows(self):
        self.assertEqual(tuple(self.row[k] for k in ('words', 'frame', 'differences', 'normalized_differences')), (959, 128, 270, 242))
        self.assertEqual((self.row['normalized_exact_opening_words'], self.row['normalized_first_PC']), (469, 0x150F3C48))
        self.assertEqual(self.words[:469], self.truth[:469])
        self.assertEqual(self.row['normalized_raw_sha'], recovery.NORMALIZED_SHA)
        self.assertEqual((self.row['new_research_guards'], self.row['production_guards_added'], self.row['matching_credit']), (0, 0, 0))
        self.assertFalse(self.row['installed'])
        self.assertEqual((self.out / 'expected-continuation-guards.csv').read_bytes(),
                         (self.root / recovery.previous.BUILD / 'expected-flag-guards.csv').read_bytes())
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
            self.assertEqual(audit['raw_neighbors'], 11)
            if len(words) > 959:
                self.assertTrue(audit['padder_rejected'])
            else:
                self.assertEqual(audit['padded_neighbors'], 11)
            rows.append(dict(name=name, words=len(words), differences=audit['differences']))
        self.assertEqual((len(rows), sum(r['words'] > 959 for r in rows)), (29, 1))
        for start, end in ((0x150F3CB4, 0x150F3D04), (0x150F3E50, 0x150F3EB8)):
            lo, hi = (start - source.ENTRY) // 4, (end - source.ENTRY) // 4
            self.assertEqual(self.raw_words[lo:hi], self.truth[lo:hi])
        self.receipt('source-controls', complete_forms=29, overflow_rejections=1, rows=rows,
                     exact_raw_C_clamp_span_words=20, exact_raw_C_pitch_span_words=26,
                     previous_research_CSV_byte_identical=True, no_new_research_or_production_guards=True)

    def test_02_AST_zero_lifetime_and_effective_source_controls(self):
        proof = recovery.check_zero_lifetime(self.body)
        self.assertEqual((proof['identifier_uses'], proof['writes']), (4, 2))
        initial = '    contactHeight = 0.0f;'
        pitch = '            pitchValue = (actor->verticalVelocity - contactHeight) * -2.0f;'
        variants = (
            recovery.replace(self.body, initial, '    contactHeight = 1.0f;'),
            recovery.replace(self.body, initial, '    if (actor->held) { contactHeight = 0.0f; }'),
            recovery.replace(self.body, pitch, '            contactHeight = 0.0f;\n' + pitch),
            recovery.replace(self.body, pitch, '            func_15059140((MovementActor34F4 *)&contactHeight);\n' + pitch),
            recovery.replace(self.body, pitch, '            while (1) {\n' + pitch + '\n            }'),
            recovery.replace(self.body, pitch, pitch + '\n            goto disabled_done;'),
            recovery.replace(self.body, '            contactHeight = 50.0f;', '            contactHeight = 25.0f;'),
            recovery.replace(self.body, 'actor->verticalVelocity - contactHeight', 'actor->verticalVelocity - (&contactHeight)'),
        )
        for body in variants:
            with self.assertRaises(ValueError):
                recovery.check_zero_lifetime(body)
        self.receipt('zero-lifetime', proof=proof, effective_AST_controls=len(variants),
                     cpp_and_C_parser_used=True, arbitrary_caller_stack_alias_not_claimed=True)

    def test_03_signed_Y_read_before_zero_stores_guest_alias_and_old_rejection(self):
        prior_obj = self.root / recovery.previous.BUILD / 'button-velocity.o'
        raw, _ = source.parts(prior_obj)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), recovery.previous.SELECTED_SHA)
        old_words = source.linked(self.root, self.out, prior_obj, 'qualified-previous-linked')
        cases, rejected = 0, 0
        for button, y, phase in itertools.product((0x4010, 0xC010), (-128, -23, 1, 127), (0, 8)):
            memory, case = model.fixture(self.rom, actor=model.INPUT - 0x20, buttons=button, y=y, phase=phase)
            machines = [model.Oracle(w, memory, case, self.connected).run() for w in (self.truth, self.raw_words, self.words)]
            expected = machines[0]
            for machine in machines:
                self.assertIn(0x150F3E14, machine.visits)
                self.assertEqual(model.public(machine.memory), model.public(expected.memory))
                self.assertEqual((machine.calls, machine.observations, machine.fired),
                                 (expected.calls, expected.observations, expected.fired))
            old = model.Oracle(old_words, memory, case, self.connected).run()
            self.assertTrue(model.public(old.memory) != model.public(expected.memory) or old.observations != expected.observations)
            rejected += 1
            cases += 1
        self.assertEqual((cases, rejected), (16, 16))
        self.receipt('Y-alias', complete_guest_cases=cases, effective_old_C_rejections=rejected,
                     actual_retail_is_reference=True, pitch_gate_fired=True,
                     prior_high_level_model_not_used_for_this_new_alias_order=True,
                     portable_C_type_alias_and_native_byte_order_not_claimed=True)

    test_04_complete_public_FP_and_cap_corpus = prior.MovementFlagPathTests.test_04_complete_three_way_public_and_cap_boundaries
    pair_at = prior.MovementFlagPathTests.pair_at
    complete_prefixes = prior.MovementFlagPathTests.complete_prefixes
    test_05_complete_disabled_mode_zero_and_remaining_private_frontier = prior.MovementFlagPathTests.test_05_new_private_frontier_and_complete_disabled_and_mode_zero

    def test_06_clamp_boundaries_and_effective_compiled_wrong_limits(self):
        cases, fired = 0, 0
        for held, velocity, mutation in itertools.product((0, 101), CLAMP_VALUES, (0, 4)):
            spec = dict(held=held, velocity=velocity, mutation=mutation)
            self.harness.compare(spec)
            memory, case = model.fixture(self.rom, **spec)
            for words in (self.truth, self.raw_words, self.words):
                machine = model.Oracle(words, memory, case, self.connected).run()
                self.assertEqual(0x150F3CB4 in machine.visits, held == 0)
            fired += int(held == 0)
            cases += 1
        for name, before, after, velocity in (
            ('negative-upper-25', '26.0f', '25.0f', 26.),
            ('negative-lower-33', '-34.0f', '-33.0f', -34.),
        ):
            body = recovery.replace(self.body, before, after, 2)
            _, words, _ = recovery.measure(self.root, self.out, name, body)
            memory, case = model.fixture(self.rom, velocity=velocity)
            expected = model.Oracle(self.truth, memory, case, self.connected).run()
            actual = model.Oracle(words, memory, case, self.connected).run()
            self.assertIn(0x150F3CB4, actual.visits)
            self.assertTrue(model.public(actual.memory) != model.public(expected.memory),
                            'Compiled wrong clamp did not change the public result')
        self.assertEqual((cases, fired), (40, 20))
        self.receipt('clamp-boundaries', complete_cases=cases, fired_clamp_cases=fired,
                     signed_zero_and_adjacent_floats=True, provider_mutation_before_clamp=True,
                     effective_compiled_wrong_limits=2)

    def test_07_native32_UBSan_rebases_aliases_and_new_clamps(self):
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
        specs.extend(dict(held=h, velocity=v) for h, v in itertools.product((0, 101), CLAMP_VALUES))
        with patch.object(model, 'fixture', fixture), patch.object(source, 'SELECTED', self.body):
            row = native.qualify(self.root, self.out, self.rom, specs)
        self.assertEqual((row['cases_per_profile'], row['effective_controls']), (169, 8))
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
        self.receipt('native-rebases-aliases', native_cases_per_profile=169, profiles=['O2', 'O0'], UBSan=True,
                     native_controls=8, new_native_clamps=20, text_rebases=2, rebase_cases=12, guest_aliases=aliases)

    def test_08_fresh_backend_layout_and_effective_controls(self):
        record, words, binary = recovery.backend.finish_trace(self.root, self.out, recovery.SELECTED_NAME, self.body)
        self.assertEqual(words, self.raw_words)
        self.assertEqual((record['correlated_events'], len(binary)), (74, 686))
        work = self.out / 'traces' / recovery.SELECTED_NAME
        self.assertEqual(source.parts(work / 'baseline.o'), source.parts(self.obj))
        content = recovery.backend.frame.isolated(self.body)
        layout = recovery.check_layout(record, words, content)
        count = 0
        for phase, markers in layout['stores'].items():
            for rows in markers.values():
                for store in rows:
                    for key, value in (('offset', store['offset'] + 4), ('dtype', 'A'), ('length', 8)):
                        bad = copy.deepcopy(record)
                        next(r for r in bad['records'][phase] if r['byte_offset'] == store['byte_offset'])[key] = value
                        with self.assertRaises(ValueError):
                            recovery.check_layout(bad, words, content)
                        count += 1
        for pc in (0x150F3CBC, 0x150F3CD8, 0x150F3E14, 0x150F3E58, 0x150F3EB4):
            bad = list(words)
            bad[(pc - source.ENTRY) // 4] ^= 64
            with self.assertRaises(ValueError):
                recovery.check_layout(record, bad, content)
            count += 1
        self.receipt('backend', newly_owned_capture=True, raw_normal_observed_identical=True,
                     source_sha=record['source_sha'], emitter_events=74, AS1_instructions=686,
                     layout=layout, effective_controls=count, normalized_output_not_AS1_output=True)

    def test_09_all_production_first_images_and_predecessors_unchanged(self):
        recovery.freeze(self.root, self.out)
        for key, path in recovery.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes())
        self.harness.test_07_production_baseline_and_callback_preserved()
        source.checkpoint.freeze_after(self.root)
        self.receipt('protected', entries=len(recovery.PATHS), paths=len(set(recovery.PATHS.values())),
                     immutable_first_image_members=10, installed=False, matching_credit=0, new_guards=0)


if __name__ == '__main__':
    unittest.main()
