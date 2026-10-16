"""Exact debris slot, full packet residue and bounded native/connected acceptance."""
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

from tools.experiments import game_six_piece_debris_match as source
from tools.pad_generated_object import parse_object
from tools import pad_generated_object as padder
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import game_six_piece_debris_match_oracle as guest
from tools.tests import test_game_randomized_ring_emitter as prior


def controls():
    return {
        'unsigned-rng': source.SELECTED.replace('func_150ADA20() >> 16', '(u32)func_150ADA20() >> 16'),
        'narrow-asset-id': source.SELECTED.replace('func_1518C900(kind)', 'func_1518C900((u8)kind)'),
        'wrong-option-priority': source.SELECTED.replace('options & 2', 'options & 1').replace('options & 1 ?', 'options & 2 ?'),
        'wrong-vertical-sign': source.SELECTED.replace('fabsf(component)', 'component'),
        'wrong-spin-scale': source.SELECTED.replace('0.0000762939453125f', '0.00006103515625f'),
        'word-actor-flag': source.SELECTED.replace('actor[0x6E] = 1;', '*(s32 *)(actor + 0x6C) = 1;'),
        'wrong-ring-value': source.SELECTED.replace('500, 0.00457763671875f', '499, 0.00457763671875f'),
        'cached-kinds': source.SELECTED.replace('    s32 index;', '    DebrisKinds19E040 kinds;\n    s32 index;').replace(
            '            DebrisKinds19E040 kinds;\n            kinds = D_800A6F80;\n', '').replace(
            '    index = 0;', '    kinds = D_800A6F80;\n    index = 0;'),
        'reset-fixed-packet': source.SELECTED.replace('        asset = func_1518C900(kind);',
            '        packet.lifetime = 60;\n        asset = func_1518C900(kind);'),
        'cached-vector-x': source.SELECTED.replace('        component = vector[0];\n', '').replace(
            '        asset = func_1518C900(kind);', '        component = vector[0];\n        asset = func_1518C900(kind);'),
        'reset-reserved-byte': source.SELECTED.replace('        packet.asset = asset;',
            '        packet.reserved44[0] = 0;\n        packet.asset = asset;'),
    }


class SixPieceDebrisMatchTests(unittest.TestCase):
    test_10_all_801_archive_fingerprints = prior.RandomizedRingTests.test_10_all_801_archive_fingerprints

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>205I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / ('qualification-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, args, mode=0, phase=0, rotation=0, streams=None):
        expected = guest.reference(memory, args, mode, rotation, phase)
        models = [guest.DebrisMatchOracle(w, memory, args, phase, mode, rotation).run()
            for w in (streams or (self.words, self.truth, self.raw_words))]
        for model in models:
            self.assertEqual((model.calls, model.full_packets, guest.public(model.memory)), expected)
        self.assertEqual(guest.literal(models[0]), guest.literal(models[1]))
        if len(models) == 3:
            self.assertEqual(models[0].observed, models[2].observed)
        return models

    def test_01_actual_padder_packet_home_all_neighbors_and_guard_plan(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (205, 288, 44))
        self.assertEqual(self.words, self.truth)
        self.assertEqual(parse_object(self.padded)[1][source.FUNCTION]['size'], 820)
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
            relative = lambda o, f: {at - f['value']: rows for at, rows in o[2].items() if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(old_obj), normalized_pools(self.obj))
        raw, rel = source.raw_target(self.obj)
        normalized, moved = source.normalize(raw, rel)
        self.assertEqual(sorted(source.ORDER), list(range(205)))
        for i, old_i in enumerate(source.ORDER):
            a, b = struct.unpack_from('>I', raw, old_i * 4)[0], struct.unpack_from('>I', normalized, i * 4)[0]
            if i == 73:
                self.assertEqual((a, b), (0x27B50094, 0x27B5009C))
            elif a != b:
                mask = sum(31 << shift for shift in source.allocation.register_fields(a))
                self.assertEqual(a & ~mask, b & ~mask)
        rows = [r for r in csv.DictReader(io.StringIO((self.out / 'qualified-guards.csv').read_text())) if r['function'] == source.FUNCTION]
        identity = sum(r['expected'] == r['replacement'] and r['expected_relocations'] == r['replacement_relocations'] for r in rows)
        self.assertEqual(len(rows), 205)
        self.assertTrue(all(r['omit'] == 'false' and not r['insert_after'] for r in rows))
        self.assertEqual(self.raw_words[155], 0x27A400BC)
        self.assertEqual(self.words[155], 0x27A400BC)
        self.receipt('shape', raw_words=205, raw_real_differences=44, frame=288, packet_home=188,
            guards=205, identity_guards=identity, transforming_guards=205 - identity,
            all_operations_retained_once=True, no_frame_packet_home_opcode_constant_or_call_boundary_change=True,
            private_kind_home=[148, 156], neighbors_unchanged=len(old[1]) - 1, pools_fixed=True)

    def test_02_expression_graph_and_effective_dependency_negatives(self):
        raw, rel = source.raw_target(self.obj)
        normalized, moved = source.normalize(raw, rel)
        a, b = list(struct.unpack('>205I', raw)), list(struct.unpack('>205I', normalized))
        result = source.prove(a, rel, b, moved)
        for at, flip in ((29, 1 << 16), (36, 4), (58, 1 << 16), (73, 4), (93, 4),
                (98, 1 << 11), (104, 4), (110, 1 << 11), (112, 4)):
            bad = list(b)
            bad[at] ^= flip
            with self.assertRaises(ValueError, msg=str(at)):
                source.prove(a, rel, bad, moved)
        self.receipt('proof', **result, effective_dependency_negatives=9)

    def test_03_all_96_bytes_literal_and_raw_provider_observations(self):
        visits, cases = set(), 0
        for options, kind, flags, pattern, mode, phase in itertools.product((0, 1, 2, 3, -1, 0x80000000),
                (1, 169, 256, 0x7FFFFFFF), (0, 0xABCDEF81), range(3), range(5), (0, 8)):
            memory, args = guest.previous.fixture(self.rom, options, kind, flags=flags, pattern=pattern)
            models = self.compare(memory, args, mode, phase, pattern)
            visits |= models[0].visits
            cases += 1
        self.assertEqual(cases, 1440)
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 820, 4)))
        self.receipt('semantics', cases=cases, three_stream_runs=cases * 3, full_packet_bytes=96,
            initial_six_stack_residue_bytes_independently_derived=True, all_205_instructions_visited=True,
            raw_staging_private_memory_not_claimed_equal=True, retained_packet_observations_equal=True)

    def test_04_fired_literal_fault_prefixes_and_retained_pointer_mutations(self):
        cases, mutations = 0, 0
        for options, phase in itertools.product((0, 2), (0, 8)):
            memory, args = guest.previous.fixture(self.rom, options)
            complete = guest.DebrisMatchOracle(self.words, memory, args, phase).run()
            for fault in range(complete.accesses):
                models = []
                for words in (self.words, self.truth):
                    model = guest.DebrisMatchOracle(words, memory, args, phase, fault=fault)
                    with self.assertRaises(guest.AccessFault):
                        model.run()
                    models.append(model)
                self.assertEqual(guest.literal(models[0]), guest.literal(models[1]))
                cases += 1
        for options, phase, mode in itertools.product((0, 1, 2, 3), (0, 8), (5, 6)):
            memory, args = guest.previous.fixture(self.rom, options)
            models = [guest.DebrisMatchOracle(w, memory, args, phase, mode).run() for w in (self.words, self.truth, self.raw_words)]
            self.assertEqual(guest.literal(models[0]), guest.literal(models[1]))
            for other in models[1:]:
                self.assertEqual((models[0].calls, models[0].full_packets, models[0].observed, guest.public(models[0].memory)),
                    (other.calls, other.full_packets, other.observed, guest.public(other.memory)))
            mutations += 1
        self.receipt('faults', fired_prefix_pairs=cases, retained_pointer_guest_probe_cases=mutations,
            RNG_retained_packet_mutations_guest_only=True, no_raw_fault_order_or_native_FCSR_claim=True)

    def test_05_all_raw_padder_word_and_binding_corruptions(self):
        raw, rel = source.raw_target(self.obj)
        manifest = self.out / 'qualified-guards.csv'
        before = (self.out / 'before-guards').read_bytes()
        self.assertTrue(manifest.read_bytes().startswith(before))
        text, functions, relocations = parse_object(self.obj)
        f = functions[source.FUNCTION]
        for i in range(205):
            bad = bytearray(raw)
            bad[i * 4] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(bad), rel)
            bad_text = bytearray(text)
            bad_text[f['value'] + i * 4] ^= 1
            with patch.object(padder, 'parse_object', return_value=(bytes(bad_text), functions, relocations)):
                with self.assertRaises(ValueError):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['edge_wrapper_original'], filename=source.OWNER, word_patches_path=manifest)
            bad_rel = {at: list(rows) for at, rows in relocations.items()}
            bad_rel[f['value'] + i * 4] = [('R_MIPS_26', 'wrong_symbol')]
            with patch.object(padder, 'parse_object', return_value=(text, functions, bad_rel)):
                with self.assertRaises(ValueError):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['edge_wrapper_original'], filename=source.OWNER, word_patches_path=manifest)
        for at in rel:
            bad_rel = {k: list(v) for k, v in rel.items()}
            bad_rel[at] = [(rel[at][0][0], 'wrong_symbol')]
            with self.assertRaises(ValueError):
                source.normalize(raw, bad_rel)
        with self.assertRaises(ValueError):
            source.guard_manifest(before + b'\n', raw, rel)
        self.receipt('guards', effective_raw_flips=205, effective_padder_word_flips=205,
            effective_padder_binding_flips=205, changed_external_bindings=len(rel))

    def test_06_effective_compiled_semantic_negatives(self):
        evidence = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED, name)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            failed = False
            for options, mode in ((0, 0), (1, 0), (3, 1), (2, 2), (2, 3)):
                memory, args = guest.previous.fixture(self.rom, options, 0x7FFFFFFF, pattern=1)
                try:
                    self.compare(memory, args, mode, streams=(self.truth, words))
                except AssertionError:
                    failed = True
                    break
            self.assertTrue(failed, name)
            evidence.append(dict(name=name, raw_sha256=row['raw_sha256'], effective=True))
        self.receipt('negatives', compiled=evidence)

    def test_07_native32_initialized_bytes_seeded_holes_and_void_ring_ABI(self):
        from tools.tests import game_six_piece_debris_native as native
        harness = self.out / 'native-harness.c'
        original = native.fixtures(self.rom)
        self.assertEqual(original.count('ringCount++;return 0;}'), 1)
        harness.write_text(original.replace('s32 func_151718F0(', 'void func_151718F0(').replace('ringCount++;return 0;}', 'ringCount++;}'))
        exits = {}
        for name, body, profile, valid in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(native.TYPES + source.DECLARATIONS.replace('#pragma intrinsic (fabsf)\n', '') +
                's32 func_150ADA20(void);\n' + body)
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-msse2', '-mfpmath=sse',
                '-mstackrealign', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie',
                '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation']
            command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error'] if valid else ['-Wno-unused-but-set-variable']
            result = subprocess.run([*command, str(path), str(harness), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            (self.out / ('native-' + name + '-diagnostics.txt')).write_text(result.stderr)
            self.assertEqual(result.returncode, 0, result.stderr[:2000])
            result = subprocess.run([str(path.with_suffix(''))], timeout=60)
            self.assertIn(result.returncode, (0,) if valid else tuple(range(20, 31)), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=1024, separate_translation_units=True, selected_UBSan=True,
            full_initialized_90_bytes_and_seeded_six_holes=True, genuine_void_ring_formal_ABI=True,
            effective_negatives=len(controls()), exits=exits, no_native_initial_indeterminate_or_retained_RNG_mutation_claim=True)

    def test_08_independent_original_rebases_all_bindings_and_full_packets(self):
        raw, rel = source.raw_target(self.obj)
        normalized, moved = source.normalize(raw, rel)
        original = (self.out / 'before-edge_wrapper_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('endlabel ' + source.FUNCTION, 1)[0]
        path = self.out / 'original-rebase.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n.type '
            + source.FUNCTION + ', @function\nglabel ' + source.FUNCTION + '\n' + original
            + '\n.size ' + source.FUNCTION + ', . - ' + source.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        text, functions, bindings = parse_object(path.with_suffix('.o'))
        f = functions[source.FUNCTION]
        original_raw = text[f['value']:f['value'] + f['size']]
        original_rel = {at - f['value']: rows for at, rows in bindings.items() if f['value'] <= at < f['value'] + f['size']}
        self.assertEqual(len(original_raw), 820)
        cases = 0
        globals_ = ('D_800A6F88', 'D_800A6F8C', 'D_800A6F90', 'D_800A6F94', 'D_800A6E90', 'D_800A6F80')
        for delta in (0, 0x10000, -0x10000):
            entry, data_delta = source.ENTRY + delta, delta + 8
            links = {name: int(name[2:], 16) + data_delta for name in globals_}
            links.update(func_1518C900=source.LOOKUP - delta, func_150ADA20=source.RANDOM - delta,
                func_15168BE4=source.SUBMIT - delta, func_151718F0=source.RING - delta)
            mapping = {links[name]: value for name, value in (('func_1518C900', source.LOOKUP), ('func_150ADA20', source.RANDOM),
                ('func_15168BE4', source.SUBMIT), ('func_151718F0', source.RING))}
            streams = [source.link_target(self.out, 'rebase-%X-%d' % (entry, i), data, rows, entry, links)
                for i, (data, rows) in enumerate(((normalized, moved), (original_raw, original_rel), (raw, rel)))]
            self.assertEqual(streams[0], streams[1])
            for options, phase, pattern in itertools.product((0, 1, 2, 3), (0, 8), range(3)):
                initial, args = guest.previous.fixture(self.rom, options, pattern=pattern)
                memory = {a + data_delta if 0x800A6E90 <= a < 0x800A6F98 else a: b for a, b in initial.items()}
                expected = guest.reference(initial, args, phase=phase)
                models = [guest.DebrisMatchOracle(w, memory, args, phase=phase, entry=entry, bindings=mapping).run() for w in streams]
                for model in models:
                    public = {a - data_delta if 0x800A6E90 + data_delta <= a < 0x800A6F98 + data_delta else a: b for a, b in guest.public(model.memory).items()}
                    self.assertEqual((model.calls, model.full_packets, public), expected)
                self.assertEqual(guest.literal(models[0]), guest.literal(models[1]))
                self.assertEqual(models[0].observed, models[2].observed)
                cases += 1
        self.receipt('rebases', independent_original_rebase_sets=3, cases=cases,
            all_six_data_and_all_four_call_bindings_changed=True, all_96_bytes=True)

    def test_09_original_and_current_dispatcher_six_input_ABI(self):
        from tools.tests.test_game_one_shot_timer_match import symbol_rows
        image = (self.out / 'before-elf').read_bytes()
        f = next(r[2] for r in symbol_rows(image) if r[1] == 'func_15170EC4')
        current = image[elf_slot_offset(image, 0x15170EC4, f[2]):][:f[2]]
        original = self.rom[0x19E374:0x19E3FC]
        class StopCaller(guest.DebrisMatchOracle):
            def record_call(model, target):
                if target == source.ENTRY:
                    model.entry_args = model.arguments(6)
                    raise guest.previous.edge.CallBoundary
                return super().record_call(target)
        cases = 0
        for data, state, phase, flags in itertools.product((original, current), (2, 16), (0, 8), (0, 0xABCDEF81)):
            memory, _ = guest.previous.fixture(self.rom)
            guest.put(memory, 0x800BE9F0, state)
            words = list(struct.unpack('>%dI' % (len(data) // 4), data))
            args = (guest.previous.ACTOR, flags, 0x87654321, 0xBAD00007)
            model = StopCaller(words, memory, args, phase=phase, entry=0x15170EC4)
            with self.assertRaises(guest.previous.edge.CallBoundary):
                model.run()
            expected = (args[0], 1, 1, 1, flags & 255, args[2]) if state == 2 else (args[0], 169, 8, 0, flags & 255, args[2])
            self.assertEqual(model.entry_args, expected)
            cases += 1
        self.receipt('caller', original_and_current_dispatcher=True, captures=cases,
            six_physical_input_words=True, matched_neighbor_not_changed=True)

    def test_11_current_consumer_allocator_and_full_96_byte_copy(self):
        image = (self.out / 'before-elf').read_bytes()
        connected = {}
        for address, rom, size in ((source.SUBMIT, 0x196094, 104), (guest.ALLOCATOR, 0x194F18, 112)):
            data = image[elf_slot_offset(image, address, size):][:size]
            self.assertEqual(data, self.rom[rom:rom + size])
            connected.update(zip(range(address, address + size, 4), struct.unpack('>%dI' % (size // 4), data)))
        cases = 0
        for options, mode, pattern, phase, fail in itertools.product((0, 1, 2, 3), (0, 1, 4), range(3), (0, 8), (False, True)):
            memory, args = guest.previous.fixture(self.rom, options, pattern=pattern)
            memory.update({0x30000 + i: (i * 13 + 0xA5) & 255 for i in range(6 * 0x100)})
            _, packets, expected = guest.reference(memory, args, mode, phase=phase)
            copies = []
            for i, packet in enumerate(packets):
                if not struct.unpack_from('>I', packet, 0x40)[0] or fail and (i + 1) % 3 == 0:
                    continue
                record = 0x30000 + i * 0x100
                guest.put(expected, record, 0x10, 1)
                guest.put(expected, record + 1, args[5], 1)
                guest.put(expected, record + 12, args[4], 1)
                for j, b in enumerate(packet):
                    expected[record + 0x90 + j] = b
                copies.append((record + 0x90, packet))
            models = [guest.DebrisMatchOracle(w, memory, args, phase, mode, connected=connected, fail=fail).run()
                for w in (self.words, self.truth, self.raw_words)]
            for model in models:
                self.assertEqual((model.full_packets, model.copies, guest.public(model.memory)), (packets, copies, expected))
            self.assertEqual(guest.literal(models[0]), guest.literal(models[1]))
            self.assertEqual(models[0].observed, models[2].observed)
            cases += 1
        self.receipt('connected', cases=cases, actual_consumer_allocator_words=54,
            all_96_copied_bytes_including_first_residue=True, zero_asset_and_allocation_failure=True,
            lookup_RNG_ring_heap_registration_and_bcopy_bounded_or_opaque=True,
            no_full_gameplay_or_hardware_claim=True)

    def test_12_initial_image_prediction_and_all_frozen_input_corruptions(self):
        source.freeze(self.root, self.out)
        expected = source.expected_inputs(self.root, self.out)
        prediction = {key: hashlib.sha256(data).hexdigest() for key, data in expected.items()}
        initial = dict(prediction, elf=hashlib.sha256(source.slot_expected_image((self.out / 'before-elf').read_bytes(), self.rom)).hexdigest())
        manifest = self.out / 'initial-prediction.json'
        if not manifest.exists():
            self.assertEqual({k: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for k, p in source.PATHS.items()}, source.BASELINE)
            manifest.write_text(json.dumps(initial, indent=2) + '\n')
        self.assertEqual(json.loads(manifest.read_text()), initial)
        qualified = self.out / 'qualified-prediction.json'
        if not qualified.exists():
            qualified.write_text(json.dumps(prediction, indent=2) + '\n')
        self.assertEqual(json.loads(qualified.read_text()), prediction)
        live = {k: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for k, p in source.PATHS.items()}
        self.assertIn(live, (source.BASELINE, dict(source.BASELINE, **prediction)))
        rb = Path.read_bytes
        for key in source.PATHS:
            target = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        self.receipt('prediction', rejected_initial=initial, qualified=prediction, serialization_changed_bytes=84, frozen_inputs=len(source.PATHS),
            expected_changed_bytes=sum(a != b for a, b in zip((self.out / 'before-elf').read_bytes(), expected['elf'])),
            all_capture_corruptions_effective=True, no_metadata_exclusion=True)

    def test_13_rejected_initial_prediction_exact_symbol_cycles_and_two_relinks(self):
        from tools.tests.test_game_one_shot_timer_match import canonical_symbols, symbol_rows
        initial = source.slot_expected_image((self.out / 'before-elf').read_bytes(), self.rom)
        accounted = source.serialize_symbols(initial)
        self.assertNotEqual(initial, accounted)
        self.assertEqual(hashlib.sha256(initial).hexdigest(), json.loads((self.out / 'initial-prediction.json').read_text())['elf'])
        self.assertEqual(sum(a != b for a, b in zip(initial, accounted)), 84)
        self.assertEqual(canonical_symbols(initial), canonical_symbols(accounted))
        names = {'func_150CBCE0', 'D_800A3E2C', 'D_800A6E90', 'D_800A2460', 'osCreateThread'}
        controls = 0
        for at, name, fields, string_at in symbol_rows(initial):
            if name not in names:
                continue
            for position in (at, at + 4, string_at):
                bad = bytearray(initial)
                bad[position] ^= 1
                with self.assertRaises(ValueError):
                    source.serialize_symbols(bytes(bad))
                controls += 1
        for index in (1, 2):
            target = self.out / ('independent-relink-%d.elf' % index)
            command = ['mips-linux-gnu-ld', '-T', 'build/conker.ld', '-Map', str(target.with_suffix('.map').relative_to(self.root / 'conker')),
                '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
                '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch', '-o', str(target.relative_to(self.root / 'conker'))]
            result = subprocess.run(command, cwd=self.root / 'conker', capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr[:1000])
            self.assertEqual(hashlib.sha256(target.read_bytes()).digest(), hashlib.sha256(accounted).digest())
            self.assertEqual(target.read_bytes(), accounted)
        self.receipt('serialization', rejected_initial_sha256=hashlib.sha256(initial).hexdigest(),
            qualified_sha256=hashlib.sha256(accounted).hexdigest(), exact_amendment_bytes=84,
            unchanged_named_definitions=True, exact_record_and_string_cycles=2,
            independent_full_relinks=2, effective_symbol_record_name_corruptions=controls,
            no_section_symbol_or_metadata_exclusions=True)
