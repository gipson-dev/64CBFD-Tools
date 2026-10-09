"""Qualify complete ribbon color scopes and the recovered callback interface."""

import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_camera_ribbon_renderer_representation as representation
from tools.tests import test_game_camera_ribbon_renderer_controlflow as flow
from tools.tests import test_game_camera_ribbon_renderer_recovery as recovery
from tools.tests import test_game_camera_ribbon_renderer_fitting as fitting
from tools.tests import test_game_camera_ribbon_renderer_lifetimes as lifetime
from tools.tests import test_game_camera_ribbon_renderer_stackfit as stackfit
from tools.tests import test_game_camera_ribbon_renderer_staging as staging


PRIMARY = 'typed-gfx-cursor-local-colors-normals-length'
CALLBACK = 'byte-callback-cursor-local-colors-normals-length'
FORMS = {PRIMARY: (545, 0x120, 509), CALLBACK: (537, 0x120, 538)}


class GameCameraRibbonRepresentationTests(unittest.TestCase):
    select = lifetime.GameCameraRibbonLifetimeTests.select
    compare = recovery.GameCameraRibbonRecoveryTests.compare
    receipt = recovery.GameCameraRibbonRecoveryTests.receipt

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.base = cls.root / 'conker/build/game-camera-ribbon-representation-test'
        cls.bodies = dict(representation.candidates())
        cls.compiled = {name: representation.compile_form(cls.root, cls.base / name, name, cls.bodies[name])
            for name in FORMS}
        cls.retail = list(struct.unpack_from('>546I',
            (cls.root / 'conker/conker.us.bin').read_bytes(), representation.flow.staging.base.ROM))
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def exercise(self, method):
        with patch.object(fitting, 'FORMS', FORMS), patch.object(lifetime, 'FORMS', FORMS), \
                patch.object(stackfit, 'FORMS', FORMS), patch.object(staging, 'FORMS', FORMS):
            method(self)

    def run_host(self, body):
        if self.name == CALLBACK:
            # Adapt only the fixture calls; the candidate has the exact table type.
            self.fixture += '\nstatic u8 *(*ribbonCallback)(u8 *, u8 *, s16) = func_1514803C;\n' \
                'static Gfx *invokeRibbon(u8 *actor, Gfx *output, s32 view) {\n' \
                '    return (Gfx *)ribbonCallback(actor, (u8 *)output, (s16)view);\n}\n'
            body = body.replace('func_1514803C(', 'invokeRibbon(')
        recovery.GameCameraRibbonRecoveryTests.run_host(self, body)

    def test_01_baseline_and_thirteen_private_homes(self):
        baseline = json.loads((self.root /
            'conker/build/game-camera-ribbon-renderer-test/baseline.json').read_text())
        for key, path in (('source', recovery.SOURCE), ('elf', 'conker/build/conker.us.elf'),
                ('guards', 'conker/retail_word_patches.us.csv'), ('progress', 'conker/progress.csv')):
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), baseline[key])
        for name, expected in FORMS.items():
            self.select(name)
            self.assertEqual(tuple(self.record[k] for k in ('body_words', 'frame', 'differences')), expected)
            self.assertEqual((self.record['diagnostics'], self.record['pool_bytes']), ('', 0))
            gpr = [(w >> 16 & 31, w & 65535) for w in self.words[:30]
                if w >> 26 == 43 and w >> 21 & 31 == 29 and 16 <= w >> 16 & 31 <= 23
                and (w & 65535) < self.record['frame']]
            self.assertEqual(gpr, [(18, 0x6C), (17, 0x68), (16, 0x64), (19, 0x70)]
                if name == PRIMARY else [(17, 0x6C), (16, 0x68), (18, 0x70)])
            fp = [(w >> 16 & 31, w & 65535) for w in self.words[:30]
                if w >> 26 == 61 and w >> 21 & 31 == 29]
            self.assertEqual(fp, [(28, 0x58), (26, 0x50), (24, 0x48), (22, 0x40), (20, 0x38)]
                if name == PRIMARY else [(28, 0x60), (26, 0x58), (24, 0x50), (22, 0x48), (20, 0x40)])
            colors = []
            for helper, homes in ((0x0D451069, [0xC2, 0xC0, 0xBE, 0xBC]),
                    (0x0D4510BF, [0xBA, 0xB8, 0xB6, 0xB4])):
                call = self.words.index(helper)
                addresses = [w & 65535 for w in self.words[call - 20:call]
                    if w >> 26 == 9 and w >> 21 & 31 == 29 and 4 <= w >> 16 & 31 <= 7]
                self.assertEqual(addresses, homes)
                colors.extend(addresses)
            if name == PRIMARY:
                backend = self.words.index(0x0D475758)
                self.assertEqual(backend, self.retail.index(0x0D475758))
                self.assertEqual(self.words[backend + 1:backend + 5], [0x27A70118, 0x8FA20118, 0x14400003, 0])
                self.assertTrue(any(w >> 26 == 40 and w >> 21 & 31 == 29 and w & 65535 == 0x117
                    for w in self.words))
                self.assertIn(0xAFA200F0, self.words)
                for address in (0xFC, 0x108):
                    self.assertTrue(any(w & 0xFFE0FFFF == (0x27A00000 | address) for w in self.words))
            self.receipt('shape', dict(self.record, saved_gpr=gpr, saved_fp=fp, color_homes=colors,
                thirteen_private_homes_match=name == PRIMARY, recovered_callback_type=name == CALLBACK,
                raw_byte_exact=False, installed=False, guards_added=0,
                source_sha256=hashlib.sha256(self.bodies[name].encode()).hexdigest()))

    test_02_complete_geometry_and_byte_domains = flow.GameCameraRibbonControlFlowTests.test_02_complete_geometry_and_byte_domains
    test_03_mutations_and_abi_clobbers = flow.GameCameraRibbonControlFlowTests.test_03_mutations_and_abi_clobbers
    test_04_faults_aliases_and_cyclic_prefixes = flow.GameCameraRibbonControlFlowTests.test_04_faults_aliases_and_cyclic_prefixes
    test_05_actual_native32_complete_outputs = flow.GameCameraRibbonControlFlowTests.test_05_actual_native32_complete_outputs
    test_06_actual_dispatcher_and_protected_pointer = flow.GameCameraRibbonControlFlowTests.test_06_actual_dispatcher_and_protected_pointer
    test_07_nonlinear_guest_and_actual_native32 = flow.GameCameraRibbonControlFlowTests.test_07_nonlinear_guest_and_actual_native32
    test_08_copied_owner_neighbors_and_actual_padding = flow.GameCameraRibbonControlFlowTests.test_08_copied_owner_neighbors_and_actual_padding
    test_09_signed_view_guest_and_actual_native32 = flow.GameCameraRibbonControlFlowTests.test_09_signed_view_guest_and_actual_native32

    def test_10_effective_capture_and_signed_active_negatives(self):
        with patch.dict(self.bodies, {'selected-outer': self.bodies[PRIMARY]}):
            flow.GameCameraRibbonControlFlowTests.test_10_effective_signed_active_and_capture_negatives(self)

    def test_11_complete_catalog_finite_controls(self):
        records, groups = [], {}
        memory = next(lifetime.nonlinear_cases())
        for name, body in representation.candidates():
            meta, words = representation.compile_form(self.root, self.base / 'screen', name, body)
            for sample, mode in ((memory, 0), (recovery.fixture(bank=1, pattern=1), 0), (recovery.fixture(), 2)):
                self.compare(sample, words=words, mode=mode, view=0x18000, write_order=False)
            fingerprint = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
            groups.setdefault(fingerprint, []).append(name)
            records.append(dict(meta, words_sha256=fingerprint,
                source_sha256=hashlib.sha256(body.encode()).hexdigest()))
        self.assertEqual(len(records), 51)
        (self.base / 'catalog.json').write_text(json.dumps(dict(forms=records,
            emitted_groups=list(groups.values()), finite_samples_per_form=3,
            full_qualification_for_every_form=False, write_order_required=False), indent=2) + '\n')

    def test_12_primary_independent_symbol_rebases(self):
        name = 'selected-outer'
        compiled = representation.compile_form(self.root, self.base / name, name, self.bodies[PRIMARY])
        self.assertEqual(compiled[1], self.compiled[PRIMARY][1])
        with patch.dict(self.compiled, {name: compiled}), patch.dict(self.bodies, {name: self.bodies[PRIMARY]}):
            flow.GameCameraRibbonControlFlowTests.test_12_original_and_candidate_independent_symbol_rebases(self)


if __name__ == '__main__':
    unittest.main()
