"""Archive integrity, conditional discovery and overlapping failure queues."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import alternative_source_coverage_refresh as source
from tools.experiments.alternative_source_c_inventory import definitions


class AlternativeSourceCoverageRefreshTests(unittest.TestCase):
    def test_801_real_inputs_unknown_manifest_changed_source_and_missing_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = {}
            for i in range(801):
                name = 'input-%d.c' % i
                path = root / name
                path.write_bytes(str(i).encode())
                files[name] = source.digest(path).upper()
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps(dict(files=files)))
            with self.assertRaisesRegex(ValueError, 'Unknown original'):
                source.verify_archive(root, manifest)
            with patch.object(source, 'MANIFEST_SHA256', source.digest(manifest)):
                self.assertEqual(source.verify_archive(root, manifest), files)
                path = root / 'input-400.c'
                path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'Changed original archive input'):
                    source.verify_archive(root, manifest)
                path.unlink()
                with self.assertRaises(FileNotFoundError):
                    source.verify_archive(root, manifest)
            files.pop('input-400.c')
            manifest.write_text(json.dumps(dict(files=files)))
            with patch.object(source, 'MANIFEST_SHA256', source.digest(manifest)):
                with self.assertRaisesRegex(ValueError, 'file count'):
                    source.verify_archive(root, manifest)

    def test_failed_queues_overlap_and_exact_recoveries_are_not_readded(self):
        def receipt(*names):
            return dict(draft_compile_gate=[dict(function=n, status='compile_error') for n in names] +
                [dict(function='compiled', status='object_compiled')])
        result = source.pending_failures(dict(individual=receipt('a', 'b', 'b', 'done'),
            commented=receipt('b', 'c', 'done')), {'done'})
        self.assertEqual(result['by_origin'], dict(individual=['a', 'b'], commented=['b', 'c']))
        self.assertEqual(result['unique_functions'], ['a', 'b', 'c'])
        self.assertEqual(result['unique_count'], 3)
        self.assertTrue(result['historical_failures_not_fresh_compiles'])
        self.assertEqual(source.pending_failures({}, set())['unique_count'], 0)

    def test_conditional_definitions_are_not_treated_as_enabled_C(self):
        text = '''void active(void) { }
#if 0
void disabled(void) { }
#endif
#ifdef FEATURE
void dependent(void) { }
#endif
'''
        rows = source.disabled_regions(text, definitions(text))
        self.assertEqual([(r['function'], r['preceding_conditional']) for r in rows],
            [('disabled', '#if 0'), ('dependent', '#ifdef FEATURE')])
        self.assertTrue(all(row['conditional_is_not_proof_of_active_compilation'] for row in rows))

    def test_all_four_historical_successful_object_corpora_are_retained(self):
        self.assertEqual(set(source.SCREENS), {'whole', 'isolated', 'interface-retry', 'commented'})
        self.assertEqual(len(set(source.SCREENS.values())), 4)
        self.assertEqual(source.MANIFEST_SHA256, 'd8a07543bcd17a19096e744a66f67a2bf36ba153b51c81e569ae76b95e6581e1')

    def test_bindings_deduplicate_profiles_and_cross_corpus_rows(self):
        row = dict(function='one', status='needs_symbol_or_pool_binding', unresolved=['table'])
        other = dict(row, unresolved=['pool', 'table'])
        result = source.binding_queue(dict(commented=dict(function_results=[row, row, other]),
            whole=dict(function_results=[other, dict(function='different', status='word_different')])))
        self.assertEqual(result, dict(one=dict(origins=['commented', 'whole'], symbols=['pool', 'table'])))

    def test_historical_source_generated_isolated_and_object_hash_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('original.c', 'expanded.c', 'isolated.c', 'isolated.o'):
                (root / name).write_bytes(name.encode())
            row = dict(path='original.c', source_sha256=source.digest(root / 'original.c'), function='target',
                generated_input_path='expanded.c', generated_input_sha256=source.digest(root / 'expanded.c'),
                isolated_source_sha256=source.digest(root / 'isolated.c'), object=str(root / 'isolated.o'),
                object_sha256=source.digest(root / 'isolated.o'), status='object_compiled')
            receipts = dict(one=dict(draft_compile_gate=[row]))
            self.assertEqual(source.verify_receipts(root, receipts), dict(object_compiled=1))
            for name in ('original.c', 'expanded.c', 'isolated.c', 'isolated.o'):
                path = root / name
                old = path.read_bytes()
                path.write_bytes(old + b'changed')
                with self.assertRaisesRegex(ValueError, 'Changed historical'):
                    source.verify_receipts(root, receipts)
                path.write_bytes(old)


if __name__ == '__main__':
    unittest.main()
