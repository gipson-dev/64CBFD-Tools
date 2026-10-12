"""Qualify carrier layout screens without confusing T0 traffic with flag state."""
import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.experiments import game_text_measurer_frontend_trace as front
from tools.tests import test_game_text_measurer_logic_candidates as semantics
from tools.tests import test_game_text_measurer_recovery as recovery


class RegisterObserver(semantics.LogicalMeasurerOracle):
    def __init__(self, *args, **kwargs):
        self.metric_t0 = []
        super().__init__(*args, **kwargs)

    def record_call(self, target):
        if target == recovery.metrics.ENTRY:
            self.metric_t0.append(self.r[8])
        super().record_call(target)


class GameTextMeasurerCarrierLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-text-measurer-carrier-layout-test'
        cls.out.mkdir(exist_ok=True)
        cls.bodies = dict(front.logic.layout_candidates())
        cls.compiled = {name: front.logic.screen.compile_candidate(cls.root, cls.out, name, body)
                        for name, body in cls.bodies.items()}
        cls.reference = front.logic.screen.compile_candidate(cls.root, cls.out, 'simple-reference',
            dict(front.logic.carrier_candidates())['carrier-simple-named'])
        cls.captures = {name: front.capture_frontend(cls.root, cls.out, 'capture-' + name, cls.bodies[name])
                        for name in ('flag-before-record', 'record-scope-normalize')}
        recovery.GameTextMeasurerRecoveryTests.setUpClass()
        cls.oracle = recovery.GameTextMeasurerRecoveryTests('test_05_production_and_protected_data_unchanged')
        cls.semantic = semantics.GameTextMeasurerLogicTests('test_02_all_nine_distinct_bodies_preserve_complete_public_semantics')
        cls.semantic.oracle = cls.oracle

    def test_01_ten_source_forms_ten_bodies_and_concrete_shape_rejections(self):
        expected = {'ordinary-before-effects': (222, 0x90, 193),
                    'ordinary-before-effects-scalars': (222, 0x90, 193),
                    'ordinary-before-effects-direct-font': (224, 0x90, 220),
                    'ternary-before-effects': (223, 0x98, 216),
                    'ternary-before-effects-direct-font': (226, 0x98, 225),
                    'record-scope-normalize': (216, 0x90, 184)}
        self.assertEqual(len(self.compiled), 10)
        self.assertEqual(len({tuple(words) for _, words in self.compiled.values()}), 10)
        for name, (meta, words) in self.compiled.items():
            self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), expected.get(name, (216, 0x90, 179)))
            self.assertEqual(meta['pool_bytes'], 0)
            self.assertNotEqual(words, self.oracle.retail)
            self.assertNotEqual(words[0], self.oracle.retail[0])
            self.assertFalse(any(word >> 26 == 2 for word in words))
        for name in ('flag-before-record', 'scalar-metrics', 'scalar-metrics-flag-first', 'record-scope-text'):
            self.assertEqual(self.compiled[name][1][:13], self.reference[1][:13])
            self.assertNotEqual(self.compiled[name][1], self.reference[1])
        self.assertNotEqual(self.compiled['ordinary-before-effects'][1], self.compiled['ordinary-before-effects-scalars'][1])

    def test_02_all_ten_bodies_preserve_bounded_public_semantics(self):
        unique = {}
        for name, (_, words) in self.compiled.items():
            unique.setdefault(tuple(words), name)
        counts = {}
        for words, name in unique.items():
            count = 0
            for byte, phase in itertools.product(range(256), (0, 8)):
                self.semantic.compare(list(words), bytes((byte, 0, 0)) if byte != 0xBC else bytes((byte, 7, 65, 0)), phase=phase)
                count += 1
            for text, alias, phase, scales in itertools.product((b'\0', b'A\0', b'A\nB\0', b' AB\0',
                    bytes((0xBC, 0, 65, 0)), bytes((0xA8, 0xAA, 0xBA, 0xAE, 65, 0))),
                    range(10), (0, 8), ((1.0, 1.0), (0.75, 1.25))):
                self.semantic.compare(list(words), text, alias, phase, scales)
                count += 1
            self.semantic.compare(list(words), b'A\0', null=True)
            self.semantic.compare(list(words), bytes((0xAA, 0)), factor=1.0 / 18.0)
            memory, args = self.oracle.font_pointer_fixture()
            model = semantics.LogicalMeasurerOracle(list(words), memory, args, self.oracle.connected).run()
            expected = recovery.Reference(memory, args).run()
            self.assertEqual(recovery.public(model.memory), recovery.public(expected.memory))
            self.assertEqual(model.calls, expected.calls)
            counts[name] = count + 3
            self.assertEqual(counts[name], 755)
        self.assertEqual(sum(counts.values()), 7550)
        (self.out / 'public.json').write_text(json.dumps(dict(counts=counts, comparisons=sum(counts.values()),
            actual_helpers=True, installable=False, full_private_fault_native_owner_qualification=False), indent=2) + '\n')

    def test_03_t0_call_save_is_maximum_width_not_the_font_flag(self):
        name = 'ordinary-before-effects-direct-font'
        words = self.compiled[name][1]
        self.assertIn(0x00004025, words)
        self.assertIn(0xAFA80088, words)
        self.assertIn(0x8FA80088, words)
        for phase in (0, 8):
            memory, args = recovery.fixture(b'AB\n\xA8\0', self.oracle.table)
            prefix = recovery.Reference(*recovery.fixture(b'AB\n\0', self.oracle.table)).run()
            maximum = recovery.read(prefix.memory, prefix.args[1])
            self.assertGreater(maximum, 0)
            original = RegisterObserver(self.oracle.retail, memory, args, self.oracle.connected,
                                        phase=phase, entry=front.logic.screen.ENTRY).run()
            candidate = RegisterObserver(words, memory, args, self.oracle.connected, phase=phase).run()
            expected = recovery.Reference(memory, args).run()
            self.assertEqual(original.metric_t0, [0])
            self.assertEqual(candidate.metric_t0, [maximum])
            for model in (original, candidate):
                self.assertEqual(recovery.public(model.memory), recovery.public(expected.memory))
                self.assertEqual(model.calls, expected.calls)
            plain = semantics.LogicalMeasurerOracle(words, memory, args, self.oracle.connected, phase=phase).run()
            self.assertEqual(candidate.events, plain.events)
            self.assertEqual(candidate.r, plain.r)
            self.assertEqual(candidate.f, plain.f)
            self.assertEqual(candidate.memory, plain.memory)

    def test_04_lexical_record_scope_does_not_move_the_call_save_home(self):
        expected = {'flag-before-record': (18632, 839, 18048, 799, -44),
                    'record-scope-normalize': (18648, 841, 18080, 802, -48)}
        for name, capture in self.captures.items():
            sizes = expected[name]
            self.assertTrue(capture['code_unchanged'])
            self.assertFalse(capture['installable'])
            self.assertEqual((capture['frontend']['bytes'], capture['record_count'],
                              capture['optimizer']['bytes'], capture['optimizer_record_count']), sizes[:4])
            vregs = [item for item in capture['records'] if item['name'] == 'vreg']
            self.assertEqual([(item['storage'], item['level'], item['length'], item['offset']) for item in vregs],
                             [('M', 1, 4, offset) for offset in (-52, -56, -60, -64)])
            addresses = [item for item in capture['records'] if item['name'] == 'lda' and item['storage'] == 'M']
            self.assertEqual([(item['length'], item['offset']) for item in addresses], [(20, sizes[4])] * 5)
            saves = [item for item in capture['optimizer_records'] if item['name'] in ('rstr', 'rlod')]
            self.assertEqual([(item['name'], item['storage'], item['level'], item['offset']) for item in saves],
                             [('rstr', 'M', 8, -56), ('rlod', 'M', 8, -56)])

    def test_05_frozen_production_and_effective_corruption_controls(self):
        self.oracle.test_05_production_and_protected_data_unchanged()
        self.oracle.test_06_effective_immutable_production_controls()

    def test_06_effective_source_and_mutually_exclusive_cli_controls(self):
        bad = self.bodies['ordinary-before-effects'].replace('((u32)*width + 4)', '((u32)*width + 5)')
        self.assertNotEqual(bad, self.bodies['ordinary-before-effects'])
        _, words = front.logic.screen.compile_candidate(self.root, self.out, 'bad-space-width', bad)
        with self.assertRaises(AssertionError):
            self.semantic.compare(words, b' \0')
        result = subprocess.run([sys.executable, '-m', 'tools.experiments.game_text_measurer_logic_candidates',
                                 '--carriers', '--layouts'], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('not allowed with argument', result.stderr)


if __name__ == '__main__':
    unittest.main()
