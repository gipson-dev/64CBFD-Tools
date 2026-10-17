"""Qualify the target-specific upstream-home trace without granting C credit."""
import hashlib
import json
from pathlib import Path
import struct
import time
import unittest
from unittest.mock import patch

from tools.experiments import game_mirrored_texture_compiler_trace as trace


class MirroredTextureCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / trace.source.BUILD
        cls.run_id = 'qualification-' + str(time.time_ns())
        cls.rows = {name: trace.trace(cls.root, name, cls.run_id) for name in trace.forms()}

    def work(self, name='record'):
        return self.out / (self.run_id + '-' + name)

    def test_01_owned_complete_traces_unchanged_code_bindings_pools_and_fired_nodes(self):
        for name, row in self.rows.items():
            with self.subTest(name=name):
                self.assertEqual(tuple(row['baseline'][k] for k in ('words', 'frame', 'differences', 'raw_sha256')), trace.KNOWN[name])
                self.assertTrue(row['code_unchanged'])
                self.assertTrue(row['isolated_target_matches_complete_owner'])
                self.assertFalse(row['installable'])
                self.assertEqual(row['isolated_pools'], {})
                self.assertGreater(len(row['node_events']), 250)
                self.assertEqual(row['compiler_sha256'], trace.frame.COMPILERS)
                self.assertEqual(row['events'][-1]['temporary'], 0)
                self.assertEqual(row['events'][-1]['pool'], [])
                # These observations are not equality with the 633-word retail routine.
                self.assertNotEqual(row['baseline']['words'], trace.source.WORDS)

    def test_02_positive_y_and_rate_homes_are_in_uopt_input_not_invented_by_ugen(self):
        row = self.rows['record']
        records = row['records']['optimizer']
        shape = lambda r: (r['name'], r['dtype'], r['storage'], r['offset'])
        self.assertEqual([shape(r) for r in records[90:96]], [
            ('rlod', 'R', 'P', 16), ('lod', 'R', 'R', 44), ('lod', 'R', 'R', 50),
            ('add', 'R', None, None), ('vreg', 'R', 'M', -120), ('str', 'R', 'M', -120)])
        # The earlier Y center is row+16 plus projected+4, allocated to float register 44.
        self.assertEqual([shape(records[i]) for i in (45, 47, 48, 49)], [
            ('ilod', 'R', None, 0), ('ilod', 'R', None, 0),
            ('add', 'R', None, None), ('str', 'R', 'R', 44)])
        self.assertEqual((records[45]['words'][1], records[47]['words'][1]), (4, 16))
        self.assertEqual(records[90]['level'], 50)
        homes = [(i, r['dtype'], r['offset']) for i, r in enumerate(records)
            if r['name'] == 'str' and r['storage'] == 'M']
        self.assertEqual(homes[:4], [(95, 'R', -120), (210, 'L', -144), (215, 'J', -148), (220, 'J', -152)])
        frame = row['baseline']['frame']
        self.assertEqual([frame + offset for _, _, offset in homes[:4]], [0x60, 0x48, 0x44, 0x40])
        self.assertEqual(records[213]['name'], 'cvt')
        self.assertEqual(records[218]['name'], 'neg')
        raw = trace.source.parts(self.work() / 'baseline.o')[0]
        words = struct.unpack('>%dI' % (len(raw) // 4), raw)
        stores = [(i * 4, w & 65535) for i, w in enumerate(words) if w >> 26 == 0x39 and (w >> 21) & 31 == 29]
        self.assertEqual(stores[0], (0xAC, 0x60))
        self.assertTrue(any(n['type_storage'] == 45 and n['raw44'] == (-120 & 0xFFFFFFFF) for n in row['node_events']))
        self.assertEqual((len(row['records']['frontend']), len(records), len(row['node_events'])), (2259, 1764, 301))

    def test_03_source_controls_explain_changes_but_remain_nonmatching(self):
        same = self.rows['step-register-short']
        self.assertEqual(trace.signature(self.work('record') / 'baseline.o'),
            trace.signature(self.work('step-register-short') / 'baseline.o'))
        self.assertEqual(same['baseline']['raw_sha256'], trace.source.RAW_SHA)
        promoted = self.rows['step-promoted-short']
        homes = [(i, r['dtype'], r['offset']) for i, r in enumerate(promoted['records']['optimizer'])
            if r['name'] == 'str' and r['storage'] == 'M']
        self.assertEqual(homes[:4], [(78, 'J', -132), (98, 'R', -120), (214, 'J', -128), (219, 'J', -148)])
        self.assertEqual(promoted['baseline']['frame'] - 120, 0x58)
        y_first = self.rows['record-y-first']
        self.assertEqual(y_first['baseline']['words'], 622)
        self.assertEqual([r['offset'] for r in y_first['records']['frontend'] if r['name'] == 'str' and
            r['storage'] == 'M' and r['dtype'] == 'R'][:4], [-8, -12, -20, -16])
        self.assertFalse(any(r['name'] == 'str' and r['storage'] == 'M' and r['dtype'] == 'R'
            for r in y_first['records']['optimizer'][:200]))

    def test_04_corrupt_capture_completion_tables_nodes_and_artifacts_fail_closed(self):
        work = self.work()
        read_text, read_bytes = Path.read_text, Path.read_bytes
        receipt = json.loads(read_text(work / 'receipt.json'))
        log = read_text(work / 'debugger.txt')
        controls = {
            'driver': log.replace('TRACE_EXIT inferior=1 code=0', 'TRACE_EXIT inferior=1 code=1'),
            'producer': log.replace('"stage": "cfe", "inferior": 2, "code": 0', '"stage": "cfe", "inferior": 2, "code": 1'),
            'input': log.replace('FRAME_INPUT ', 'MISSING_INPUT '),
            'tables': log.replace('RECT_TABLES ', 'MISSING_TABLES '),
            'nodes': log.replace('UGEN_NODE ', 'MISSING_NODE '),
            'install': log.replace('MIRROR_NODE_INSTALLED', 'MISSING_INSTALL'),
            'cleanup': log.replace('MIRROR_NODE_REMOVED', 'MISSING_CLEANUP'),
        }
        for name, changed in controls.items():
            self.assertNotEqual(changed, log, name)
            bad = dict(receipt, capture_sha256=dict(receipt['capture_sha256'],
                **{'debugger.txt': hashlib.sha256(changed.encode()).hexdigest()}))
            def mocked(path, *args, **kwargs):
                if path == work / 'debugger.txt':
                    return changed
                if path == work / 'receipt.json':
                    return json.dumps(bad)
                return read_text(path, *args, **kwargs)
            with self.subTest(control=name), patch.object(Path, 'read_text', mocked), self.assertRaises(ValueError):
                trace.validate(work, self.root)
        for name in ('frontend.ucode', 'optimizer.ucode', 'ucode-table.json', 'ucode-types.json',
                'baseline.c', 'baseline-processed.c', 'trace.gdb', 'trace.o'):
            target = work / name
            def changed(path):
                data = read_bytes(path)
                return data + b'corruption' if path == target else data
            with self.subTest(artifact=name), patch.object(Path, 'read_bytes', changed), self.assertRaises(ValueError):
                trace.validate(work, self.root)

    def test_05_no_restart_no_install_or_production_change(self):
        with patch.object(trace.subprocess, 'run', side_effect=AssertionError('Unexpected compiler restart')):
            with self.assertRaises(ValueError):
                trace.trace(self.root, 'record', self.run_id)
            for label, run in (('not-a-candidate', None), ('record', '../escape')):
                with self.assertRaises(ValueError):
                    trace.trace(self.root, label, run)
        trace.source.freeze(self.root, self.out)
        before = (self.out / 'before-color_owner').read_text()
        lo, hi = trace.source.build.function_span(before, trace.source.FUNCTION)
        self.assertEqual(before[lo:hi], 's32 func_1517FB9C() {\n    return 0;\n}')


if __name__ == '__main__':
    unittest.main()
