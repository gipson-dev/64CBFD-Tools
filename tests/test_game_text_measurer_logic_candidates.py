"""Semantic screens and concrete rejection of effectful-predicate source forms."""
import itertools
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from tools.experiments import game_text_measurer_logic_candidates as logic
from tools.experiments import game_text_measurer_ugen_nodes as fingerprint
from tools.tests import test_game_text_measurer_recovery as recovery


DIAGNOSTIC_ENTRY = 0x152428D4


class LogicalMeasurerOracle(recovery.MeasurerOracle):
    def __init__(self, words, memory, args, connected, phase=0, entry=DIAGNOSTIC_ENTRY):
        with patch.object(logic.screen, 'ENTRY', entry):
            super().__init__(words, memory, args, connected, phase)

    def execute(self, word):
        if word >> 26 == 0 and word & 63 == 38:
            rs, rt, rd = word >> 21 & 31, word >> 16 & 31, word >> 11 & 31
            self.r[rd] = (self.r[rs] ^ self.r[rt]) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)


class GameTextMeasurerLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-text-measurer-logic-test'
        cls.out.mkdir(exist_ok=True)
        recovery.GameTextMeasurerRecoveryTests.setUpClass()
        cls.oracle = recovery.GameTextMeasurerRecoveryTests('test_05_production_and_protected_data_unchanged')
        cls.bodies = dict(logic.candidates())
        cls.compiled = {name: logic.screen.compile_candidate(cls.root, cls.out, name, body)
                        for name, body in cls.bodies.items()}

    def compare(self, words, text, alias=0, phase=0, scales=(1.0, 1.0), null=False, factor=None):
        memory, args = recovery.fixture(text, self.oracle.table, alias, scales)
        if factor is not None:
            recovery.put(memory, recovery.metrics.SYMBOLS['D_80098B00'], recovery.bits(factor))
        if null:
            args = (0, *args[1:])
        expected = recovery.Reference(memory, args).run()
        original = LogicalMeasurerOracle(self.oracle.retail, memory, args, self.oracle.connected,
                                         phase, logic.screen.ENTRY)
        candidate = LogicalMeasurerOracle(words, memory, args, self.oracle.connected, phase)
        for model in (original, candidate):
            model.run()
            self.assertEqual(recovery.public(model.memory), recovery.public(expected.memory))
            self.assertEqual(model.calls, expected.calls)
        return original, candidate

    def test_01_shape_matrix_rejects_all_forms_and_checks_identical_controls(self):
        expected = {'or-effects-named': (219, 0x80, 201), 'or-effects-direct': (216, 0x78, 207),
                    'and-effects-named': (221, 0x90, 176), 'and-effects-direct': (216, 0x70, 191),
                    'ternary-effects-named': (226, 0x90, 197), 'ternary-effects-direct': (228, 0x90, 200),
                    'disjoint-bitwise-named': (231, 0x90, 224),
                    'disjoint-bitwise-direct': (233, 0x88, 227), 'memory-lvalue-named': (220, 0x80, 175)}
        self.assertEqual(len(self.compiled), 16)
        records = []
        for name, (meta, words) in self.compiled.items():
            key = name.removesuffix('-locals').removesuffix('-void-address')
            with self.subTest(name=name):
                self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), expected[key])
                self.assertEqual(meta['pool_bytes'], 0)
                self.assertNotEqual(words, self.oracle.retail)
                self.assertFalse(any(word >> 26 == 2 for word in words), 'Unrebased internal absolute jump')
                if key != name:
                    self.assertEqual(words, self.compiled[key][1])
                # Matching length and frame alone do not qualify the extra saved-register prologue.
                if meta['body_words'] == 219 and meta['frame'] == 0x80:
                    self.assertNotEqual(words[:13], self.oracle.retail[:13])
            records.append(dict(meta, installable=False))
        (self.out / 'shapes.json').write_text(json.dumps(records, indent=2) + '\n')
        for name, home in (('disjoint-bitwise-named', 0x50), ('disjoint-bitwise-direct', 0x4C)):
            words = self.compiled[name][1]
            self.assertIn(0x00004025, words)
            self.assertIn(0xAFA80000 | home, words)
            self.assertIn(0x8FA80000 | home, words)
            self.assertNotIn(0xAFA80068, words)
            self.assertNotIn(0x8FA80068, words)

    def test_02_all_nine_distinct_bodies_preserve_complete_public_semantics(self):
        unique = {name: pair for name, pair in self.compiled.items()
                  if not name.endswith(('-locals', '-void-address'))}
        self.assertEqual(len(unique), 9)
        records = []
        for name, (_meta, words) in unique.items():
            cases = 0
            with self.subTest(name=name):
                for byte, phase in itertools.product(range(256), (0, 8)):
                    text = bytes((byte, 0, 0)) if byte != 0xBC else bytes((byte, 7, 65, 0))
                    self.compare(words, text, phase=phase)
                    cases += 1
                for text, alias, phase, scales in itertools.product((b'\0', b'A\0', b'A\nB\0', b' AB\0',
                        bytes((0xBC, 0, 65, 0)), bytes((0xA8, 0xAA, 0xBA, 0xAE, 65, 0))),
                        range(10), (0, 8), ((1.0, 1.0), (0.75, 1.25))):
                    self.compare(words, text, alias, phase, scales)
                    cases += 1
                self.compare(words, b'A\0', null=True)
                self.compare(words, bytes((0xAA, 0)), factor=1.0 / 18.0)
                memory, args = self.oracle.font_pointer_fixture()
                model = LogicalMeasurerOracle(words, memory, args, self.oracle.connected).run()
                expected = recovery.Reference(memory, args).run()
                self.assertEqual(recovery.public(model.memory), recovery.public(expected.memory))
                self.assertEqual(model.calls, expected.calls)
                cases += 3
                self.assertEqual(cases, 755)
            records.append(dict(name=name, cases=cases, actual_helpers_no_hooks=True,
                                public_memory_calls=True, private_fault_native_owner_qualification=False,
                                candidate_entry=DIAGNOSTIC_ENTRY, helpers_at_original_addresses=True,
                                installable=False))
        (self.out / 'public.json').write_text(json.dumps(records, indent=2) + '\n')

    def test_03_effective_non_disjoint_bitwise_and_wrong_space_controls(self):
        body = self.bodies['disjoint-bitwise-named']
        bad = body.replace('text[index] != 0xA ||', 'text[index] != 0xA |')
        self.assertNotEqual(bad, body)
        for name, source, text in (('unsafe-newline-bitwise', bad, b'A\0'),
                                  ('wrong-space', body.replace('(u32)*width + 4', '(u32)*width + 5'), b' \0')):
            _, words = logic.screen.compile_candidate(self.root, self.out, name, source)
            memory, args = recovery.fixture(text, self.oracle.table)
            expected = recovery.Reference(memory, args).run()
            model = LogicalMeasurerOracle(words, memory, args, self.oracle.connected).run()
            self.assertNotEqual(recovery.public(model.memory), recovery.public(expected.memory), name)

    def test_04_complete_ugen_dump_contains_upstream_register8_call_save(self):
        expected = dict(fingerprint.qualified.COMPILERS, ugen=fingerprint.UGEN_SHA256)
        self.assertEqual(fingerprint.compiler_fingerprints(self.root), expected)
        record = logic.screen.trace_ugen(self.root, self.out, 'bitwise-upstream',
                                        self.bodies['disjoint-bitwise-named'])
        self.assertTrue(record['code_unchanged'])
        log = (self.out / 'bitwise-upstream-ugen.txt').read_text()
        emit, tree = log.split('Tree dump after Build', 1)
        tree = tree.split('Tree dump', 1)[0]
        self.assertIn('emit_rob: zsw xr8          80 xr29', emit)
        self.assertIn('emit_rob: zlw xr8          80 xr29', emit)
        store = re.search(r'^\s*(\d+)\s+str dtype=J mtype=M .*offset=-64 .*op1=(\d+)', tree, re.MULTILINE)
        self.assertIsNotNone(store)
        load = re.search(r'^\s*(\d+)\s+str dtype=J mtype=R .*offset=32 .*op1=(\d+)', tree[store.end():], re.MULTILINE)
        self.assertIsNotNone(load)
        self.assertRegex(tree, r'(?m)^\s*' + store[2] + r'\s+lod dtype=J mtype=R .*offset=32 ')
        self.assertRegex(tree, r'(?m)^\s*' + load[2] + r'\s+lod dtype=J mtype=M .*offset=-64 ')
        between = tree[store.end():store.end() + load.start()]
        self.assertRegex(between, r'cup dtype=P .*pop=6')
        left = logic.screen.compiler.sections(self.out / 'bitwise-upstream-baseline.o')
        right = logic.screen.compiler.sections(self.out / 'bitwise-upstream-trace.o')
        pools = {name for name in left.keys() | right.keys()
                 if name.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))}
        self.assertTrue(all(left.get(name) == right.get(name) for name in pools))
        self.assertEqual(fingerprint.compiler_fingerprints(self.root), expected)
        record.update(installable=False, upstream_register=8, memory_offset=-64,
                      final_spill_home=0x50, pool_sections=sorted(pools), all_pool_identity=True,
                      no_claim_CFE_vs_UOPT_origin=True)
        (self.out / 'upstream.json').write_text(json.dumps(record, indent=2) + '\n')

    def test_05_production_and_protected_data_unchanged(self):
        self.oracle.test_05_production_and_protected_data_unchanged()

    def test_06_effective_immutable_production_controls(self):
        self.oracle.test_06_effective_immutable_production_controls()

    def test_07_local_xor_and_nonoverlapping_helper_control(self):
        memory, args = recovery.fixture(b'A\0', self.oracle.table)
        for left, right in ((0, 0), (0xFFFFFFFF, 0xAAAAAAAA), (0x12345678, 0xFEDCBA98)):
            model = LogicalMeasurerOracle([], memory, args, self.oracle.connected)
            model.r[8], model.r[9] = left, right
            model.execute((8 << 21) | (9 << 16) | (10 << 11) | 38)
            self.assertEqual(model.r[10], (left ^ right) & 0xFFFFFFFF)
            model.execute((8 << 21) | (9 << 16) | 38)
            self.assertEqual(model.r[0], 0)
            self.assertEqual((model.r[8], model.r[9]), (left, right))
            with self.assertRaisesRegex(AssertionError, 'Unsupported word'):
                model.execute(63)
        words = self.compiled['disjoint-bitwise-named'][1]
        candidate = LogicalMeasurerOracle(words, memory, args, self.oracle.connected)
        self.assertEqual({address: candidate.code[address] for address in self.oracle.connected}, self.oracle.connected)
        self.assertEqual(candidate.code[DIAGNOSTIC_ENTRY], words[0])
        self.assertGreater(len(words), 219)

if __name__ == '__main__':
    unittest.main()
