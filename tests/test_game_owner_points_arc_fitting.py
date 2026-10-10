"""Qualify complete arc fitting forms without granting installation credit."""
import hashlib
import itertools
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_arc_fitting as fitting
from tools.tests import test_game_owner_points_arc_recovery as recovery


def saved_signature(words):
    gpr, fp = [], []
    for word in words:
        op, base, register, offset = word >> 26, word >> 21 & 31, word >> 16 & 31, word & 65535
        if base != 29:
            continue
        if op == 43 and register in (*range(16, 24), 31):
            gpr.append((register, offset))
        if op == 61 and register >= 20:
            fp.append((register, offset))
    return dict(gpr=sorted(gpr), fp=sorted(fp))


class GameOwnerPointsArcFittingTests(unittest.TestCase):
    compare = recovery.GameOwnerPointsArcRecoveryTests.compare
    receipt = recovery.GameOwnerPointsArcRecoveryTests.receipt
    run_host = recovery.GameOwnerPointsArcRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-arc-fitting-test'
        cls.forms = dict(fitting.candidates())
        if len(cls.forms) != len(list(fitting.candidates())):
            raise ValueError('duplicate fitting names')
        cls.body = cls.forms['midpoint-pointer']
        cls.meta, cls.words = fitting.compile_candidate(cls.root, cls.out, 'midpoint-pointer', cls.body)
        cls.retail = list(struct.unpack_from('>142I', (cls.root / 'conker/conker.us.bin').read_bytes(),
            fitting.base.ROM))
        cls.paths = dict(source=fitting.base.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        previous = cls.root / 'conker/build/game-owner-points-arc-test/baseline.json'
        cls.baseline = json.loads(previous.read_text()) if previous.exists() else {
            name: hashlib.sha256((cls.root / path).read_bytes()).hexdigest() for name, path in cls.paths.items()}
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def test_01_complete_forms_profiles_and_frame_coincidence(self):
        rows, cases = [], 0
        for name, body in self.forms.items():
            profiles = fitting.base.compiler.PROFILES if name in (
                'midpoint-pointer', 'snapshot-all-reused-radius-sine', 'grouped-compact') else ('o2g3',)
            for profile in profiles:
                meta, words = fitting.compile_candidate(self.root, self.out, name + '-' + profile, body, profile)
                self.assertEqual((meta['pool_bytes'], meta['diagnostics']), (0, ''))
                for index, phase in itertools.product((0, 2, 4, 5), (0, 8)):
                    self.compare(recovery.fixture(index), phase=phase, bodies=(self.retail, words))
                    cases += 1
                rows.append(dict(meta, saved=saved_signature(words), byte_exact=words == self.retail))
        coincident = next(row for row in rows if row['name'] == 'snapshot-all-reused-radius-sine-o1g3')
        self.assertEqual((coincident['body_words'], coincident['frame'], coincident['differences']), (178, 136, 175))
        self.assertNotEqual(coincident['saved'], saved_signature(self.retail))
        self.assertFalse(any(row['byte_exact'] for row in rows))
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences')), (147, 152, 147))
        self.receipt('forms', dict(forms=len(self.forms), profiles=len(rows), cases=cases, executions=cases * 2,
            measurements=rows, retail_saved=saved_signature(self.retail), installation_rejected=True,
            frame_size_alone_not_acceptance=True, guards=0))

    def test_02_midpoint_pointer_flags_boundaries_mutations_and_coverage(self):
        coverage, cases = [set(), set()], 0
        for flags, index, phase in itertools.product(range(256), (0, 2, 4, 5), (0, 8)):
            for i, model in enumerate(self.compare(recovery.fixture(index, flags), phase=phase, seed=flags % 4)):
                coverage[i].update(model.visits)
            cases += 1
        for visited, length in zip(coverage, (142, 147)):
            self.assertEqual(visited, set(range(fitting.base.ENTRY, fitting.base.ENTRY + length * 4, 4)))
        actions = {0: [(recovery.ACTOR + 0x14, recovery.bits(99), 4),
            (fitting.base.SYMBOLS['D_800AA3A4'], recovery.bits(-0.5), 4),
            (fitting.base.SYMBOLS['D_800AA3A8'], recovery.bits(0.125), 4)],
            1: [(fitting.base.SYMBOLS['D_800AA3A8'], recovery.bits(-3), 4), (recovery.ACTOR + 0x10, 0xA2, 1)]}
        for index, phase, mutate in itertools.product(range(len(recovery.GEOMETRIES)), (0, 8), (False, True)):
            self.compare(recovery.fixture(index), phase=phase, actions=actions if mutate else {})
        negatives = (
            ('return', '    return 1;', '    return 0;'),
            ('count', 'offset != 0xF0', 'offset != 0xD8'),
            ('step', 'angle += angleStep;', 'angle -= angleStep;'),
            ('fresh-step', 'angle += angleStep;', 'angle += D_800AA3A8;'),
            ('arg-order', 'func_150484A0(vertical, projection)', 'func_150484A0(projection, vertical)'),
            ('threshold', 'D_800AA3A0 < fabsf(dx)', 'D_800AA3A0 <= fabsf(dx)'),
            ('position', 'along * nx + center->x', 'along * nz + center->x'),
        )
        for name, old, new in negatives:
            self.assertEqual(self.body.count(old), 1, name)
            _, words = fitting.compile_candidate(self.root, self.out, 'negative-' + name, self.body.replace(old, new))
            rejected = False
            for index in (1, 4, 5):
                try:
                    self.compare(recovery.fixture(index), actions=actions, bodies=(words,))
                except AssertionError:
                    rejected = True
                    break
            self.assertTrue(rejected, name)
        self.receipt('guest', dict(cases=cases, executions=cases * 2, boundary_cases=48, boundary_executions=96,
            complete_words_reached=[142, 147], effective_compiled_negatives=len(negatives),
            saved_registers_actor_and_canaries_preserved=True, helper_contracts_only=True))

    def test_03_actual_native32_midpoint_pointer(self):
        with patch.object(recovery.screen, 'COMPACT', self.body):
            recovery.GameOwnerPointsArcRecoveryTests.test_04_actual_native32_source_against_original_guest(self)

    def test_04_production_fingerprints_and_closed_installation_gate(self):
        for name, path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), self.baseline[name])
        self.assertGreater(len(self.words), fitting.base.WORDS)
        self.assertNotEqual(saved_signature(self.words), saved_signature(self.retail))
        self.assertNotEqual(self.words, self.retail)
        self.assertEqual(saved_signature(self.retail), dict(gpr=[(16, 68), (17, 72), (18, 76), (19, 80), (31, 84)],
            fp=[(20, 16), (22, 24), (24, 32), (26, 40), (28, 48), (30, 56)]))
        self.receipt('production', dict(fingerprints=self.baseline, unchanged=True, installation_rejected=True,
            reason='frame, saved-register homes, word count and schedule differ', guards_added=0,
            matching_credit=0, no_FCSR_hardware_or_rendering_acceptance=True))


if __name__ == '__main__':
    unittest.main()
