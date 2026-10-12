"""Qualify address/height reuse without claiming a complete retail match."""
import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.experiments import game_text_measurer_work_lifetime as screen
from tools.experiments import game_text_measurer_frontend_trace as front
from tools.tests import test_game_text_measurer_logic_candidates as semantics
from tools.tests import test_game_text_measurer_predicate_snapshot as snapshot
from tools.tests import test_game_text_measurer_recovery as recovery


class GameTextMeasurerWorkLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-text-measurer-work-lifetime-test'
        cls.out.mkdir(exist_ok=True)
        cls.bodies = dict(screen.candidates())
        cls.compiled = {name: screen.source.logic.screen.compile_candidate(cls.root, cls.out, name, body)
                        for name, body in cls.bodies.items()}
        recovery.GameTextMeasurerRecoveryTests.setUpClass()
        cls.oracle = recovery.GameTextMeasurerRecoveryTests('test_05_production_and_protected_data_unchanged')
        cls.semantic = semantics.GameTextMeasurerLogicTests('test_02_all_nine_distinct_bodies_preserve_complete_public_semantics')
        cls.semantic.oracle = cls.oracle

    def test_01_seven_saves_frame_and_home_coexist_but_complete_match_is_rejected(self):
        shapes = {'direct-control': (218, 210, 8), 'integer-address-work': (216, 181, 7),
                  'forward-ordinary-work': (217, 176, 7), 'forward-ternary-work': (216, 171, 7),
                  'excluded-join-control': (217, 120, 7)}
        compiler = screen.source.logic.screen.compiler
        self.assertEqual(len({tuple(words) for _, words in self.compiled.values()}), 5)
        for name, (meta, words) in self.compiled.items():
            self.assertEqual((meta['body_words'], meta['differences'], meta['frame']), (*shapes[name][:2], 0x80))
            self.assertNotEqual(words, self.oracle.retail)
            if name == 'forward-ternary-work':
                self.assertEqual(words[:13], self.oracle.retail[:13])
                self.assertEqual(words[14:28], self.oracle.retail[14:28])
            else:
                self.assertNotEqual(words[:13], self.oracle.retail[:13])
            saves = [w >> 16 & 31 for w in words[:36] if w >> 26 == 43 and w >> 21 & 31 == 29
                     and (16 <= w >> 16 & 31 <= 23 or w >> 16 & 31 == 30)]
            self.assertEqual(len(saves), shapes[name][2])
            if name != 'direct-control':
                self.assertEqual(sorted(saves), list(range(16, 23)))
                role_differences = [] if name == 'forward-ternary-work' else [1, 8, 10]
                self.assertEqual([i for i, (a, b) in enumerate(zip(words[:13], self.oracle.retail[:13])) if a != b], role_differences)
                relocs = compiler.parse_object(self.out / (name + '.o'))[2]
                font = [(offset // 4, kind) for offset, entries in relocs.items()
                        for kind, symbol in entries if symbol == 'D_80085994']
                self.assertEqual([kind for _, kind in font], ['R_MIPS_HI16', 'R_MIPS_LO16'])
                for index, _ in font:
                    self.assertEqual(words[index] >> 16 & 31, 3)
            pools = compiler.sections(self.out / (name + '.o'))
            self.assertTrue(all(not value[1] for section, value in pools.items()
                if section.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))))
            self.assertFalse(any(w >> 26 == 2 for w in words))
            self.assertNotIn('metrics.useFont', self.bodies[name])

    def test_02_all_five_bodies_preserve_bounded_public_semantics(self):
        counts = {}
        for name, (_, words) in self.compiled.items():
            count = 0
            for byte, phase in itertools.product(range(256), (0, 8)):
                self.semantic.compare(words, bytes((byte, 0, 0)) if byte != 0xBC else bytes((byte, 7, 65, 0)), phase=phase)
                count += 1
            for text, alias, phase, scales in itertools.product((b'\0', b'A\0', b'A\nB\0', b' AB\0',
                    bytes((0xBC, 0, 65, 0)), bytes((0xA8, 0xAA, 0xBA, 0xAE, 65, 0))),
                    range(10), (0, 8), ((1.0, 1.0), (0.75, 1.25))):
                self.semantic.compare(words, text, alias, phase, scales)
                count += 1
            self.semantic.compare(words, b'A\0', null=True)
            self.semantic.compare(words, bytes((0xAA, 0)), factor=1.0 / 18.0)
            memory, args = self.oracle.font_pointer_fixture()
            model = semantics.LogicalMeasurerOracle(words, memory, args, self.oracle.connected).run()
            expected = recovery.Reference(memory, args).run()
            self.assertEqual(recovery.public(model.memory), recovery.public(expected.memory))
            self.assertEqual(model.calls, expected.calls)
            counts[name] = count + 3
            self.assertEqual(counts[name], 755)
        self.assertEqual(sum(counts.values()), 3775)
        (self.out / 'public.json').write_text(json.dumps(dict(counts=counts, comparisons=sum(counts.values()),
            actual_helpers=True, installable=False, full_private_fault_owner_qualification=False), indent=2) + '\n')

    def test_03_common_reset_and_fired_observers_with_effective_negative_controls(self):
        compiler = screen.source.logic.screen.compiler
        records = []
        for name, (_, words) in self.compiled.items():
            relocs = compiler.parse_object(self.out / (name + '.o'))[2]
            calls = [offset // 4 for offset, entries in relocs.items() if ('R_MIPS_26', 'func_15042C40') in entries]
            self.assertEqual(len(calls), 1)
            call = calls[0]
            self.assertEqual([i for i, w in enumerate(words) if w == 0x00004025], [call + 6])
            self.assertEqual(words[call + 1], 0)
            self.assertTrue(all(w >> 26 in (9, 12) for w in words[call + 2:call + 5]))
            self.assertEqual(words[call + 5] >> 26, 5)
            self.assertEqual([w & 65535 for w in words if w & 0xFFFF0000 == 0xAFA80000], [0x68])
            self.assertEqual([w & 65535 for w in words if w & 0xFFFF0000 == 0x8FA80000], [0x68])
            for phase, text in itertools.product((0, 8), (b'A\0', b' \0', b'AB\n\xA8\0')):
                memory, args = recovery.fixture(text, self.oracle.table)
                observed = snapshot.TextObserver(words, memory, args, self.oracle.connected, phase=phase).run()
                plain = semantics.LogicalMeasurerOracle(words, memory, args, self.oracle.connected, phase=phase).run()
                for field in ('events', 'r', 'f', 'memory'):
                    self.assertEqual(getattr(observed, field), getattr(plain, field))
                if text == b'A\0':
                    self.assertEqual(observed.first_text_t0, [0])
                elif text == b' \0':
                    self.assertEqual(observed.first_width_t0, [0])
                else:
                    self.assertEqual(observed.metric_t0, [0])
                records.append(dict(name=name, phase=phase, text=text.hex(), first_text_t0=observed.first_text_t0,
                    first_width_t0=observed.first_width_t0, metric_t0=observed.metric_t0, installable=False))
        words = self.compiled['integer-address-work'][1].copy()
        self.assertEqual(words[43], 0x00004025)
        words[43] = 0
        with self.assertRaises(AssertionError):
            self.semantic.compare(words, b' \0')
        body = self.bodies['integer-address-work']
        cached = body.replace('    s32 extent;', '    s32 extent;\n    u8 *cachedFont;').replace(
            'extent = (s32)(u32)&D_80085994;', 'extent = (s32)(u32)&D_80085994;\n                        cachedFont = *(u8 **)(u32)extent;').replace(
            '(*(u8 **)(u32)extent)[', 'cachedFont[')
        self.assertNotEqual(cached, body)
        _, words = screen.source.logic.screen.compile_candidate(self.root, self.out, 'negative-cached-pointer', cached)
        memory, args = self.oracle.font_pointer_fixture()
        actual = semantics.LogicalMeasurerOracle(words, memory, args, self.oracle.connected).run()
        self.assertNotEqual(recovery.public(actual.memory), recovery.public(recovery.Reference(memory, args).run().memory))
        (self.out / 'roles.json').write_text(json.dumps(records, indent=2) + '\n')

    def test_04_completed_captures_keep_named_flag_separate_from_five_metric_homes(self):
        expected = {'integer-address-work': (18816, 854, 18304, 817, 3520, 3552),
                    'forward-ternary-work': (18824, 861, 18264, 821, 2768, 2800),
                    'excluded-join-control': (19032, 877, 18424, 834, 2864, 2896)}
        for name, values in expected.items():
            capture = front.capture_frontend(self.root, self.out, 'capture-' + name, self.bodies[name])
            self.assertTrue(capture['code_unchanged'])
            self.assertFalse(capture['installable'])
            self.assertEqual((capture['frontend']['bytes'], capture['record_count'],
                              capture['optimizer']['bytes'], capture['optimizer_record_count']), values[:4])
            self.assertEqual([(x['byte_offset'], x['name'], x['storage'], x['level'], x['offset'])
                              for x in capture['optimizer_records'] if x['name'] in ('rstr', 'rlod')],
                             [(values[4], 'rstr', 'M', 8, -24), (values[5], 'rlod', 'M', 8, -24)])
            self.assertIn(values[4] + 16, [x['byte_offset'] for x in capture['optimizer_records'] if x['name'] == 'cup'])
            self.assertEqual([(x['length'], x['offset']) for x in capture['records'] if x['name'] == 'lda' and x['storage'] == 'M'],
                             [(20, -44)] * 5)
            self.assertIn(1544, [x['byte_offset'] for x in capture['records']
                                if x['name'] == 'str' and x['storage'] == 'M' and x['offset'] == -24])
        self.assertEqual(front.compiler_fingerprints(self.root),
                         dict(front.trace.qualified.COMPILERS, ugen=front.trace.UGEN_SHA256, cfe=front.CFE_SHA256))

    def test_05_native32_all_bodies_both_profiles_and_effective_compiled_control(self):
        cases = self.oracle.native_cases()
        self.assertEqual(len(cases), 733)
        for name, body in self.bodies.items():
            source = self.oracle.native_source(body, cases)
            for profile in ('-O2', '-O0'):
                self.assertEqual(self.oracle.run_native('work-' + name + '-' + profile[1:], source, profile), (0, ''))
        body = self.bodies['integer-address-work']
        bad = body.replace('(u32)*height + 12', '(u32)*height + 13')
        self.assertNotEqual(bad, body)
        code, detail = self.oracle.run_native('work-negative-empty-height', self.oracle.native_source(bad, cases))
        self.assertIn(code, range(1, 5))
        self.assertEqual(len(detail), 3)
        self.assertEqual(detail[0], code)
        (self.out / 'native.json').write_text(json.dumps(dict(bodies=5, profiles=['O2', 'O0'], cases_per_profile=733,
            comparisons=7330, pointer_integer_bytes4=True, actual_helpers=True, canaries=True,
            compiled_negative_effective=True, synthetic_low_pointer_alias_private_faults_not_claimed=True,
            installable=False), indent=2) + '\n')

    def test_06_invalid_cli_and_frozen_production_controls(self):
        result = subprocess.run([sys.executable, '-m', 'tools.experiments.game_text_measurer_work_lifetime',
                                 '--filter', 'recovered'], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('invalid choice', result.stderr)
        self.oracle.test_05_production_and_protected_data_unchanged()
        self.oracle.test_06_effective_immutable_production_controls()


if __name__ == '__main__':
    unittest.main()
