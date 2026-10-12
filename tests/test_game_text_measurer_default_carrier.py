"""Qualify the shared T0 reset and source home without granting a full match."""
import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.experiments import game_text_measurer_default_carrier as screen
from tools.experiments import game_text_measurer_frontend_trace as front
from tools.tests import test_game_text_measurer_logic_candidates as semantics
from tools.tests import test_game_text_measurer_predicate_snapshot as snapshot
from tools.tests import test_game_text_measurer_recovery as recovery


class GameTextMeasurerDefaultCarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-text-measurer-default-carrier-test'
        cls.out.mkdir(exist_ok=True)
        cls.bodies = dict(screen.candidates())
        cls.compiled = {name: screen.logic.screen.compile_candidate(cls.root, cls.out, name, body)
                        for name, body in cls.bodies.items()}
        recovery.GameTextMeasurerRecoveryTests.setUpClass()
        cls.oracle = recovery.GameTextMeasurerRecoveryTests('test_05_production_and_protected_data_unchanged')
        cls.semantic = semantics.GameTextMeasurerLogicTests('test_02_all_nine_distinct_bodies_preserve_complete_public_semantics')
        cls.semantic.oracle = cls.oracle

    def test_01_seven_distinct_bodies_remain_rejected_for_frame_or_saved_roles(self):
        shapes = {'whole-shared-default': (222, 0x90, 216, 9), 'whole-metrics-false': (219, 0x88, 210, 8),
                  'split-direct-font': (218, 0x80, 210, 8), 'split-font-address': (216, 0x88, 182, 7),
                  'split-inline-address': (218, 0x80, 210, 8), 'split-address-after-record': (216, 0x88, 182, 7),
                  'split-address-font-only': (218, 0x88, 211, 8)}
        self.assertEqual(len(self.compiled), 7)
        self.assertEqual(len({tuple(words) for _, words in self.compiled.values()}), 7)
        for name, (meta, words) in self.compiled.items():
            self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), shapes[name][:3])
            self.assertNotEqual(words, self.oracle.retail)
            self.assertNotEqual(words[:13], self.oracle.retail[:13])
            saves = [w >> 16 & 31 for w in words[:36] if w >> 26 == 43 and w >> 21 & 31 == 29
                     and (16 <= w >> 16 & 31 <= 23 or w >> 16 & 31 == 30)]
            self.assertEqual(len(saves), shapes[name][3])
            self.assertFalse(any(w >> 26 == 2 for w in words))
            self.assertNotIn('metrics.useFont', self.bodies[name])
            pools = screen.logic.screen.compiler.sections(self.out / (name + '.o'))
            self.assertTrue(all(not value[1] for section, value in pools.items()
                if section.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))))
        for name in ('split-direct-font', 'split-inline-address'):
            self.assertEqual(self.compiled[name][1][32] >> 16 & 31, 21)
            self.assertEqual(screen.logic.screen.compiler.parse_object(self.out / (name + '.o'))[2][128],
                             [('R_MIPS_HI16', 'D_80085994')])

    def test_02_split_zero_is_a_common_nonlikely_delay_before_any_caller_ram_access(self):
        homes = {'split-direct-font': 0x68, 'split-font-address': 0x6C, 'split-inline-address': 0x68,
                 'split-address-after-record': 0x70, 'split-address-font-only': 0x70}
        for name, home in homes.items():
            meta, words = self.compiled[name]
            relocations = screen.logic.screen.compiler.parse_object(self.out / (name + '.o'))[2]
            calls = [offset // 4 for offset, entries in relocations.items()
                     if ('R_MIPS_26', 'func_15042C40') in entries]
            self.assertEqual(len(calls), 1)
            call = calls[0]
            reset = [i for i, w in enumerate(words) if w == 0x00004025]
            self.assertEqual(reset, [call + 6])
            self.assertEqual(words[call + 1], 0)
            self.assertTrue(all(w >> 26 in (9, 12) for w in words[call + 2:call + 5]))
            self.assertEqual(words[call + 5] >> 26, 5)
            self.assertEqual([w & 65535 for w in words if w & 0xFFFF0000 == 0xAFA80000], [home])
            self.assertEqual([w & 65535 for w in words if w & 0xFFFF0000 == 0x8FA80000], [home])

    def test_03_all_seven_bodies_preserve_bounded_public_semantics(self):
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
        self.assertEqual(sum(counts.values()), 5285)
        (self.out / 'public.json').write_text(json.dumps(dict(counts=counts, comparisons=sum(counts.values()),
            actual_helpers=True, installable=False, full_private_fault_native_owner_qualification=False), indent=2) + '\n')

    def test_04_fired_first_reads_call_state_and_effective_reset_mutation(self):
        records = []
        for name, (_, words) in self.compiled.items():
            split = name.startswith('split-')
            for phase, text in itertools.product((0, 8), (b'A\0', b' \0', b'AB\n\xA8\0')):
                memory, args = recovery.fixture(text, self.oracle.table)
                original = snapshot.TextObserver(self.oracle.retail, memory, args, self.oracle.connected,
                                                 phase=phase, entry=screen.logic.screen.ENTRY).run()
                candidate = snapshot.TextObserver(words, memory, args, self.oracle.connected, phase=phase).run()
                plain = semantics.LogicalMeasurerOracle(words, memory, args, self.oracle.connected, phase=phase).run()
                self.assertEqual(candidate.events, plain.events)
                self.assertEqual(candidate.r, plain.r)
                self.assertEqual(candidate.f, plain.f)
                self.assertEqual(candidate.memory, plain.memory)
                if text == b'A\0':
                    self.assertEqual(original.first_text_t0, [0])
                    self.assertEqual(candidate.first_text_t0, [0] if split else [50])
                elif text == b' \0':
                    self.assertEqual(original.first_width_t0, [0])
                    self.assertEqual(candidate.first_width_t0, [0] if split else [0x5A000008])
                else:
                    self.assertEqual(original.metric_t0, [0])
                    self.assertEqual(candidate.metric_t0, [0])
                records.append(dict(name=name, phase=phase, text=text.hex(), first_text_t0=candidate.first_text_t0,
                    first_width_t0=candidate.first_width_t0, metrics_t0=candidate.metric_t0, installable=False,
                    full_instruction_fault_qualification=False))
        words = self.compiled['split-direct-font'][1].copy()
        self.assertEqual(words[46], 0x00004025)
        words[46] = 0
        memory, args = recovery.fixture(b' \0', self.oracle.table)
        model = snapshot.TextObserver(words, memory, args, self.oracle.connected).run()
        self.assertNotEqual(model.first_width_t0, [0])
        self.assertNotEqual(recovery.public(model.memory), recovery.public(recovery.Reference(memory, args).run().memory))
        (self.out / 'roles.json').write_text(json.dumps(records, indent=2) + '\n')

    def test_05_complete_split_capture_moves_r8_from_temporary_to_named_source_home(self):
        names = ('whole-shared-default', 'whole-metrics-false', 'split-direct-font')
        captures = {name: front.capture_frontend(self.root, self.out, 'capture-' + name, self.bodies[name]) for name in names}
        sizes = {names[0]: (18552, 838, 18216, 812), names[1]: (18568, 838, 18168, 809),
                 names[2]: (18544, 837, 18240, 814)}
        expected_saves = {names[0]: (3600, 3616, 3632, -52), names[1]: (3544, 3560, 3576, -52),
                          names[2]: (3552, 3568, 3584, -24)}
        for name, capture in captures.items():
            self.assertTrue(capture['code_unchanged'])
            self.assertFalse(capture['installable'])
            self.assertEqual((capture['frontend']['bytes'], capture['record_count'],
                              capture['optimizer']['bytes'], capture['optimizer_record_count']), sizes[name])
            offsets = (-48, -52) if name == 'split-direct-font' else (-48, -52, -56, -60)
            self.assertEqual([(x['storage'], x['level'], x['length'], x['offset']) for x in capture['records']
                              if x['name'] == 'vreg'], [('M', 1, 4, offset) for offset in offsets])
            save, call, reload, home = expected_saves[name]
            self.assertEqual([(x['byte_offset'], x['name'], x['storage'], x['level'], x['offset'])
                              for x in capture['optimizer_records'] if x['name'] in ('rstr', 'rlod')],
                             [(save, 'rstr', 'M', 8, home), (reload, 'rlod', 'M', 8, home)])
            self.assertIn(call, [x['byte_offset'] for x in capture['optimizer_records'] if x['name'] == 'cup'])
            self.assertEqual(self.compiled[name][0]['frame'] + home,
                             {'whole-shared-default': 0x5C, 'whole-metrics-false': 0x54, 'split-direct-font': 0x68}[name])
        split = captures['split-direct-font']['records']
        stores = [x['byte_offset'] for x in split if x['name'] == 'str' and x['storage'] == 'M' and x['offset'] == -24]
        self.assertEqual(stores, [1544, 1968, 2992, 4440])
        self.assertEqual([x['byte_offset'] for x in split if x['name'] == 'cup'], [1424, 3592])
        self.assertLess(stores[2], 3592)
        self.assertEqual([(x['length'], x['offset']) for x in split if x['name'] == 'lda' and x['storage'] == 'M'],
                         [(20, -44)] * 5)

    def test_06_effective_source_cli_and_immutable_controls(self):
        body = self.bodies['split-direct-font']
        bad = body.replace('s32 useFont = 0;', 's32 useFont = 1;')
        self.assertNotEqual(bad, body)
        _, words = screen.logic.screen.compile_candidate(self.root, self.out, 'wrong-default', bad)
        with self.assertRaises(AssertionError):
            self.semantic.compare(words, b' \0')
        result = subprocess.run([sys.executable, '-m', 'tools.experiments.game_text_measurer_default_carrier',
                                 '--filter', 'recovered'], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('invalid choice', result.stderr)
        self.assertEqual(front.compiler_fingerprints(self.root),
                         dict(front.trace.qualified.COMPILERS, ugen=front.trace.UGEN_SHA256, cfe=front.CFE_SHA256))
        self.oracle.test_05_production_and_protected_data_unchanged()
        self.oracle.test_06_effective_immutable_production_controls()


if __name__ == '__main__':
    unittest.main()
