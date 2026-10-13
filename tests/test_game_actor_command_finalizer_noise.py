"""Qualify bounded promotion screens and owned optimizer-prefix evidence."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_noise as screen
from tools.tests import test_game_actor_command_finalizer_fitting as trace_tests


class GameActorCommandFinalizerNoiseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-command-finalizer-noise-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = ('conker/src/game/generated_61D10.c', 'conker/build/conker.us.elf',
            'conker/retail_word_patches.us.csv', 'conker/Makefile', 'conker/progress.csv')
        cls.before = {p: hashlib.sha256((cls.root / p).read_bytes()).hexdigest() for p in cls.paths}
        assert cls.before[cls.paths[0]] == 'ce9efbb40671a56699d587183f31b9c72cfa835441af6809dfe729ad2d0402ee'
        assert cls.before[cls.paths[1]] == '687cfa25054d239a1a081d23b91b1e199ecf1b595972824cfc32df751319d6e2'
        cls.forms = {}
        compiler = screen.previous.previous.fitting.compile_candidate
        for name, body in screen.candidates():
            meta, words = compiler(cls.root, cls.out, name, body)
            cls.forms[name] = (body, meta, words)
        cls.retail = list(struct.unpack_from('>405I', (cls.root / 'conker/conker.us.bin').read_bytes(), 0x61D10))
        cls.baseline_words = cls.forms['baseline'][2]

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_all_complete_source_forms_retain_the_production_boundary(self):
        self.assertEqual(len(self.forms), 55)
        eligible = []
        for name, (body, meta, words) in self.forms.items():
            self.assertEqual((meta['frame'], meta['pool_bytes'], meta['diagnostics']), (72, 0, ''), name)
            self.assertIn('s32 first, s32 second)', body)
            if meta['body_words'] == 405 and words[:14] == self.retail[:14]:
                eligible.append(name)
                self.assertIn(meta['differences'], (76, 78), name)
            else:
                self.assertFalse(meta['body_words'] == 405 and words[:14] == self.retail[:14], name)
        self.assertEqual(len(eligible), 24)
        self.assertEqual(sum(self.forms[n][1]['differences'] == 76 for n in eligible), 22)
        self.receipt('screens', complete_bodies=55, original_extent_and_opening=eligible,
            no_lower_score_eligible_body=True, matching_credit=0)

    def test_02_whole_word_families_and_fired_fault_states(self):
        groups = {}
        for name, (_body, meta, words) in self.forms.items():
            if meta['body_words'] == 405 and words[:14] == self.retail[:14]:
                groups.setdefault(tuple(words), []).append(name)
        base = screen.previous.previous.previous.previous.fault_sweep(self.baseline_words, self.retail)
        self.assertEqual((len(base['cases']), base['fired_pairs'], base['equal_states']), (52, 2938, 1598))
        results = []
        for words, names in groups.items():
            result = screen.previous.previous.previous.previous.fault_sweep(list(words), self.retail)
            self.assertEqual((len(result['cases']), result['fired_pairs']), (52, 2938))
            self.assertEqual(result['first_cuts'], {10: 44, 7: 8})
            lost = sum(len(set(old['equal_cuts']) - set(new['equal_cuts']))
                for old, new in zip(base['cases'], result['cases']))
            if self.forms[names[0]][1]['differences'] == 76:
                self.assertEqual((result['equal_states'], lost), (1598, 0), names)
            results.append(dict(names=names, equal_states=result['equal_states'], lost_exact_cuts=lost))
        self.receipt('word-families', literal_families=len(groups), results=results,
            equal_scores_not_used_as_identity=True, installable_improvement=False)

    def test_03_owned_optimizer_inputs_and_normal_object_identity(self):
        observations = []
        fitting = screen.previous.previous.fitting
        for name in ('baseline', 'mixed-2', 'value-u0'):
            body = self.forms[name][0]
            record = fitting.trace(self.root, self.out / 'owned', name, body)
            self.assertEqual(record['compiler_sha256'], fitting.observer.COMPILERS)
            self.assertTrue(record['code_unchanged'])
            self.assertEqual(record['baseline']['body_words'], self.forms[name][1]['body_words'])
            summary = screen.prefix_summary(record)
            if name != 'value-u0':
                self.assertTrue(summary['typed_L_cache_before_bias'])
                self.assertEqual([(r['byte_offset'], r['dtype'], r['words'][1])
                    for r in summary['bias_constants']], [(592, 'L', 7)])
                self.assertEqual([(r['byte_offset'], r['dtype'], r['offset'])
                    for r in summary['storage_R3']], [(656, 'L', 3)])
                self.assertEqual([r['byte_offset'] for r in summary['bias_comparisons']], [704])
            else:
                self.assertFalse(summary['bias_constants'])
                self.assertFalse(summary['typed_L_cache_before_bias'])
                self.assertEqual([r['dtype'] for r in summary['storage_R3']], ['J', 'J'])
            work = self.out / 'owned' / name
            log = (work / 'debugger.txt').read_text()
            bad = '\n'.join(line for line in log.splitlines() if not line.startswith('FRAME_TRACE '))
            with self.assertRaises(ValueError):
                trace_tests.GameActorCommandFinalizerFittingTests.reject_trace(work, bad)
            with self.assertRaises(ValueError):
                trace_tests.GameActorCommandFinalizerFittingTests.reject_trace(work,
                    log.replace('TRACE_EXIT inferior=1 code=0', 'TRACE_EXIT inferior=1 code=1'))
            actual = Path.read_bytes
            input_path = work / 'optimizer.ucode'
            data = input_path.read_bytes()
            with patch.object(Path, 'read_bytes', lambda p: bytes((data[0] ^ 1,)) + data[1:]
                    if p == input_path else actual(p)):
                with self.assertRaises(ValueError):
                    trace_tests.GameActorCommandFinalizerFittingTests.reject_trace(work, log)
            observations.append(dict(candidate=name, inputs=record['inputs'], summary=summary))
        self.receipt('optimizer', observations=observations, effective_gate_exit_digest_controls=9,
            cached_before_bias_observed=True, physical_ready_list_not_observed=True,
            source_and_assembler_causality_not_fully_proven=True)

    def test_04_repeated_limit_records_and_typed_cache_are_not_conflated(self):
        record = json.loads((self.out / 'owned/baseline/receipt.json').read_text())
        limits = [r for r in record['records']['optimizer'] if r['name'] == 'rldc' and r['constants'] == [255, 0]]
        self.assertGreater(len(limits), 1)
        boundary = min(r['byte_offset'] for r in limits)
        self.assertTrue(all(r['byte_offset'] < boundary for r in screen.optimizer_prefix(record)))
        altered = copy.deepcopy(record)
        for r in altered['records']['optimizer']:
            if r['name'] == 'str' and r['storage'] == 'R' and r['offset'] == 3:
                r['dtype'] = 'J'
        self.assertFalse(screen.prefix_summary(altered)['typed_L_cache_before_bias'])
        self.assertTrue(screen.prefix_summary(altered)['storage_R3'])
        self.receipt('prefix-controls', earliest_actual_limit_used=True,
            typed_L_cache_not_any_R3_store=True, fabricated_field_control_only=True)

    def test_05_rejected_category_body_changes_actual_access_counts(self):
        recovery = screen.previous.previous.previous.previous.recovery
        oracle = screen.previous.previous.previous.previous.previous.previous.faults.InstructionOracle
        words = self.forms['category-primaryIndex'][2]
        differences = []
        for kind, pattern, first, second, phase in itertools.product((0, 0x70), (0, 1, 3),
                (1, 255), (2, 255), (0, 8)):
            memory, args = recovery.fixture(kind, pattern, first, second)
            models = [oracle(code, memory, args, phase, 0xFFFFFFFF).run() for code in (self.retail, words)]
            if models[0].accesses != models[1].accesses:
                differences.append(dict(kind=kind, pattern=pattern, first=first, second=second,
                    phase=phase, counts=[m.accesses for m in models]))
        self.assertTrue(differences)
        with self.assertRaises(AssertionError):
            screen.previous.previous.previous.previous.fault_sweep(words, self.retail)
        self.receipt('access-control', actual_mismatches=differences,
            original_extent_and_prefix_failed=True, original_fault_gate_not_weakened=True)

    def test_06_production_source_image_guards_profile_and_progress_unchanged(self):
        self.assertEqual(self.before, {p: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for p in self.paths})
        self.assertEqual((self.root / self.paths[0]).read_text().count(screen.BASE), 1)


if __name__ == '__main__':
    unittest.main()
