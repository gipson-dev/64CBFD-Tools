"""Qualify the literal metrics region and renewed complete access-cut boundary."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_text_measurer_repeated_predicate as screen
from tools.experiments import game_text_measurer_candidates as compiler
from tools.experiments import game_text_measurer_frontend_trace as front
from tools.tests import test_game_text_measurer_logic_candidates as semantics
from tools.tests import test_game_text_measurer_predicate_snapshot as snapshot
from tools.tests import test_game_text_measurer_recovery as recovery


class InstructionPredicateFault(semantics.LogicalMeasurerOracle):
    def execute(self, word):
        self.dispatched_word = word
        return super().execute(word)


class GameTextMeasurerRepeatedPredicateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-text-measurer-repeated-predicate-test'
        cls.out.mkdir(exist_ok=True)
        cls.bodies = dict(screen.candidates())
        cls.compiled = {name: compiler.compile_candidate(cls.root, cls.out, name, body)
                        for name, body in cls.bodies.items()}
        recovery.GameTextMeasurerRecoveryTests.setUpClass()
        cls.oracle = recovery.GameTextMeasurerRecoveryTests('test_05_production_and_protected_data_unchanged')
        cls.semantic = semantics.GameTextMeasurerLogicTests('test_02_all_nine_distinct_bodies_preserve_complete_public_semantics')
        cls.semantic.oracle = cls.oracle

    def test_01_literal_53_word_region_and_shapes_do_not_grant_full_match(self):
        shapes = {'forward-control': (216, 128, 171), 'repeated-ordinary-range': (218, 128, 114),
                  'repeated-range-gate': (219, 128, 117), 'initialized-ordinary-predicate': (218, 136, 178)}
        self.assertEqual(len({tuple(words) for _, words in self.compiled.values()}), 4)
        for name, (meta, words) in self.compiled.items():
            self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), shapes[name])
            self.assertNotEqual(words, self.oracle.retail)
            if name in ('forward-control', 'repeated-ordinary-range'):
                self.assertEqual(words[:13], self.oracle.retail[:13])
                self.assertEqual(words[14:28], self.oracle.retail[14:28])
            else:
                self.assertNotEqual(words[:13], self.oracle.retail[:13])
            pools = compiler.compiler.sections(self.out / (name + '.o'))
            self.assertTrue(all(not value[1] for section, value in pools.items()
                if section.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))))
            self.assertFalse(any(w >> 26 == 2 for w in words))
            self.assertNotIn('metrics.useFont', self.bodies[name])
        words = self.compiled['repeated-ordinary-range'][1]
        self.assertEqual(words[59:112], self.oracle.retail[59:112])
        self.assertEqual(words[113:118], self.oracle.retail[113:118])
        self.assertNotEqual(words[112], self.oracle.retail[112])
        self.assertNotEqual(words[118], self.oracle.retail[118])
        relocs = compiler.compiler.parse_object(self.out / 'repeated-ordinary-range.o')[2]
        self.assertEqual(relocs[67 * 4], [('R_MIPS_26', 'func_150415E0')])

    def test_02_all_four_bodies_preserve_bounded_public_semantics(self):
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
        self.assertEqual(sum(counts.values()), 3020)
        (self.out / 'public.json').write_text(json.dumps(dict(counts=counts, comparisons=3020,
            actual_helpers=True, installable=False), indent=2) + '\n')

    def test_03_common_reset_call_homes_and_fired_observers(self):
        homes = {'forward-control': 0x68, 'repeated-ordinary-range': 0x68,
                 'repeated-range-gate': 0x68, 'initialized-ordinary-predicate': 0x70}
        for name, (_, words) in self.compiled.items():
            relocs = compiler.compiler.parse_object(self.out / (name + '.o'))[2]
            call = next(off // 4 for off, entries in relocs.items() if ('R_MIPS_26', 'func_15042C40') in entries)
            self.assertEqual([i for i, w in enumerate(words) if w == 0x00004025], [call + 6])
            self.assertEqual(words[call + 5] >> 26, 5)
            self.assertTrue(all(w >> 26 in (0, 9, 10, 11, 12, 13, 14) for w in words[call + 2:call + 5]))
            self.assertEqual([w & 65535 for w in words if w & 0xFFFF0000 == 0xAFA80000], [homes[name]])
            self.assertEqual([w & 65535 for w in words if w & 0xFFFF0000 == 0x8FA80000], [homes[name]])
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
        words = self.compiled['repeated-ordinary-range'][1].copy()
        self.assertEqual(words[43], 0x00004025)
        words[43] = 0
        with self.assertRaises(AssertionError):
            self.semantic.compare(words, b' \0')

    def test_04_complete_captures_preserve_actual_named_flag_and_five_outputs(self):
        expected = {'repeated-ordinary-range': (18896, 866, 18320, 825, 2824, 2856),
                    'repeated-range-gate': (18984, 872, 18392, 830, 2896, 2928)}
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
        self.assertEqual(front.compiler_fingerprints(self.root),
                         dict(front.trace.qualified.COMPILERS, ugen=front.trace.UGEN_SHA256, cfe=front.CFE_SHA256))

    def test_05_native32_and_cache_definition_cover_every_branch(self):
        cases = self.oracle.native_cases()
        self.assertEqual(len(cases), 733)
        cached = self.bodies['initialized-ordinary-predicate']
        self.assertLess(cached.index('s32 ordinary = glyph < 0xA1;'), cached.index('if (glyph == 0x60)'))
        for name, body in self.bodies.items():
            source = self.oracle.native_source(body, cases)
            for profile in ('-O2', '-O0'):
                self.assertEqual(self.oracle.run_native('predicate-' + name + '-' + profile[1:], source, profile), (0, ''))
        bad = cached.replace('ordinary = glyph < 0xA1', 'ordinary = glyph >= 0xA1')
        self.assertNotEqual(bad, cached)
        _, words = compiler.compile_candidate(self.root, self.out, 'negative-inverted-predicate', bad)
        with self.assertRaises(AssertionError):
            self.semantic.compare(words, b'A\0')
        code, detail = self.oracle.run_native('predicate-negative-inverted', self.oracle.native_source(bad, cases))
        self.assertIn(code, range(1, 5))
        self.assertEqual(len(detail), 3)
        self.assertEqual(detail[0], code)
        (self.out / 'native.json').write_text(json.dumps(dict(bodies=4, profiles=['O2', 'O0'], cases_per_profile=733,
            comparisons=5864, pointer_integer_bytes4=True, actual_helpers=True, canaries=True,
            compiled_negative_effective=True, synthetic_low_pointer_alias_FCSR_not_claimed=True,
            installable=False), indent=2) + '\n')

    def test_06_all_access_cuts_move_first_difference_to_font_pointer_load(self):
        entry = 0x152428D4
        with patch.object(compiler, 'ENTRY', entry):
            _, words = compiler.compile_candidate(self.root, self.out, 'fault-candidate', self.bodies['repeated-ordinary-range'])
        asm = (self.root / 'conker/asm/6E770.s').read_text().split('glabel ' + compiler.FUNCTION + '\n', 1)[1].split(
            'endlabel ' + compiler.FUNCTION, 1)[0]
        path = self.out / 'fault-original.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n'
            '.section .text.measurer,"ax"\n.set noreorder\n.set noat\n.globl ' + compiler.FUNCTION + '\n'
            '.type ' + compiler.FUNCTION + ',@function\n' + compiler.FUNCTION + ':\n' + asm +
            '\n.size ' + compiler.FUNCTION + ',.-' + compiler.FUNCTION + '\n')
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], check=True, capture_output=True)
        script = self.out / 'fault-original.ld'
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text.measurer) } }\n' % entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', compiler.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in compiler.SYMBOLS.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
        original = list(struct.unpack('>219I', compiler.compiler.sections(elf)['.text'][1]))
        self.assertEqual(original, self.oracle.retail)
        records = []
        total = equal_total = 0
        for text, phase in itertools.product((b'A\0', b' \0', b'\n\0', bytes((0xA8, 0))), (0, 8)):
            memory, args = recovery.fixture(text, self.oracle.table)
            def models():
                return [InstructionPredicateFault(code, memory, args, self.oracle.connected, phase, entry=entry)
                        for code in (original, words)]
            plain = [m.run() for m in models()]
            expected = recovery.Reference(memory, args).run()
            for m in plain:
                self.assertEqual(recovery.public(m.memory), recovery.public(expected.memory))
                self.assertEqual(m.calls, expected.calls)
                self.assertEqual(m.accesses, sum(e[0] in ('R', 'W') for e in m.events))
            counts = [m.accesses for m in plain]
            self.assertEqual(counts[0], counts[1])
            self.assertEqual(counts[0], {b'A\0': 56, b' \0': 38, b'\n\0': 136, bytes((0xA8, 0)): 154}[text])
            first = None
            equal = 0
            for fault in range(counts[0]):
                pair = models()
                for m in pair:
                    m.fault = fault
                    with self.assertRaises(recovery.guest.AccessFault):
                        m.run()
                    self.assertEqual(m.accesses, fault)
                    self.assertIn(m.dispatched_word >> 26, (32, 33, 35, 36, 37, 40, 41, 43, 49, 57))
                state = lambda m: (m.memory, m.events, m.r, m.f, m.condition)
                same = state(pair[0]) == state(pair[1])
                equal += same
                if not same and first is None:
                    first = dict(fault=fault, words=['0x%08X' % m.dispatched_word for m in pair],
                        changed_gprs=[i for i in range(32) if pair[0].r[i] != pair[1].r[i]],
                        t0=[m.r[8] for m in pair], ra_equal=pair[0].r[31] == pair[1].r[31],
                        memory_equal=pair[0].memory == pair[1].memory, events_equal=pair[0].events == pair[1].events)
            if text == b'A\0':
                self.assertEqual(equal, 27)
                self.assertEqual(first, dict(fault=27, words=['0x8D295994', '0x8C690000'],
                    changed_gprs=[1, 3, 9], t0=[1, 1], ra_equal=True, memory_equal=True, events_equal=True))
            else:
                self.assertEqual(equal, counts[0])
                self.assertIsNone(first)
            for m in models():
                m.fault = counts[0]
                m.run()
                self.assertEqual(m.accesses, counts[0])
            records.append(dict(text=text.hex(), phase=phase, accesses=counts[0], equal=equal, first=first))
            total += counts[0]
            equal_total += equal
        self.assertEqual((total, equal_total), (768, 710))
        (self.out / 'instruction-faults.json').write_text(json.dumps(dict(records=records, fired_pairs=total,
            equal_pairs=equal_total, independent_same_entry_links=True, original_219_literal_words_exact=True,
            memory_events_GPR_FPR_condition_compared=True, not_all_inputs_private_aliases_PC_FCSR_hardware=True,
            installable=False), indent=2) + '\n')

    def test_07_cli_and_effective_frozen_production_controls(self):
        result = subprocess.run([sys.executable, '-m', 'tools.experiments.game_text_measurer_repeated_predicate',
                                 '--filter', 'recovered'], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('invalid choice', result.stderr)
        self.oracle.test_05_production_and_protected_data_unchanged()
        self.oracle.test_06_effective_immutable_production_controls()


if __name__ == '__main__':
    unittest.main()
