"""Qualify frontend provenance and reject current ordinary-flag carrier shapes."""
import copy
import itertools
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from tools.experiments import game_text_measurer_frontend_trace as front
from tools.tests import test_game_text_measurer_logic_candidates as semantics
from tools.tests import test_game_text_measurer_recovery as recovery


class GameTextMeasurerFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-text-measurer-frontend-test'
        cls.out.mkdir(exist_ok=True)
        cls.bodies = dict(front.logic.carrier_candidates())
        cls.compiled = {name: front.logic.screen.compile_candidate(cls.root, cls.out, name, body)
                        for name, body in cls.bodies.items()}
        cls.record = front.capture_frontend(cls.root, cls.out, 'valid', cls.bodies['carrier-simple-named'])
        cls.valid = cls.out / 'valid'
        cls.log = (cls.valid / 'debugger.txt').read_text()
        cls.table = json.loads((cls.valid / 'ucode-table.json').read_text())
        cls.types = json.loads((cls.valid / 'ucode-types.json').read_text())
        cls.payload = (cls.valid / 'frontend.ucode').read_bytes()
        recovery.GameTextMeasurerRecoveryTests.setUpClass()
        cls.oracle = recovery.GameTextMeasurerRecoveryTests('test_05_production_and_protected_data_unchanged')
        cls.semantic = semantics.GameTextMeasurerLogicTests('test_02_all_nine_distinct_bodies_preserve_complete_public_semantics')
        cls.semantic.oracle = cls.oracle

    def disposable(self, name):
        work = self.out / name
        work.mkdir(exist_ok=True)
        for filename in ('baseline.o', 'trace.o', 'frontend.ucode', 'optimizer.ucode', 'ucode-table.json', 'ucode-types.json'):
            shutil.copy2(self.valid / filename, work / filename)
        return work

    def rejected(self, work, log=None, complete=None, message='(?i)frontend'):
        with self.assertRaisesRegex(ValueError, message):
            front.validate_capture(self.root, work, self.log if log is None else log,
                                   self.record['complete'] if complete is None else complete)
        self.assertFalse(json.loads((work / 'frontend.json').read_text())['code_unchanged'])

    def test_01_complete_frontend_capture_distinguishes_anonymous_homes_from_register8(self):
        record = self.record
        self.assertTrue(record['code_unchanged'])
        self.assertFalse(record['installable'])
        self.assertEqual((record['frontend']['bytes'], record['record_count']), (18632, 839))
        self.assertEqual((record['optimizer']['bytes'], record['optimizer_record_count']), (18048, 799))
        self.assertEqual(record['frontend']['producer_exits'], [0])
        records = record['records']
        self.assertEqual((records[0]['name'], records[-1]['name']), ('bgn', 'stp'))
        vregs = [entry for entry in records if entry['name'] == 'vreg']
        self.assertEqual([(entry['storage'], entry['level'], entry['length'], entry['offset']) for entry in vregs],
                         [('M', 1, 4, offset) for offset in (-52, -56, -60, -64)])
        registers = [entry for entry in records if entry['name'] in ('lod', 'str') and entry['storage'] == 'R']
        self.assertEqual([(entry['name'], entry['offset']) for entry in registers], [('lod', 2)])
        call = next(entry for entry in records if entry['name'] == 'cup' and entry['dtype'] == 'P')
        self.assertTrue(any(entry['name'] == 'str' and entry['storage'] == 'M' and entry['offset'] == -56
                            and entry['byte_offset'] < call['byte_offset'] for entry in records))
        self.assertTrue(any(entry['name'] == 'lod' and entry['storage'] == 'M' and entry['offset'] == -56
                            and entry['byte_offset'] > call['byte_offset'] for entry in records))
        optimized = record['optimizer_records']
        self.assertTrue(any(entry['name'] == 'lod' and entry['storage'] == 'R' and entry['offset'] == 8 for entry in optimized))
        self.assertTrue(any(entry['name'] == 'rstr' and entry['storage'] == 'M' and entry['level'] == 8
                            and entry['offset'] == -56 for entry in optimized))
        self.assertTrue(any(entry['name'] == 'rlod' and entry['storage'] == 'M' and entry['level'] == 8
                            and entry['offset'] == -56 for entry in optimized))
        self.assertTrue(any(entry['name'] == 'str' and entry['storage'] == 'R' and entry['offset'] == 8 for entry in optimized))
        words = self.compiled['carrier-simple-named'][1]
        self.assertIn(0xAFA80058, words)
        self.assertIn(0x8FA80058, words)

    def test_02_seven_source_forms_four_bodies_and_original_saved_roles_are_not_a_match(self):
        expected = {'carrier-simple-named': (216, 0x90, 179), 'carrier-simple-direct': (218, 0x88, 193),
                    'carrier-retail-gates-named': (231, 0x98, 195), 'carrier-retail-gates-direct': (233, 0x90, 201)}
        self.assertEqual(len(self.compiled), 7)
        for name, (meta, words) in self.compiled.items():
            reference = name if name in expected else 'carrier-simple-named'
            self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), expected[reference])
            self.assertEqual(meta['pool_bytes'], 0)
            self.assertNotEqual(words, self.oracle.retail)
            if name not in expected:
                self.assertEqual(words, self.compiled[reference][1])
        simple = self.compiled['carrier-simple-named'][1]
        self.assertEqual(simple[1:13], self.oracle.retail[1:13])
        self.assertNotEqual(simple[0], self.oracle.retail[0])
        self.assertNotIn(0xAFA80068, simple)
        self.assertNotIn(0x8FA80068, simple)

    def test_03_four_complete_bodies_preserve_bounded_public_semantics(self):
        counts = {}
        for name in ('carrier-simple-named', 'carrier-simple-direct',
                     'carrier-retail-gates-named', 'carrier-retail-gates-direct'):
            words = self.compiled[name][1]
            self.assertFalse(any(word >> 26 == 2 for word in words))
            cases = 0
            for byte, phase in itertools.product(range(256), (0, 8)):
                self.semantic.compare(words, bytes((byte, 0, 0)) if byte != 0xBC else bytes((byte, 7, 65, 0)), phase=phase)
                cases += 1
            for text, alias, phase, scales in itertools.product((b'\0', b'A\0', b'A\nB\0', b' AB\0',
                    bytes((0xBC, 0, 65, 0)), bytes((0xA8, 0xAA, 0xBA, 0xAE, 65, 0))),
                    range(10), (0, 8), ((1.0, 1.0), (0.75, 1.25))):
                self.semantic.compare(words, text, alias, phase, scales)
                cases += 1
            self.semantic.compare(words, b'A\0', null=True)
            self.semantic.compare(words, bytes((0xAA, 0)), factor=1.0 / 18.0)
            memory, args = self.oracle.font_pointer_fixture()
            model = semantics.LogicalMeasurerOracle(words, memory, args, self.oracle.connected).run()
            expected = recovery.Reference(memory, args).run()
            self.assertEqual(recovery.public(model.memory), recovery.public(expected.memory))
            self.assertEqual(model.calls, expected.calls)
            counts[name] = cases + 3
            self.assertEqual(counts[name], 755)
        (self.out / 'carrier-public.json').write_text(json.dumps(dict(counts=counts, comparisons=sum(counts.values()),
            actual_helpers=True, private_fault_native_owner_qualification=False, installable=False), indent=2) + '\n')

    def test_04_effective_producer_consumer_probe_payload_and_table_controls(self):
        self.rejected(self.disposable('missing'), log='')
        self.rejected(self.disposable('failed-completion'), complete=dict(self.record['complete'], code_unchanged=False))
        capture = self.record['frontend']
        original = front.PREFIX + json.dumps(capture)
        for name, changed in (('producer-failed', dict(capture, producer_exits=[11])),
                              ('bad-size', dict(capture, bytes=capture['bytes'] + 8)),
                              ('bad-hash', dict(capture, sha256='0' * 64))):
            self.rejected(self.disposable(name), log=self.log.replace(original, front.PREFIX + json.dumps(changed)))
        self.rejected(self.disposable('consumer-failed'), log=self.log.replace(
            'TRACE_EXIT inferior=%d code=0' % capture['inferior'], 'TRACE_EXIT inferior=%d code=11' % capture['inferior']))
        optimizer = self.record['optimizer']
        optimizer_line = front.OPTIMIZER_PREFIX + json.dumps(optimizer)
        self.rejected(self.disposable('optimizer-failed'), log=self.log.replace(optimizer_line,
            front.OPTIMIZER_PREFIX + json.dumps(dict(optimizer, producer_exits=[11]))), message='(?i)optimizer')
        self.rejected(self.disposable('missing-optimizer'), log=self.log.replace(optimizer_line, ''), message='(?i)optimizer')
        self.rejected(self.disposable('late-optimizer'), log=self.log.replace(optimizer_line, '') + '\n' + optimizer_line,
                      message='outside producer/consumer lifetime')
        for filename in ('frontend.ucode', 'optimizer.ucode', 'ucode-table.json', 'ucode-types.json'):
            work = self.disposable('changed-' + filename)
            path = work / filename
            data = path.read_bytes()
            path.write_bytes(bytes((data[0] ^ 1,)) + data[1:])
            self.rejected(work, message='(mismatch|tables changed)')
        without_table = '\n'.join(line for line in self.log.splitlines() if not line.startswith(front.TABLE_PREFIX))
        self.rejected(self.disposable('no-table-probe'), log=without_table, message='descriptor probe')
        with patch.object(front, 'compiler_fingerprints', return_value={}):
            self.rejected(self.disposable('changed-compiler'), message='fingerprint changed')

    def test_05_wire_decoder_controls_and_owned_recipe_boundaries(self):
        self.assertEqual(front.decode_ucode(self.payload, self.table, self.types), self.record['records'])
        for data in (b'', self.payload[:-1], self.payload[:-8], bytes((255,)) + self.payload[1:]):
            with self.assertRaises(ValueError):
                front.decode_ucode(data, self.table, self.types)
        for key, value in (('opcode', 255), ('descriptor', []), ('name', 'too-long')):
            table = copy.deepcopy(self.table)
            table[0][key] = value
            with self.assertRaisesRegex(ValueError, 'descriptor'):
                front.decode_ucode(self.payload, table, self.types)
        with patch.object(front, 'compiler_fingerprints', return_value={}), \
                patch.object(front.trace, 'trace_nodes') as compile:
            with self.assertRaisesRegex(ValueError, 'fingerprint mismatch'):
                front.capture_frontend(self.root, self.out, 'wrong', self.bodies['carrier-simple-named'])
            compile.assert_not_called()
        for out, name in ((self.root / 'DOCS', 'outside'), (self.out, '../outside')):
            with self.assertRaisesRegex(ValueError, 'inside conker/build'):
                front.capture_frontend(self.root, out, name, self.bodies['carrier-simple-named'])
        script = front.debugger_script(self.root, self.valid)
        for forbidden in ('\nattach ', 'target remote', '\nshell ', 'write_memory', '\ncall '):
            self.assertNotIn(forbidden, script)
        self.assertIn('/proc/%d/cmdline', script)

    def test_06_frozen_production_and_effective_corruption_controls(self):
        self.oracle.test_05_production_and_protected_data_unchanged()
        self.oracle.test_06_effective_immutable_production_controls()


if __name__ == '__main__':
    unittest.main()
