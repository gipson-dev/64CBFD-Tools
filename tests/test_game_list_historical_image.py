"""Frozen historical object substitution is exact, scoped and fail-closed."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from tools.experiments.game_list_historical_image import digest, historical_dependencies


class HistoricalImageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / 'private'
        self.output.mkdir()
        self.source = 'conker/src/list.c'
        self.paths = {
            self.source: b'list owner',
            'conker/retail_word_patches.us.csv': b'qualified guards',
            'conker/src/effect.c': b'qualified effect source',
            'conker/build/effect.o': b'qualified live object',
            'conker/private/before/effect.o': b'original frozen object',
            'conker/build/conker.ld': b'INPUT(build/effect.o)\n',
        }
        for name, value in self.paths.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value)
        self.entry = dict(
            source_sha256=digest(self.root / self.source),
            guards_sha256=digest(self.root / 'conker/retail_word_patches.us.csv'),
            overrides=[dict(source='conker/src/effect.c',
                            source_sha256=digest(self.root / 'conker/src/effect.c'),
                            object='conker/build/effect.o',
                            live_sha256=digest(self.root / 'conker/build/effect.o'),
                            frozen='conker/private/before/effect.o',
                            frozen_sha256=digest(self.root / 'conker/private/before/effect.o'))])
        self.manifest = dict(historical_image_dependencies=[self.entry])

    def enter(self, manifest=None):
        return historical_dependencies(self.root, self.output, self.source,
                                       self.manifest if manifest is None else manifest)

    def test_exact_snapshot_uses_only_private_linker_copy(self):
        with self.enter() as script:
            self.assertEqual(script, 'private/historical-dependencies.ld')
            self.assertEqual((self.root / script).read_bytes(),
                             b'INPUT(private/before/effect.o)\n')
        for name, value in self.paths.items():
            self.assertEqual((self.root / name).read_bytes(), value)

    def test_absent_or_other_snapshot_keeps_live_script(self):
        for field in ('source_sha256', 'guards_sha256'):
            manifest = deepcopy(self.manifest)
            manifest['historical_image_dependencies'][0][field] = '0' * 64
            with self.enter(manifest) as script:
                self.assertEqual(script, 'conker/build/conker.ld')
        with self.enter({}) as script:
            self.assertEqual(script, 'conker/build/conker.ld')
        self.assertFalse((self.output / 'historical-dependencies.ld').exists())

    def test_each_dependency_fingerprint_is_enforced(self):
        for field in ('source_sha256', 'live_sha256', 'frozen_sha256'):
            manifest = deepcopy(self.manifest)
            manifest['historical_image_dependencies'][0]['overrides'][0][field] = '0' * 64
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'fingerprint changed'):
                with self.enter(manifest):
                    self.fail('Changed dependency accepted')

    def test_duplicate_snapshot_is_rejected(self):
        manifest = deepcopy(self.manifest)
        manifest['historical_image_dependencies'].append(deepcopy(self.entry))
        with self.assertRaisesRegex(ValueError, 'Duplicate historical'):
            with self.enter(manifest):
                self.fail('Ambiguous snapshot accepted')

    def test_missing_or_ambiguous_object_reference_is_rejected(self):
        for value in (b'INPUT(build/other.o)\n', b'INPUT(build/effect.o build/effect.o)\n'):
            (self.root / 'conker/build/conker.ld').write_bytes(value)
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'reference changed'):
                with self.enter():
                    self.fail('Ambiguous linker substitution accepted')


if __name__ == '__main__':
    unittest.main()
