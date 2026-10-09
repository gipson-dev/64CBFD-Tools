"""Qualify the complete frame/slot-fitting renderer without installing it."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_ribbon_renderer_candidates as screen
from tools.experiments import game_owner_ribbon_renderer_fitting as fitting
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_owner_ribbon_renderer_recovery as recovery


class GameOwnerRibbonRendererFittingTests(recovery.GameOwnerRibbonRendererRecoveryTests):
    @classmethod
    def setUpClass(cls):
        original_compile = screen.compile_candidate

        def compile_fitted(root, out, name, body=None, profile='o2g3'):
            return original_compile(root, out, name,
                fitting.SELECTED if body is None else body, profile)

        for name, value in (('SELECTED', fitting.SELECTED), ('compile_candidate', compile_fitted)):
            handle = patch.object(screen, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-ribbon-renderer-fitting-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>475I', cls.rom, screen.ROM))
        cls.paths = (screen.SOURCE, 'conker/build/conker.us.elf',
                     'conker/retail_word_patches.us.csv', 'conker/progress.csv')
        cls.baseline = {p: hashlib.sha256((cls.root / p).read_bytes()).hexdigest() for p in cls.paths}
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def test_01_complete_profiles_and_reject_installation(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences')), (475, 328, 243))
        homes = (0x27A70140, 0x27B30134, 0x27B40128, 0xAFAA0120, 0x27B000EF, 0x27A500E8)
        for home in homes:
            self.assertIn(home, self.words)
        rows = []
        forms = [('selected', fitting.SELECTED), *fitting.candidates()]
        for name, body in forms:
            for profile in screen.compiler.PROFILES if name == 'selected' else ('o2g3',):
                meta, words = screen.compile_candidate(self.root, self.out, name + '-' + profile, body, profile)
                self.assertEqual(meta['diagnostics'], '')
                self.assertEqual(meta['pool_bytes'], 0)
                self.assertNotEqual(words, self.retail)
                failures = []
                for pattern, success, material, alias in itertools.product(range(4), (False, True),
                        (False, True), (False, True)):
                    memory, vertex = recovery.fixture(pattern=pattern, alias=alias)
                    try:
                        self.compare(memory, success=success, material=material,
                            vertex=vertex, bodies=(words,))
                    except AssertionError as error:
                        failures.append(dict(pattern=pattern, allocation=success, material=material,
                            alias=alias, reason=str(error).splitlines()[0]))
                if body == fitting.SELECTED and profile == 'o2g3':
                    self.assertEqual(failures, [])
                meta['contract_cases'] = 32
                meta['contract_failures'] = failures
                rows.append(meta)
        self.receipt('shape', dict(measurements=rows, full_variants=len(forms),
            cases_per_row=32, target_words=475, target_frame=328, selected_public_contract=True,
            retail_private_cursor_point_origin_sync_material_homes=True,
            no_unused_local_padding=True, no_installation_authorized=True, guards=0))

    def test_05_actual_owner_neighbors_and_padder_rejection(self):
        """The slot fits the real padder, but remaining byte differences reject installation."""
        before = (self.root / screen.SOURCE).read_text()
        after = before.replace('/* Non-matching placeholders', screen.TYPES + screen.DECLARATIONS +
            '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.SELECTED)
        objects, warnings = [], []
        for name, body in (('owner-before', before), ('owner-after', after)):
            obj, diagnostics = compile_owner(self.root, self.out, body, name)
            subprocess.run(['python3', str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / (name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
            warnings.append(diagnostics)
        self.assertEqual(warnings[0], warnings[1])
        old, of, orels = parse_object(objects[0])
        new, nf, nrels = parse_object(objects[1])
        self.assertEqual(of.keys(), nf.keys())
        for name, f in nf.items():
            if name == screen.FUNCTION:
                continue
            prior = of[name]
            self.assertEqual((f['size'], new[f['value']:f['value'] + f['size']]),
                (prior['size'], old[prior['value']:prior['value'] + prior['size']]), name)
            relative = lambda rs, ff: {o - ff['value']: r for o, r in rs.items()
                                     if ff['value'] <= o < ff['value'] + ff['size']}
            self.assertEqual(relative(nrels, f), relative(orels, prior), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        isolated, fs, _ = parse_object(self.out / 'selected.o')
        target = nf[screen.FUNCTION]
        self.assertEqual(target['size'], 1900)
        owner_body = new[target['value']:target['value'] + target['size']]
        self.assertEqual(owner_body,
            isolated[fs[screen.FUNCTION]['value']:fs[screen.FUNCTION]['value'] + fs[screen.FUNCTION]['size']])
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_1E0560')
        emitted = assembly.split(screen.FUNCTION + ':\n', 1)[1].split('.size ' + screen.FUNCTION, 1)[0]
        emitted_words = [int(line.split()[1], 16) for line in emitted.splitlines() if line.startswith('.word')]
        self.assertEqual(emitted_words, list(struct.unpack('>475I', owner_body)))
        self.assertNotIn('.space', emitted)
        self.receipt('owner', dict(neighbors=len(nf) - 1, existing_warnings=len(warnings[0]),
            new_warnings=0, pools_and_relative_relocations_preserved=True,
            actual_padder_accepts_complete_1900_byte_slot=True,
            emitted_target_raw_body_unchanged=True, no_new_guards=True, not_installed=True))

    def test_12_complete_candidate_coverage_and_saved_FP_lifetime(self):
        coverage = [set(), set()]
        cases = 0
        for flags, pattern, success, material, phase in itertools.product(
                (0, 2, 4, 8), range(2), (False, True), (False, True), (0, 8)):
            memory, vertex = recovery.fixture(flags, pattern)
            reference = recovery.RibbonReference(memory, success=success, material=material).run()
            private_calls = []
            for hits, body in zip(coverage, (self.retail, self.words)):
                model = recovery.RibbonOracle(body, memory, success=success, material=material, phase=phase)
                saved = tuple(0x3F000001 + i * 0x10001 for i in range(12))
                model.f[20:] = list(saved)
                model.saved_f = list(saved)
                model.run()
                self.assertEqual(tuple(model.f[20:]), saved)
                self.assertEqual(model.r[2], reference.result)
                self.assertEqual(model.calls, reference.calls)
                self.assertEqual(recovery.external(model.memory), recovery.external(reference.memory))
                self.assertEqual(recovery.writes(model), reference.events)
                hits.update(model.visits)
                private_calls.append(model.arguments_by_call)
            self.assertEqual(private_calls[0], private_calls[1])
            cases += 1
        expected = set(range(screen.ENTRY, screen.ENTRY + 1900, 4))
        self.assertEqual(coverage, [expected, expected])
        self.receipt('coverage', dict(cases=cases, executions=cases * 2,
            complete_retail_words=475, complete_candidate_words=475,
            all_12_callee_saved_FP_words_restored=True, exact_private_callback_output_homes=True,
            caller_saved_and_outgoing_homes_hostile=True))


if __name__ == '__main__':
    unittest.main()
