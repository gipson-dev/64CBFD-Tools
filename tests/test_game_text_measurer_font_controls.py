"""Bounded font controls; matching shape does not qualify a retail lifetime."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest

from tools.experiments import game_text_measurer_font_controls as controls
from tools.experiments import game_text_measurer_frontend_trace as front
from tools.tests import test_game_text_measurer_logic_candidates as semantics
from tools.tests import test_game_text_measurer_recovery as recovery


class FontObserver(semantics.LogicalMeasurerOracle):
    def __init__(self, *args, **kwargs):
        self.font_reads = []
        self.metric_t0 = []
        self.first_width_t0 = []
        self.width_pending = False
        super().__init__(*args, **kwargs)

    def record_call(self, target):
        if target == recovery.lookup.ENTRY:
            self.width_pending = True
        elif target == recovery.metrics.ENTRY:
            self.metric_t0.append(self.r[8])
        super().record_call(target)

    def get(self, address, size):
        if address == controls.logic.screen.SYMBOLS['D_80085994'] and size == 4:
            self.font_reads.append(self.r[8])
        if self.width_pending and address == self.before[5] and size == 4:
            self.first_width_t0.append(self.r[8])
            self.width_pending = False
        return super().get(address, size)


class GameTextMeasurerFontControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-text-measurer-font-controls-test'
        cls.out.mkdir(exist_ok=True)
        cls.sources = {name: (body, declarations) for name, body, declarations in controls.candidates()}
        cls.compiled = {name: controls.logic.screen.compile_candidate(cls.root, cls.out, name, body,
                        declarations=declarations) for name, (body, declarations) in cls.sources.items()}
        cls.objects = {name: controls.logic.screen.compiler.parse_object(cls.out / (name + '.o'))
                       for name in cls.compiled}
        recovery.GameTextMeasurerRecoveryTests.setUpClass()
        cls.oracle = recovery.GameTextMeasurerRecoveryTests('test_05_production_and_protected_data_unchanged')
        cls.semantic = semantics.GameTextMeasurerLogicTests('test_02_all_nine_distinct_bodies_preserve_complete_public_semantics')
        cls.semantic.oracle = cls.oracle

    def test_01_four_forms_three_bodies_not_count_based_identity(self):
        hashes = {'plain': '785d4fbf774b1d13677f71fbe03a492752e0335ed66589f08790c9b1c86d9d06',
                  'volatile-bytes': '785d4fbf774b1d13677f71fbe03a492752e0335ed66589f08790c9b1c86d9d06',
                  'volatile-pointer': '6c971bc349c2e9579e7273a8051f2db0ba825edcd8411d2229fd7574d7e645e2',
                  'volatile-pointer-and-bytes': 'e1a53d69173f19ee5b2296ac3edd6ef9e9472c1ae23ac3e0880718b4cfbfc1b6'}
        self.assertEqual(len(self.compiled), 4)
        self.assertEqual(len({tuple(words) for _, words in self.compiled.values()}), 3)
        for name, (meta, words) in self.compiled.items():
            self.assertEqual((meta['body_words'], meta['frame'], meta['differences']),
                             (223, 0x80, 216) if 'pointer' in name else (219, 0x80, 208))
            self.assertEqual(hashlib.sha256(self.objects[name][0]).hexdigest(), hashes[name])
            self.assertNotEqual(words, self.oracle.retail)
            self.assertNotEqual(words[:13], self.oracle.retail[:13])
            saves = [word >> 16 & 31 for word in words[:35]
                     if word >> 26 == 43 and word >> 21 & 31 == 29 and 16 <= word >> 16 & 31 <= 23]
            self.assertEqual(sorted(saves), list(range(16, 24)))
            self.assertEqual([i for i, word in enumerate(words) if word == 0x00004025], [54])
            self.assertEqual(words[93], 0xAFA80068)
            self.assertEqual(words[99], 0x8FA80068)
            self.assertFalse(any(word >> 26 == 2 for word in words))
            pools = controls.logic.screen.compiler.sections(self.out / (name + '.o'))
            self.assertTrue(all(not value[1] for section, value in pools.items()
                if section.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))))
        self.assertEqual(self.objects['plain'], self.objects['volatile-bytes'])
        left, right = self.objects['volatile-pointer'], self.objects['volatile-pointer-and-bytes']
        self.assertEqual(left[1:], right[1:])
        left_words, right_words = (struct.unpack('>%dI' % (len(item[0]) // 4), item[0]) for item in (left, right))
        self.assertEqual([i for i, (a, b) in enumerate(zip(left_words, right_words)) if a != b],
                         [146, 147, 150, 151, 152, 153, 158, 159, 160, 161, 162])

    def test_02_three_distinct_bodies_preserve_bounded_public_semantics(self):
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
            actual_helpers=True, installable=False, recovered_declaration=False,
            full_private_fault_native_owner_qualification=False), indent=2) + '\n')

    def test_03_font_address_still_hoists_and_pointer_reads_double(self):
        for name, (_, words) in self.compiled.items():
            relocations = self.objects[name][2]
            self.assertEqual(relocations[128], [('R_MIPS_HI16', 'D_80085994')])
            self.assertEqual(relocations[132], [('R_MIPS_LO16', 'D_80085994')])
            self.assertEqual(words[32] >> 16 & 31, 19 if 'pointer' in name else 21)
            for phase in (0, 8):
                memory, args = recovery.fixture(b'A\0', self.oracle.table)
                model = FontObserver(words, memory, args, self.oracle.connected, phase=phase).run()
                plain = semantics.LogicalMeasurerOracle(words, memory, args, self.oracle.connected, phase=phase).run()
                self.assertEqual(len(model.font_reads), 4 if 'pointer' in name else 2)
                self.assertEqual(model.events, plain.events)
                self.assertEqual(model.r, plain.r)
                self.assertEqual(model.f, plain.f)
                self.assertEqual(model.memory, plain.memory)

    def test_04_metrics_t0_is_zero_but_first_space_width_read_is_not(self):
        records = []
        for name, (_, words) in self.compiled.items():
            for phase in (0, 8):
                memory, args = recovery.fixture(b' \0', self.oracle.table)
                original = FontObserver(self.oracle.retail, memory, args, self.oracle.connected,
                                        phase=phase, entry=controls.logic.screen.ENTRY).run()
                candidate = FontObserver(words, memory, args, self.oracle.connected, phase=phase).run()
                self.assertEqual(original.first_width_t0, [0])
                self.assertEqual(len(candidate.first_width_t0), 1)
                self.assertNotEqual(candidate.first_width_t0[0], 0)
                space_t0 = candidate.first_width_t0[0]
                self.assertEqual(recovery.public(candidate.memory), recovery.public(original.memory))
                self.assertEqual(candidate.calls, original.calls)
                memory, args = recovery.fixture(b'AB\n\xA8\0', self.oracle.table)
                candidate = FontObserver(words, memory, args, self.oracle.connected, phase=phase).run()
                self.assertEqual(candidate.metric_t0, [0])
                plain = semantics.LogicalMeasurerOracle(words, memory, args, self.oracle.connected, phase=phase).run()
                self.assertEqual(candidate.events, plain.events)
                self.assertEqual(candidate.r, plain.r)
                self.assertEqual(candidate.f, plain.f)
                self.assertEqual(candidate.memory, plain.memory)
                expected = recovery.Reference(memory, args).run()
                self.assertEqual(recovery.public(candidate.memory), recovery.public(expected.memory))
                self.assertEqual(candidate.calls, expected.calls)
                records.append(dict(name=name, phase=phase, metrics_t0=candidate.metric_t0,
                                    first_space_width_t0=space_t0, shared_early_zero=False, installable=False))
        (self.out / 'roles.json').write_text(json.dumps(records, indent=2) + '\n')

    def test_05_effective_negative_source_cli_and_immutable_controls(self):
        body, declarations = self.sources['plain']
        bad = body.replace('(u32)*width + 4', '(u32)*width + 5')
        self.assertNotEqual(bad, body)
        _, words = controls.logic.screen.compile_candidate(self.root, self.out, 'wrong-space', bad, declarations=declarations)
        with self.assertRaises(AssertionError):
            self.semantic.compare(words, b' \0')
        result = subprocess.run([sys.executable, '-m', 'tools.experiments.game_text_measurer_font_controls',
                                 '--filter', 'recovered'], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('invalid choice', result.stderr)
        self.assertEqual(front.compiler_fingerprints(self.root),
                         dict(front.trace.qualified.COMPILERS, ugen=front.trace.UGEN_SHA256, cfe=front.CFE_SHA256))
        self.oracle.test_05_production_and_protected_data_unchanged()
        self.oracle.test_06_effective_immutable_production_controls()

    def test_06_complete_initializer_capture_tracks_the_actual_r8_call_save(self):
        capture = front.capture_frontend(self.root, self.out, 'capture-initializer', controls.initializer())
        self.assertTrue(capture['code_unchanged'])
        self.assertFalse(capture['installable'])
        self.assertEqual((capture['frontend']['bytes'], capture['record_count'],
                          capture['optimizer']['bytes'], capture['optimizer_record_count']),
                         (18520, 834, 18232, 813))
        vregs = [item for item in capture['records'] if item['name'] == 'vreg']
        self.assertEqual([(item['byte_offset'], item['storage'], item['level'], item['length'], item['offset'])
                         for item in vregs], [(1520, 'M', 1, 4, -48), (1536, 'M', 1, 4, -52)])
        saves = [item for item in capture['optimizer_records'] if item['name'] in ('rstr', 'rlod')]
        self.assertEqual([(item['name'], item['byte_offset'], item['storage'], item['level'], item['offset'])
                         for item in saves], [('rstr', 3544, 'M', 8, -24), ('rlod', 3576, 'M', 8, -24)])
        calls = [item for item in capture['optimizer_records'] if item['name'] == 'cup']
        self.assertEqual([item['byte_offset'] for item in calls], [1712, 3560])
        self.assertEqual(0x80 + saves[0]['offset'], 0x68)
        baseline = controls.logic.screen.compiler.parse_object(self.out / 'capture-initializer/baseline.o')
        self.assertEqual(baseline, self.objects['plain'])


if __name__ == '__main__':
    unittest.main()
