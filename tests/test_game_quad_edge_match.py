"""Closed emitter normalization, literal guest state and defined native C checks."""
import ast
import csv
import hashlib
import inspect
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_quad_edge_match as source
from tools.experiments import game_quad_edge_loop_values as proof
from tools.experiments import game_quad_edge_frame as frame
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools import pad_generated_object as padder
from tools.tests import test_game_quad_edge_emitter as edge
from tools.tests import test_game_quad_edge_frame as fitting
from tools.tests import test_game_quad_edge_path_recovery as wrapper
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset


class QuadEdgeMatchTests(unittest.TestCase):
    test_10_all_801_archive_fingerprints = edge.QuadEdgeEmitterTests.test_10_all_original_801_archive_fingerprints

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>266I', cls.rom, source.ROM))
        cls.table = cls.rom[0x2316B4:0x2316B4 + 33]

    def receipt(self, name, **values):
        (self.out / ('qualification-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_actual_owner_padding_neighbors_and_closed_operation_plan(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual((self.row['raw_differences'], self.row['guards_added'], self.row['identity_guards']), (137, 266, 129))
        raw, rel = source.raw_target(self.obj)
        self.assertEqual((hashlib.sha256(raw).hexdigest(), rel), (source.RAW_SHA256, source.RELOCATIONS))
        before, diagnostics = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(before), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'])
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']])
            relative = lambda obj, f: {at - f['value']: rows for at, rows in obj[2].items()
                if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(old, f), relative(new, g))
        self.assertEqual(normalized_pools(before), normalized_pools(self.obj))
        neighbors = len(old[1]) - 1
        self.assertEqual(neighbors, 29)
        normalized, moved = source.normalize(raw, rel)
        a, b = list(struct.unpack('>266I', raw)), list(struct.unpack('>266I', normalized))
        self.assertEqual(sorted(i for i in source.ORDER if isinstance(i, int)),
            [i for i in range(266) if i not in (66, 72, 145)])
        for at, old in enumerate(source.ORDER):
            if isinstance(old, str):
                self.assertIn((at, old), ((142, 'store-edge'), (151, 'load-edge'), (156, 'store-edge')))
                self.assertEqual(b[at], 0x8FA5018C if old == 'load-edge' else 0xAFA5018C)
                continue
            mask = sum(31 << shift for shift in source.register_fields(a[old]))
            value = a[old]
            if old == 75:
                value = value & ~65535 | 2
            if value >> 21 & 31 == 29 and value >> 26 in (35, 43) and value & 65535 in (0x108, 0xE0):
                value = value & ~65535 | {0x108: 0x104, 0xE0: 0xF4}[value & 65535]
            if value >> 26 in (4, 5, 21, 22):
                mask |= 65535
            self.assertEqual(value & ~mask, b[at] & ~mask, (at, old))
        self.assertEqual(set(rel), {old * 4 for old in source.ORDER if isinstance(old, int) and old * 4 in rel})
        rows = list(csv.DictReader(io.StringIO((self.out / 'qualified-guards.csv').read_text())))
        target = [row for row in rows if row['function'] == source.FUNCTION]
        self.assertEqual(len(target), 266)
        self.assertTrue(all(row['omit'] == 'false' and not row['insert_after'] for row in target))
        self.assertEqual(len(moved), 12)
        self.receipt('shape', retained_operations=263, omitted_move_constant_NOP=3,
            materialized_unescaped_edge_operations=3, changed_guards=137, identity_guards=129,
            unchanged_neighbors=neighbors,
            raw_not_byte_exact=True, full_owner_actual_padding_exact=True)

    def test_02_conditional_loop_proof_and_effective_dependency_negatives(self):
        result = proof.prove(self.raw_words, self.words)
        self.assertEqual((result['outer_cases'], result['induction_steps']), (24, 24))
        effective = []
        for name, old, replacement in (
                ('wrong-increment', 0x26940001, 0x26940002),
                ('wrong-width', 0x0057001B, 0x0056001B),
                ('wrong-preset-byte', 0x93AB019F, 0x93AB019C),
                ('wrong-scale', 0xC7BC01A0, 0xC7BC0194),
                ('wrong-context', 0x8FA901B4, 0x8FA901A4),
                ('wrong-flags', 0x93B801B3, 0x93B801B0)):
            words = list(self.words)
            words[words.index(old)] = replacement
            with self.assertRaises(ValueError, msg=name):
                proof.prove(self.raw_words, words)
            effective.append(name)
        legal = list(self.words)
        legal[12], legal[13] = legal[13], legal[12]
        proof.prove(self.raw_words, legal)
        self.receipt('proof', **result, effective_normalized_dependency_controls=effective,
            legal_independent_save_schedule_accepted=True)

    def test_03_complete_literal_states_all_packets_and_guest_singleton(self):
        cases, visits = 0, set()
        for kind, counts, scale, randoms, phase, mode in itertools.product(range(3),
                ((-1, 0), (0, 0), (1, 1), (2, 3), (4, 2), (7, -1)),
                (-0.5, 0.25, 1., 64.), edge.SAMPLES, (0, 8), range(4)):
            memory, args = edge.fixture(self.table, kind, counts, scale, phase, pattern=kind)
            expected, calls, packets, trapped = edge.reference(memory, args, randoms, phase, mode)
            self.assertFalse(trapped)
            models = [edge.EdgeOracle(w, memory, args, randoms, phase, mode).run() for w in (self.words, self.truth)]
            self.assertEqual(edge.state(models[0]), edge.state(models[1]))
            self.assertEqual(models[0].calls, calls)
            self.assertEqual(models[0].packets, packets)
            self.assertEqual(edge.public(models[0].memory), edge.public(expected))
            visits |= models[0].visits
            cases += 1
        self.assertEqual(cases, 2304)
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 1064, 4)) - {source.ENTRY + 0x2B4, source.ENTRY + 0x3B0})
        self.receipt('private', pairs=cases, full_RAM_GPR_FPR_HI_LO_events_calls_and_access_count_equal=True,
            singleton_and_incoming_home_mutations_guest_only=True, all_non_BREAK_words_visited=True)

    def test_04_fired_fault_prefixes_traps_and_bounded_guest_aliases(self):
        faults = aliases = traps = 0
        for phase, counts in itertools.product((0, 8), ((0, 0), (2, 3))):
            memory, args = edge.fixture(self.table, counts=counts, phase=phase)
            whole = edge.EdgeOracle(self.truth, memory, args, edge.SAMPLES[2], phase).run()
            for cut in range(whole.accesses):
                models = [edge.EdgeOracle(w, memory, args, edge.SAMPLES[2], phase, fault=cut) for w in (self.words, self.truth)]
                for model in models:
                    with self.assertRaises(edge.AccessFault):
                        model.run()
                self.assertEqual(edge.state(models[0]), edge.state(models[1]))
                faults += 1
        for phase, scale, counts in itertools.product((0, 8), (0., 0.001), ((0, 0), (2, 2))):
            memory, args = edge.fixture(self.table, counts=counts, scale=scale, phase=phase)
            models = [edge.EdgeOracle(w, memory, args, edge.SAMPLES[2], phase) for w in (self.words, self.truth)]
            expected = edge.reference(memory, args, edge.SAMPLES[2], phase)
            for model in models:
                if expected[3]:
                    with self.assertRaises(edge.DivideZeroTrap):
                        model.run()
                else:
                    model.run()
            self.assertEqual(edge.state(models[0]), edge.state(models[1]))
            self.assertEqual(models[0].calls, expected[1])
            traps += 1
        for phase, offset in itertools.product((0, 8), (-0x180, -0x100, -0x80, -0x60, -0x40, 0, 0x30)):
            memory, args = edge.fixture(self.table, counts=(2, 3), phase=phase)
            args = (edge.STACK + phase + offset, *args[1:])
            models = [edge.EdgeOracle(w, memory, args, edge.SAMPLES[2], phase).run() for w in (self.words, self.truth)]
            self.assertEqual(edge.state(models[0]), edge.state(models[1]))
            aliases += 1
        self.receipt('faults-aliases-traps', fired_prefix_pairs=faults, guest_aliases=aliases,
            trap_and_empty_pairs=traps, both_integer_BREAK7_sites=True,
            exact_private_state=True, not_valid_native_C_alias_or_exception_claims=True)

    def test_05_every_raw_word_and_binding_corruption_actual_padder(self):
        raw, rel = source.raw_target(self.obj)
        parsed = parse_object(self.obj)
        start = parsed[1][source.FUNCTION]['value']
        manifest = self.out / 'qualified-guards.csv'
        for i in range(266):
            changed = bytearray(raw)
            changed[i * 4] ^= 1
            with self.assertRaisesRegex(ValueError, 'Unknown emitter compiler'):
                source.normalize(bytes(changed), rel)
            text = bytearray(parsed[0])
            text[start + i * 4] ^= 1
            with patch.object(padder, 'parse_object', return_value=(bytes(text), parsed[1], parsed[2])):
                with self.assertRaisesRegex(ValueError, 'stale word patch'):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'],
                        filename=source.OWNER, word_patches_path=manifest)
            altered = dict(parsed[2])
            altered[start + i * 4] = [('R_MIPS_32', 'wrong')]
            with patch.object(padder, 'parse_object', return_value=(parsed[0], parsed[1], altered)):
                with self.assertRaisesRegex(ValueError, 'relocation'):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'],
                        filename=source.OWNER, word_patches_path=manifest)
        for i in rel:
            altered = dict(rel)
            altered[i] = [('R_MIPS_26', 'wrong')]
            with self.assertRaisesRegex(ValueError, 'Unknown emitter compiler'):
                source.normalize(raw, altered)
        with self.assertRaisesRegex(ValueError, 'guard predecessor'):
            source.guard_manifest((self.out / 'before-guards').read_bytes() + b'\n', raw, rel)
        self.receipt('corruptions', raw_words_rejected=266, actual_padder_word_flips_rejected=266,
            actual_padder_binding_flips_rejected=266, changed_external_bindings_rejected=len(rel),
            guard_history_closed=True)

    def test_06_native32_correct_word_preset_ABI_O2_O0_and_negatives(self):
        method = edge.QuadEdgeEmitterTests.test_06_native32_valid_conversion_domain_O2_O0_and_controls
        # Keep triple-quoted C at its original indentation; dedent sees those
        # literal lines as column zero and cannot dedent the Python method.
        tree = ast.parse('class NativeFixture:\n' + inspect.getsource(method))
        assignment = next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'harness' for target in node.targets))
        harness = ast.literal_eval(assignment.value)
        def once(text, old, new):
            self.assertEqual(text.count(old), 1)
            return text.replace(old, new)
        harness = once(harness, 'invoke)(f32*,f32,f32,u8,f32', 'invoke)(f32*,f32,f32,s32,f32')
        harness = once(harness, 'invoke(vertices,12.25f,-3.75f,129,',
            'invoke(vertices,12.25f,-3.75f,(s32)0xABCD0081u,')
        prototype = source.build.body((self.out / 'before-preset_owner').read_text(), 'func_1516D4E8').split('{', 1)[0]
        factory = prototype + '{u32 v[31]={' + ','.join('arg%d' % i for i in range(31)) + '''};u32 i;
 order[orderCount++]=2;for(i=0;i<31;i++)captured[packetCount][i]=v[i];packetCount++;
 if(mode==2&&packetCount==1){D_800A6E84=513.0f;D_8008CC0C.values[0]=1;}}
'''
        controls = {name: body for name, body in fitting.controls(source.SELECTED).items()
            if name not in ('integer-table', 'integer-vertices', 'wide-color')}
        controls['wrong-preset-byte'] = source.SELECTED.replace('(u8)preset', '(u8)(preset >> 8)')
        exits = {}
        for name, body, profile, valid in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in controls.items()]:
            self.assertTrue(valid or body != source.SELECTED)
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace('DECLARATIONS', source.previous.previous.DECLARATIONS).replace(
                'FACTORY', factory).replace('BODY', body))
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-msse2', '-mfpmath=sse',
                '-mstackrealign', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie',
                '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation', '-Wno-unused-variable']
            if valid:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            result = subprocess.run([*command, str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            self.assertIn(result.returncode, (0,) if valid else (10, 11, 12, 13, 14), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=3600, UBSan_selected=True, matching_s32_preset_function_pointer=True,
            high_word_preset=0xABCD0081, formally_projected_31_factory_fields=True,
            effective_native_negative_count=len(controls), exits=exits, guest_stack_fault_and_FP_environment_excluded=True)

    def test_07_independent_original_raw_and_normalized_rebases(self):
        raw, rel = source.raw_target(self.obj)
        normalized, moved = source.normalize(raw, rel)
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        path = self.out / 'independent-original.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n'
            '.type ' + source.FUNCTION + ', @function\nglabel ' + source.FUNCTION + '\n' + original
            + '\n.size ' + source.FUNCTION + ', . - ' + source.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
            check=True, capture_output=True)
        tx, fs, rs = parse_object(path.with_suffix('.o'))
        f = fs[source.FUNCTION]
        original_raw = tx[f['value']:f['value'] + f['size']]
        original_rel = {at - f['value']: rows for at, rows in rs.items() if f['value'] <= at < f['value'] + f['size']}
        pairs = 0
        for number, delta, table, scale in ((0, 0, edge.TABLE, edge.source.SCALE),
                (1, 0x10000, 0x80207FF4, 0x80318004), (2, -0x10000, 0x80418004, 0x80507FFC)):
            entry, rng, factory = source.ENTRY + delta, edge.source.RANDOM - delta, edge.source.FACTORY - delta
            bindings = dict(func_150ADA20=rng, func_1516D4E8=factory,
                D_8008CBF4=table, D_8008CC00=table + 12, D_8008CC0C=table + 24, D_800A6E84=scale)
            bodies = [source.link_target(self.root, self.out, '%s-rebase-%d' % (name, number), body, bindings_rel, entry, bindings)
                for name, body, bindings_rel in (('original', original_raw, original_rel), ('normalized', normalized, moved), ('raw', raw, rel))]
            self.assertEqual(bodies[0], bodies[1])
            if number == 0:
                self.assertEqual(bodies, [self.truth, self.words, self.raw_words])
            with patch.multiple(edge.source, ENTRY=entry, RANDOM=rng, FACTORY=factory, SCALE=scale), patch.object(edge, 'TABLE', table):
                for kind, mode in itertools.product(range(3), range(4)):
                    memory, args = edge.fixture(self.table, kind, counts=(2, 3))
                    expected = edge.reference(memory, args, edge.SAMPLES[2], mode=mode)
                    models = [edge.EdgeOracle(words, memory, args, edge.SAMPLES[2], mode=mode, entry=entry).run() for words in bodies]
                    self.assertEqual(edge.state(models[0]), edge.state(models[1]))
                    for model in models:
                        self.assertEqual(model.calls, expected[1])
                        self.assertEqual(model.packets, expected[2])
                    pairs += 1
        self.receipt('rebases', independent_three_stream_links=3, private_pairs=pairs, raw_public_pairs=pairs,
            all_266_words_all_four_calls_four_data_HI_LO_pairs=True, signed_low_carry_crossed=True)

    def test_08_current_wrapper_emitter_factory_allocator_chain(self):
        image = (self.out / 'before-elf').read_bytes()
        wrapper_words = list(struct.unpack('>61I', image[elf_slot_offset(image, 0x151717FC, 244):][:244]))
        self.assertEqual(wrapper_words, list(struct.unpack_from('>61I', self.rom, 0x19ECAC)))
        lower = {}
        for address, rom, count in ((edge.source.FACTORY, 0x19A998, 100), (0x15167A68, 0x194F18, 28)):
            raw = image[elf_slot_offset(image, address, count * 4):][:count * 4]
            self.assertEqual(raw, self.rom[rom:rom + count * 4])
            lower.update(zip(range(address, address + count * 4, 4), struct.unpack('>%dI' % count, raw)))
        pairs = 0
        for kind, counts, phase, mode, fail in itertools.product(range(3), ((0, 0), (2, 3), (4, 2)), (0, 8), range(4), (False, True)):
            memory, args = wrapper.fixture(pattern=1)
            args = (*args[:6], kind, args[7], *counts, edge.bits(1.0), *args[11:])
            memory.update({edge.TABLE + i: value for i, value in enumerate(self.table)})
            memory.update({0x30000 + i: (i * 13 + 0xA5) & 255 for i in range(4096)})
            models = []
            for words in (self.words, self.truth):
                connected = dict(lower)
                connected.update(zip(range(source.ENTRY, source.ENTRY + 1064, 4), words))
                models.append(edge.EdgeOracle(wrapper_words, memory, args, edge.SAMPLES[2], phase, mode,
                    connected=connected, entry=0x151717FC, allocation_fail=fail).run())
            self.assertEqual(edge.state(models[0]), edge.state(models[1]))
            pairs += 1
        self.receipt('chain', pairs=pairs, actual_current_wrapper_words=61, staged_emitter_words=266,
            actual_current_factory_allocator_words=128, complete_literal_state_equal=True,
            lower_heap_and_registration_opaque=True, full_gameplay_not_claimed=True)

    def test_09_frozen_inputs_preinstall_prediction_and_every_capture_flip(self):
        source.freeze(self.root, self.out)
        expected = source.expected_inputs(self.root, self.out)
        before = (self.out / 'before-elf').read_bytes()
        self.assertEqual(len(before), len(expected['elf']))
        slot = elf_slot_offset(before, source.ENTRY, 1064)
        self.assertEqual(expected['elf'][slot:slot + 1064], self.rom[source.ROM:source.ROM + 1064])
        for key, path in source.PATHS.items():
            if key not in expected:
                self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), source.BASELINE[key], key)
        rb = Path.read_bytes
        for key in source.PATHS:
            target = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        self.receipt('predicted-image', after={key: hashlib.sha256(value).hexdigest() for key, value in expected.items()},
            changed_ELF_bytes=sum(a != b for a, b in zip(before, expected['elf'])),
            protected_inputs=63, unaffected_current_inputs=60, symbol_extent=[12, 1064], target_slot=1064,
            actual_installed_image_requires_separate_gate=True)

    def test_11_effective_compiled_guest_controls(self):
        controls = fitting.controls(source.SELECTED)
        with patch.object(edge.source, 'PATHS', source.PATHS), patch.object(edge.source, 'BASELINE', source.BASELINE), \
                patch.object(edge.source, 'SELECTED', source.SELECTED), patch.object(edge, 'controls', return_value=controls):
            edge.QuadEdgeEmitterTests.test_04_effective_compiled_semantic_controls(self)

    def test_12_live_count_snapshot_and_dead_edge_home_poison(self):
        class Writer(edge.EdgeOracle):
            def hook(model, target):
                super().hook(target)
                if target == edge.source.FACTORY and model.factory_count == 1:
                    model.put(model.r[29] + model.offset, model.value, 4)

        results = {}
        for name, offset, value, counts, size in (
                ('live-count', 0x138, 3, (2, 2), 9), ('dead-edge', 0x18C, 2, (2, 3), 10)):
            memory, args = edge.fixture(self.table, counts=counts)
            models = []
            for words in (self.words, self.truth, self.raw_words):
                model = Writer(words, memory, args, edge.SAMPLES[2])
                model.offset, model.value = offset, value
                models.append(model.run())
            self.assertEqual(edge.state(models[0]), edge.state(models[1]))
            self.assertEqual(models[0].packets, models[2].packets)
            self.assertEqual(len(models[0].packets), size)
            results[name] = size
        memory, args = edge.fixture(self.table, counts=(2, 2))
        wanted = Writer(self.truth, memory, args, edge.SAMPLES[2])
        wanted.offset, wanted.value = 0x138, 3
        wanted.run()
        inline = frame.candidates()['inline-fraction'].replace('f32 originZ, u8 preset', 'f32 originZ, s32 preset').replace(
            'presetByte = preset;', 'presetByte = (u8)preset;')
        controls = {'cached-count': source.SELECTED.replace('(&count)[0]', 'count'), 'recomputed-reciprocal': inline}
        wrong = {}
        for name, body in controls.items():
            self.assertNotEqual(body, source.SELECTED)
            _, words, row = source.previous.measure(self.root, self.out, 'negative-home-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            model = Writer(words, memory, args, edge.SAMPLES[2])
            model.offset, model.value = fitting.count_home(words) or 0x138, 3
            model.run()
            self.assertNotEqual(model.packets, wanted.packets)
            wrong[name] = len(model.packets)
        self.assertEqual(wrong, {'cached-count': 8, 'recomputed-reciprocal': 9})
        self.receipt('home-poisons', literal_original_normalized_state_equal=True, raw_public_equal=True,
            original_packet_counts=results, effective_negative_packet_counts=wrong,
            unescaped_private_writes_are_guest_only_not_C_provider_contract=True)


if __name__ == '__main__':
    unittest.main()
