"""Direct orthographic setup words, ABI, signed defaults and live storage."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_view_orthographic_setup as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function, nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests import game_view_orthographic_oracle as model
from tools.tests import game_view_orthographic_native as native
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_callback_update_match import external
from tools.tests import view_orthographic_setup_checkpoint as checkpoint
from tools.tests import view_pending_queue_checkpoint
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout

SERIALIZATION = (
    (('D_800A2C20', 'D_80090850', 'D_80090420'), (1, 2, 0),
     ((0x800A2C20, 0, 16, 0, 65521), (0x80090850, 0, 16, 0, 6), (0x80090420, 0, 16, 0, 6))),
    (('D_800CC26D', 'D_800DBEF0', 'D_8008A1F0'), (2, 0, 1),
     ((0x800CC26D, 0, 16, 0, 65521), (0x800DBEF0, 0, 16, 0, 65521), (0x8008A1F0, 0, 16, 0, 6))),
    (('D_800D2040', 'D_8008A470'), (1, 0),
     ((0x800D2040, 0, 16, 0, 65521), (0x8008A470, 0, 16, 0, 6))),
)


def expected_image(before, rom):
    expected = bytearray(before)
    at = elf_slot_offset(before, source.ENTRY, 184)
    expected[at:at + 184] = rom[source.ROM:source.ROM + 184]
    rows = [(offset, fields) for offset, name, fields, _ in machine.symbol_rows(before) if name == source.FUNCTION]
    assert len(rows) == 1 and rows[0][1][1:] == (source.ENTRY, 12, 18, 0, 5)
    struct.pack_into('>I', expected, rows[0][0] + 8, 184)
    with patch.object(machine, 'SERIALIZATION', SERIALIZATION):
        machine.apply_burst_symbol_serialization(expected)
    return bytes(expected)


class ViewOrthographicSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)
        cls.before = (cls.out / 'before-owner').read_text()
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.obj, cls.diagnostics = build.compile_owner(cls.root, cls.out, source.recover(cls.before), 'qualified')
        cls.raw, cls.functions, cls.relocations = parse_object(cls.obj)
        cls.data, _ = build.link_owner(cls.root, cls.out, cls.obj, source.OWNER)
        cls.info = cls.functions[source.FUNCTION]
        cls.words = list(struct.unpack_from('>46I', cls.data, cls.info['value']))
        cls.retail = list(struct.unpack_from('>46I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    @classmethod
    def assemble(cls, assembly, label):
        path = cls.out / (label + '.s')
        path.write_text('.include "' + str(cls.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + assembly)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], capture_output=True, check=True)
        return obj

    def test_01_direct_body_neighbors_pools_and_both_padders(self):
        self.assertEqual((self.diagnostics, self.info['size'], self.words), ('', 184, self.retail))
        self.assertEqual(self.words[0], 0x27BDFFD8)
        self.assertEqual(self.words[6], 0xAFA40028)
        old, diagnostics = build.compile_owner(self.root, self.out, self.before, 'before-owner')
        raw, functions, relocations = parse_object(old)
        relative = lambda rows, info: {at - info['value']: uses for at, uses in rows.items() if info['value'] <= at < info['value'] + info['size']}
        for name in set(functions) - {source.FUNCTION}:
            a, b = functions[name], self.functions[name]
            self.assertEqual(a['size'], b['size'], name)
            self.assertEqual(raw[a['value']:a['value'] + a['size']], self.raw[b['value']:b['value'] + b['size']], name)
            self.assertEqual(relative(relocations, a), relative(self.relocations, b), name)
        self.assertEqual((diagnostics, normalized_pools(old)), ('', normalized_pools(self.obj)))
        for name, assembly in (('primary', pad_c_object.emit_padded_assembly(self.obj, self.root / source.PATHS['layout'],
                source.OWNER, word_patches_path=self.out / 'before-guards')),
                ('generated', emit_padded_assembly(self.obj, self.root / source.PATHS['original'],
                    filename=source.OWNER, word_patches_path=self.out / 'before-guards'))):
            data, functions = build.link_owner(self.root, self.out, self.assemble(assembly, name), source.OWNER)
            at = functions[source.FUNCTION]['value']
            self.assertEqual(data[at:at + 184], struct.pack('>46I', *self.retail))
        screens = json.loads((self.out / 'screens.json').read_text())
        self.assertEqual(len(screens), 20)
        self.assertEqual([row['label'] for row in screens if not row['differences']],
            ['direct', 'direct-scale', 'far-pointer-direct', 'far-pointer-direct-scale'])
        self.assertTrue(all(row['bytes'] == 184 and row['frame'] == 40 and row['diagnostics'] == '' for row in screens))
        self.receipt('owner', direct_words=46, frame=40, unused_incoming_home='entrySP', guards=0,
            unchanged_raw_neighbors=len(functions) - 1, both_padders=True, screens=20, raw_exact_forms=4,
            header_profile_progress_guard_changes=0)

    def test_02_independent_original_and_generated_rebases(self):
        original = (self.out / 'before-original').read_text()
        original = 'glabel ' + source.FUNCTION + original.split('glabel ' + source.FUNCTION, 1)[1].split('endlabel ' + source.FUNCTION, 1)[0] + 'endlabel ' + source.FUNCTION + '\n'
        original_obj = self.assemble(original, 'independent-original')
        emitted, unresolved = emit_function(self.raw, self.info, self.relocations, source.FUNCTION,
            nm_anchors(self.root / source.PATHS['elf']))
        self.assertFalse(unresolved)
        generated_obj = self.assemble(emitted, 'independent-generated')
        used = {name for at, rows in self.relocations.items() if self.info['value'] <= at < self.info['value'] + 184 for _, name in rows}
        anchors = nm_anchors(self.root / source.PATHS['elf'])
        for delta in (0, 0x1000000):
            outputs = []
            for label, obj in (('original', original_obj), ('generated', generated_obj)):
                script = self.out / ('%s-%X.ld' % (label, delta))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + delta))
                elf = script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % (name, anchors[name] + delta) for name in sorted(used)],
                    '-o', str(elf), str(obj)], capture_output=True, check=True)
                self.assertEqual(nm_anchors(elf)[source.FUNCTION], source.ENTRY + delta)
                outputs.append(sections(elf)['.text'][1][:184])
            self.assertEqual(outputs[0], outputs[1])
            if not delta:
                self.assertEqual(outputs[0], struct.pack('>46I', *self.retail))

    def compare(self, memory, unused=0, mode=0, phase=0):
        expected, packet = model.reference(memory, mode)
        instances = [model.SetupOracle(words, memory, unused, mode, phase).run() for words in (self.retail, self.words)]
        for instance in instances:
            self.assertEqual(external(instance.memory), external(expected))
            self.assertEqual(instance.calls, [(model.ORTHO, packet)])
            self.assertEqual(model.read(instance.memory, machine.STACK + phase), unused)
        self.assertEqual(machine.complete_state(instances[0]), machine.complete_state(instances[1]))
        return instances

    def test_03_signed_defaults_live_field_aliases_and_full_return_state(self):
        cases = 0
        coverage = set()
        for case in model.mock_cases():
            for phase in (0, 8):
                instances = self.compare(case['memory'], case['unused'], case['mode'], phase)
                coverage.update(instances[0].visits)
                cases += 1
        for near, far in itertools.product(model.SHORTS, repeat=2):
            self.compare(model.fixture(near, far), 0xFEDCBA98)
            cases += 1
        self.assertEqual(coverage, set(range(source.ENTRY, source.ENTRY + 184, 4)))
        self.receipt('guest', cases=cases, all_46_words_reached=True, full_modeled_return_state=True,
            signed16_boundaries_seven_view_aliases_and_all_eight_argument_words=True,
            unused_home_width_preserved=True, raw_FP_payload_transport_not_hardware_FCSR=True)

    def test_04_every_fired_root_access_prefix(self):
        prefixes = 0
        for view, mode, phase in itertools.product((0, 2, 3, 5), (0, 1), (0, 8)):
            memory = model.fixture(-32768, 32767, view=view)
            full = model.SetupOracle(self.retail, memory, 0x87654321, mode, phase).run()
            self.assertEqual(full.accesses, 17)
            for cut in range(full.accesses):
                instances = []
                for words in (self.retail, self.words):
                    instance = model.SetupOracle(words, memory, 0x87654321, mode, phase, fault=cut)
                    with self.assertRaises(faults.AccessBoundary):
                        instance.run()
                    instances.append(instance)
                self.assertEqual(machine.complete_state(instances[0]), machine.complete_state(instances[1]))
                self.assertEqual((instances[0].current_pc, instances[0].delay_of), (instances[1].current_pc, instances[1].delay_of))
                prefixes += 1
        self.receipt('prefixes', fired_prefixes=prefixes, full_state_PC_and_delay_identity=True,
            bounded_helper_atomic_no_portable_C_fault_or_hardware_exception_claim=True)

    def test_05_actual_sdk_chain_in_finite_exact_conversion_domain(self):
        connected = {}
        for key, label, targets in (('callee', 'orthographic-sdk', ((model.ORTHO_FLOAT, 85), (model.ORTHO, 27))),
                ('converter', 'matrix-sdk', ((model.CONVERTER, 64), (model.IDENTITY, 34)))):
            obj, diagnostics = source.compile_sdk(self.root, self.out, (self.out / ('before-' + key)).read_text(), source.PATHS[key], label)
            data, functions = build.link_owner(self.root, self.out, obj, label)
            self.assertEqual(diagnostics, 'uld:\nWarning: -Xfullwarn not supported.\n')
            for entry, count in targets:
                name = {model.ORTHO_FLOAT: 'func_151EF800', model.ORTHO: 'func_151EF954', model.CONVERTER: 'guMtxF2L2', model.IDENTITY: 'func_151EFE00'}[entry]
                words = list(struct.unpack_from('>%dI' % count, data, functions[name]['value']))
                self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, entry - 0x15000000 + 0x2D4B0)))
                connected.update({entry + i * 4: word for i, word in enumerate(words)})
        cases = 0
        for width, height, coefficient, phase in itertools.product((0.5, 1, 2, 4), (0.5, 1, 2, 4), (3, 5, 9), (0, 8)):
            memory = model.finite_sdk_fixture(width, height, coefficient)
            expected, packet = model.sdk_reference(memory)
            instances = [model.SetupOracle(words, memory, 0x87654321, phase=phase, connected=connected).run() for words in (self.retail, self.words)]
            for instance in instances:
                self.assertEqual(external(instance.memory), external(expected))
                self.assertEqual([entry for entry, _ in instance.calls], [model.ORTHO, model.ORTHO_FLOAT, model.IDENTITY, model.CONVERTER])
                self.assertEqual(instance.calls[0][1], packet)
                matrix = instance.calls[1][1][0]
                self.assertEqual(instance.calls[1][1][1:], packet[1:])
                self.assertEqual(instance.calls[2][1], (matrix,))
                self.assertEqual(instance.calls[3][1], (matrix, model.MATRIX))
            self.assertEqual(machine.complete_state(instances[0]), machine.complete_state(instances[1]))
            cases += 1
        self.receipt('sdk', cases=cases, freshly_compiled_original_sdk_words=210, actual_whole_four_function_chain=True,
            all_matrix_bytes_and_argument_packets=True, exactly_integral_scaled_conversion_domain=True,
            converter_is_distinct_truncating_guMtxF2L2=True, no_hardware_or_general_FP_exception_claim=True)

    def test_06_frozen_inputs_and_actual_direct_call_sites(self):
        source.freeze(self.root, self.out)
        for key, words in (('caller_init', ('0D442C1C', '8FA4002C')), ('caller_scene', ('0D442C1C', '00002025'))):
            text = (self.out / ('before-' + key)).read_text()
            at = text.index('jal        ' + source.FUNCTION)
            lines = text[:at].splitlines()[-1] + text[at:].splitlines()[0]
            self.assertIn(words[0], lines)
            self.assertIn(words[1], text[at:].splitlines()[1])
        rb = Path.read_bytes
        for key in source.BASELINE:
            path = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'immutable orthographic setup input'):
                    source.freeze(self.root, self.out)

    def test_07_actual_native32_setup_and_sdk_with_effective_controls(self):
        rows = native.vectors()
        self.assertEqual(len(rows), 1056)
        self.assertEqual(native.run(self.out, 'selected', rows), [0, 0])
        for label, body, row, status in native.negative_cases(rows):
            self.assertNotEqual(body, source.BODY)
            self.assertEqual(native.run(self.out, label, [row], body), [status, status])
        self.receipt('native', cases_per_profile=1056, profiles=['O2', 'O0'], mock_cases=1008, actual_whole_SDK_cases=48,
            all_banks_config_output_canaries_and_eight_argument_words=True, four_semantic_controls_effective=True,
            actual_SDK_domain_finite_exact_scaled_integer=True, native_endian_normalization_and_bounded_aliases=True,
            unused_home_private_frame_faults_and_hardware_FCSR_not_claimed=True)

    def test_08_effective_compiled_IDO_semantic_controls(self):
        for label, body, row, _ in native.negative_cases(native.vectors()):
            obj, diagnostics = build.compile_owner(self.root, self.out, source.recover(self.before, body), 'negative-' + label)
            data, functions = build.link_owner(self.root, self.out, obj, source.OWNER)
            info = functions[source.FUNCTION]
            words = list(struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value']))
            self.assertEqual(diagnostics, '')
            instance = model.SetupOracle(words, row['memory'], row['unused'], row['mode']).run()
            self.assertNotEqual((external(instance.memory), instance.calls), (external(row['expected']), [(model.ORTHO, row['packet'])]), label)

    def test_09_installed_source_progress_guards_and_independent_closed_image(self):
        source.freeze(self.root, self.out)
        expected = {'owner': source.recover(self.before).encode(),
            'elf': expected_image((self.out / 'before-elf').read_bytes(), self.rom)}
        for key, path in source.PATHS.items():
            current = view_pending_queue_checkpoint.previous_input((self.root / path).read_bytes(), path, self.root)
            self.assertEqual(current, expected[key] if key in expected else (self.out / ('before-' + key)).read_bytes(), key)
        self.assertEqual(view_pending_queue_checkpoint.previous_input((self.root / source.PATHS['owner']).read_text().encode(),
            source.PATHS['owner'], self.root), expected['owner'])
        self.assertEqual(hashlib.sha256(expected['elf']).hexdigest(), checkpoint.AFTER['elf'])
        data = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('image', ELF_sha256=hashlib.sha256((self.root / source.PATHS['elf']).read_bytes()).hexdigest(),
            orthographic_checkpoint_ELF_sha256=checkpoint.AFTER['elf'],
            historical_orthographic_changed_bytes=sum(a != b for a, b in zip((self.out / 'before-elf').read_bytes(), expected['elf'])),
            code_extent=[12, 184], exact_symbol_string_groups=3, non_target_definition_changes=0,
            every_other_ELF_byte_fixed=True, guards_headers_profiles_progress_and_callers_fixed=True,
            protected_data=data)

    def test_10_effective_current_and_immutable_image_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key, relative in source.PATHS.items():
            path = self.root / relative
            bad = rb(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p, value=bad: value if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_09_installed_source_progress_guards_and_independent_closed_image()
        path = self.root / source.PATHS['owner']
        with patch.object(Path, 'read_text', lambda p, *a, **k: rt(p, *a, **k) + '\n' if p == path else rt(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_09_installed_source_progress_guards_and_independent_closed_image()
        path = self.root / source.PATHS['elf']
        current = rb(path)
        names = {name for group, _, _ in SERIALIZATION for name in group}
        rows = machine.symbol_rows(current)
        offsets = [offset for at, name, _, string in rows if name in names for offset in (at, string)]
        target = next(row for row in rows if row[1] == source.FUNCTION)
        offsets.extend((target[0] + 8, target[3]))
        offsets.extend(elf_slot_offset(current, entry, 4) for entry in (source.ENTRY, 0x1510B128, 0x150A7790))
        for offset in offsets:
            bad = bytearray(current)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_09_installed_source_progress_guards_and_independent_closed_image()
        before = bytearray((self.out / 'before-elf').read_bytes())
        row = next(row for row in machine.symbol_rows(before) if row[1] == SERIALIZATION[0][0][0])
        before[row[0] + 7] ^= 1
        with self.assertRaises(AssertionError):
            expected_image(bytes(before), self.rom)
        exists = Path.exists
        path = self.out / 'baseline.json'
        with patch.object(Path, 'exists', lambda p: False if p == path else exists(p)):
            with self.assertRaisesRegex(ValueError, 'Changed orthographic setup baseline'):
                source.freeze(self.root, self.out)
        self.receipt('image-controls', all_current_inputs=len(source.PATHS), in_file_byte_flips=len(offsets),
            altered_baseline_definition_rejected=True, current_state_recapture_refused=True)

    def test_11_exact_checkpoint_unknown_input_and_capture_controls(self):
        self.test_09_installed_source_progress_guards_and_independent_closed_image()
        checkpoint.freeze_after(self.root)
        rb = Path.read_bytes
        for relative, key in checkpoint.PATHS.items():
            current = (self.root / relative).read_bytes()
            before = checkpoint.fixture(self.root, 'before', key)
            self.assertEqual(checkpoint.previous_input(current, relative, self.root), before)
            self.assertEqual(checkpoint.previous_input(current, self.root / relative, self.root), before)
            self.assertEqual(checkpoint.previous_input(current + b'\n', relative, self.root), current + b'\n')
            for stage in ('before', 'after'):
                path = self.out / (stage + '-' + key)
                with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                    with self.assertRaisesRegex(AssertionError, 'orthographic setup fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        path = self.root / source.PATHS['owner']
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(AssertionError, 'Unexpected installed orthographic setup input'):
                checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
