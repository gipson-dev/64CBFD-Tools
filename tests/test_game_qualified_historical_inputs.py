"""Exact supplemental source/guard/Makefile contexts preserve old fixtures."""
from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from tools.experiments.game_list_historical_image import digest,qualified_input_context,assert_qualified_makefile

class QualifiedHistoricalInputTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.source='conker/src/owner.c';self.baseline=self.root/'before'
        values={self.source:b'unchanged owner','conker/retail_word_patches.us.csv':b'old guards plus qualified rows',
                'conker/Makefile':b'old rules plus one table binding','conker/src/audio.c':b'qualified audio body',
                'before/conker/Makefile':b'old rules'}
        for name,data in values.items():
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        self.entry=dict(selector=dict(source_sha256=digest(self.root/self.source),
            guards_sha256=digest(self.root/'conker/retail_word_patches.us.csv')),
            inputs={n:digest(self.root/n)for n in('conker/Makefile','conker/src/audio.c')},
            overrides={'conker/Makefile':digest(self.root/'conker/Makefile')})
        self.manifest=dict(inputs={'conker/Makefile':digest(self.baseline/'conker/Makefile')},
                           qualified_input_contexts=[self.entry])

    def test_exact_context_returns_only_declared_overrides(self):
        self.assertEqual(qualified_input_context(self.root,self.source,self.manifest),self.entry['overrides'])

    def test_absent_or_other_selector_preserves_original_inputs(self):
        self.assertEqual(qualified_input_context(self.root,self.source,{}),{})
        for key in self.entry['selector']:
            manifest=deepcopy(self.manifest);manifest['qualified_input_contexts'][0]['selector'][key]='0'*64
            self.assertEqual(qualified_input_context(self.root,self.source,manifest),{})

    def test_each_qualified_input_fingerprint_is_enforced(self):
        for name in self.entry['inputs']:
            manifest=deepcopy(self.manifest);manifest['qualified_input_contexts'][0]['inputs'][name]='0'*64
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'context fingerprint changed'):
                qualified_input_context(self.root,self.source,manifest)

    def test_duplicate_context_is_rejected(self):
        self.manifest['qualified_input_contexts'].append(deepcopy(self.entry))
        with self.assertRaisesRegex(ValueError,'Duplicate qualified'):
            qualified_input_context(self.root,self.source,self.manifest)

    def test_frozen_and_exact_qualified_makefiles_are_accepted(self):
        assert_qualified_makefile(self.root,self.baseline,self.source,self.manifest)
        (self.root/'conker/retail_word_patches.us.csv').write_bytes(b'original guards')
        (self.root/'conker/Makefile').write_bytes((self.baseline/'conker/Makefile').read_bytes())
        assert_qualified_makefile(self.root,self.baseline,self.source,self.manifest)

    def test_changed_frozen_or_live_makefile_is_rejected(self):
        (self.baseline/'conker/Makefile').write_bytes(b'altered frozen rule')
        with self.assertRaisesRegex(ValueError,'fixture changed'):
            assert_qualified_makefile(self.root,self.baseline,self.source,self.manifest)
        (self.baseline/'conker/Makefile').write_bytes(b'old rules')
        (self.root/'conker/Makefile').write_bytes(b'unqualified rules')
        with self.assertRaisesRegex(ValueError,'context fingerprint changed'):
            assert_qualified_makefile(self.root,self.baseline,self.source,self.manifest)
