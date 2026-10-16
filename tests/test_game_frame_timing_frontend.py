"""Bind real frontend promotions to optimized roles and unchanged emission."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_frame_timing_frontend as source
from tools.pad_generated_object import parse_object


class TimingFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/source.BUILD
        cls.records = {variant:source.capture_owner(cls.root, variant)
            for variant in ('predecessor','unsigned-zero')}

    def receipt(self, name, **row):
        (self.out/(name+'.json')).write_text(json.dumps(row, indent=2)+'\n')

    def summary(self, record, variant='predecessor', content=None):
        work = self.out/variant
        return source.phase_summary(record, content if content is not None else (work/'baseline.c').read_text(),
            work/'baseline.o', variant)

    def test_01_completed_producers_and_normal_emission_with_exact_source_bindings(self):
        results = {}
        for variant, record in self.records.items():
            summary = self.summary(record, variant)
            self.assertEqual(summary, record['phase_summary'])
            self.assertTrue(record['code_unchanged'])
            self.assertEqual(record['frontend']['producer_exits'], [0])
            self.assertEqual(record['optimizer']['producer_exits'], [0])
            self.assertEqual((record['record_count'],record['optimizer_record_count'],record['complete']['event_count']),
                (6463 if variant=='predecessor' else 6464,6950,626))
            self.assertEqual((summary['frontend_byte_home'],summary['frontend_total_home']), (-2,-8))
            self.assertTrue(summary['allocation_precedes_UGEN'])
            self.assertTrue(summary['ugen_events_not_uniquely_attributed_to_target'])
            self.assertFalse(summary['installable'])
            digest = (source.source.previous.RAW_SHA256 if variant=='predecessor' else
                '495cf7b8fcd35a9148c69f8dc39cf5c5da55c540dbe1a85493b43c380a10263c')
            self.assertEqual(record['complete']['baseline']['raw_sha256'], digest)
            results[variant] = summary
        self.assertEqual(results['predecessor']['optimized_extra_unsigned_gate_registers'], [])
        self.assertEqual(results['unsigned-zero']['optimized_extra_unsigned_gate_registers'], [5])
        self.assertEqual(results['predecessor']['optimized_residual_register'], 9)
        self.assertEqual(results['unsigned-zero']['optimized_residual_register'], 8)
        self.receipt('qualified-phase-bindings', captures=results, completed_owned_driver_compiles=2,
            complete_text_functions_relocations_and_pools_unchanged=True, not_hardware_or_original_source_recovery=True)

    def test_02_wire_tables_and_lifecycle_markers_reject_corruption(self):
        checks = 0
        read = Path.read_bytes
        for variant, record in self.records.items():
            work = self.out/variant
            log = (work/'debugger.txt').read_text()
            for filename in ('frontend.ucode','optimizer.ucode','ucode-table.json','ucode-types.json'):
                target = work/filename
                with patch.object(Path, 'read_bytes', lambda p:read(p)+b'\n' if p==target else read(p)):
                    with self.assertRaises(ValueError):
                        source.capture.validate_capture(self.root, work, log, record['complete'])
                checks += 1
            for marker in (source.capture.PREFIX, source.capture.OPTIMIZER_PREFIX, source.capture.TABLE_PREFIX,
                    source.capture.trace.INSTALLED, source.capture.trace.CHILD_EXIT, source.capture.trace.REMOVED,
                    source.capture.trace.qualified.EXIT_MARKER):
                self.assertIn(marker, log)
                with self.assertRaises(ValueError):
                    source.capture.validate_capture(self.root, work, log.replace(marker,'CORRUPTED_MARKER'), record['complete'])
                checks += 1
            validated = source.capture.validate_capture(self.root, work, log, record['complete'])
            self.assertTrue(validated['code_unchanged'])
            (work/'trace.json').write_text(json.dumps(record['complete'], indent=2)+'\n')
            (work/'frontend.json').write_text(json.dumps(record, indent=2)+'\n')
        self.assertEqual(checks, 22)
        self.receipt('capture-corruption-controls', rejected=checks, mutated_wire_or_table_files=8,
            mutated_lifecycle_markers=14, producer_consumer_and_cleanup_gates=True)

    def test_03_phase_bindings_and_procedure_boundaries_fail_closed(self):
        record = self.records['predecessor']
        procedure = record['phase_summary']['frontend_procedure']
        front = source.procedure_records(record['records'], procedure)
        optimized = source.procedure_records(record['optimizer_records'], procedure)
        targets = [
            ('records', next(r for r in front if r['name']=='str' and r['storage']=='M' and r['offset']==-2)),
            ('records', next(r for r in front if r['name']=='str' and r['storage']=='M' and r['offset']==-8)),
            ('optimizer_records', next(r for r in optimized if r['name']=='rlda' and r['block']==2678)),
        ]
        for phase, target in targets:
            for removal in (False,True):
                bad = copy.deepcopy(record)
                index = next(i for i,r in enumerate(bad[phase]) if r['byte_offset']==target['byte_offset'])
                if removal:
                    del bad[phase][index]
                elif target['name']=='rlda':
                    bad[phase][index]['words'][2] ^= 1
                else:
                    bad[phase][index]['offset'] -= 4
                with self.assertRaises(ValueError):
                    self.summary(bad)
        for phase in ('records','optimizer_records'):
            rows = source.procedure_records(record[phase], procedure)
            for changed in (rows[:-1], [rows[0],*rows]):
                with self.assertRaises(ValueError):
                    source.procedure_records(changed, procedure)
        bad = dict(record, code_unchanged=False)
        with self.assertRaises(ValueError):
            self.summary(bad)
        content = (self.out/'predecessor'/'baseline.c').read_text()
        with self.assertRaises(ValueError):
            self.summary(record, content=content.replace('    divisor = D_800BEA0C;',''))
        with patch.object(source.capture,'capture_frontend') as invocation:
            with self.assertRaises(ValueError):
                source.capture_owner(self.root, 'unknown')
            invocation.assert_not_called()
        self.receipt('role-corruption-controls', rejected_role_changes=6, procedure_boundary_controls=4,
            unqualified_capture_and_missing_source_marker_rejected=True, invalid_variant_does_not_launch=True)

    def test_04_nineteen_complete_owner_controls_preserve_neighbors_not_instruction_match(self):
        rows = {}
        old = parse_object(self.out/'predecessor'/'baseline.o')
        candidates = (*source.comparison_forms(), *source.step_word_forms(), *source.switch_forms(),
            *source.global_divisor_forms(), *source.home_forms(), *source.signed_gate_forms())
        self.assertEqual(len(candidates), 19)
        for name, body in candidates:
            obj, _, row = source.source.measure(self.root, self.out, name, body)
            new = parse_object(obj)
            self.assertEqual(set(new[1]), set(old[1]))
            for function, f in old[1].items():
                if function==source.source.FUNCTION:
                    continue
                g = new[1][function]
                self.assertEqual(old[0][f['value']:f['value']+f['size']], new[0][g['value']:g['value']+g['size']], function)
                relative = lambda p,s:{a-s['value']:r for a,r in p[2].items() if s['value']<=a<s['value']+s['size']}
                self.assertEqual(relative(old,f), relative(new,g), function)
            self.assertEqual(row['frame'], 24)
            self.assertFalse(row['pools'])
            self.assertGreaterEqual(row['differences'], 141)
            rows[name] = {key:row[key] for key in ('words','differences','raw_sha256')}
        for name,_ in source.home_forms():
            self.assertEqual(rows[name]['raw_sha256'], source.source.previous.RAW_SHA256)
        self.assertEqual(rows['u16-gate']['raw_sha256'], source.source.previous.RAW_SHA256)
        self.assertEqual((rows['unsigned-zero']['words'],rows['unsigned-zero']['differences']), (190,180))
        self.assertEqual((rows['s32-gate']['words'],rows['s32-gate']['differences']), (189,170))
        self.receipt('source-controls', screens=rows, unchanged_neighbors_each=15,
            adopted=False, functional_qualification_of_all_screens_not_claimed=True)

    def test_05_all109_live_inputs_and_production_guards_unchanged(self):
        wanted = source.source.BASELINE
        self.assertEqual(len(wanted), 109)
        for key,path in source.source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(), wanted[key], key)
        self.receipt('unchanged-production', hashes=wanted, inputs=109, production_source_image_and_guards_unchanged=True,
            no_normal_guest_build_needed=True)


if __name__ == '__main__':
    unittest.main()
