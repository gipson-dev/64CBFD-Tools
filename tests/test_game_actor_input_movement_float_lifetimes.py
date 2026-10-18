"""Full movement float-lifetime qualification and explicit remaining GPR gap."""
import ctypes
import copy
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_float_lifetimes as recovery
from tools.tests import test_game_actor_input_movement_preload as prior

source, model = recovery.source, prior.model
backend = recovery.previous.previous.backend
original = prior.prior.previous
native = prior.prior.native


class MovementFloatLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / recovery.BUILD
        cls.body = recovery.selected_body()
        cls.obj, cls.words, cls.row = recovery.measure(cls.root, cls.out, recovery.SELECTED_NAME, cls.body)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>959I', cls.rom, source.ROM))
        cls.connected = {0x150F34A0 + i * 4: w for i, w in enumerate(struct.unpack_from('>21I', cls.rom, 0x120950))}
        cls.harness = original.MovementRecoveryTests('test_02_all_three_paths_and_numeric_boundaries')
        for name in ('root', 'out', 'rom', 'obj', 'words', 'truth', 'connected'):
            setattr(cls.harness, name, getattr(cls, name))
        cls.harness.coverage, cls.harness.providers = set(), set()
        cls.work = cls.out / 'traces' / recovery.SELECTED_NAME

    def receipt(self, name, **data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def test_01_complete_sources_neighbors_and_exact_velocity_cap(self):
        self.assertEqual(tuple(self.row[k] for k in ('words', 'frame', 'differences')), (959, 128, 392))
        self.assertEqual(self.row['raw_sha'], recovery.SELECTED_SHA)
        self.assertEqual((self.row['first_unequal_word'], self.row['first_unequal_PC']), (361, 0x150F3A98))
        self.assertEqual(self.words[:361], self.truth[:361])
        self.assertNotIn('u32 heading;', self.body)
        before = (self.out / 'before-record_gate_owner').read_text()
        rows = []
        for name, body in recovery.all_forms():
            self.assertEqual((self.out / (name + '.c')).read_text(), source.recovered_owner(before, body), name)
            raw, _ = source.parts(self.out / (name + '.o'))
            row = json.loads((self.out / (name + '-audit.json')).read_text())
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['raw_sha'])
            words = list(struct.unpack_from('>959I', source.projection.sections(self.out / (name + '-linked.elf'))['.text'][1]))
            self.assertEqual((len(raw) // 4, (-words[0]) & 65535, sum(x != y for x, y in zip(words, self.truth))),
                             tuple(row[k] for k in ('words', 'frame', 'differences')))
            self.assertEqual((row['raw_neighbors'], row['padded_neighbors']), (11, 11))
            self.assertEqual((row['new_guards'], row['matching_credit'], row['installed']), (0, 0, False))
            self.assertEqual(row['padded_differences'], row['differences'])
            first = next((i for i, (a, b) in enumerate(zip(words, self.truth)) if a != b), None)
            rows.append(dict(name=name, words=row['words'], frame=row['frame'], differences=row['differences'],
                             raw_sha=row['raw_sha'], first_unequal_word=first))
        self.assertEqual(len(rows), 28)
        self.receipt('source-controls', complete_forms=len(rows), rows=rows, no_trimming_or_padding_variables=True)

    def test_02_real_backend_and_effective_capture_rejections(self):
        record, words, binary = recovery.finish_trace(self.root, self.out)
        self.assertEqual(words, self.words)
        self.assertEqual((record['correlated_events'], len(binary)), (74, 684))
        content = recovery.frame.isolated(self.body)
        layout = recovery.check_layout(record, words, content)
        summary = recovery.frame.summary(record, content, recovery.MARKERS)
        for name, register in (('cap', 34), ('stickSample', 44)):
            stores = [r for r in summary['phases']['optimizer']['markers'][name] if r['name'] == 'str']
            self.assertEqual([(r['storage'], r['offset'], r['dtype'], r['length']) for r in stores], [('R', register, 'R', 4)])
        fp = [i for i in range(352, 395) if self.truth[i] >> 26 in (49, 57)
              or (self.truth[i] >> 26 == 17 and self.truth[i] >> 21 & 31 >= 16)]
        self.assertTrue(fp)
        for i in fp:
            self.assertEqual(self.words[i], self.truth[i], hex(source.ENTRY + i * 4))
        transfer = (0x150F3B0C - source.ENTRY) // 4
        self.assertEqual((self.truth[transfer], self.words[transfer]), (0x440F2000, 0x440E2000))
        log = (self.work / 'debugger.txt').read_text()
        controls = 0
        with patch.object(backend.nodes, 'CHILD_EXIT', 'TRACE_EXIT inferior=4 code=0'):
            for name in backend.PROBES:
                for prefix in ('FINALIZER_EMIT_INSTALLED ', 'FINALIZER_EMIT_REMOVED '):
                    with self.assertRaises(ValueError):
                        backend.emitter_events(log.replace(prefix + name, ''))
                    controls += 1
            marker = next(line for line in log.splitlines() if line.startswith('FINALIZER_AS1 '))
            event = json.loads(marker.removeprefix('FINALIZER_AS1 '))
            with self.assertRaises(ValueError):
                backend.validate_as1(self.work, log.replace(marker, 'FINALIZER_AS1 ' + json.dumps(dict(event, arguments=['as1', '-O1']))))
            controls += 1
            path, read = self.work / 'as1-input-11.bin', Path.read_bytes
            data = path.read_bytes()
            with patch.object(Path, 'read_bytes', lambda p: data + b'\0' if p == path else read(p)):
                with self.assertRaises(ValueError):
                    backend.validate_as1(self.work, log)
            controls += 1
        path, read_text = self.work / 'allocation-summary.json', Path.read_text
        saved = json.loads(path.read_text())
        for key, value in (('exit_code', 1), ('code_unchanged', False), ('source_sha', '0' * 64),
                           ('whole_owner_target_identical', False), ('compiler_sha256', {})):
            bad = dict(saved, **{key: value})
            with patch.object(Path, 'read_text', lambda p, *a, **k: json.dumps(bad) if p == path else read_text(p, *a, **k)):
                with self.assertRaises(ValueError):
                    recovery.finish_trace(self.root, self.out)
            controls += 1
        self.receipt('backend', layout=layout, emitter_events=74, actual_AS1_instructions=684,
                     effective_capture_controls=controls, optimizer_cap_register=34, optimizer_X_register=44,
                     matching_smoothing_FP_arithmetic_and_storage=len(fp), mixed_MFC1_GPR_gap_retained=True,
                     actual_objects_relocations_pools_and_lifetimes_qualified=True)

    def test_03_effective_new_layout_and_existing_emitted_store_controls(self):
        record = json.loads((self.work / 'return-summary.json').read_text())
        content = recovery.frame.isolated(self.body)
        recovery.check_layout(record, self.words, content)
        summary = recovery.frame.summary(record, content, recovery.MARKERS)
        count = 0
        for phase in ('frontend', 'optimizer'):
            bad = copy.deepcopy(record)
            next(r for r in bad['records'][phase] if r['name'] == 'def' and r['storage'] == 'M')['length'] += 4
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, self.words, content)
            count += 1
        for name in recovery.HOMES:
            store = next(r for r in summary['phases']['frontend']['markers'][name] if r['name'] == 'str' and r['storage'] == 'M')
            for key, value in (('offset', store['offset'] - 4), ('dtype', 'J' if store['dtype'] != 'J' else 'L'), ('length', 1)):
                bad = copy.deepcopy(record)
                next(r for r in bad['records']['frontend'] if r['byte_offset'] == store['byte_offset'])[key] = value
                with self.assertRaisesRegex(ValueError, 'live home'):
                    recovery.check_layout(bad, self.words, content)
                count += 1
        for key, value in (('offset', -88), ('dtype', 'J'), ('length', 2)):
            bad = copy.deepcopy(record)
            next(r for r in bad['records']['frontend'] if r['name'] == 'str' and r['storage'] == 'M' and r['offset'] == -84)[key] = value
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, self.words, content)
            count += 1
        for i in range(4):
            for key in ('host_pc', 'frame'):
                bad = copy.deepcopy(record)
                bad['events'][i][key] ^= 4
                with self.assertRaises(ValueError):
                    recovery.check_layout(bad, self.words, content)
                count += 1
        for key, value in (('locals', 88), ('saved', 24), ('temporary', 4)):
            bad = copy.deepcopy(record)
            bad['events'][-1][key] = value
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, self.words, content)
            count += 1
        call = self.words.index(0x0D4169BE)
        slots = [0, 5, self.words.index(0x0D416973) + 1]
        for op, offset in ((43, 0x50), (43, 0x34), (57, 0x48)):
            slots.append(next(i for i in range(call - 5, call + 2) if self.words[i] >> 26 == op and self.words[i] & 65535 == offset))
        for i in slots:
            bad = list(self.words)
            bad[i] ^= 4
            with self.assertRaises(ValueError):
                recovery.check_layout(record, bad, content)
            count += 1
        self.assertEqual(count, 55)
        self.receipt('layout-controls', effective_controls=count, all_previous_homes_and_new_cap_X_homes_checked=True)

    def test_04_complete_public_corpus_and_fired_cap_boundaries(self):
        prior.prior.MovementReturnTests.test_05_complete_public_width_filter_mutation_and_FP_corpus(self)
        count, fired = 0, 0
        for held, velocity in itertools.product((0, 101), (-40., -30., -29.999998, -0., 0., 30.)):
            boundary = 2100. + (16. if held else 0.)
            for position in (boundary, model.floating(model.bits(boundary) + 1), 2200.):
                spec = dict(held=held, velocity=velocity, position=position)
                self.harness.compare(spec)
                memory, case = model.fixture(self.rom, **spec)
                for words in (self.truth, self.words):
                    machine = model.Oracle(words, memory, case, self.connected).run()
                    self.assertEqual(0x150F3A38 in machine.visits, position > boundary)
                fired += int(position > boundary)
                count += 1
        self.assertEqual((count, fired), (36, 24))
        self.receipt('cap-public', complete_cases=count, fired_cap_cases=fired, actual_threshold=2100.,
                     held_descent_accounted_for=True, not_hardware_FCSR_acceptance=True)

    pair_at = prior.MovementPreloadTests.pair_at
    complete_prefixes = prior.MovementPreloadTests.complete_prefixes

    def test_05_active_FP_lifetimes_complete_disabled_and_mode_zero_private(self):
        cuts = (42, 50, 41, 43, 44)
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
                            self.assertEqual([x.current_pc for x in pair], [0x150F3AB8] * 2)
                            self.assertEqual([i for i, (a, b) in enumerate(zip(pair[0].r, pair[1].r)) if a != b], [10, 11, 24])
                            self.assertEqual([0x150F3A38 in x.visits for x in pair], [position == 2200.] * 2)
                    states += 1
        self.assertEqual((states, totals), (100, {100.: 880, 2200.: 3720}))
        disabled = (dict(phase=p, pattern=b, gate=g, held=h, disabled=1)
                    for p, b, g, h in itertools.product((0, 8), (0, 1), range(5), (0, 100, 101, 124)))
        disabled_states, disabled_prefixes = self.complete_prefixes(disabled)
        mode_zero = (dict(phase=p, pattern=b, gate=g, mode=0, nearby=n, depth=d, pressed=a,
                          position=-101. if a else 100.)
                     for p, b, g, n, d, a in itertools.product((0, 8), (0, 1), range(5),
                                                              (0, 101), (0., 100.00001), (0, 0xC000)))
        zero_states, zero_prefixes = self.complete_prefixes(mode_zero)
        self.assertEqual((disabled_states, disabled_prefixes, zero_states, zero_prefixes), (80, 2700, 160, 8320))
        self.receipt('private', active_states=states, equal_active_prefixes=sum(totals.values()),
                     low_position_prefixes=880, fired_high_position_prefixes=3720, first_PC='0x150F3AB8',
                     GPR_gap=[10, 11, 24], all_FPR_memory_PC_LO_condition_agree_at_first_gap=True,
                     disabled_complete_states=80, disabled_fault_prefixes=2700,
                     mode_zero_complete_states=160, mode_zero_fault_prefixes=8320,
                     full_opaque_provider_or_hardware_acceptance_not_claimed=True)

    def test_06_native32_rebases_aliases_and_cap_boundaries(self):
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
        with patch.object(model, 'fixture', fixture), patch.object(source, 'SELECTED', self.body):
            row = native.qualify(self.root, self.out, self.rom, specs)
            for spec in specs[-19:]:
                self.harness.compare(spec)
        self.assertEqual((row['cases_per_profile'], row['effective_controls']), (149, 8))
        count = 0
        for alias, gate, mode in itertools.product((0x800CC284, 0x800CC288, model.SLOT), (0, 1), (0, 1)):
            memory, case = model.fixture(self.rom, gate=gate, mode=mode, pattern=1, pressed=0x8000)
            model.put(memory, model.SLOT, alias)
            memory.update({0x800C0080 + i: 0xA5 for i in range(32)})
            expected = model.reference(memory, case)
            for words in (self.truth, self.words):
                actual = model.Oracle(words, memory, case, self.connected).run()
                self.assertEqual(model.public(actual.memory), model.public(expected[0]))
                self.assertEqual(actual.calls, expected[1])
                self.assertEqual(actual.observations, expected[2])
            count += 1
        self.receipt('native-rebases-aliases', native_cases_per_profile=149, profiles=['O2', 'O0'], UBSan=True,
                     effective_native_controls=8, new_cap_guest_and_native_cases=10, unsigned_heading_cases=9,
                     text_rebases=2, rebase_cases=12, guest_alias_cases=count)

    def test_07_effective_cap_equality_control(self):
        body = recovery.replace(self.body, '-30.0f < (velocity = actor->verticalVelocity)',
                                '-30.0f <= (velocity = actor->verticalVelocity)')
        _, words, _ = recovery.measure(self.root, self.out, 'negative-cap-equality', body)
        memory, case = model.fixture(self.rom, position=2200., held=101, velocity=-30.)
        expected = model.reference(memory, case)
        actual = model.Oracle(words, memory, case, self.connected).run()
        self.assertIn(0x150F3A38, actual.visits)
        self.assertTrue(model.public(actual.memory) != model.public(expected[0]) or actual.calls != expected[1]
                        or actual.observations != expected[2])
        self.receipt('cap-control', complete_wrong_C_body_rejected=True, equality_boundary=-30., gate_fired=True)

    def test_08_production_data_and_all_immutable_members(self):
        recovery.freeze(self.root, self.out)
        for key, path in recovery.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes())
        self.harness.test_07_production_baseline_and_callback_preserved()
        source.checkpoint.freeze_after(self.root)
        self.receipt('protected', entries=len(recovery.PATHS), paths=len(set(recovery.PATHS.values())),
                     ELF_sha=hashlib.sha256((self.root / 'conker/build/conker.us.elf').read_bytes()).hexdigest(),
                     immutable_first_image_members=10, installed=False, new_guards=0, matching_credit=0)


if __name__ == '__main__':
    unittest.main()
