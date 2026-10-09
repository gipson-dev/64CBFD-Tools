"""Qualify the complete slot-fitting ribbon exit-flow candidate."""

import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_camera_ribbon_renderer_controlflow as flow
from tools.tests import test_game_camera_ribbon_renderer_recovery as recovery
from tools.tests import test_game_camera_ribbon_renderer_fitting as fitting
from tools.tests import test_game_camera_ribbon_renderer_lifetimes as lifetime
from tools.tests import test_game_camera_ribbon_renderer_stackfit as stackfit
from tools.tests import test_game_camera_ribbon_renderer_staging as staging
from tools.tests.test_game_record_ring_renderer_recovery import external, writes


FORMS = {'selected-outer': (545, 0x120, 509)}


class GameCameraRibbonControlFlowTests(unittest.TestCase):
    select = lifetime.GameCameraRibbonLifetimeTests.select
    compare = recovery.GameCameraRibbonRecoveryTests.compare
    receipt = recovery.GameCameraRibbonRecoveryTests.receipt
    run_host = recovery.GameCameraRibbonRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.base = cls.root / 'conker/build/game-camera-ribbon-controlflow-test'
        cls.bodies = dict(flow.candidates())
        cls.compiled = {name: flow.compile_form(cls.root, cls.base / name, name, cls.bodies[name])
            for name in FORMS}
        cls.retail = list(struct.unpack_from('>546I',
            (cls.root / 'conker/conker.us.bin').read_bytes(), flow.staging.base.ROM))
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def exercise(self, method):
        with patch.object(fitting, 'FORMS', FORMS), patch.object(lifetime, 'FORMS', FORMS), \
                patch.object(stackfit, 'FORMS', FORMS), patch.object(staging, 'FORMS', FORMS):
            method(self)

    def test_01_baseline_slots_and_retail_exit_flow(self):
        baseline = json.loads((self.root /
            'conker/build/game-camera-ribbon-renderer-test/baseline.json').read_text())
        for key, path in (('source', recovery.SOURCE), ('elf', 'conker/build/conker.us.elf'),
                ('guards', 'conker/retail_word_patches.us.csv'), ('progress', 'conker/progress.csv')):
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), baseline[key])
        self.assertIn(flow.staging.base.ORIGINAL, (self.root / recovery.SOURCE).read_text())
        for name, expected in FORMS.items():
            self.select(name)
            self.assertEqual(tuple(self.record[k] for k in ('body_words', 'frame', 'differences')), expected)
            self.assertEqual((self.record['diagnostics'], self.record['pool_bytes']), ('', 0))
            gpr = [(w >> 16 & 31, w & 65535) for w in self.words[:30]
                if w >> 26 == 43 and w >> 21 & 31 == 29 and 16 <= w >> 16 & 31 <= 23
                and (w & 65535) < self.record['frame']]
            fp = [(w >> 16 & 31, w & 65535) for w in self.words[:30]
                if w >> 26 == 61 and w >> 21 & 31 == 29]
            self.assertEqual(gpr, [(18, 0x6C), (17, 0x68), (16, 0x64), (19, 0x70)])
            self.assertEqual(fp, [(28, 0x58), (26, 0x50), (24, 0x48), (22, 0x40), (20, 0x38)])
            backend = self.words.index(0x0D475758)
            self.assertEqual(backend, self.retail.index(0x0D475758))
            self.assertEqual(self.words[21] & 0xFFFF0000, 0x14200000)
            self.assertEqual(self.words[backend + 1:backend + 5],
                [0x27A70118, 0x8FA20118, 0x14400003, 0])
            self.assertEqual(self.words[backend + 5] & 0xFFFF0000, 0x10000000)
            self.assertEqual(self.words[backend + 6], 0x02001025)
            self.assertEqual(self.words[backend + 7] & 0xFFFF0000, 0x10400000)
            origin = self.words.index(0x0D4512CD)
            self.assertTrue(any(w >> 26 == 40 and w >> 21 & 31 == 29 and w & 65535 == 0x117
                for w in self.words[backend:origin + 2]))
            self.assertIn(0xAFA200F0, self.words[origin:origin + 10])
            self.assertTrue(any(w & 0xFFE0FFFF == 0x27A000FC for w in self.words))
            self.assertTrue(any(w & 0xFFE0FFFF == 0x27A00108 for w in self.words))
            self.receipt('shape', dict(self.record, saved_gpr=gpr, saved_fp=fp,
                cursor=0x118, sync=0x117, origin=0xF0, previous=0xFC, current=0x108,
                active_and_cursor_branch_shape=True, setup_register_roles_match=False,
                raw_difference_improved=False, installed=False, guards_added=0,
                source_sha256=hashlib.sha256(self.bodies[name].encode()).hexdigest()))

    def test_02_complete_geometry_and_byte_domains(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_02_full_geometry_and_all_byte_widths)

    def test_03_mutations_and_abi_clobbers(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_03_live_setup_mutations_and_abi_clobbers)

    def test_04_faults_aliases_and_cyclic_prefixes(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_04_fault_prefixes_aliases_and_cyclic_prefixes)

    def test_05_actual_native32_complete_outputs(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_05_actual_native32_complete_outputs)

    def test_06_actual_dispatcher_and_protected_pointer(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_06_complete_dispatcher_and_protected_table)

    def test_07_nonlinear_guest_and_actual_native32(self):
        self.exercise(lifetime.GameCameraRibbonLifetimeTests.test_08_nonlinear_float32_geometry_guest_and_native)

    def test_08_copied_owner_neighbors_and_actual_padding(self):
        self.exercise(stackfit.GameCameraRibbonStackFitTests.test_08_copied_owner_neighbors_and_padding_boundary)

    def test_09_signed_view_guest_and_actual_native32(self):
        self.exercise(staging.GameCameraRibbonStagingTests.test_09_raw_view_clipping_guest_and_native32)

    def test_10_effective_signed_active_and_capture_negatives(self):
        body = self.bodies['selected-outer']
        unsigned = body.replace('*(s8 *)(actor + 0x2C)', '*(u8 *)(actor + 0x2C)')
        capture = body.replace('        origin = func_15144B34(view);\n'
            '        records = *(CameraRibbonRecord **)(actor + 0x94);',
            '        records = *(CameraRibbonRecord **)(actor + 0x94);\n'
            '        origin = func_15144B34(view);')
        records = []
        for name, altered, memory, mode in (('unsigned-active', unsigned, recovery.fixture(active=255), 0),
                ('early-records', capture, recovery.fixture(), 2)):
            self.assertNotEqual(altered, body)
            meta, words = flow.compile_form(self.root, self.base, 'negative-' + name, altered)
            model = recovery.CameraRibbonOracle(words, memory, mode=mode).run()
            reference = recovery.CameraRibbonReference(memory, mode=mode).run()
            self.assertNotEqual((external(model.memory), model.calls, model.r[2]),
                (external(reference.memory), reference.calls, reference.result))
            records.append(dict(meta, effective=True, mode=mode))
        (self.base / 'negatives.json').write_text(json.dumps(records, indent=2) + '\n')

    def test_11_catalog_finite_controls_and_duplicate_schedules(self):
        records, groups, fingerprints = [], {}, {}
        memory = next(lifetime.nonlinear_cases())
        for name, body in flow.candidates():
            meta, words = flow.compile_form(self.root, self.base / 'screen', name, body)
            for sample, mode in ((memory, 0), (recovery.fixture(bank=1, pattern=1), 0), (recovery.fixture(), 2)):
                self.compare(sample, words=words, mode=mode, view=0x18000, write_order=False)
            fingerprint = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
            fingerprints[name] = fingerprint
            groups.setdefault(fingerprint, []).append(name)
            records.append(dict(meta, words_sha256=fingerprint,
                source_sha256=hashlib.sha256(body.encode()).hexdigest()))
        for name in ('selected', 'mixed'):
            self.assertEqual(fingerprints[name + '-outer'], fingerprints[name + '-goto'])
            for mode in ('early', 'outer', 'empty-null', 'goto'):
                self.assertNotEqual(fingerprints[name + '-' + mode], fingerprints[name + '-' + mode + '-phase'])
                self.assertEqual(fingerprints[name + '-' + mode + '-phase-stride'],
                    fingerprints[name + '-' + mode + '-phase-stride-register'])
        for suffix in ('', '-split-index'):
            scaled = [fingerprints['mixed-outer-scale-' + order + suffix]
                for order in ('XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX')]
            self.assertEqual(len(set(scaled)), 6)
        (self.base / 'catalog.json').write_text(json.dumps(dict(forms=records,
            emitted_groups=list(groups.values()), finite_samples_per_form=3,
            full_qualification_for_every_form=False, write_order_required=False,
            independent_scale_orders_change_words=True,
            same_shape_does_not_imply_same_instruction_stream=True), indent=2) + '\n')

    def test_12_original_and_candidate_independent_symbol_rebases(self):
        base = flow.staging.base
        name = 'selected-outer'
        self.select(name)
        assembly, original_obj = self.out / 'original.s', self.out / 'original.o'
        original = (self.root / 'conker/asm/nonmatchings/generated_175250/func_1514803C.s').read_text()
        assembly.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n.type ' +
            base.FUNCTION + ', @function\n' + original + '\n.size ' + base.FUNCTION +
            ', . - ' + base.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(original_obj), str(assembly)],
            cwd=self.root, check=True, capture_output=True)
        _, functions, original_rel = recovery.parse_object(original_obj)
        candidate_obj = self.out / (name + '.o')
        _, _, candidate_rel = recovery.parse_object(candidate_obj)
        self.assertEqual(functions[base.FUNCTION]['size'], 2184)
        self.assertCountEqual([r for rows in original_rel.values() for r in rows],
            [r for rows in candidate_rel.values() for r in rows])
        results = []
        for variant, entry in enumerate((base.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = dict(base.SYMBOLS)
            if variant:
                for index, symbol in enumerate(n for n in symbols if n.startswith('D_')):
                    symbols[symbol] = 0x70000000 + (index + 1) * 0x100000 + \
                        (0x7FFC, 0x8000, 0xFFF8)[(index + variant) % 3]
                for index, symbol in enumerate(recovery.COUNTS):
                    symbols[symbol] = (entry & 0xF0000000) + 0x100800 + index * 0x100
            script = self.out / ('rebase-%d.ld' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for kind, obj, count in (('original', original_obj, 546), ('candidate', candidate_obj, 545)):
                elf = self.out / ('rebase-%d-%s.elf' % (variant, kind))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', base.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % count, base.sections(elf)['.text'][1])))
            if not variant:
                self.assertEqual(bodies, [self.retail, self.words])
            cases = []
            with patch.dict(base.SYMBOLS, symbols, clear=True):
                for bank, phase, view, mode in itertools.product((0, 1), (0, 8),
                        (0, 0x18000, 0x80000000), (0, 2, 7)):
                    cases.append((recovery.fixture(bank=bank), view, mode, phase, True))
                for active, success in itertools.product((128, 1, 2, 127), (False, True)):
                    cases.append((recovery.fixture(active=active), 0x18000, 0, 0, success))
                nonlinear = next(lifetime.nonlinear_cases())
                cases.extend((nonlinear, 0x7FFFFFFF, 0, phase, True) for phase in (0, 8))
                for memory, view, mode, phase, success in cases:
                    reference = recovery.CameraRibbonReference(memory, view=view, mode=mode, success=success).run()
                    expected = (external(reference.memory), reference.calls, reference.result, reference.events)
                    for body in bodies:
                        model = recovery.CameraRibbonOracle(body, memory, view=view, mode=mode,
                            phase=phase, success=success, entry=entry).run()
                        self.assertEqual((external(model.memory), model.calls, model.r[2], writes(model)), expected)
            results.append(dict(entry=entry, cases=len(cases), guest_executions=len(cases) * 2,
                symbols=symbols, independent_original_and_candidate_links=True))
        self.receipt('rebases', dict(symbol_sets=len(results), independent_links=len(results) * 2,
            relocation_uses=sum(map(len, original_rel.values())), results=results,
            HI16_carry_LO16_sign_and_JAL_regions=True, whole_native_caller_or_hardware_proven=False))


if __name__ == '__main__':
    unittest.main()
