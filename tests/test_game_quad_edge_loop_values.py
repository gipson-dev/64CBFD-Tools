"""Current emitter loop obligations, effective negatives and retained boundaries."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_quad_edge_loop as source
from tools.experiments import game_quad_edge_loop_values as proof
from tools.pad_generated_object import parse_object
from tools.tests import test_game_quad_edge_emitter as edge
from tools.tests.game_owner_pool import normalized_pools


class QuadEdgeLoopValuesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.words, cls.row = source.measure(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>266I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / ('qualification-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_current_baseline_and_unchanged_owner_neighbors(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences'],
            self.row['diagnostics'], self.row['pool_bytes']), (266, 400, 137, '', 0))
        build = source.previous.build
        old_obj, diagnostics = build.compile_owner(self.root, self.out,
            (self.out / 'before-preset_owner').read_text(), 'unchanged-owner')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(old_obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'])
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']])
            rel = lambda obj, f: {at - f['value']: rows for at, rows in obj[2].items()
                if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(rel(old, f), rel(new, g))
        self.assertEqual(normalized_pools(old_obj), normalized_pools(self.obj))
        self.assertIn('s32 func_151700D8() {\n    return 0;\n}',
            (self.root / source.PATHS['preset_owner']).read_text())
        with patch.object(source.previous, 'PATHS', source.PATHS), patch.object(source.previous, 'BASELINE', source.BASELINE):
            with self.assertRaisesRegex(ValueError, 'not a direct match'):
                source.previous.qualify(self.root, self.out)
        self.receipt('owner', raw_words=266, frame=400, differences=137,
            neighbors=len(old[1]) - 1, normalized_pools_equal=True, production_placeholder_retained=True,
            strict_installation_rejected=True)

    def test_02_symbolic_induction_for_all_three_kinds(self):
        result = proof.prove(self.words, self.truth)
        self.assertEqual((result['outer_cases'], result['induction_steps']), (24, 24))
        self.assertTrue(result['symbolic_index_and_count'])
        self.assertTrue(result['finite_non_nan_addition_commutation_assumed'])
        self.assertTrue(result['not_installation_qualification'])
        self.receipt('loop-obligations', **result)

    def test_03_effective_instruction_dependency_negatives(self):
        tests = {
            'increment-by-two': (0x26940001, 0x26940002),
            'wrong-width-divisor': (0x0057001B, 0x0056001B),
            'wrong-preset-byte': (0x93AF019F, 0x93AF019C),
            'wrong-scale-home': (0xC7BC01A0, 0xC7BC0194),
            'wrong-context-home': (0x8FAC01B4, 0x8FAC01A4),
            'wrong-flags-byte': (0x93A901B3, 0x93A901B0),
            'wrong-extent-shift': (0x00037C03, 0x00037BC3),
            'wrong-rng-binding': (0x0D42B688, 0x0D42B689),
        }
        for name, (old, new) in tests.items():
            with self.subTest(name=name):
                words = list(self.words)
                at = words.index(old)
                words[at] = new
                with self.assertRaises(ValueError):
                    proof.prove(words, self.truth)
        words = list(self.words)
        at = proof.layout(words)['inner_branch']
        words[at] = words[at] & ~(31 << 16) | 20 << 16
        with self.assertRaises(ValueError):
            proof.prove(words, self.truth)
        self.receipt('negatives', effective_instruction_controls=[*tests, 'self-compare-loop-exit'])

    def test_04_independent_save_schedule_is_accepted(self):
        words = list(self.words)
        self.assertEqual(words[12:14], [0xAFB000B8, 0xF7BE00B0])
        words[12:14] = reversed(words[12:14])
        self.assertNotEqual(words, self.words)
        result = proof.prove(words, self.truth)
        self.assertEqual(result['induction_steps'], 24)
        self.receipt('legal-schedule', independent_save_permutation_accepted=True,
            not_literal_fault_or_instruction_identity=True)

    def test_05_guest_values_with_external_provider_mutations(self):
        pairs, private_different = 0, 0
        table = self.rom[0x2316B4:0x2316B4 + 33]
        for kind, counts, scale, mode, phase, randoms in itertools.product(range(3),
                ((-1, 0), (2, 3), (4, 2), (2, -1)), (-0.5, 1.25), (0, 1, 2), (0, 8), edge.SAMPLES[:2]):
            memory, args = edge.fixture(table, kind, counts, scale, phase, pattern=kind)
            expected, calls, packets, trap = edge.reference(memory, args, randoms, phase, mode)
            self.assertFalse(trap)
            models = [edge.EdgeOracle(w, memory, args, randoms, phase, mode).run() for w in (self.truth, self.words)]
            for model in models:
                self.assertEqual(model.calls, calls)
                self.assertEqual(model.packets, packets)
                self.assertEqual(edge.public(model.memory), edge.public(expected))
            private_different += edge.state(models[0]) != edge.state(models[1])
            pairs += 1
        self.assertEqual(pairs, 288)
        self.assertEqual(private_different, pairs)
        self.receipt('guest-values', pairs=pairs, private_states_different=private_different,
            incoming_home_poison_excluded_from_C_domain=True, native_or_hardware_not_exercised=True)

    def test_06_current_inputs_and_each_frozen_corruption(self):
        self.assertEqual(len(source.PATHS), 63)
        for key, path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), source.BASELINE[key], key)
        read_bytes = Path.read_bytes
        for key in source.PATHS:
            target = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: read_bytes(p) + b'\0' if p == target else read_bytes(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        self.receipt('inputs', unchanged_current_and_frozen=63, every_frozen_flip_rejected=True)

    def test_07_loop_home_screen_is_not_installation_credit(self):
        expected = {'word-preset': (266, 137), 'inner-home-read': (266, 134),
            'inner-home-read-after': (267, 158), 'inner-home-write': (266, 134),
            'outer-home-next': (267, 207), 'edge-next-home': (264, 205),
            'no-next-edge-one-home-read': (264, 205), 'next-computed-before': (264, 193),
            'signed-next-before': (263, 200)}
        for name, body in source.candidates():
            _, _, row = source.measure(self.root, self.out, name, body)
            self.assertEqual((row['words'], row['differences']), expected[name])
            self.assertEqual((row['frame'], row['diagnostics'], row['pool_bytes']), (400, '', 0))
        self.receipt('screens', words_and_length_inclusive_differences=expected,
            frame=400, no_qualified_replacement=True)

    def test_08_fail_closed_symbolic_memory_and_instruction_contract(self):
        for value in (0, 1, 0x80000000, 0xFFFFFFFF, ('symbolic-word',)):
            self.assertEqual(proof.join([proof.byte(value, i) for i in range(4)]), value)
        self.assertEqual(proof.add(proof.add(('vertices',), 12), 12), proof.add(('vertices',), 24))
        self.assertEqual(proof.add(proof.STACK - 400, (-4) & proof.MASK), proof.STACK - 404)
        with self.assertRaisesRegex(ValueError, 'three valid kinds'):
            proof.Machine(self.words, 3)
        machine = proof.Machine(self.words, 0)
        with self.assertRaisesRegex(ValueError, 'Uninitialized private'):
            machine.load(proof.STACK - 4, 4)
        with self.assertRaisesRegex(ValueError, 'symbolic private-frame'):
            machine.load(('addu', ('index',), proof.STACK - 288), 4)
        for word in (0x44819001, 0x4601234D, 0x241A0001):
            with self.assertRaises(ValueError):
                proof.Machine(self.words, 0).ordinary(word)
        machine.run(machine.layout['outer'])
        before = proof.protected(machine)
        machine.call(edge.source.RANDOM)
        self.assertEqual(proof.protected(machine), before)
        self.assertEqual(machine.r[2], ('provider-result', 0))
        self.assertEqual(machine.r[15], ('provider-gpr', 0, 15))
        self.assertEqual(machine.f[19], ('provider-fpr', 0, 19))
        self.assertEqual((machine.hi, machine.lo), (('provider-hi', 0), ('provider-lo', 0)))
        self.assertEqual(machine.load(machine.r[29], 4), ('provider-home', 0, 0))
        self.receipt('checker-contract', partial_initialization_and_symbolic_frame_escape_rejected=True,
            malformed_COP1_and_kernel_register_write_rejected=True, arbitrary_provider_clobbers_checked=True)


if __name__ == '__main__':
    unittest.main()
