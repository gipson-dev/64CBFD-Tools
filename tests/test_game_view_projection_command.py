"""Private semantic qualification; these non-matching drafts are not installed."""
import csv
import hashlib
import itertools
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_view_projection_command_candidates as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.pad_generated_object import parse_object
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_view_fov_transfer as transfer
from tools.tests import test_game_trig_match as trig
from tools.tests import test_game_cosine_match as cosine
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_point_transform_match import put, read

ENTRY, CHILD, WRAPPER = source.ENTRY, 0x1510B5F8, 0x1510B32C
BASE, COEF_X, COEF_Y = 0x800BE628, 0x800A2C24, 0x800A2C28
FOV_OVERRIDE, NEAR_OVERRIDE, FAR_OVERRIDE = 0x800C3648, 0x800C364C, 0x800C3650
NEAR_DEFAULT, FAR_DEFAULT = 0x800D9B20, 0x800D9B1C
VIEWS, ALTERNATE, THIRD = transfer.VIEWS, transfer.ALTERNATE, transfer.THIRD
RESULTS = tuple(map(bits, (0.25, 1.0, -0.5, 2.0, 0.125, -0.25)))
CLIPS = (0, 0x80000000, bits(0.5), bits(-2.0), 0x7FC12345)
fp = transfer.fp


def external(memory):
    return {a: b for a, b in memory.items() if not machine.STACK - 0x600 <= a < machine.STACK + 0x180}


def fixture(index=0, near=0, far=0):
    memory = {machine.STACK + i: 0xA5 for i in range(-0x600, 0x180)}
    for region, base in enumerate((VIEWS, ALTERNATE, THIRD)):
        memory.update({base + i: (i * 13 + 0xA5) & 255 for i in range(0x900)})
        for slot in range(6):
            for offset, value in ((0xC, 160.0), (0x10, 120.0), (0x14, 1.25),
                    (0x18, 0.75), (0x1C, -123.0), (0x20, -456.0),
                    (0x6C, 60.0), (0x70, 45.0), (0x74, 75.0), (0x78, 50.0),
                    (0x7C, 1.5), (0x80, 0.5)):
                put(memory, base + slot * 0x180 + offset, bits(value + slot + region))
    for address in (BASE, COEF_X, FOV_OVERRIDE, 0x800D9AC0):
        memory.update({address + i: 0xA5 for i in range(0x80)})
    for address, value in ((BASE, VIEWS), (COEF_X, 0x3C0EFA35), (COEF_Y, 0x3C0EFA35),
            (FOV_OVERRIDE, bits(3.0)), (NEAR_OVERRIDE, near), (FAR_OVERRIDE, far),
            (NEAR_DEFAULT, bits(0.125)), (FAR_DEFAULT, bits(1000.0))):
        put(memory, address, value)
    return memory


def view(memory, index, offset):
    return (read(memory, BASE) + index * 0x180 + offset) & 0xFFFFFFFF


def effects(memory, index, ordinal, mode):
    if mode == 1 and ordinal == 1:
        put(memory, BASE, ALTERNATE)
        put(memory, COEF_X, bits(2.0))
        put(memory, ALTERNATE + index * 0x180 + 0x74, bits(179.0))
    if mode == 2 and ordinal == 2:
        put(memory, BASE, THIRD)
        put(memory, COEF_Y, bits(0.125))
        put(memory, THIRD + index * 0x180 + 0xC, bits(321.0))
    if mode == 3 and ordinal == 3:
        put(memory, BASE, ALTERNATE)
        put(memory, ALTERNATE + index * 0x180 + 0x78, bits(100.0))
    if mode == 4 and ordinal == 4:
        put(memory, NEAR_OVERRIDE, bits(7.0))
        put(memory, FAR_OVERRIDE, bits(777.0))
        put(memory, BASE, THIRD)
    if mode == 5 and ordinal == 5:
        put(memory, BASE, ALTERNATE)
        put(memory, ALTERNATE + index * 0x180 + 0xB8, 0x12345678)


def reference(memory, args, seed=0, mode=0, real_trig=False):
    memory, calls = dict(memory), []
    index, x, y, scale, fallback = args
    for offset, base_offset, delta in ((0x74, 0x6C, x), (0x78, 0x70, y)):
        result = fp(fp(read(memory, view(memory, index, base_offset)), delta, 'add'), read(memory, FOV_OVERRIDE), 'add')
        put(memory, view(memory, index, offset), result)
    for fov, coefficient, extent, axis, factor, output in (
            (0x74, COEF_X, 0xC, 0x14, 0x7C, 0x1C), (0x78, COEF_Y, 0x10, 0x18, 0x80, 0x20)):
        angle = fp(read(memory, view(memory, index, fov)), read(memory, coefficient), 'mul')
        values = []
        for target in (cosine.ENTRY, trig.ENTRY):
            calls.append((target, (angle,)))
            values.append((cosine.reference(angle) if target == cosine.ENTRY else trig.reference(angle))
                if real_trig else RESULTS[(seed + len(calls) * 3) % len(RESULTS)])
            effects(memory, index, len(calls), mode)
        focal = fp(fp(values[0], read(memory, view(memory, index, extent)), 'mul'), values[1], 'div')
        value = fp(fp(read(memory, view(memory, index, factor)),
            fp(read(memory, view(memory, index, axis)), focal, 'mul'), 'mul'), scale, 'mul')
        put(memory, view(memory, index, output), value)
    near, far = read(memory, NEAR_OVERRIDE), read(memory, FAR_OVERRIDE)
    if floating(near) == 0.0:
        near = fallback if floating(fallback) != 0.0 else read(memory, NEAR_DEFAULT)
    if floating(far) == 0.0:
        far = read(memory, FAR_DEFAULT)
    calls.append((CHILD, (index, view(memory, index, 0xB8), read(memory, view(memory, index, 0x78)),
        read(memory, view(memory, index, 0x74)), near, far, scale)))
    effects(memory, index, len(calls), mode)
    return external(memory), calls


class CommandOracle(cosine.CosineOracle):
    def __init__(self, words, memory, args, seed=0, mode=0, phase=0, connected=None, entry=ENTRY, fault=None):
        super().__init__(words, memory, entry=entry, arguments=args, phase=phase, connected=connected)
        self.index, self.seed, self.mode = args[0], seed, mode
        self.root_fault, self.root_accesses = fault, 0
        self.command_calls = []

    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 3:
            self.f[word >> 6 & 31] = fp(self.f[word >> 11 & 31], self.f[word >> 16 & 31], 'div')
        else:
            super().execute(word)

    def access(self):
        if self.own_instruction and ENTRY <= self.current_pc < ENTRY + 516:
            if self.root_accesses == self.root_fault:
                raise faults.AccessBoundary
            self.root_accesses += 1

    def record_call(self, target):
        if target == ENTRY:
            self.command_calls.append(self.arguments(5))
            return
        assert target in (cosine.ENTRY, trig.ENTRY, CHILD), hex(target)
        args = (self.f[12],) if target != CHILD else self.arguments(7)
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        ordinal = len(self.calls)
        effects(self.memory, self.index, ordinal, self.mode)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2], self.f[0] = 0x11223344 + ordinal, RESULTS[(self.seed + ordinal * 3) % len(RESULTS)]


class ViewProjectionCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)
        cls.body = dict(source.variants())[source.SELECTED_LABEL]
        cls.before = (cls.out / 'before-owner').read_text()
        cls.obj, cls.diagnostics = build.compile_owner(cls.root, cls.out, source.recover(cls.before, cls.body), 'qualified-command')
        cls.data, cls.functions = build.link_owner(cls.root, cls.out, cls.obj, source.OWNER)
        cls.words = cls.function_words(source.FUNCTION)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>129I', cls.rom, source.ROM))

    @classmethod
    def function_words(cls, name):
        info = cls.functions[name]
        return list(struct.unpack_from('>%dI' % (info['size'] // 4), cls.data, info['value']))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def models(self, args, near=0, far=0, seed=0, mode=0, phase=0, bodies=None, connected=None, memory=None):
        memory = fixture(args[0], near, far) if memory is None else memory
        expected = reference(memory, args, seed, mode, bool(connected))
        models = [CommandOracle(words, memory, args, seed, mode, phase, connected=connected).run()
            for words in (bodies or (self.retail, self.words))]
        for model in models:
            self.assertEqual((external(model.memory), model.calls), expected)
        return models

    def test_01_shape_neighbors_and_actual_obsolete_guard_boundary(self):
        self.assertEqual(self.diagnostics, '')
        self.assertEqual((len(self.words), self.words[0]), (129, 0x27BDFFB0))
        self.assertEqual(sum(a != b for a, b in zip(self.words, self.retail)), 41)
        old, warnings = build.compile_owner(self.root, self.out, self.before, 'before-command-owner')
        a, af, ar = parse_object(old)
        b, bf, br = parse_object(self.obj)
        self.assertEqual(warnings, '')
        self.assertEqual(set(af), set(bf))
        retained = set(af) - {source.FUNCTION, 'func_1510B32C', 'func_1510B5F8'}
        for name in retained:
            x, y = af[name], bf[name]
            self.assertEqual(x['size'], y['size'], name)
            self.assertEqual(a[x['value']:x['value'] + x['size']], b[y['value']:y['value'] + y['size']], name)
            relative = lambda rows, info: {at - info['value']: value for at, value in rows.items() if info['value'] <= at < info['value'] + info['size']}
            self.assertEqual(relative(ar, x), relative(br, y), name)
        self.assertEqual(normalized_pools(old), normalized_pools(self.obj))
        wrapper = self.function_words('func_1510B32C')
        self.assertEqual(struct.pack('>33I', *wrapper), self.rom[0x1387DC:0x1387DC + 132])
        self.assertEqual((af['func_1510B5F8']['size'], bf['func_1510B5F8']['size']), (12, 28))
        with self.assertRaises(ValueError):
            pad_c_object.emit_padded_assembly(self.obj, self.root / source.PATHS['layout'], source.OWNER,
                word_patches_path=self.root / source.PATHS['guards'])
        rows = list(csv.DictReader(io.StringIO((self.out / 'before-guards').read_text())))
        removed = [r for r in rows if r['function'] == 'func_1510B32C']
        self.assertEqual(len(removed), 8)
        private = self.out / 'private-compatible-guards.csv'
        with private.open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(r for r in rows if r not in removed)
        assembly = pad_c_object.emit_padded_assembly(self.obj, self.root / source.PATHS['layout'], source.OWNER, word_patches_path=private)
        path = self.out / 'private-padded.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + assembly)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], capture_output=True, check=True)
        data, functions = build.link_owner(self.root, self.out, path.with_suffix('.o'), source.OWNER)
        at = functions[source.FUNCTION]['value']
        self.assertEqual(data[at:at + 516], struct.pack('>129I', *self.words))
        self.receipt('owner', words=129, frame=80, differences=41, untouched_neighbors=len(retained),
            typed_wrapper_direct_words=33, obsolete_wrapper_guards=8, typed_child_stub_bytes=[12, 28],
            production_guard_rejection=True, private_padder_preserves_nonmatching_body=True, not_installable=True)

    def test_02_finite_arithmetic_clip_bits_live_callbacks_and_public_state(self):
        cases, coverage = 0, [set(), set()]
        for index, clip, seed, mode, phase in itertools.product((0, 1, 3), range(5), range(6), range(6), (0, 8)):
            args = (index, bits(1.25), bits(-2.5), bits((1.0, -1.25, 0.0)[index % 3]), CLIPS[(clip + 2) % 5])
            models = self.models(args, CLIPS[clip], CLIPS[(clip + 1) % 5], seed, mode, phase)
            for i, model in enumerate(models):
                coverage[i].update(model.visits)
            cases += 1
        self.receipt('public', paired_cases=cases, reached_root_words=[len(s & set(range(ENTRY, ENTRY + 516, 4))) for s in coverage],
            signed_zero_and_qNaN_clip_payloads=True, finite_arithmetic_and_trig_results=True,
            entire_external_memory_and_all_five_calls=True, no_private_stack_FCSR_native_or_gameplay_claim=True)

    def test_03_connected_actual_recovered_trig(self):
        connected = {}
        for name, entry, rom, count in (('sinf', trig.ENTRY, trig.ROM, 104), ('cosf', cosine.ENTRY, cosine.ROM, 88)):
            obj, diagnostics = build.compile_owner(self.root, self.out, (self.root / source.PATHS[name]).read_text(), 'connected-command-' + name)
            data, _ = build.link_owner(self.root, self.out, obj, name)
            self.assertEqual((diagnostics, data), ('', self.rom[rom:rom + count * 4]))
            connected.update(zip(range(entry, entry + count * 4, 4), struct.unpack('>%dI' % count, data)))
        for index, phase in itertools.product((0, 1, 3), (0, 8)):
            args = (index, bits(1.25), bits(-2.5), bits(1.0), 0)
            self.models(args, phase=phase, connected=connected, memory=self.trig_fixture(index))
        self.receipt('connected', paired_cases=6, both_recovered_trig_bodies_executed=True,
            actual_matrix_child_still_bounded=True, no_production_camera_acceptance=True)

    def trig_fixture(self, index):
        memory = fixture(index)
        for address, value in {**trig.GLOBALS, **trig.COS_GLOBALS}.items():
            put(memory, address, value)
        return memory

    def test_04_actual_typed_wrapper_to_private_command(self):
        wrapper = self.function_words('func_1510B32C')
        cases = 0
        for index, mode, phase in itertools.product((0, 1, 3), (0, 1, 4), (0, 8)):
            args = (index, bits(1.25), bits(-2.5), bits(1.0))
            memory = fixture(index)
            expected, calls = reference(memory, (*args, 0), mode=mode)
            for offset, word in ((0, args[3]), (4, args[1]), (8, args[2])):
                put(expected, 0x800D9AC0 + index * 12 + offset, word)
            expected[0x800D9AF0] = 1
            for body in (self.retail, self.words):
                connected = dict(zip(range(ENTRY, ENTRY + 516, 4), body))
                model = CommandOracle(wrapper, memory, args, mode=mode, phase=phase, connected=connected, entry=WRAPPER).run()
                self.assertEqual(model.command_calls, [(*args, 0)])
                self.assertEqual((external(model.memory), model.calls), (expected, calls))
            cases += 1
        self.receipt('wrapper', paired_cases=cases, actual_direct_33_word_wrapper=True,
            five_o32_argument_words_and_postcall_stores=True, no_child_or_full_caller_acceptance=True)

    def test_05_effective_compiled_semantic_controls(self):
        controls = {
            'ignore-near-override': self.body.replace('nearOverride = D_800C364C;', 'nearOverride = 0.0f;'),
            'wrong-scale': self.body.replace('* scale;', '* 2.0f;'),
            'wrong-fov-addition': self.body.replace('baseFovX + offsetX + D_800C3648', 'baseFovX - offsetX + D_800C3648'),
        }
        for label, body in controls.items():
            self.assertNotEqual(body, self.body)
            obj, diagnostics = build.compile_owner(self.root, self.out, source.recover(self.before, body), 'negative-' + label)
            data, functions = build.link_owner(self.root, self.out, obj, source.OWNER)
            info = functions[source.FUNCTION]
            words = list(struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value']))
            self.assertEqual(diagnostics, '')
            with self.assertRaises(AssertionError):
                self.models((0, bits(1.25), bits(-2.5), bits(1.0), 0), near=bits(7.0), bodies=(words,))
        self.receipt('controls', effective_compiled_negatives=list(controls))

    def test_06_actual_fault_witness_not_private_state_parity(self):
        args, memory = (0, bits(1.25), bits(-2.5), bits(1.0), 0), fixture()
        full = CommandOracle(self.retail, memory, args).run()
        differences = []
        for cut in range(full.root_accesses):
            models = [CommandOracle(words, memory, args, fault=cut) for words in (self.retail, self.words)]
            for model in models:
                with self.assertRaises(faults.AccessBoundary):
                    model.run()
            if machine.complete_state(models[0]) != machine.complete_state(models[1]):
                differences.append(dict(cut=cut, pc=[m.current_pc for m in models], delay=[m.delay_of for m in models],
                    gpr_differences=[i for i in range(32) if models[0].r[i] != models[1].r[i]],
                    fpr_differences=[i for i in range(32) if models[0].f[i] != models[1].f[i]],
                    memory_equal=models[0].memory == models[1].memory))
        self.assertTrue(differences)
        self.receipt('fault-boundary', fired_paired_prefixes=full.root_accesses,
            different_states=len(differences), first=differences[0], not_full_private_or_fault_equivalent=True)

    def test_07_frozen_production_and_capture_controls(self):
        source.freeze(self.root, self.out)
        for key, path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), source.BASELINE[key], key)
        rb, target = Path.read_bytes, self.out / 'before-owner'
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
            with self.assertRaisesRegex(ValueError, 'immutable view-command input'):
                source.freeze(self.root, self.out)
        self.assertNotIn('return 0;', self.body)
        self.assertEqual(self.body.count('cosineX'), 3)
        self.assertEqual(self.body.count('cosineY'), 3)

    def test_08_completed_screens_and_unused_local_shape_controls(self):
        rows = json.loads((self.out / 'candidates.json').read_text())
        self.assertEqual(len(rows), 130)
        self.assertEqual({r['label'] for r in rows}, {label for label, _ in source.variants()})
        self.assertTrue(all(not r['diagnostics'] for r in rows))
        self.assertFalse(any(not r['differences'] and not r['uncompared_slot_words'] for r in rows))
        selected = next(r for r in rows if r['label'] == source.SELECTED_LABEL)
        self.assertEqual((selected['code_bytes'], selected['frame_bytes'], len(selected['differences']), selected['unused_cosine_control']),
            (516, 80, 41, False))
        control = next(r for r in rows if r['label'] == 'nested-direct-product')
        self.assertTrue(control['unused_cosine_control'])


if __name__ == '__main__':
    unittest.main()
