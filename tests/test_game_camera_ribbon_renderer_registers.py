"""Bounded complete-body controls for rejected ribbon register-lifetime forms."""

import hashlib
import json
import struct
import unittest
from pathlib import Path

from tools.experiments import game_camera_ribbon_renderer_registers as screen
from tools.tests import test_game_camera_ribbon_renderer_recovery as recovery
from tools.tests import test_game_camera_ribbon_renderer_lifetimes as lifetime


class GameCameraRibbonRegisterTests(unittest.TestCase):
    compare = recovery.GameCameraRibbonRecoveryTests.compare

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.base = cls.root / 'conker/build/game-camera-ribbon-registers-test'
        cls.bodies = dict(screen.candidates())
        cls.compiled = {name: screen.compile_form(cls.root, cls.base / name, name, body)
            for name, body in cls.bodies.items()}
        cls.retail = list(struct.unpack_from('>546I',
            (cls.root / 'conker/conker.us.bin').read_bytes(), screen.representation.flow.staging.base.ROM))

    def test_01_baseline_and_measured_exclusions(self):
        baseline = json.loads((self.root /
            'conker/build/game-camera-ribbon-renderer-test/baseline.json').read_text())
        for key, path in (('source', recovery.SOURCE), ('elf', 'conker/build/conker.us.elf'),
                ('guards', 'conker/retail_word_patches.us.csv'), ('progress', 'conker/progress.csv')):
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), baseline[key])
        self.assertEqual(len(self.bodies), 18)
        self.assertEqual(hashlib.sha256(self.bodies['color-homes'].encode()).hexdigest(),
            'a534396c5cd213f73ce0f33f5567ab8bfe55446df98de1cdf892c621203d3425')
        for name, (meta, words) in self.compiled.items():
            self.assertEqual((meta['diagnostics'], meta['pool_bytes']), ('', 0))
            if name in ('color-homes', 'color-homes-phase'):
                self.assertEqual(tuple(meta[k] for k in ('body_words', 'frame', 'differences')),
                    (545, 0x120, 509))
                self.assertEqual(meta['saved_FP'], [28, 26, 24, 22, 20])
            else:
                self.assertGreater(meta['body_words'], 546)
                if not name.startswith('color-homes'):
                    self.assertEqual(meta['saved_FP'], [30, 28, 26, 24, 22, 20])
            payload = [w >> 16 & 31 for w in words if w >> 26 == 35 and
                w >> 21 & 31 == 17 and w & 65535 == 0x98]
            records = [w >> 16 & 31 for w in words if w >> 26 == 35 and
                w >> 21 & 31 == 17 and w & 65535 == 0x94]
            self.assertNotEqual((payload, records), ([18], [13]))

    def test_02_complete_body_finite_controls_and_fingerprints(self):
        cases = ((next(lifetime.nonlinear_cases()), 0),
            (recovery.fixture(bank=1, pattern=1), 0), (recovery.fixture(), 2))
        groups, records = {}, []
        for name, (meta, words) in self.compiled.items():
            for memory, mode in cases:
                self.compare(memory, words=words, mode=mode, view=0x18000, write_order=False)
            fingerprint = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
            groups.setdefault(fingerprint, []).append(name)
            records.append(dict(meta, words_sha256=fingerprint,
                source_sha256=hashlib.sha256(self.bodies[name].encode()).hexdigest()))
        (self.base / 'catalog.json').write_text(json.dumps(dict(forms=records,
            emitted_groups=list(groups.values()), finite_cases=len(cases) * len(records),
            full_qualification_for_every_form=False, ordered_writes_required=False,
            production_installed=False, guards_added=0), indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
