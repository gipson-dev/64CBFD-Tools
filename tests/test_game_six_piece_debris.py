"""Pre-install debris recovery gates; deliberately withhold byte-match credit."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_six_piece_debris as source
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import game_six_piece_debris_oracle as guest


def controls():
    return {
        'unsigned-rng': source.SELECTED.replace('func_150ADA20() >> 16', '(u32)func_150ADA20() >> 16'),
        'narrow-asset-id': source.SELECTED.replace('func_1518C900(kind)', 'func_1518C900((u8)kind)'),
        'wrong-option-priority': source.SELECTED.replace('options & 2', 'options & 1').replace('options & 1) {\n                kind', 'options & 2) {\n                kind'),
        'wrong-vertical-sign': source.SELECTED.replace('fabsf(y)', 'y'),
        'wrong-spin-scale': source.SELECTED.replace('0.0000762939453125f', '0.00006103515625f'),
        'word-actor-flag': source.SELECTED.replace('actor[0x6E] = 1;', '*(s32 *)(actor + 0x6C) = 1;'),
        'wrong-ring-value': source.SELECTED.replace('500, 0.00457763671875f', '499, 0.00457763671875f'),
        'cached-kinds': source.SELECTED.replace('    index = 0;', '    kinds = D_800A6F80;\n    index = 0;').replace('            kinds = D_800A6F80;\n', ''),
        'reset-fixed-packet': source.SELECTED.replace('        asset = func_1518C900(kind);', '        packet.lifetime = 60;\n        asset = func_1518C900(kind);'),
        'cached-vectors': source.SELECTED.replace('        asset = func_1518C900(kind);\n', '').replace('        packet.position[0]', '        asset = func_1518C900(kind);\n        packet.position[0]', 1),
    }


class SixPieceDebrisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.words, cls.row = source.measure(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>205I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / ('qualification-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, args, mode=0, phase=0, rotation=0, words=None):
        expected = guest.reference(memory, args, mode, rotation)
        models = [guest.DebrisOracle(w, memory, args, phase, mode, rotation).run()
            for w in (self.truth, self.words if words is None else words)]
        for model in models:
            self.assertEqual((model.calls, model.packets, guest.edge.public(model.memory)),
                (expected[0], expected[1], expected[3]))
            for actual, known in zip(model.holes, expected[2]):
                if known is not None:
                    self.assertEqual(actual, known)
        return models

    def test_01_measure_and_reject_the_incomplete_install_gate(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences'], self.row['pool_bytes']),
            (210, 296, 205, 0))
        self.assertEqual(self.row['diagnostics'], '')
        self.assertNotEqual(self.words, self.truth)
        self.assertEqual(self.row['raw_sha256'], 'd6b82be73d6ada072ac7fab93cc77d66bf625b1589535dad2478381dd4e54671')
        old_obj, diagnostics = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-edge_wrapper_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(old_obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            if name == 'func_151718F0':
                self.assertEqual((f['size'], g['size']), (12, 28))
                typed = new[0][g['value']:g['value'] + g['size']]
                self.assertEqual(typed[:16], struct.pack('>4I', 0xE7AC0000, 0xE7AE0004, 0xAFA60008, 0xAFA7000C))
                self.assertEqual(typed[16:], old[0][f['value']:f['value'] + f['size']])
                continue
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda obj, f: {at - f['value']: rows for at, rows in obj[2].items()
                if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(old_obj), normalized_pools(self.obj))
        self.receipt('shape', **{k: self.row[k] for k in ('words', 'frame', 'differences', 'pool_bytes', 'raw_sha256')},
            retail_words=205, retail_frame=288, installed=False, guards_added=0,
            neighbors_unchanged=len(old[1]) - 2, typed_ring_stub_size=[12, 28],
            install_gate_rejected=['target_exceeds_slot', 'frame_differs', 'typed_ring_changes_neighbor'])

    def test_02_whole_six_packet_sequences_and_live_providers(self):
        coverage, cases = [set(), set()], 0
        for options, kind, flags, pattern, mode, phase in itertools.product(
                (0, 1, 2, 3, -1, 0x80000000), (1, 169, 256, 0x7FFFFFFF),
                (0, 0xABCDEF81), range(3), range(5), (0, 8)):
            memory, args = guest.fixture(self.rom, options, kind, flags=flags, pattern=pattern)
            for i, model in enumerate(self.compare(memory, args, mode, phase, pattern)):
                coverage[i] |= model.visits
            cases += 1
        self.assertEqual(cases, 1440)
        self.assertEqual(coverage, [set(range(source.ENTRY, source.ENTRY + n * 4, 4)) for n in (205, 210)])
        self.receipt('semantics', cases=cases, model_runs=cases * 2, packet_size=96,
            compared_initialized_bytes=90, known_provider_seeded_holes_compared=True,
            six_lookup_and_submit_calls=True, random_calls_per_sequence=36,
            full_ten_word_ring_ABI=True, every_body_instruction_visited=[205, 210],
            raw_private_ram_and_first_indeterminate_bytes_not_claimed=True)

    def test_03_compiled_effective_negatives(self):
        evidence = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED, name)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            failed = False
            for options, mode in ((0, 0), (1, 0), (3, 1), (2, 2), (2, 3)):
                memory, args = guest.fixture(self.rom, options, 0x7FFFFFFF, pattern=1)
                try:
                    self.compare(memory, args, mode=mode, words=words)
                except AssertionError:
                    failed = True
                    break
            self.assertTrue(failed, name)
            evidence.append(dict(name=name, raw_sha256=row['raw_sha256'], effective=True))
        self.receipt('negatives', compiled=evidence)

    def test_04_immutable_captures_and_no_production_changes(self):
        source.freeze(self.root, self.out)
        for key, path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), source.BASELINE[key], key)
        for key in ('elf', 'edge_wrapper_owner', 'guards', 'debris_constants'):
            path = self.out / ('before-' + key)
            original = path.read_bytes()
            try:
                corrupted = bytearray(original)
                corrupted[len(corrupted) // 2] ^= 1
                path.write_bytes(corrupted)
                with self.assertRaises(ValueError):
                    source.freeze(self.root, self.out)
            finally:
                path.write_bytes(original)
        source.freeze(self.root, self.out)
        self.receipt('boundaries', frozen_inputs=len(source.PATHS), live_input_hashes_unchanged=True,
            effective_capture_corruptions=4, no_source_guard_ELF_or_status_changes=True)

    def test_05_native32_packets_and_formal_ring_ABI(self):
        from tools.tests import game_six_piece_debris_native as native
        harness = self.out / 'native-harness.c'
        harness.write_text(native.fixtures(self.rom))
        exits = {}
        for name, body, profile, valid in [('O2', source.SELECTED, '-O2', True),
                ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(native.TYPES + source.DECLARATIONS.replace('#pragma intrinsic (fabsf)\n', '') + body)
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-msse2', '-mfpmath=sse',
                '-mstackrealign', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static', '-fno-pie',
                '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation']
            if valid:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            result = subprocess.run([*command, str(path), str(harness), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=60)
            self.assertIn(result.returncode, (0,) if valid else tuple(range(20, 31)), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=1024, separate_translation_units=True, UBSan_selected=True,
            initialized_packet_bytes=90, seeded_holes_checked_after_first_submit=True,
            formal_ten_argument_ring_ABI=True, effective_negatives=len(controls()), exits=exits,
            no_first_hole_value_physical_register_FAULT_or_FCSR_claim=True)


if __name__ == '__main__':
    unittest.main()
