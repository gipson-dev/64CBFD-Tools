"""Full radial factory emitter, physical packets and closed initialization guards."""
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_randomized_ring_emitter as source
from tools.pad_generated_object import parse_object
from tools import pad_generated_object as padder
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import game_randomized_ring_oracle as guest
from tools.tests import test_game_scaled_random_spray as prior


def controls():
    return {
        'wrong-phase-step': source.SELECTED.replace('0xFFFF / count', '0x10000 / count'),
        'wrong-angle-shift': source.SELECTED.replace('phase >> 8', 'phase >> 7'),
        'swapped-trig': source.SELECTED.replace('sine = func_15048A40', 'sine = func_150489B0').replace(
            'cosine = func_150489B0', 'cosine = func_15048A40'),
        'wrong-delay-base': source.SELECTED.replace('+ 100.0f', '+ 99.0f'),
        'upper-random-half': source.SELECTED.replace('(u32)func_150ADA20() & 0xFFFFU', '(u32)func_150ADA20() >> 16'),
        'wide-random-tail': source.SELECTED.replace('tail & 15', 'tail & 31'),
        'wrong-factory-mode': source.SELECTED.replace('0, 0, 0, 0, 2,', '0, 0, 0, 0, 3,'),
        'live-instead-of-staged-colors': source.SELECTED.replace('color[0], color[1], color[2]',
            'D_8008CC20.values[0], D_8008CC20.values[1], D_8008CC20.values[2]'),
        'wrong-z-coordinate': source.SELECTED.replace('(s16)(s32)positionZ', '(s16)(s32)x'),
        'byte-extents': source.SELECTED.replace('(s16)extent, (s16)extent', '(u8)extent, (u8)extent'),
    }


class RandomizedRingTests(unittest.TestCase):
    test_10_all_801_archive_fingerprints = prior.ScaledRandomSprayTests.test_09_all_801_archive_fingerprints

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>193I', cls.rom, source.ROM))
        cls.table = struct.unpack_from('>65I', cls.rom, 0x23ECE0)
        image = (cls.out / 'before-elf').read_bytes()
        cls.colors = image[elf_slot_offset(image, source.COLORS, 64):][:64]
        assert cls.colors == cls.rom[0x2316E0:0x231720]
        assert cls.rom.find(cls.colors) == 0x2316E0 and cls.rom.find(cls.colors, 0x2316E1) == -1

    def receipt(self, name, **values):
        (self.out / ('qualification-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, args, randoms=guest.RANDOMS[0], phase=0, mode=0, streams=None):
        expected = guest.reference(memory, args, self.table, randoms, phase, mode)
        models = [guest.RingOracle(w, memory, args, self.table, randoms, phase, mode).run()
            for w in (streams or (self.words, self.truth, self.raw_words))]
        for model in models:
            self.assertEqual((model.calls, model.packets, guest.public(model.memory)), expected)
        self.assertEqual(guest.state(models[0]), guest.state(models[1]))
        if len(models) == 3:
            self.assertEqual(guest.state(models[0]), guest.state(models[2]))
        return models

    def test_01_shape_all_neighbors_pools_and_guard_scope(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (193, 320, 8))
        self.assertEqual(self.words, self.truth)
        old_obj, diagnostics = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-edge_wrapper_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(old_obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda o, f: {at - f['value']: rows for at, rows in o[2].items()
                if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(old_obj), normalized_pools(self.obj))
        self.assertEqual(parse_object(self.padded)[1][source.FUNCTION]['size'], 772)
        raw, rel = source.raw_target(self.obj)
        before, after = struct.unpack('>193I', raw), struct.unpack('>193I', source.normalize(raw, rel))
        self.assertEqual({i for i, (a, b) in enumerate(zip(before, after)) if a != b}, source.CHANGED)
        rows = [r for r in csv.DictReader(io.StringIO((self.out / 'qualified-guards.csv').read_text())) if r['function'] == source.FUNCTION]
        self.assertEqual(len(rows), 193)
        self.assertEqual(sum(r['expected'] != r['replacement'] for r in rows), 8)
        self.assertTrue(all(r['omit'] == 'false' and not r['insert_after'] and r['expected_relocations'] == r['replacement_relocations'] for r in rows))
        self.receipt('shape', raw_words=193, frame=320, raw_differences=8, guards=193,
            identity_guards=185, transforming_guards=8, neighbors_unchanged=len(old[1]) - 1,
            no_pool_insertion_omission_frame_home_constant_schedule_or_binding_changes=True,
            color_home=244, actual_three_color_bytes=self.colors[:3].hex(), color_ROM=0x2316E0)

    def test_02_checked_initialization_cycle_and_effective_instruction_negatives(self):
        result = source.prove_register_cycle(self.raw_words, self.words)
        for at, flip in ((44, 1 << 21), (47, 1 << 6), (50, 1 << 6), (51, 1), (54, 1 << 21), (55, 1 << 21), (61, 4)):
            bad = list(self.words)
            bad[at] ^= flip
            with self.assertRaises(ValueError, msg=str(at)):
                source.prove_register_cycle(self.raw_words, bad)
        self.receipt('proof', **result, effective_instruction_negatives=7)

    def test_03_whole_loops_all_physical_factory_words_and_home_probes(self):
        visits, cases = [set(), set(), set()], 0
        for count, pattern, flags, randoms, phase, mode in itertools.product(
                (-3, 0, 1, 2, 5, 10), range(3), (0, 0xABCDEF81), guest.RANDOMS, (0, 8), range(4)):
            memory, args = guest.fixture(self.colors, count, pattern, flags)
            for i, model in enumerate(self.compare(memory, args, randoms, phase, mode)):
                visits[i] |= model.visits
            cases += 1
        self.assertEqual(cases, 864)
        # The signed division trap arms and unsigned correction arms are retained
        # compiler instructions but unreachable after the positive count/mask gates.
        unreachable = {35, 39, 40, 41, 83, 84, 85, 98, 99, 100, 101}
        expected = set(range(source.ENTRY, source.ENTRY + 772, 4)) - {source.ENTRY + i * 4 for i in unreachable}
        self.assertEqual(visits, [expected] * 3)
        self.receipt('semantics', cases=cases, three_stream_runs=cases * 3, all_31_physical_words=True,
            raw_literal_state_equal_with_hostile_caller_saved_clobbers=True,
            unreachable_instruction_indices=sorted(unreachable), incoming_home_poison_guest_only=True,
            staged_colors_and_empty_count_copy=True)

    def test_04_literal_fault_prefixes_and_empty_input_gates(self):
        cases = 0
        for count, phase in itertools.product((0, 1, 3), (0, 8)):
            memory, args = guest.fixture(self.colors, count)
            complete = guest.RingOracle(self.words, memory, args, self.table, phase=phase).run()
            for fault in range(complete.accesses):
                models = []
                for words in (self.words, self.truth):
                    model = guest.RingOracle(words, memory, args, self.table, phase=phase, fault=fault)
                    with self.assertRaises(guest.AccessFault):
                        model.run()
                    models.append(model)
                self.assertEqual(guest.state(models[0]), guest.state(models[1]))
                cases += 1
        for count in (0, -1, -2147483648):
            memory, args = guest.fixture(self.colors, count)
            models = []
            for words in (self.words, self.truth, self.raw_words):
                model = guest.RingOracle(words, memory, args, self.table)
                for at in range(16, 40):
                    if not 28 <= at < 32:
                        del model.memory[guest.STACK + at]
                models.append(model.run())
            self.assertEqual(guest.state(models[0]), guest.state(models[1]))
            self.assertEqual(guest.state(models[0]), guest.state(models[2]))
        self.receipt('faults', fired_prefix_pairs=cases, empty_count_reads_only_count_and_four_byte_LWR_table=True,
            no_raw_fault_order_native_FCSR_or_hardware_claim=True)

    def test_05_every_word_binding_and_production_padder_corruption(self):
        raw, rel = source.raw_target(self.obj)
        manifest = self.out / 'qualified-guards.csv'
        before = (self.out / 'before-guards').read_bytes()
        self.assertTrue(manifest.read_bytes().startswith(before))
        for i in range(193):
            bad = bytearray(raw)
            bad[i * 4] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(bad), rel)
        text, functions, relocations = parse_object(self.obj)
        f = functions[source.FUNCTION]
        for i in range(193):
            bad = bytearray(text)
            bad[f['value'] + i * 4] ^= 1
            with patch.object(padder, 'parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaises(ValueError):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['edge_wrapper_original'], filename=source.OWNER, word_patches_path=manifest)
            bad_rel = {at: list(rows) for at, rows in relocations.items()}
            bad_rel[f['value'] + i * 4] = [('R_MIPS_26', 'wrong_symbol')]
            with patch.object(padder, 'parse_object', return_value=(text, functions, bad_rel)):
                with self.assertRaises(ValueError):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['edge_wrapper_original'], filename=source.OWNER, word_patches_path=manifest)
        for at in rel:
            bad = {k: list(v) for k, v in rel.items()}
            bad[at] = [(bad[at][0][0], 'wrong_symbol')]
            with self.assertRaises(ValueError):
                source.normalize(raw, bad)
        with self.assertRaises(ValueError):
            source.guard_manifest(before + b'\n', raw, rel)
        self.receipt('guards', effective_raw_flips=193, effective_padder_flips=193, effective_padder_binding_flips=193,
            external_binding_changes=len(rel), changed_predecessor_rejected=True)

    def test_06_compiled_semantic_negatives(self):
        evidence = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED, name)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            failed = False
            for count, pattern, randoms, mode in itertools.product((2, 5), range(3), guest.RANDOMS, (0, 2)):
                memory, args = guest.fixture(self.colors, count, pattern)
                try:
                    self.compare(memory, args, randoms, mode=mode, streams=(self.truth, words))
                except AssertionError:
                    failed = True
                    break
            self.assertTrue(failed, name)
            evidence.append(dict(name=name, raw_sha256=row['raw_sha256'], effective=True))
        self.receipt('negatives', compiled=evidence)

    def test_07_native32_formal_packets_staged_colors_and_numeric_boundaries(self):
        from tools.tests import game_randomized_ring_native as native
        harness = self.out / 'native-harness.c'
        harness.write_text(native.fixture(self.rom, self.colors))
        exits = {}
        for name, body, profile, valid in [('O2', source.SELECTED, '-O2', True),
                ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(native.TYPES + source.DECLARATIONS + body)
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-msse2', '-mfpmath=sse',
                '-mstackrealign', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static', '-fno-pie',
                '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation']
            command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error'] if valid else ['-Wno-unused-but-set-variable']
            result = subprocess.run([*command, str(path), str(harness), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            (self.out / ('native-' + name + '-diagnostics.txt')).write_text(result.stderr)
            self.assertEqual(result.returncode, 0, result.stderr[:2000])
            result = subprocess.run([str(path.with_suffix(''))], timeout=60)
            self.assertIn(result.returncode, (0,) if valid else tuple(range(20, 27)), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=1024, selected_UBSan=True, separate_translation_units=True,
            correct_ten_input_FP_word_byte_ABI=True, all_31_formal_factory_fields=True,
            palette_zero_and_finite_representable_conversion_domain=True,
            incoming_home_overwrite_and_physical_upper_bits_not_native_claims=True,
            effective_negatives=len(controls()), exits=exits)

    def test_08_independent_rebases_and_large_count_prefixes(self):
        raw, rel = source.raw_target(self.obj)
        normalized = source.normalize(raw, rel)
        original = (self.out / 'before-edge_wrapper_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('endlabel ' + source.FUNCTION, 1)[0]
        path = self.out / 'original-rebase.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n.type '
            + source.FUNCTION + ', @function\nglabel ' + source.FUNCTION + '\n' + original
            + '\n.size ' + source.FUNCTION + ', . - ' + source.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        tx, fs, rs = parse_object(path.with_suffix('.o'))
        f = fs[source.FUNCTION]
        original_raw = tx[f['value']:f['value'] + f['size']]
        original_rel = {at - f['value']: rows for at, rows in rs.items() if f['value'] <= at < f['value'] + f['size']}
        self.assertEqual(len(original_raw), 772)
        cases, prefixes = 0, 0
        for delta in (0, 0x10000, -0x10000):
            entry = source.ENTRY + delta
            b = dict(sine=source.SINE - delta, cosine=source.COSINE - delta,
                random=source.RANDOM - delta, factory=source.FACTORY - delta, colors=source.COLORS + delta + 16)
            bindings = dict(D_8008CC20=b['colors'], func_15048A40=b['sine'], func_150489B0=b['cosine'],
                func_150ADA20=b['random'], func_1516D4E8=b['factory'])
            streams = [source.link_target(self.out, 'rebase-%X-%d' % (entry, i), data, rows, entry, bindings)
                for i, (data, rows) in enumerate(((normalized, rel), (original_raw, original_rel), (raw, rel)))]
            self.assertEqual(streams[0], streams[1])
            for count, phase, mode in itertools.product((-1, 0, 1, 3), (0, 8), (0, 2)):
                memory, args = guest.fixture(self.colors, count, colors_address=b['colors'])
                expected = guest.reference(memory, args, self.table, phase=phase, mode=mode, bindings=b)
                models = [guest.RingOracle(w, memory, args, self.table, phase=phase, mode=mode, entry=entry, bindings=b).run() for w in streams]
                for model in models:
                    self.assertEqual((model.calls, model.packets, guest.public(model.memory)), expected)
                self.assertEqual(guest.state(models[0]), guest.state(models[1]))
                self.assertEqual(guest.state(models[0]), guest.state(models[2]))
                cases += 1
        for count, phase in itertools.product((65535, 65536, 0x7FFFFFFF), (0, 8)):
            memory, args = guest.fixture(self.colors, count)
            expected = guest.reference(memory, args, self.table, phase=phase, limit=3)
            models = []
            for words in (self.words, self.truth, self.raw_words):
                model = guest.RingOracle(words, memory, args, self.table, phase=phase, limit=3)
                with self.assertRaises(guest.edge.CallBoundary):
                    model.run()
                self.assertEqual((model.calls, model.packets, guest.public(model.memory)), expected)
                models.append(model)
            self.assertEqual(guest.state(models[0]), guest.state(models[1]))
            self.assertEqual(guest.state(models[0]), guest.state(models[2]))
            prefixes += 1
        self.receipt('rebases', independent_original_links=3, whole_rebased_cases=cases,
            changed_table_and_all_four_call_bindings=True, large_count_three_factory_prefixes=prefixes,
            zero_phase_step_above_65535=True, no_full_large_loop_native_claim=True)

    def test_09_all_four_original_caller_windows(self):
        cases = 0
        actor = 0x20000
        windows = ((0x15169ED4, 0x197384, 29, 50.0, 40, 0x3B480000, 20, -113.5),
            (0x15169F48, 0x1973F8, 29, 30.0, 40, 0x3B480000, 10, -128.5),
            (0x1516A234, 0x1976E4, 26, 20.0, 50, 0x39F00000, 4, -128.5),
            (0x15170E28, 0x19E2D8, 18, 70.0, 500, 0x3B960000, 10, -60080.25))
        for entry, rom, size, radius, lifetime, spread, count, y in windows:
            words = list(struct.unpack_from('>%dI' % size, self.rom, rom))
            for phase in (0, 8):
                memory, args = guest.fixture(self.colors)
                memory.update({actor + i: 0xA5 for i in range(0x200)})
                for at, value in ((0x90, guest.bits(50000.75)), (0x94, guest.bits(-123.5)), (0x98, guest.bits(32768.5)),
                        (0xE9, 20), (0xC, 0x81), (1, 0xFE)):
                    guest.put(memory, actor + at, value, 1 if at in (0xE9, 0xC, 1) else 4)
                model = guest.RingOracle(words, memory, args, self.table, phase=phase, entry=entry, stop_entry=True)
                model.r[16], model.r[13], model.r[14], model.r[15], model.r[30] = actor, 20, 50, 4, 0x81
                model.f[6], model.f[8], model.f[12] = guest.bits(-100.0), guest.bits(80.0), guest.bits(50000.75)
                model.f[26], model.f[28], model.f[30] = guest.bits(50000.75), guest.bits(-60000.25), guest.bits(32768.5)
                guest.put(model.memory, guest.STACK + phase + 0x134, 0x87654321)
                with self.assertRaises(guest.edge.CallBoundary):
                    model.run()
                expected = (guest.bits(50000.75), guest.bits(y), guest.bits(32768.5), guest.bits(radius),
                    lifetime, spread, 0, count, 0x81, 0x87654321 if entry == 0x15170E28 else 0xFE)
                self.assertEqual(model.entry_args, expected)
                cases += 1
        self.receipt('callers', original_windows=4, physical_ten_input_captures=cases,
            every_direct_caller_palette_zero=True, complete_callers_not_claimed_restored=True)

    def test_11_actual_trig_table_factory_and_allocator_chain(self):
        from tools.tests import test_game_small_record_factory as small
        image = (self.out / 'before-elf').read_bytes()
        connected = {}
        for address, rom, size in ((source.SINE, 0x75EF0, 48), (source.COSINE, 0x75E60, 144),
                (source.FACTORY, 0x19A998, 400), (0x15167A68, 0x194F18, 112)):
            data = image[elf_slot_offset(image, address, size):][:size]
            self.assertEqual(data, self.rom[rom:rom + size])
            connected.update(zip(range(address, address + size, 4), struct.unpack('>%dI' % (size // 4), data)))
        table = image[elf_slot_offset(image, 0x8009A220, 260):][:260]
        self.assertEqual(table, self.rom[0x23ECE0:0x23ECE0 + 260])
        cases = 0
        for count, pattern, randoms, phase, fail in itertools.product((-1, 0, 1, 3, 5, 10), range(3),
                guest.RANDOMS, (0, 8), (False, True)):
            memory, args = guest.fixture(self.colors, count, pattern)
            memory.update({0x8009A220 + i: value for i, value in enumerate(table)})
            memory.update({0x30000 + i: (i * 13 + 0xA5) & 255 for i in range(1024)})
            _, packets, _ = guest.reference(memory, args, self.table, randoms, phase)
            expected = dict(memory)
            for index, p in enumerate(packets):
                if fail and (index + 1) % 3 == 0:
                    continue
                for i, value in enumerate(p[4:], 4):
                    guest.put(expected, guest.STACK + phase - 320 + i * 4, value)
                record = 0x30000 + index * 80
                expected, _ = small.reference(expected, p, record, phase=phase - 320)
                guest.put(expected, record, 0x12, 1)
                guest.put(expected, record + 1, p[30], 1)
                guest.put(expected, record + 12, p[29], 1)
            models = []
            for words in (self.words, self.truth, self.raw_words):
                model = guest.RingOracle(words, memory, args, self.table, randoms, phase, connected=connected)
                model.allocation_fail = fail
                model.run()
                self.assertEqual(model.packets, packets)
                self.assertEqual(guest.public(model.memory), guest.public(expected))
                models.append(model)
            self.assertEqual(guest.state(models[0]), guest.state(models[1]))
            self.assertEqual(guest.state(models[0]), guest.state(models[2]))
            cases += 1
        self.assertEqual(cases, 216)
        self.receipt('connected', cases=cases, current_connected_helper_words=176, real_65_float_trig_table=True,
            actual_factory_allocator_and_all_52_record_bytes_checked=True, every_third_allocation_failure=True,
            RNG_heap_and_registration_opaque=True, no_full_gameplay_or_hardware_claim=True)

    def test_12_frozen_inputs_initial_prediction_and_capture_corruptions(self):
        source.freeze(self.root, self.out)
        expected = source.expected_inputs(self.root, self.out)
        prediction = {key: hashlib.sha256(data).hexdigest() for key, data in expected.items()}
        manifest = self.out / 'initial-prediction.json'
        if not manifest.exists():
            self.assertEqual({k: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for k, p in source.PATHS.items()}, source.BASELINE)
            manifest.write_text(json.dumps(prediction, indent=2) + '\n')
        self.assertEqual(json.loads(manifest.read_text()), prediction)
        live = {k: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for k, p in source.PATHS.items()}
        self.assertIn(live, (source.BASELINE, dict(source.BASELINE, **prediction)))
        rb = Path.read_bytes
        for key in source.PATHS:
            target = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        self.receipt('prediction', initial=prediction, frozen_inputs=len(source.PATHS),
            expected_changed_bytes=sum(a != b for a, b in zip((self.out / 'before-elf').read_bytes(), expected['elf'])),
            all_capture_corruptions_effective=True, no_metadata_exclusion=True)


if __name__ == '__main__':
    unittest.main()
