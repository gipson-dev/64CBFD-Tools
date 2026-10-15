"""Actual typed parent/wrapper/child qualification with bounded SDK contracts."""
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_view_projection_family as family
from tools.experiments import game_view_projection_command_candidates as source
from tools.experiments import game_view_projection_command_matching as matching
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function, nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests import game_view_projection_family_oracle as model
from tools.tests import game_view_projection_family_native as native
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import view_projection_family_checkpoint as checkpoint
from tools.check_game_data_layout import audit_layout
from tools.tests.test_game_record_constructor_match import elf_slot_offset

SERIALIZATION = (
    (('D_800A2C24', 'D_80090854', 'D_80099C90'), (1, 2, 0),
     ((0x800A2C24, 0, 16, 0, 65521), (0x80090854, 0, 16, 0, 6), (0x80099C90, 0, 16, 0, 65521))),
    (('D_800A2C28', 'D_80090858', 'D_800A68F8'), (1, 2, 0),
     ((0x800A2C28, 0, 16, 0, 65521), (0x80090858, 0, 16, 0, 6), (0x800A68F8, 0, 16, 0, 65521))),
    (('D_800C3650', 'D_800B0E50'), (1, 0),
     ((0x800C3650, 0, 16, 0, 65521), (0x800B0E50, 0, 16, 0, 65521))),
    (('D_800D2F40', 'D_80042790', 'D_8008AB90'), (2, 0, 1),
     ((0x800D2F40, 0, 16, 0, 65521), (0x80042790, 0, 16, 0, 65521), (0x8008AB90, 0, 16, 0, 65521))),
)


def expected_image(before, rom):
    expected = bytearray(before)
    for name, entry, address, size in ((source.FUNCTION, source.ENTRY, source.ROM, 516),
            (family.CHILD, family.ENTRY, family.ROM, 152)):
        at = elf_slot_offset(before, entry, size)
        expected[at:at + size] = rom[address:address + size]
        rows = [(at, fields) for at, label, fields, _ in machine.symbol_rows(before) if label == name]
        assert len(rows) == 1 and rows[0][1][1:] == (entry, 12, 18, 0, 5)
        struct.pack_into('>I', expected, rows[0][0] + 8, size)
    with patch.object(machine, 'SERIALIZATION', SERIALIZATION):
        machine.apply_burst_symbol_serialization(expected)
    return bytes(expected)


class ViewProjectionFamilyTests(unittest.TestCase):
    @classmethod
    def assemble(cls, text, label):
        path = cls.out / (label + '.s')
        path.write_text('.include "' + str(cls.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], check=True, capture_output=True)
        return obj

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / family.BUILD
        family.freeze(cls.root, cls.out)
        cls.before = (cls.out / 'before-owner').read_text()
        cls.obj, cls.diagnostics = build.compile_owner(cls.root, cls.out, family.recover(cls.before), 'qualified-family')
        cls.raw_data, cls.raw_functions = build.link_owner(cls.root, cls.out, cls.obj, source.OWNER)
        cls.rows = family.parent_guard_rows(cls.obj) + family.child_guard_rows(cls.obj)
        cls.guard_bytes = family.guard_manifest((cls.out / 'before-guards').read_bytes(), cls.rows)
        cls.guards = cls.out / 'qualified-guards.csv'
        cls.guards.write_bytes(cls.guard_bytes)
        padded = pad_c_object.emit_padded_assembly(cls.obj, cls.root / source.PATHS['layout'], source.OWNER, word_patches_path=cls.guards)
        cls.primary = cls.assemble(padded, 'primary-padded')
        cls.data, cls.functions = build.link_owner(cls.root, cls.out, cls.primary, source.OWNER)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.words, cls.retail, cls.raw = {}, {}, {}
        for name, entry, rom, count in ((source.FUNCTION, source.ENTRY, source.ROM, 129),
                (family.CHILD, family.ENTRY, family.ROM, 38), ('func_1510B32C', model.WRAPPER, 0x1387DC, 33)):
            a, b = cls.functions[name], cls.raw_functions[name]
            cls.words[entry] = list(struct.unpack_from('>%dI' % count, cls.data, a['value']))
            cls.raw[entry] = list(struct.unpack_from('>%dI' % count, cls.raw_data, b['value']))
            cls.retail[entry] = list(struct.unpack_from('>%dI' % count, cls.rom, rom))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def models(self, root, args, memory, trig_mode=0, sdk_mode=0, seed=0, phase=0, tables=None):
        expected = model.reference(memory, args, trig_mode, sdk_mode, seed, root)
        result = []
        for table in (tables or (self.retail, self.raw, self.words)):
            connected = {entry + i * 4: word for entry, words in table.items() if entry != root for i, word in enumerate(words)}
            instance = model.FamilyOracle(table[root], memory, args, trig_mode, sdk_mode, seed, phase, root, connected).run()
            self.assertEqual((model.parent.external(instance.memory), instance.calls), expected)
            result.append(instance)
        for instance in result[1:]:
            self.assertEqual(machine.complete_state(result[0]), machine.complete_state(instance))
        return result

    def test_01_full_family_owners_both_padders_and_manifest(self):
        self.assertEqual(self.diagnostics, '')
        self.assertEqual([r['function'] for r in self.rows].count(source.FUNCTION), 23)
        self.assertEqual([r['function'] for r in self.rows].count(family.CHILD), 2)
        for entry in self.words:
            self.assertEqual(self.words[entry], self.retail[entry])
        self.assertEqual(sum(a != b for a, b in zip(self.raw[family.ENTRY], self.retail[family.ENTRY])), 2)
        old_obj, diagnostics = build.compile_owner(self.root, self.out, self.before, 'before-family-owner')
        a, af, ar = parse_object(old_obj)
        b, bf, br = parse_object(self.obj)
        for name in set(af) - {source.FUNCTION, family.CHILD, 'func_1510B32C'}:
            x, y = af[name], bf[name]
            self.assertEqual(x['size'], y['size'], name)
            self.assertEqual(a[x['value']:x['value'] + x['size']], b[y['value']:y['value'] + y['size']], name)
            rel = lambda rows, info: {at - info['value']: value for at, value in rows.items() if info['value'] <= at < info['value'] + info['size']}
            self.assertEqual(rel(ar, x), rel(br, y), name)
        self.assertEqual((diagnostics, normalized_pools(old_obj)), ('', normalized_pools(self.obj)))
        header = self.guard_bytes.splitlines(keepends=True)[0]
        self.assertEqual(header, (self.out / 'before-guards').read_bytes().splitlines(keepends=True)[0])
        old_rows = list(csv.DictReader(io.StringIO((self.out / 'before-guards').read_text())))
        new_rows = list(csv.DictReader(io.StringIO(self.guard_bytes.decode())))
        retained = [r for r in old_rows if r['function'] != 'func_1510B32C']
        self.assertEqual(new_rows, retained + self.rows)
        for name, count in ((source.FUNCTION, 129), (family.CHILD, 38)):
            original = (self.root / source.PATHS['original']).read_text()
            target = 'glabel ' + name + original.split('glabel ' + name, 1)[1].split('endlabel ' + name, 1)[0] + 'endlabel ' + name + '\n'
            retail = self.out / (name + '-retail.s')
            retail.write_text(target)
            emitted, unresolved = emit_function(b, bf[name], br, name, nm_anchors(self.root / source.PATHS['elf']))
            self.assertFalse(unresolved)
            isolated = self.assemble(emitted, name + '-isolated')
            selected = self.out / (name + '-guards.csv')
            with selected.open('w') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(self.rows[0]), lineterminator='\n')
                writer.writeheader()
                writer.writerows(r for r in self.rows if r['function'] == name)
            assembly = emit_padded_assembly(isolated, retail, filename=source.OWNER, word_patches_path=selected)
            generated = self.assemble(assembly, name + '-generated')
            data, functions = build.link_owner(self.root, self.out, generated, source.OWNER)
            entry = source.ENTRY if name == source.FUNCTION else family.ENTRY
            self.assertEqual(data[functions[name]['value']:functions[name]['value'] + count * 4], struct.pack('>%dI' % count, *self.retail[entry]))
        self.receipt('owner', parent_words=129, child_words=38, wrapper_words=33, parent_guards=23,
            child_commutative_address_guards=2, obsolete_wrapper_guards_removed=8, other_raw_neighbors=11,
            both_padders=True, no_frame_or_stack_home_guards=True)

    def test_02_child_float_bits_pages_reloads_and_normalization_alias(self):
        cases = 0
        for index, page, mode, phase in itertools.product((0, 1, 3, 0x80000000), (0, 1, 128, 255), (0, 1, 2, 3), (0, 8)):
            memory = model.fixture(page=page)
            normalization = model.BASE + 2 if mode == 3 else model.VIEWS + (index * 0x180 & 0xFFFFFFFF) + 0xB8
            args = (index, normalization, 0x7FC12345, 0x80000000, 0x7F810000, 0x7F800000, 0)
            self.models(model.CHILD, args, memory, sdk_mode=mode, phase=phase)
            cases += 1
        self.receipt('child', cases=cases, raw_and_guarded_complete_state=True, u8_pages=[0, 1, 128, 255],
            normalization_low_half_alias_redirects_live_base=True, guest_only_low_word_index_overflow_and_FP_payload_transport=True,
            SDK_helpers_atomic_bounded_not_actual_matrix_math=True)

    def test_03_actual_parent_wrapper_child_connections(self):
        cases = 0
        for root, index, seed, trig_mode, sdk_mode, page in itertools.product((model.PARENT, model.WRAPPER),
                (0, 1, 3), range(3), (0, 1, 4), (0, 1, 2), (0, 1)):
            memory = model.fixture(near=model.parent.CLIPS[seed], far=model.parent.CLIPS[(seed + 2) % 5], page=page)
            args = (index, model.bits(1.25), model.bits(-2.5), model.bits(1.0))
            if root == model.PARENT:
                args += (model.parent.CLIPS[(seed + 1) % 5],)
            self.models(root, args, memory, trig_mode, sdk_mode, seed)
            cases += 1
        self.receipt('connections', cases=cases, actual_typed_parent_wrapper_and_child=True,
            all_seven_parent_child_words_and_SDK_packets=True, SDK_math_bounded_no_gameplay_or_FCSR_claim=True)

    def test_04_parent_global_field_aliases_and_fired_prefixes(self):
        cases, prefixes = 0, 0
        for near, far in ((0, model.bits(777.0)), (model.bits(2.0), model.bits(100.0))):
            memory = model.fixture(near=near, far=far)
            record = model.parent.FOV_OVERRIDE - 0x74
            for offset in range(0x180):
                memory.setdefault(record + offset, (offset * 13 + 0xA5) & 255)
            for offset, value in ((0xC, 160.0), (0x10, 120.0), (0x14, 1.25), (0x18, 0.75),
                    (0x6C, 60.0), (0x70, 45.0), (0x80, 0.5)):
                model.put(memory, record + offset, model.bits(value))
            model.put(memory, model.BASE, record)
            args = (0, model.bits(1.25), model.bits(-2.5), model.bits(1.0), 0)
            self.models(model.PARENT, args, memory, tables=(self.retail, self.words))
            cases += 1
        for root in (model.PARENT, model.CHILD):
            args = ((0, model.bits(1.25), model.bits(-2.5), model.bits(1.0), 0) if root == model.PARENT else
                (0, model.VIEWS + 0xB8, model.bits(45.0), model.bits(60.0), model.bits(0.125), model.bits(1000.0), model.bits(1.0)))
            memory = model.fixture()
            connected = {e + i * 4: word for e, words in self.retail.items() if e != root for i, word in enumerate(words)}
            full = model.FamilyOracle(self.retail[root], memory, args, root=root, connected=connected).run()
            for cut in range(full.root_accesses):
                instances = []
                for table in (self.retail, self.words):
                    connected = {e + i * 4: word for e, words in table.items() if e != root for i, word in enumerate(words)}
                    instance = model.FamilyOracle(table[root], memory, args, root=root, connected=connected, fault=cut)
                    with self.assertRaises(faults.AccessBoundary):
                        instance.run()
                    instances.append(instance)
                self.assertEqual(machine.complete_state(instances[0]), machine.complete_state(instances[1]))
                self.assertEqual((instances[0].current_pc, instances[0].delay_of), (instances[1].current_pc, instances[1].delay_of))
                prefixes += 1
        self.receipt('aliases', shared_bias_near_and_factor_field_alias_cases=cases, fired_prefixes=prefixes,
            full_modeled_state_and_PC_delay_identity=True, no_portable_native_stack_alias_or_fault_claim=True)

    def test_05_dependency_audit_and_frozen_inputs(self):
        family.freeze(self.root, self.out)
        for key, path in family.PATHS.items():
            current = checkpoint.previous_input((self.root / path).read_bytes(), path, self.root)
            self.assertEqual(hashlib.sha256(current).hexdigest(), family.BASELINE[key], key)
        audit = json.loads((self.out / 'sdk-dependencies.json').read_text())
        self.assertEqual([(x['name'], x['word_differences']) for x in audit],
            [('guPerspectiveF', 0), ('guMtxF2L', 114), ('guMtxIdentF', 0)])
        with self.assertRaises(ValueError):
            family.guard_manifest((self.out / 'before-guards').read_bytes() + b'\n', self.rows)

    def test_06_native32_actual_C_and_effective_controls(self):
        records = native.vectors()
        self.assertEqual(len(records), 216)
        self.assertEqual(native.run(self.out, 'family', records), [0, 0])
        controls = {
            'cached-base': family.SELECTED_CHILD.replace('    guPerspectiveF(', '    u8 *cached = D_800BE628;\n    guPerspectiveF(', 1).replace(
                'D_800BE628 + index', 'cached + index'),
            'wrong-scale': family.SELECTED_CHILD.replace('farPlane, scale);', 'farPlane, scale + 1.0f);'),
            'swapped-fov': family.SELECTED_CHILD.replace('fovY, fovX, nearPlane', 'fovX, fovY, nearPlane'),
        }
        witness = next(r for r in records if r['kind'] == 1 and r['index'] == 0 and r['sdk_mode'] == 1)
        for label, body in controls.items():
            self.assertNotEqual(body, family.SELECTED_CHILD)
            self.assertTrue(all(code in (1, 2) for code in native.run(self.out, label, [witness], child_body=body)), label)
        parent_witness = next(r for r in records if r['kind'] == 0 and r['index'] == 0 and r['trig_mode'] == 0 and r['sdk_mode'] == 0)
        wrong = family.PARENT_BODY.replace('* scale;', '* (scale + 1.0f);')
        self.assertNotEqual(wrong, family.PARENT_BODY)
        self.assertTrue(all(code in (1, 2) for code in native.run(self.out, 'parent-scale', [parent_witness], parent_body=wrong)))
        order_witness = next(r for r in records if r['kind'] == 0 and r['index'] == 0 and r['trig_mode'] == 4 and r['sdk_mode'] == 0)
        self.assertEqual(native.run(self.out, 'parent-early-extent', [order_witness], parent_body=matching.SELECTED), [2, 2])
        self.receipt('native', cases_per_profile=216, profiles=['O2', 'O0'],
            actual_parent_wrapper_child_C=True, complete_views_globals_rows_dirty_and_all_SDK_packets=True,
            effective_child_controls=list(controls), effective_parent_control=True,
            unsequenced_parent_extent_control_fails_full_state_in_both_profiles=True,
            ordinary_pages_0_1_only=True, finite_arithmetic_quiet_NaN_clip_transport=True,
            no_actual_SDK_math_FCSR_native_fault_stack_alias_or_overflow_claim=True)

    def test_07_compiled_unsigned_page_negative(self):
        child = family.SELECTED_CHILD.replace('D_800BE9C0 * 0x40', '(s8)D_800BE9C0 * 0x40')
        self.assertNotEqual(child, family.SELECTED_CHILD)
        obj, diagnostics = build.compile_owner(self.root, self.out, family.recover(self.before, child), 'negative-signed-page')
        data, functions = build.link_owner(self.root, self.out, obj, source.OWNER)
        info = functions[family.CHILD]
        words = list(struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value']))
        self.assertEqual(diagnostics, '')
        args = (0, model.VIEWS + 0xB8, model.bits(45.0), model.bits(60.0), model.bits(0.125), model.bits(1000.0), model.bits(1.0))
        memory = model.fixture(page=128)
        expected, calls = model.reference(memory, args, root=model.CHILD)
        instance = model.FamilyOracle(words, memory, args, root=model.CHILD)
        with self.assertRaisesRegex(AssertionError, 'Unowned mock matrix output'):
            instance.run()
        self.assertNotEqual(instance.calls[-1], calls[-1])

    def test_08_independent_rebases_and_guard_corruptions(self):
        raw, functions, relocations = parse_object(self.obj)
        anchors = nm_anchors(self.root / source.PATHS['elf'])
        for name, entry, count in ((source.FUNCTION, source.ENTRY, 129), (family.CHILD, family.ENTRY, 38)):
            assembly = (self.root / source.PATHS['original']).read_text()
            target = 'glabel ' + name + assembly.split('glabel ' + name, 1)[1].split('endlabel ' + name, 1)[0] + 'endlabel ' + name + '\n'
            original = self.assemble(target + '.type ' + name + ',@function\n.size ' + name + ',%d\n' % (count * 4), name + '-independent')
            emitted, unresolved = emit_function(raw, functions[name], relocations, name, anchors)
            self.assertFalse(unresolved)
            isolated = self.assemble(emitted, name + '-rebase-isolated')
            selected = self.out / (name + '-rebase-guards.csv')
            with selected.open('w') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(self.rows[0]), lineterminator='\n')
                writer.writeheader()
                writer.writerows(r for r in self.rows if r['function'] == name)
            retail_path = self.out / (name + '-rebase-retail.s')
            retail_path.write_text(target)
            generated = self.assemble(emit_padded_assembly(isolated, retail_path, filename=source.OWNER, word_patches_path=selected), name + '-rebased-padded')
            used = {symbol for at, uses in relocations.items() if functions[name]['value'] <= at < functions[name]['value'] + functions[name]['size'] for _, symbol in uses}
            for delta in (0, 0x9000):
                outputs = []
                for label, obj in (('original', original), ('generated', generated)):
                    script = self.out / ('rebase-%s-%s-%d.ld' % (name, label, delta))
                    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (entry + delta))
                    elf = script.with_suffix('.elf')
                    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', name,
                        *['--defsym=%s=0x%X' % (symbol, anchors[symbol] + delta) for symbol in sorted(used)],
                        '-o', str(elf), str(obj)], capture_output=True, check=True)
                    self.assertEqual(nm_anchors(elf)[name], entry + delta)
                    outputs.append(sections(elf)['.text'][1][:count * 4])
                self.assertEqual(outputs[0], outputs[1])
                if not delta:
                    self.assertEqual(outputs[0], struct.pack('>%dI' % count, *self.retail[entry]))
        for index in range(len(self.rows)):
            bad = [dict(row) for row in self.rows]
            bad[index]['expected'] = '0x%08X' % (int(bad[index]['expected'], 16) ^ 1)
            path = self.out / 'negative-guards.csv'
            with path.open('w') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(bad[0]), lineterminator='\n')
                writer.writeheader()
                writer.writerows(bad)
            with self.assertRaises(ValueError):
                pad_c_object.emit_padded_assembly(self.obj, self.root / source.PATHS['layout'], source.OWNER, word_patches_path=path)
        with patch.dict(family.PARENT_LOAD_CYCLES, {44: (0, 0)}):
            with self.assertRaisesRegex(ValueError, 'load cycle'):
                family.parent_guard_rows(self.obj)
        with patch.object(family, 'CHILD_RELOCATIONS', {}):
            with self.assertRaisesRegex(ValueError, 'child words/relocations'):
                family.child_guard_rows(self.obj)

    def test_09_installed_family_and_independent_closed_image(self):
        family.freeze(self.root, self.out)
        expected = {
            'owner': family.recover(self.before).encode(),
            'parent': source.recover_parent((self.out / 'before-parent').read_text()).encode(),
            'guards': self.guard_bytes,
            'elf': expected_image((self.out / 'before-elf').read_bytes(), self.rom),
        }
        for key, path in family.PATHS.items():
            current = (self.root / path).read_bytes()
            self.assertEqual(current, expected[key] if key in expected else (self.out / ('before-' + key)).read_bytes(), key)
        for key in ('owner', 'parent'):
            self.assertEqual((self.root / family.PATHS[key]).read_text(), expected[key].decode())
        current = expected['elf']
        before = (self.out / 'before-elf').read_bytes()
        self.assertEqual(hashlib.sha256(current).hexdigest(), checkpoint.AFTER['elf'])
        data = audit_layout(self.root / family.PATHS['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('image', ELF_sha256=checkpoint.AFTER['elf'], complete_changed_bytes=sum(a != b for a, b in zip(before, current)),
            parent_extent=[12, 516], child_extent=[12, 152], exact_adjacent_symbol_string_groups=4,
            no_non_target_definition_changes=True, every_other_ELF_byte_fixed=True, protected_data=data)

    def test_10_effective_current_and_immutable_input_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key, relative in family.PATHS.items():
            path = self.root / relative
            bad = rb(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p, value=bad: value if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_09_installed_family_and_independent_closed_image()
        for key in ('owner', 'parent'):
            path = self.root / family.PATHS[key]
            with patch.object(Path, 'read_text', lambda p, *a, **k: rt(p, *a, **k) + '\n' if p == path else rt(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_09_installed_family_and_independent_closed_image()
        for key in family.BASELINE:
            path = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'immutable projection-family input'):
                    family.freeze(self.root, self.out)
        bad = bytearray((self.out / 'before-elf').read_bytes())
        name = SERIALIZATION[0][0][0]
        at = next(at for at, label, _, _ in machine.symbol_rows(bad) if label == name)
        bad[at + 7] ^= 1
        with self.assertRaises(AssertionError):
            expected_image(bytes(bad), self.rom)
        path = self.root / family.PATHS['elf']
        current = rb(path)
        names = {name for group, _, _ in SERIALIZATION for name in group}
        offsets = [offset for at, label, _, string in machine.symbol_rows(current) if label in names for offset in (at, string)]
        offsets += [elf_slot_offset(current, entry, 4) for entry in (source.ENTRY, family.ENTRY, 0x15001000)]
        for offset in offsets:
            bad = bytearray(current)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_09_installed_family_and_independent_closed_image()
        self.receipt('image-controls', current_record_string_and_code_byte_flips=len(offsets),
            current_input_append_controls=len(family.PATHS), immutable_before_controls=len(family.BASELINE),
            all_effective=True, no_metadata_section_exclusion=True)

    def test_11_exact_inverse_unknown_input_and_capture_controls(self):
        self.test_09_installed_family_and_independent_closed_image()
        checkpoint.freeze_after(self.root)
        for relative, key in checkpoint.PATHS.items():
            current = (self.root / relative).read_bytes()
            before = checkpoint.fixture(self.root, 'before', key)
            self.assertEqual(checkpoint.previous_input(current, relative, self.root), before)
            self.assertEqual(checkpoint.previous_input(current, self.root / relative, self.root), before)
            self.assertEqual(checkpoint.previous_input(current + b'\n', relative, self.root), current + b'\n')
        rb = Path.read_bytes
        for stage in ('before', 'after'):
            path = self.out / (stage + '-owner')
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(AssertionError, 'projection family fixture'):
                    if stage == 'before':
                        checkpoint.previous_input((self.root / family.PATHS['owner']).read_bytes(), family.PATHS['owner'], self.root)
                    else:
                        checkpoint.freeze_after(self.root)
        path = self.root / family.PATHS['owner']
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(AssertionError, 'Unexpected installed projection family input'):
                checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
