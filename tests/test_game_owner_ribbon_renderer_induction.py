"""Qualify the complete induction fit and a closed FP allocation remap."""
import hashlib
import itertools
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_ribbon_renderer_candidates as screen
from tools.experiments import game_owner_ribbon_renderer_induction as induction
from tools.tests import test_game_owner_ribbon_renderer_fitting as fitting_tests
from tools.tests import test_game_owner_ribbon_renderer_recovery as recovery


class GameOwnerRibbonRendererInductionTests(fitting_tests.GameOwnerRibbonRendererFittingTests):
    @classmethod
    def setUpClass(cls):
        original_compile = screen.compile_candidate

        def compile_selected(root, out, name, body=None, profile='o2g3'):
            return original_compile(root, out, name,
                induction.SELECTED if body is None else body, profile)

        for name, value in (('SELECTED', induction.SELECTED), ('compile_candidate', compile_selected)):
            handle = patch.object(screen, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-ribbon-renderer-induction-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.normalized = induction.normalize_fp(cls.words)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>475I', cls.rom, screen.ROM))
        cls.paths = (screen.SOURCE, 'conker/build/conker.us.elf',
                     'conker/retail_word_patches.us.csv', 'conker/progress.csv')
        cls.baseline = {p: hashlib.sha256((cls.root / p).read_bytes()).hexdigest() for p in cls.paths}
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def receipt(self, name, data):
        if getattr(self, 'normalized_run', False):
            name = 'normalized-' + name
        if name == 'rebases':
            data.update(executions=data['cases'] * 3, normalized_body_in_every_symbol_set=True)
        super().receipt(name, data)

    def compare(self, *args, **kwargs):
        bodies = kwargs.get('bodies')
        if getattr(self, 'rebasing', False):
            kwargs['bodies'] = (*bodies, induction.normalize_fp(bodies[-1]))
        return super().compare(*args, **kwargs)

    def test_01_complete_profiles_and_reject_installation(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences')), (475, 328, 163))
        rows = []
        for name, body in induction.candidates():
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
            if name == induction.SELECTED_NAME:
                self.assertEqual(failures, [])
            rows.append(dict(meta, contract_cases=32, contract_failures=failures))
        self.assertEqual(sum(a != b for a, b in zip(self.retail, self.normalized)), 151)
        self.assertNotEqual(self.words, self.retail)
        self.assertNotEqual(self.normalized, self.retail)
        self.receipt('shape', dict(rows=rows, full_variants=len(rows), cases_per_row=32,
            raw_differences=163, normalized_differences=151, guards=0, not_installed=True))

    def test_04_effective_compiled_semantic_negatives(self):
        body = screen.SELECTED
        controls = {
            'wrong-triangle': body.replace('1, 3, 2, 0', '0, 2, 3, 0'),
            'zero-holes': body.replace('cursor++;', 'cursor->v.flag = 0; cursor++;'),
            'wrong-UV': body.replace('0x3C0', '0x4000'),
            'wrong-loop': body.replace('offset != 0xF0', 'offset != 0xD8'),
            'late-origin': body.replace('    points = actor + 0x48;',
                '    origin = (OwnerRibbonPosition32C8 *)(D_800DBFF0 + view * 0x9A0 + 0x2F8);\n'
                '    points = actor + 0x48;'),
            'cached-step': body.replace('textureT += *(s32 *)(actor + 0x13C);',
                'textureT += initialStep;').replace('u32 textureT;', 'u32 textureT, initialStep;').replace(
                'textureT = *(s32 *)(actor + 0x13C);', 'textureT = *(s32 *)(actor + 0x13C); initialStep = textureT;'),
        }
        rows = []
        for name, changed in controls.items():
            self.assertNotEqual(changed, body, name)
            meta, words = screen.compile_candidate(self.root, self.out, name, changed)
            memory, vertex = recovery.fixture(pattern=1 if name == 'cached-step' else 0)
            if name == 'cached-step':
                vertex = recovery.ACTOR + 0x11C
                for axis in range(3):
                    recovery.put(memory, recovery.VIEWS + 0x2F8 + axis * 4, recovery.bits(0.))
            mode = 2 if name == 'late-origin' else 0
            reference = recovery.RibbonReference(memory, mode=mode, vertex=vertex).run()
            model = recovery.RibbonOracle(words, memory, mode=mode, vertex=vertex).run()
            self.assertNotEqual((recovery.external(model.memory), model.r[2]),
                               (recovery.external(reference.memory), reference.result), name)
            rows.append(meta)
        self.receipt('negatives', dict(complete_controls=len(rows), detected=len(rows), rows=rows))

    def test_07_independent_original_relocations_and_semantic_rebases(self):
        self.rebasing = True
        try:
            super().test_07_independent_original_relocations_and_semantic_rebases()
        finally:
            self.rebasing = False

    def test_13_closed_FP_provenance_and_effective_unsafe_map(self):
        certificate = induction.certify_fp(self.words)
        self.assertEqual((certificate['paths'], certificate['words_reached'], certificate['changed_words']),
                         (1024, 313, 13))
        unsafe = ((0x288, 0x380, {26: 30, 28: 26, 30: 28}), induction.FP_MAPS[1])
        with patch.object(induction, 'FP_MAPS', unsafe):
            changed = induction.normalize_fp(self.words)
            self.assertEqual(sum(a != b for a, b in zip(changed, self.words)), 13)
            with self.assertRaisesRegex(ValueError, 'live FP operand mismatch'):
                induction.certify_fp(self.words)
        for offset, value in ((0, 0x27BDFEB0), (0x288, 0x4480D000), (0x4D0, 0x25080030)):
            changed = list(self.words)
            changed[offset // 4] = value
            with self.assertRaises(ValueError):
                induction.certify_fp(changed)
        self.receipt('fp-certificate', dict(certificate, unsafe_live_map_rejected=True,
            stale_frame_zero_and_counter_rejected=3, remaining_differences=151))

    def test_14_full_normalized_body_qualification(self):
        original = self.words
        self.words = self.normalized
        self.normalized_run = True
        try:
            for method in (self.test_02_full_guest_strip_lazy_exits_aliases_and_coverage,
                           self.test_03_mutation_signed_views_and_callback_output_widths,
                           self.test_08_actual_complete_registered_material_callback,
                           self.test_09_lazy_reads_and_fault_prefixes,
                           self.test_11_complete_original_registered_graphics_walker,
                           self.test_12_complete_candidate_coverage_and_saved_FP_lifetime):
                method()
        finally:
            self.words = original
            self.normalized_run = False


if __name__ == '__main__':
    unittest.main()
