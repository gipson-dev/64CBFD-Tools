"""Full renderer qualification for shared point bases and closed GPR leases."""
import hashlib
import itertools
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_ribbon_renderer_candidates as screen
from tools.experiments import game_owner_ribbon_renderer_induction as induction
from tools.experiments import game_owner_ribbon_renderer_registers as registers
from tools.tests import test_game_owner_ribbon_renderer_induction as induction_tests
from tools.tests import test_game_owner_ribbon_renderer_recovery as recovery


class GameOwnerRibbonRendererRegistersTests(induction_tests.GameOwnerRibbonRendererInductionTests):
    @classmethod
    def setUpClass(cls):
        original_compile = screen.compile_candidate

        def compile_selected(root, out, name, body=None, profile='o2g3'):
            return original_compile(root, out, name,
                registers.SELECTED if body is None else body, profile)

        for name, value in (('SELECTED', registers.SELECTED), ('compile_candidate', compile_selected)):
            handle = patch.object(screen, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-ribbon-renderer-registers-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.normalized = registers.normalize(cls.words)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>475I', cls.rom, screen.ROM))
        cls.paths = (screen.SOURCE, 'conker/build/conker.us.elf',
                     'conker/retail_word_patches.us.csv', 'conker/progress.csv')
        cls.baseline = {p: hashlib.sha256((cls.root / p).read_bytes()).hexdigest() for p in cls.paths}
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def receipt(self, name, data):
        if name == 'fp-certificate':
            data['remaining_differences'] = 149
        super().receipt(name, data)

    def compare(self, *args, **kwargs):
        if getattr(self, 'rebasing', False):
            bodies = kwargs['bodies']
            kwargs['bodies'] = (*bodies, registers.normalize(bodies[-1]))
            return recovery.GameOwnerRibbonRendererRecoveryTests.compare(self, *args, **kwargs)
        return super().compare(*args, **kwargs)

    def test_01_complete_profiles_and_reject_installation(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences')), (475, 328, 161))
        rows = []
        for name, body in registers.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, name, body)
            self.assertEqual(meta['diagnostics'], '')
            self.assertEqual(meta['pool_bytes'], 0)
            failures = []
            for pattern, success, material, alias in itertools.product(range(4), (False, True),
                    (False, True), (False, True)):
                memory, vertex = recovery.fixture(pattern=pattern, alias=alias)
                try:
                    self.compare(memory, success=success, material=material, vertex=vertex, bodies=(words,))
                except AssertionError as error:
                    failures.append(str(error).splitlines()[0])
            if name == registers.SELECTED_NAME:
                self.assertEqual(failures, [])
            rows.append(dict(meta, contract_cases=32, contract_failures=failures))
        self.assertEqual(sum(a != b for a, b in zip(self.retail, induction.normalize_fp(self.words))), 149)
        self.assertEqual(sum(a != b for a, b in zip(self.retail, self.normalized)), 44)
        self.assertNotEqual(self.words, self.retail)
        self.assertNotEqual(self.normalized, self.retail)
        self.assertEqual([self.words[o // 4] for o in (0x29C, 0x2A4, 0x2AC)],
                         [0x8C610018, 0x8C6F001C, 0x8C610020])
        self.receipt('shape', dict(rows=rows, full_variants=len(rows), cases_per_row=32,
            raw_differences=161, FP_only_differences=149, normalized_differences=44,
            actual_shared_second_copy_base=True, guards=0, not_installed=True))

    def test_15_closed_GPR_paths_effective_collision_and_composition(self):
        certificate = registers.certify_gpr(self.words)
        self.assertEqual((certificate['paths'], certificate['words_reached'], certificate['changed_words']),
                         (1024, 320, 107))
        self.assertEqual(registers.normalize(self.words),
                         induction.normalize_fp(registers.normalize_gpr(self.words)))
        self.assertEqual(sum(a != b for a, b in zip(self.words, self.normalized)), 120)
        unsafe = {14: 15, 15: 14, 24: 14, 25: 24}
        with patch.object(registers, 'GPR_MAP', unsafe):
            changed = registers.normalize_gpr(self.words)
            self.assertEqual(sum(a != b for a, b in zip(changed, self.words)), 107)
            with self.assertRaisesRegex(ValueError, 'live GPR operand mismatch'):
                registers.certify_gpr(self.words)
        changed = list(self.words)
        changed[0x4D0 // 4] = 0x25080030
        with self.assertRaises(ValueError):
            registers.certify_gpr(changed)
        phases = []
        for begin, end in ((0, 0x26C), (0x26C, 0x380), (0x380, 0x4CC),
                           (0x4CC, 0x5D4), (0x5D4, 0x730), (0x730, 0x76C)):
            phases.append(dict(begin=begin, end=end, raw=sum(self.words[i] != self.retail[i]
                for i in range(begin // 4, end // 4)), normalized=sum(self.normalized[i] != self.retail[i]
                for i in range(begin // 4, end // 4))))
        self.receipt('gpr-certificate', dict(certificate, unsafe_live_collision_rejected=True,
            stale_counter_rejected=True, independent_FP_and_GPR_fields_commute=True,
            total_changed_words=120, remaining_differences=44, phases=phases))


if __name__ == '__main__':
    unittest.main()
