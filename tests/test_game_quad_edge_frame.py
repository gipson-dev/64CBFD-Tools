"""Qualify the smaller named-local frame without crediting an unmatched body."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_quad_edge_frame as fitting
from tools.experiments import game_quad_edge_emitter as source
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_quad_edge_emitter as previous


def controls(body):
    return {
        'wrong-count-pair': body.replace('edge == 0 || edge == 2', 'edge == 0 || edge == 1'),
        'wrong-stride': body.replace('nextIndex * 12', 'nextIndex * 4'),
        'integer-table': body.replace('ranges.values[kind] * scale', '*(s32 *)&ranges.values[kind] * scale'),
        'integer-vertices': body.replace('next[0] - current[0]', 'next[0] - *(s32 *)current'),
        'signed-modulo': body.replace('(u32)func_150ADA20() % (u32)(s32)(836.0f * scale)',
            'func_150ADA20() % (s32)(836.0f * scale)'),
        'missing-endpoint': body.replace('(f32)((&count)[0] - 1)', '(f32)(&count)[0]'),
        'wide-color': body.replace('color[0], color[1], color[2]', '*(u16 *)color, *(u16 *)(color + 1), *(u16 *)(color + 2)'),
        'cached-vertices': body.replace('x = (next[0] - current[0]) * ((f32)index * inverse) + current[0];',
            'x = (next[0] - vertices[0]) * ((f32)index * inverse) + vertices[0];'),
        'wrong-lifetime': body.replace('143.0f * scale', '144.0f * scale'),
    }


def count_home(words):
    call = 0x0C000000 | (source.FACTORY >> 2 & 0x3FFFFFF)
    index = words.index(call) + 2
    for word in words[index:index + 5]:
        if word >> 26 in (5, 21):
            break
        if word >> 26 == 35 and word >> 21 & 31 == 29:
            return word & 65535
    return None


class QuadEdgeFrameTests(unittest.TestCase):
    test_02_complete_public_packets = previous.QuadEdgeEmitterTests.test_02_complete_public_packets_four_edges_and_live_inputs
    test_03_both_traps_and_empty_edges = previous.QuadEdgeEmitterTests.test_03_both_zero_divisor_traps_and_empty_path
    test_05_all_62_immutable_inputs = previous.QuadEdgeEmitterTests.test_05_all_inputs_and_capture_corruptions_fail_closed
    test_07_fault_prefix_difference_boundary = previous.QuadEdgeEmitterTests.test_07_original_fault_prefixes_and_candidate_difference_boundary
    test_08_original_caller_ABI = previous.QuadEdgeEmitterTests.test_08_original_caller_windows_and_wrapper_ABI
    test_09_current_factory_allocator = previous.QuadEdgeEmitterTests.test_09_actual_current_factory_allocator_and_record_fields
    test_10_all_801_archive_fingerprints = previous.QuadEdgeEmitterTests.test_10_all_original_801_archive_fingerprints
    test_12_independent_links = previous.QuadEdgeEmitterTests.test_12_independent_original_and_C_rebases

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / fitting.BUILD
        cls.body = fitting.candidates()['named-homes']
        cls.obj, cls.words, cls.row = source.measure(cls.root, cls.out, 'qualified-named-homes', cls.body)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>266I', cls.rom, source.ROM))
        cls.table = cls.rom[0x2316B4:0x2316B4 + 33]

    def receipt(self, name, **values):
        (self.out / ('qualification-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_frame_named_homes_neighbors_padding_and_strict_rejection(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences'],
            self.row['diagnostics'], self.row['pool_bytes']), (266, 400, 137, '', 0))
        # These exact prologue words address the three initializer destinations.
        for at, word in ((0x58, 0x27A20120), (0x68, 0x27AE012C), (0x9C, 0x27AD0114),
                (0xF4, 0xAFAC0150)):
            self.assertEqual(self.words[at // 4], word)
            self.assertEqual(self.words[at // 4], self.truth[at // 4])
        self.assertEqual(count_home(self.words), 0x138)
        with patch.object(source, 'measure', return_value=(self.obj, self.words, self.row)):
            with self.assertRaisesRegex(ValueError, 'not a direct match'):
                source.qualify(self.root, self.out)
        original, diagnostics = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-preset_owner').read_text(), 'qualification-before-owner')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(original), parse_object(self.obj)
        neighbors = 0
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda o, f: [(at - f['value'], entries) for at, entries in o[2].items()
                if f['value'] <= at < f['value'] + f['size']]
            self.assertEqual(relative(old, f), relative(new, g), name)
            neighbors += 1
        self.assertEqual(neighbors, 29)
        self.assertEqual(normalized_pools(original), normalized_pools(self.obj))
        path = self.out / 'qualification-unmatched-padded.s'
        path.write_text(emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'],
            filename=source.OWNER, word_patches_path=self.out / 'before-guards'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        data, functions = source.build.link_owner(self.root, self.out, path.with_suffix('.o'), source.OWNER)
        f = functions[source.FUNCTION]
        self.assertEqual(f['size'], 1064)
        self.assertEqual(list(struct.unpack_from('>266I', data, f['value'])), self.words)
        for order in (fitting.HOME_ORDER[:-1], fitting.HOME_ORDER + ('edge',), ('unknown',) + fitting.HOME_ORDER[1:]):
            with self.assertRaisesRegex(ValueError, 'each actual local'):
                fitting.reorder(self.body, order)
        self.receipt('shape', **{key: value for key, value in self.row.items() if key != 'different_words'},
            neighbors_unchanged=neighbors, table_homes=[0x12C, 0x120, 0x114], count_home=0x138,
            limit_home=0x150, actual_padder_preserves_all_words=True, installation_rejected=True,
            no_target_guards_or_profile_changes=True)

    def test_04_effective_compiled_controls(self):
        negatives = controls(self.body)
        self.assertTrue(all(body != self.body for body in negatives.values()))
        with patch.object(source, 'SELECTED', self.body), patch.object(previous, 'controls', return_value=negatives):
            previous.QuadEdgeEmitterTests.test_04_effective_compiled_semantic_controls(self)

    def test_06_native32_O2_O0_with_effective_controls(self):
        with patch.object(source, 'SELECTED', self.body), patch.object(previous, 'controls', return_value=controls(self.body)):
            previous.QuadEdgeEmitterTests.test_06_native32_valid_conversion_domain_O2_O0_and_controls(self)

    def test_11_exact_count_home_and_reciprocal_snapshot_controls(self):
        class CountWriter(previous.EdgeOracle):
            def hook(model, target):
                super().hook(target)
                if target == source.FACTORY and model.factory_count == 1:
                    model.put(model.r[29] + model.count_home, 3, 4)

        memory, args = previous.fixture(self.table, counts=(2, 2))
        expected = previous.reference(memory, args, previous.SAMPLES[2])[2]
        extra = list(expected[0])
        for axis in range(3):
            start = previous.floating(previous.read(memory, previous.VERTICES + axis * 4))
            delta = previous.rounded(previous.floating(previous.read(memory, previous.VERTICES + 12 + axis * 4)) - start)
            extra[axis] = previous.short(previous.trunc(previous.rounded(previous.rounded(delta * 2.0) + start))) & 0xFFFFFFFF
        expected = expected[:2] + [tuple(extra)] + expected[2:]
        for words in (self.truth, self.words):
            self.assertEqual(count_home(words), 0x138)
            model = CountWriter(words, memory, args, previous.SAMPLES[2])
            model.count_home = 0x138
            model.run()
            self.assertEqual(model.packets, expected)
        controls_seen = {}
        for name, body in (('cached-count', self.body.replace('(&count)[0]', 'count')),
                ('recomputed-reciprocal', fitting.candidates()['inline-fraction'])):
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            model = CountWriter(words, memory, args, previous.SAMPLES[2])
            model.count_home = count_home(words) or 0x138
            model.run()
            self.assertNotEqual(model.packets, expected, name)
            controls_seen[name] = dict(packets=len(model.packets), count_home=count_home(words))
        self.receipt('count-home', original_and_candidate_home=0x138, packets=9,
            reciprocal_snapshot_retained=True, effective_controls=controls_seen,
            same_count_address_does_not_establish_whole_private_state_parity=True)

    def test_13_actual_compiler_observation_and_fail_closed_controls(self):
        for name, body, frontend, local, total, difference in (
                ('selected', source.SELECTED, 156, 192, 416, 149),
                ('named-homes', self.body, 140, 176, 400, 137)):
            record = fitting.trace(self.root, self.out, name, body)
            defs = {stage: [row['length'] for row in rows if row['name'] == 'def' and row['storage'] == 'M']
                for stage, rows in record['records'].items()}
            self.assertEqual(defs, dict(frontend=[frontend], optimizer=[local]))
            self.assertEqual((record['baseline']['words'], record['baseline']['frame'],
                record['baseline']['differences']), (266, total, difference))
            self.assertTrue(record['code_unchanged'] and record['standalone_equals_complete_owner'])
            self.assertFalse(record['installable'])
            self.assertEqual([e['frame'] for e in record['events']], [0, 96, 224, total])
            self.assertEqual((record['events'][-1]['locals'], record['events'][-1]['saved'],
                record['events'][-1]['outgoing'], record['events'][-1]['temporary']), (local, 96, 128, 0))
            self.assertTrue(all(not e['pool'] for e in record['events']))
            self.assertEqual(record['different_object_sections'], ['.mdebug'])
            work = self.out / name
            log = (work / 'debugger.txt').read_text()
            for prefix in ('FRAME_TRACE ', 'FRAME_INPUT ', 'TRACE_EXIT '):
                bad = '\n'.join(line for line in log.splitlines() if not line.startswith(prefix))
                with self.assertRaises(ValueError):
                    fitting.frame.observer.validate_observations(work, bad)
            rb = Path.read_bytes
            for stage in ('frontend', 'optimizer'):
                target = work / (stage + '.ucode')
                with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\0' if p == target else rb(p)):
                    with self.assertRaisesRegex(ValueError, 'integrity'):
                        fitting.frame.observer.validate_observations(work, log)
        with patch.object(fitting.frame.observer, 'fingerprints', return_value={}):
            with self.assertRaisesRegex(ValueError, 'fingerprints'):
                fitting.trace(self.root, self.out, 'rejected-compiler', self.body)
        for out, label in ((self.root / 'DOCS', 'x'), (self.out, '../escape'), (self.out, '.'), (self.out, '')):
            with self.assertRaisesRegex(ValueError, 'Owned frame output'):
                fitting.trace(self.root, out, label, self.body)
        for key, path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), source.BASELINE[key], key)
        self.receipt('compiler-frame', frontend=[156, 140], uopt=[192, 176], frames=[416, 400],
            saved=96, outgoing=128, temporary=0, all_producer_consumer_driver_exits_zero=True,
            text_functions_relocations_pools_unchanged_by_tracing=True,
            capture_and_compiler_controls_fail_closed=True)


if __name__ == '__main__':
    unittest.main()
