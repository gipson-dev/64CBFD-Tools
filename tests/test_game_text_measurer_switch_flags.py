"""Statement flags and literal register hints do not prove retail T0 lifetime."""
import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.experiments import game_text_measurer_frontend_trace as front
from tools.experiments import game_text_measurer_switch_flags as screen
from tools.tests import test_game_text_measurer_logic_candidates as semantics
from tools.tests import test_game_text_measurer_predicate_snapshot as snapshot
from tools.tests import test_game_text_measurer_recovery as recovery


class SavedFlagObserver(snapshot.TextObserver):
    def __init__(self, *args, **kwargs):
        self.normalizer_s4 = []
        self.metrics_s4 = []
        super().__init__(*args, **kwargs)

    def record_call(self, target):
        if target == recovery.lookup.ENTRY:
            self.normalizer_s4.append(self.r[20])
        elif target == recovery.metrics.ENTRY:
            self.metrics_s4.append(self.r[20])
        super().record_call(target)


class GameTextMeasurerSwitchFlagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-text-measurer-switch-flags-test'
        cls.out.mkdir(exist_ok=True)
        cls.bodies = dict(screen.candidates())
        cls.compiled = {name: screen.logic.screen.compile_candidate(cls.root, cls.out, name, body)
                        for name, body in cls.bodies.items()}
        recovery.GameTextMeasurerRecoveryTests.setUpClass()
        cls.oracle = recovery.GameTextMeasurerRecoveryTests('test_05_production_and_protected_data_unchanged')
        cls.semantic = semantics.GameTextMeasurerLogicTests('test_02_all_nine_distinct_bodies_preserve_complete_public_semantics')
        cls.semantic.oracle = cls.oracle

    def test_01_six_forms_three_bodies_and_missing_retail_lifetime(self):
        self.assertEqual(len(self.compiled), 6)
        self.assertEqual(len({tuple(words) for _, words in self.compiled.values()}), 3)
        for name, (meta, words) in self.compiled.items():
            expected = (217, 0x80, 212) if name == 'five-field-scoped-register-flag' else (
                (216, 0x80, 203) if name in ('five-field-newline-switch', 'five-field-glyph-switch') else (216, 0x80, 204))
            self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), expected)
            self.assertNotEqual(words[:13], self.oracle.retail[:13])
            self.assertNotEqual(words, self.oracle.retail)
            self.assertNotIn(0x00004025, words)
            self.assertFalse(any(w & 0xFFFF0000 in (0xAFA80000, 0x8FA80000) for w in words))
            self.assertFalse(any(w >> 26 == 2 for w in words))
            saves = [w >> 16 & 31 for w in words[:36]
                     if w >> 26 == 43 and w >> 21 & 31 == 29 and 16 <= w >> 16 & 31 <= 23]
            self.assertEqual(sorted(saves), list(range(16, 24)))
            self.assertEqual(words[39], 0x0000A025)
            self.assertNotIn('metrics.useFont', self.bodies[name])
            self.assertIn('s32 height, width; } metrics;', self.bodies[name])
            pools = screen.logic.screen.compiler.sections(self.out / (name + '.o'))
            self.assertTrue(all(not value[1] for section, value in pools.items()
                if section.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))))

    def test_02_complete_object_identity_and_fourteen_real_word_differences(self):
        parser = screen.logic.screen.compiler.parse_object
        objects = {name: parser(self.out / (name + '.o')) for name in self.bodies}
        reference = 'five-field-if-reference'
        for name in ('five-field-both-switches', 'five-field-register-flag'):
            self.assertEqual(objects[name], objects[reference])
        self.assertEqual(objects['five-field-newline-switch'], objects['five-field-glyph-switch'])
        left, right = self.compiled[reference][1], self.compiled['five-field-newline-switch'][1]
        self.assertEqual([i for i, (a, b) in enumerate(zip(left, right)) if a != b],
                         [1, 8, 10, 18, 20, 101, 103, 115, 124, 127, 165, 168, 195, 204])
        self.assertEqual(objects[reference][1:], objects['five-field-newline-switch'][1:])
        self.assertNotEqual(objects['five-field-scoped-register-flag'], objects[reference])

    def test_03_three_distinct_bodies_preserve_bounded_public_semantics(self):
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
        self.assertEqual(sum(counts.values()), 2265)
        (self.out / 'public.json').write_text(json.dumps(dict(counts=counts, comparisons=sum(counts.values()),
            actual_helpers=True, installable=False, full_private_fault_native_owner_qualification=False), indent=2) + '\n')

    def test_04_saved_flag_is_not_t0_and_all_first_read_observers_fire(self):
        records = []
        for name in ('five-field-if-reference', 'five-field-newline-switch', 'five-field-scoped-register-flag'):
            words = self.compiled[name][1]
            for phase, text in itertools.product((0, 8), (b'A\0', b' \0', b'AB\n\xA8\0')):
                memory, args = recovery.fixture(text, self.oracle.table)
                original = SavedFlagObserver(self.oracle.retail, memory, args, self.oracle.connected,
                                            phase=phase, entry=screen.logic.screen.ENTRY).run()
                candidate = SavedFlagObserver(words, memory, args, self.oracle.connected, phase=phase).run()
                plain = semantics.LogicalMeasurerOracle(words, memory, args, self.oracle.connected, phase=phase).run()
                self.assertEqual(candidate.events, plain.events)
                self.assertEqual(candidate.r, plain.r)
                self.assertEqual(candidate.f, plain.f)
                self.assertEqual(candidate.memory, plain.memory)
                expected = recovery.Reference(memory, args).run()
                self.assertEqual(recovery.public(candidate.memory), recovery.public(expected.memory))
                self.assertEqual(candidate.calls, expected.calls)
                self.assertEqual(candidate.normalizer_s4, [0] * len(candidate.normalizer_s4))
                self.assertGreater(len(candidate.normalizer_s4), 0)
                if text == b'A\0':
                    self.assertEqual(original.first_text_t0, [0])
                    self.assertEqual(candidate.first_text_t0, [50])
                elif text == b' \0':
                    self.assertEqual(original.first_width_t0, [0])
                    self.assertEqual(candidate.first_width_t0, [0x5A000008])
                else:
                    self.assertEqual(original.metric_t0, [0])
                    self.assertEqual(candidate.metric_t0, [50])
                    self.assertEqual(candidate.metrics_s4, [0])
                records.append(dict(name=name, phase=phase, text=text.hex(), first_text_t0=candidate.first_text_t0,
                    first_width_t0=candidate.first_width_t0, metrics_t0=candidate.metric_t0, metrics_s4=candidate.metrics_s4,
                    installable=False, full_instruction_fault_qualification=False))
        (self.out / 'roles.json').write_text(json.dumps(records, indent=2) + '\n')

    def test_05_completed_register_hint_captures_and_whole_optimizer_stream_identity(self):
        names = ('five-field-if-reference', 'five-field-register-flag', 'five-field-scoped-register-flag')
        captures = {name: front.capture_frontend(self.root, self.out, 'capture-' + name, self.bodies[name]) for name in names}
        sizes = {names[0]: (18592, 853, 18216, 828), names[1]: (18608, 854, 18216, 828),
                 names[2]: (18632, 857, 18256, 832)}
        vregs = {names[0]: [], names[1]: [(216, 'M', 0, 4, -44)], names[2]: [(1560, 'M', 0, 4, -48)]}
        for name, capture in captures.items():
            self.assertTrue(capture['code_unchanged'])
            self.assertFalse(capture['installable'])
            self.assertEqual((capture['frontend']['bytes'], capture['record_count'],
                              capture['optimizer']['bytes'], capture['optimizer_record_count']), sizes[name])
            self.assertEqual([(x['byte_offset'], x['storage'], x['level'], x['length'], x['offset'])
                              for x in capture['records'] if x['name'] == 'vreg'], vregs[name])
            self.assertFalse(any(x['name'] in ('rstr', 'rlod', 'vreg') for x in capture['optimizer_records']))
        left, right = (self.out / ('capture-' + name) for name in names[:2])
        self.assertNotEqual((left / 'frontend.ucode').read_bytes(), (right / 'frontend.ucode').read_bytes())
        self.assertEqual((left / 'optimizer.ucode').read_bytes(), (right / 'optimizer.ucode').read_bytes())

    def test_06_effective_source_cli_and_immutable_controls(self):
        body = self.bodies['five-field-newline-switch']
        bad = body.replace('case 0xA:', 'case 0xB:')
        self.assertNotEqual(bad, body)
        _, words = screen.logic.screen.compile_candidate(self.root, self.out, 'wrong-newline', bad)
        with self.assertRaises(AssertionError):
            self.semantic.compare(words, b'A\nB\0')
        result = subprocess.run([sys.executable, '-m', 'tools.experiments.game_text_measurer_switch_flags',
                                 '--filter', 'recovered'], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('invalid choice', result.stderr)
        self.assertEqual(front.compiler_fingerprints(self.root),
                         dict(front.trace.qualified.COMPILERS, ugen=front.trace.UGEN_SHA256, cfe=front.CFE_SHA256))
        self.oracle.test_05_production_and_protected_data_unchanged()
        self.oracle.test_06_effective_immutable_production_controls()


if __name__ == '__main__':
    unittest.main()
