"""Direct queue words and retail control-flow qualification."""
from pathlib import Path
import hashlib
import itertools
import json
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_view_pending_queue as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function, nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import game_view_pending_queue_oracle as model
from tools.tests import game_view_pending_queue_native as native
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_record_callback_update_match import external
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout
from tools.tests import view_pending_queue_checkpoint as checkpoint
from tools.tests import view_clipping_checkpoint

SERIALIZATION = ()


def expected_image(before, rom):
    expected = bytearray(before)
    at = elf_slot_offset(before, source.ENTRY, 168)
    expected[at:at+168] = rom[source.ROM:source.ROM+168]
    rows = [(offset, fields) for offset, name, fields, _ in machine.symbol_rows(before) if name == source.FUNCTION]
    assert len(rows) == 1 and rows[0][1][1:] == (source.ENTRY, 12, 18, 0, 5)
    struct.pack_into('>I', expected, rows[0][0]+8, 168)
    with patch.object(machine, 'SERIALIZATION', SERIALIZATION):
        machine.apply_burst_symbol_serialization(expected)
    return bytes(expected)


class ViewPendingQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)
        cls.before = (cls.out / 'before-owner').read_text()
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.obj, cls.diagnostics = build.compile_owner(cls.root, cls.out, source.recover(cls.before), 'qualified')
        cls.raw_data, cls.raw_functions = build.link_owner(cls.root, cls.out, cls.obj, source.OWNER)
        cls.info = cls.raw_functions[source.FUNCTION]
        cls.raw = list(struct.unpack_from('>%dI' % (cls.info['size'] // 4), cls.raw_data, cls.info['value']))
        cls.retail = list(struct.unpack_from('>42I', cls.rom, source.ROM))
        cls.guard_bytes = source.guard_manifest((cls.out / 'before-guards').read_bytes())
        cls.guards = cls.out / 'qualified-guards.csv'
        cls.guards.write_bytes(cls.guard_bytes)
        assembly = pad_c_object.emit_padded_assembly(cls.obj, cls.root / source.PATHS['layout'],
            source.OWNER, word_patches_path=cls.guards)
        cls.primary = cls.assemble(assembly, 'primary')
        cls.data, cls.functions = build.link_owner(cls.root, cls.out, cls.primary, source.OWNER)
        cls.words = list(struct.unpack_from('>42I', cls.data, cls.functions[source.FUNCTION]['value']))

    @classmethod
    def assemble(cls, assembly, label):
        path = cls.out / (label + '.s')
        path.write_text('.include "' + str(cls.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + assembly)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], capture_output=True, check=True)
        return obj

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_complete_words_and_both_padders(self):
        self.assertEqual((self.diagnostics, self.info['size'], self.words), ('', 168, self.retail))
        self.assertEqual(self.raw[0], 0x27BDFFC8)
        self.assertEqual([(i * 4, a, b) for i, (a, b) in enumerate(zip(self.raw, self.retail)) if a != b], list(source.GUARDS))
        self.assertEqual(sorted(self.raw[21:24]), sorted(self.retail[21:24]))
        for offset, _, _ in source.GUARDS:
            _, info, relocations = parse_object(self.obj)
            self.assertFalse(relocations.get(info[source.FUNCTION]['value'] + offset))
        generated = emit_padded_assembly(self.obj, self.root / source.PATHS['original'],
            filename=source.OWNER, word_patches_path=self.guards)
        data, functions = build.link_owner(self.root, self.out, self.assemble(generated, 'generated'), source.OWNER)
        at = functions[source.FUNCTION]['value']
        self.assertEqual(data[at:at + 168], struct.pack('>42I', *self.retail))
        self.receipt('words', words=42, frame=56, guards=3, closed_independent_move_load_cycle=True,
            both_padders=True, every_other_word_direct=True)

    def test_02_raw_owner_neighbors_pools_and_relative_relocations(self):
        old, diagnostics = build.compile_owner(self.root, self.out, self.before, 'before-owner')
        old_data, old_functions, old_relocations = parse_object(old)
        data, functions, relocations = parse_object(self.obj)
        relative = lambda rows, info: {at-info['value']:uses for at, uses in rows.items() if info['value'] <= at < info['value']+info['size']}
        self.assertEqual(set(old_functions), set(functions))
        for name in set(functions) - {source.FUNCTION}:
            a, b = old_functions[name], functions[name]
            self.assertEqual(a['size'], b['size'], name)
            self.assertEqual(old_data[a['value']:a['value']+a['size']], data[b['value']:b['value']+b['size']], name)
            self.assertEqual(relative(old_relocations, a), relative(relocations, b), name)
        self.assertEqual((diagnostics, normalized_pools(old)), ('', normalized_pools(self.obj)))
        self.receipt('neighbors', unchanged_raw_functions=len(functions)-1, normalized_pools_and_relocations=True)

    def test_03_independent_original_generated_rebases(self):
        original = (self.out / 'before-original').read_text()
        original = 'glabel ' + source.FUNCTION + original.split('glabel '+source.FUNCTION, 1)[1].split('endlabel '+source.FUNCTION, 1)[0] + 'endlabel ' + source.FUNCTION + '\n'
        original_obj = self.assemble(original, 'independent-original')
        raw, functions, relocations = parse_object(self.obj)
        info = functions[source.FUNCTION]
        raw = bytearray(raw)
        for offset, expected, replacement in source.GUARDS:
            at = info['value'] + offset
            self.assertEqual(struct.unpack_from('>I', raw, at)[0], expected)
            struct.pack_into('>I', raw, at, replacement)
        anchors = nm_anchors(self.root / source.PATHS['elf'])
        emitted, unresolved = emit_function(raw, info, relocations, source.FUNCTION, anchors)
        self.assertFalse(unresolved)
        generated_obj = self.assemble(emitted, 'independent-generated')
        used = {name for at, rows in relocations.items() if info['value'] <= at < info['value']+168 for _, name in rows}
        for delta in (0, 0x1000000):
            outputs = []
            for label, obj in (('original', original_obj), ('generated', generated_obj)):
                script = self.out / ('%s-%X.ld' % (label, delta))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + delta))
                elf = script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % (name, anchors[name]+delta) for name in sorted(used)],
                    '-o', str(elf), str(obj)], capture_output=True, check=True)
                self.assertEqual(nm_anchors(elf)[source.FUNCTION], source.ENTRY+delta)
                outputs.append(sections(elf)['.text'][1][:168])
            self.assertEqual(outputs[0], outputs[1])
            if not delta:
                self.assertEqual(outputs[0], struct.pack('>42I', *self.retail))

    def test_04_signed_live_count_sentinels_packets_and_callback_mutations(self):
        cases, coverage = 0, set()
        for case in model.cases():
            expected, calls = model.reference(case['memory'], case['mode'])
            for phase in (0, 8):
                instances = [model.QueueOracle(words, case['memory'], case['mode'], phase).run() for words in (self.retail, self.words, self.raw)]
                for instance in instances:
                    self.assertEqual((external(instance.memory), instance.calls), (external(expected), calls))
                self.assertEqual(machine.complete_state(instances[0]), machine.complete_state(instances[1]))
                coverage.update(instances[0].visits)
                cases += 1
        self.assertEqual(coverage, set(range(source.ENTRY, source.ENTRY+168, 4)))
        self.receipt('guest', cases=cases, all_42_words_reached=True, full_padded_return_state=True,
            raw_and_padded_public_state=True, signed_inclusive_live_count=True,
            six_rows_include_dirty_byte_word_alias=True, raw_FP_payloads_not_hardware_flags=True)

    def test_05_every_fired_root_access_prefix(self):
        prefixes = 0
        for count, skip, mode, phase in itertools.product((-1, 0, 3, 5), (0, 0x15, 0x3F), (0, 1, 3, 6), (0, 8)):
            memory = model.fixture(count, 3, skip)
            full = model.QueueOracle(self.retail, memory, mode, phase).run()
            for cut in range(full.accesses):
                instances = []
                for words in (self.retail, self.words):
                    instance = model.QueueOracle(words, memory, mode, phase, fault=cut)
                    with self.assertRaises(faults.AccessBoundary):
                        instance.run()
                    instances.append(instance)
                self.assertEqual(machine.complete_state(instances[0]), machine.complete_state(instances[1]))
                self.assertEqual((instances[0].current_pc, instances[0].delay_of), (instances[1].current_pc, instances[1].delay_of))
                prefixes += 1
        self.receipt('prefixes', fired_prefixes=prefixes, complete_padded_state_PC_delay_identity=True,
            callbacks_atomic_not_portable_C_fault_or_hardware_FCSR=True)

    def test_06_actual_native_C_and_effective_semantic_controls(self):
        rows = native.vectors()
        self.assertEqual(len(rows), 2352)
        self.assertEqual(native.run(self.out, 'selected', rows), [0, 0])
        for label, body, row, status in native.negatives(rows):
            self.assertNotEqual(body, source.BODY)
            self.assertEqual(native.run(self.out, label, [row], body), [status, status], label)
        self.receipt('native', cases_per_profile=len(rows), profiles=['O2', 'O0'], effective_controls=6,
            full_banks_and_canaries=True, endian_normalized_dirty_float_word_alias=True,
            no_private_frame_fault_or_hardware_flag_claim=True)

    def test_07_effective_IDO_semantic_controls(self):
        for label, body, row, _ in native.negatives(native.vectors()):
            obj, diagnostics = build.compile_owner(self.root, self.out, source.recover(self.before, body), 'negative-'+label)
            data, functions = build.link_owner(self.root, self.out, obj, source.OWNER)
            info = functions[source.FUNCTION]
            words = list(struct.unpack_from('>%dI' % (info['size']//4), data, info['value']))
            self.assertEqual(diagnostics, '')
            instance = model.QueueOracle(words, row['memory'], row['mode']).run()
            self.assertNotEqual((external(instance.memory), instance.calls), (external(row['expected']), row['calls']), label)

    def test_08_effective_expected_word_and_relocation_guards(self):
        original = self.guards.read_bytes()
        for line, (_, expected, _) in zip(source.GUARD_ROWS.splitlines(keepends=True), source.GUARDS):
            bad_line = line.replace('0x%08X' % expected, '0x%08X' % (expected ^ 1), 1)
            bad = original.replace(line.encode(), bad_line.encode())
            self.assertNotEqual(bad, original)
            path = self.out / 'invalid-guards.csv'
            path.write_bytes(bad)
            with self.assertRaises(ValueError):
                pad_c_object.emit_padded_assembly(self.obj, self.root/source.PATHS['layout'], source.OWNER, word_patches_path=path)
            with self.assertRaises(ValueError):
                emit_padded_assembly(self.obj, self.root/source.PATHS['original'], filename=source.OWNER, word_patches_path=path)
        bad = original.replace(source.GUARD_ROWS.encode(), source.GUARD_ROWS.replace(',-,-,', ',R_MIPS_HI16:D_800D9AC0,-,', 1).encode())
        path = self.out/'invalid-relocation-guards.csv'
        path.write_bytes(bad)
        with self.assertRaises(ValueError):
            pad_c_object.emit_padded_assembly(self.obj, self.root/source.PATHS['layout'], source.OWNER, word_patches_path=path)
        with self.assertRaises(ValueError):
            emit_padded_assembly(self.obj, self.root/source.PATHS['original'], filename=source.OWNER, word_patches_path=path)

    def test_09_frozen_inputs_archive_and_original_caller(self):
        source.freeze(self.root, self.out)
        rb = Path.read_bytes
        for key in source.BASELINE:
            path = self.out/('before-'+key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p)+b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'immutable pending queue input'):
                    source.freeze(self.root, self.out)
        archive = self.root/'../Another Source/CBFD-Recompiled/conker/conker/src/game_138520.c'
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), '4c7932efd534f588ea02099b9ac32657de498be6cef55bc35d3f3b08bc0754d2')
        self.assertIn('#pragma GLOBAL_ASM("asm/nonmatchings/game_138520/func_1510B3B0.s")', archive.read_text())
        # Original1501878C gates this void command by DIRTY; V0 is not consumed.
        self.assertEqual(struct.unpack_from('>10I', self.rom, 0x45D74),
            (0x3C19800E, 0x93399AF0, 0x13200003, 0, 0x0D442CEC, 0, 0x3C0B800E, 0x916B9B18, 0x11600003, 0))

    def test_10_actual_queue_projection_parent_and_matrix_child(self):
        connected = {}
        for name, entry, rom, words in (('func_1510B128', model.COMMAND, 0x1385D8, 129),
                ('func_1510B5F8', model.family.CHILD, 0x138AA8, 38)):
            info = self.functions[name]
            body = list(struct.unpack_from('>%dI' % words, self.data, info['value']))
            self.assertEqual(body, list(struct.unpack_from('>%dI' % words, self.rom, rom)))
            connected.update({entry+i*4: word for i, word in enumerate(body)})
        cases = 0
        for count, skip, page, sdk_mode, phase in itertools.product((-1, 0, 1, 3), (0, 5, 15), (0, 1), (0, 1), (0, 8)):
            memory = model.family.fixture(page=page)
            memory.update(external(model.fixture(count, 3, skip)))
            for index in range(4):
                for field, value in enumerate((model.bits(-1 if skip>>index&1 else 0.5+index), model.bits(1.25), model.bits(-2.5))):
                    model.put(memory, model.ROWS+index*12+field*4, value)
            expected, calls, commands = model.connected_reference(memory, sdk_mode)
            instances = [model.ConnectedQueueOracle(words, memory, connected, sdk_mode, phase).run() for words in (self.retail, self.words)]
            for instance in instances:
                self.assertEqual((model.family.parent.external(instance.memory), instance.calls, instance.command_calls),
                    (model.family.parent.external(expected), calls, commands))
            self.assertEqual(machine.complete_state(instances[0]), machine.complete_state(instances[1]))
            cases += 1
        self.receipt('connected', cases=cases, actual_queue_parent_and_child_words=209,
            live_SDK_base_page_mutation=True, trig_and_SDK_helpers_bounded_not_actual_math=True,
            complete_modeled_state_and_all_call_packets=True)

    def test_11_raw_schedule_is_not_full_fault_state_equivalence(self):
        memory = model.fixture(0, 3)
        full = model.QueueOracle(self.retail, memory).run()
        different = []
        for cut in range(full.accesses):
            instances = []
            for words in (self.retail, self.raw):
                instance = model.QueueOracle(words, memory, fault=cut)
                with self.assertRaises(faults.AccessBoundary):
                    instance.run()
                instances.append(instance)
            if machine.complete_state(instances[0]) != machine.complete_state(instances[1]):
                different.append(cut)
        self.assertTrue(different)
        self.receipt('raw-schedule-boundary', fired_different_prefixes=different,
            raw_C_public_agreement_not_literal_fault_state_agreement=True,
            only_padded_words_claim_complete_prefix_identity=True)

    def test_12_installed_source_guards_progress_and_independent_closed_image(self):
        source.freeze(self.root, self.out)
        expected = dict(owner=source.recover(self.before).encode(), guards=self.guard_bytes,
            elf=expected_image((self.out/'before-elf').read_bytes(), self.rom))
        for key, path in source.PATHS.items():
            current=view_clipping_checkpoint.previous_input((self.root/path).read_bytes(),path,self.root)
            self.assertEqual(current, expected.get(key, (self.out/('before-'+key)).read_bytes()), key)
        self.assertEqual(view_clipping_checkpoint.previous_input((self.root/source.PATHS['owner']).read_text().encode(),
            source.PATHS['owner'],self.root),expected['owner'])
        self.assertEqual(hashlib.sha256(expected['elf']).hexdigest(), checkpoint.AFTER['elf'])
        data = audit_layout(self.root/source.PATHS['elf'], self.root/'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('image', ELF_sha256=hashlib.sha256((self.root/source.PATHS['elf']).read_bytes()).hexdigest(),
            pending_queue_checkpoint_ELF_sha256=checkpoint.AFTER['elf'],
            historical_pending_queue_changed_bytes=sum(a != b for a,b in zip((self.out/'before-elf').read_bytes(), expected['elf'])),
            code_extent=[12,168], exact_symbol_string_groups=len(SERIALIZATION), non_target_definition_changes=0,
            every_other_ELF_byte_fixed=True, protected_data=data,
            headers_profiles_progress_and_all_old_guard_bytes_fixed=True)

    def test_13_effective_installed_and_immutable_image_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key, relative in source.PATHS.items():
            path = self.root/relative
            bad = rb(path)+b'\n'
            with patch.object(Path, 'read_bytes', lambda p, value=bad: value if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_12_installed_source_guards_progress_and_independent_closed_image()
        path = self.root/source.PATHS['owner']
        with patch.object(Path, 'read_text', lambda p, *a, **k: rt(p,*a,**k)+'\n' if p == path else rt(p,*a,**k)):
            with self.assertRaises(AssertionError):
                self.test_12_installed_source_guards_progress_and_independent_closed_image()
        path = self.root/source.PATHS['elf']
        current = rb(path)
        target = next(row for row in machine.symbol_rows(current) if row[1] == source.FUNCTION)
        offsets = [target[0]+8, target[3]]
        offsets += [elf_slot_offset(current, entry, 4) for entry in (source.ENTRY, model.COMMAND, 0x150A7790)]
        for offset in offsets:
            bad = bytearray(current)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_12_installed_source_guards_progress_and_independent_closed_image()
        before = bytearray((self.out/'before-elf').read_bytes())
        row = next(row for row in machine.symbol_rows(before) if row[1] == source.FUNCTION)
        before[row[0]+4] ^= 1
        with self.assertRaises(AssertionError):
            expected_image(bytes(before), self.rom)
        exists = Path.exists
        path = self.out/'baseline.json'
        with patch.object(Path, 'exists', lambda p: False if p == path else exists(p)):
            with self.assertRaisesRegex(ValueError, 'Changed pending queue baseline'):
                source.freeze(self.root, self.out)
        self.receipt('image-controls', current_inputs=len(source.PATHS), in_file_byte_flips=len(offsets),
            changed_baseline_definition_rejected=True, current_state_recapture_refused=True)

    def test_14_exact_inverse_unknown_input_and_capture_controls(self):
        self.test_12_installed_source_guards_progress_and_independent_closed_image()
        checkpoint.freeze_after(self.root)
        rb = Path.read_bytes
        for relative, key in checkpoint.PATHS.items():
            current = (self.root/relative).read_bytes()
            before = checkpoint.fixture(self.root, 'before', key)
            self.assertEqual(checkpoint.previous_input(current, relative, self.root), before)
            self.assertEqual(checkpoint.previous_input(current, self.root/relative, self.root), before)
            self.assertEqual(checkpoint.previous_input(current+b'\n', relative, self.root), current+b'\n')
            self.assertEqual(checkpoint.previous_input(current, 'unowned-path', self.root), current)
            for stage in ('before', 'after'):
                path = self.out/(stage+'-'+key)
                with patch.object(Path, 'read_bytes', lambda p: rb(p)+b'\n' if p == path else rb(p)):
                    with self.assertRaisesRegex(AssertionError, 'pending queue fixture'):
                        if stage == 'before':
                            checkpoint.previous_input(current, relative, self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        path = self.root/source.PATHS['owner']
        with patch.object(Path, 'read_bytes', lambda p: rb(p)+b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(AssertionError, 'Unexpected installed pending queue input'):
                checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
