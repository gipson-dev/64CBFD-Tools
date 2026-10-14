"""Direct Game cosine and connected recovered trig qualification."""
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_cosine_candidates as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests import test_game_trig_match as sine
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.tests import game_cosine_checkpoint as checkpoint

ENTRY, ROM, SLOT = source.ENTRY, source.ROM, 352
INVERSES = (0x3EA2F984, 0xBEA2F984)
SERIALIZATION = (
    (('D_80098D70', 'D_80090B50', 'D_800A6BF0'), (1, 2, 0),
     ((0x80098D70, 0, 16, 0, 65521), (0x80090B50, 0, 16, 0, 6), (0x800A6BF0, 0, 16, 0, 65521))),
    (('D_80085EA8', 'D_8008ADA8'), (1, 0),
     ((0x80085EA8, 0, 16, 0, 65521), (0x8008ADA8, 0, 16, 0, 65521))),
)


def reference(word, inverse=INVERSES[0]):
    if word >> 22 & 0x1FF >= 0x136:
        return 0x7F810000 if word & 0x7F800000 == 0x7F800000 and word & 0x7FFFFF else 0
    absolute = word if sine.floating(word) > 0 else word ^ 0x80000000
    periods = sine.operation(sine.operation(absolute, inverse, 'mul'), 0x3F000000, 'add')
    rounded = sine.operation(periods, 0x3F000000, 'add' if sine.floating(periods) >= 0 else 'sub')
    period = math.trunc(sine.floating(rounded))
    periods = sine.operation(sine.bits(float(period)), 0x3F000000, 'sub')
    reduced = absolute
    for scale in (0x40490FDC, 0x330885A3):
        reduced = sine.operation(reduced, sine.operation(periods, scale, 'mul'), 'sub')
    squared = sine.operation(reduced, reduced, 'mul')
    polynomial = sine.COEFFICIENTS[4]
    for coefficient in reversed(sine.COEFFICIENTS[1:4]):
        polynomial = sine.operation(sine.operation(polynomial, squared, 'mul'), coefficient, 'add')
    result = sine.operation(sine.operation(sine.operation(reduced, squared, 'mul'), polynomial, 'mul'), reduced, 'add')
    return result ^ (0x80000000 if period & 1 else 0)


def fixture(word, phase=0, inverse=INVERSES[0]):
    memory = sine.fixture(word, phase)
    for address, value in sine.COS_GLOBALS.items():
        sine.put(memory, address, value)
    sine.put(memory, 0x80085EA0, inverse)
    return memory


def expected_image(before, retail):
    expected = bytearray(before)
    at = sine.image.elf_slot_offset(before, ENTRY, SLOT)
    expected[at:at + SLOT] = retail
    with patch.object(sine.image.screen, 'ENTRY', ENTRY):
        size = sine.image.elf_symbol_size_offset(before, 'cosf')
    assert struct.unpack_from('>I', before, size)[0] == 20
    struct.pack_into('>I', expected, size, 340)
    with patch.object(sine.machine, 'SERIALIZATION', SERIALIZATION):
        sine.machine.apply_burst_symbol_serialization(expected)
    return bytes(expected)


class TrackedCode(sine.faults.TrackedCode):
    def __getitem__(self, pc):
        previous_pc, previous_word = self.last_pc, self.last_word
        word = super().__getitem__(pc)
        if previous_word >> 26 == 17 and previous_word >> 21 & 31 == 8 and pc == previous_pc + 4:
            self.owner.delay_of = previous_pc
        return word


class CosineOracle(sine.TrigOracle):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('entry', ENTRY)
        super().__init__(*args, **kwargs)
        self.code = TrackedCode(self.code, self)


class GameCosineMatchTests(unittest.TestCase):
    native = sine.GameTrigMatchTests.native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>88I', cls.rom, ROM))
        cls.obj, cls.diagnostics = build.compile_owner(cls.root, cls.out, source.body(), 'qualified-cosine')
        cls.data, cls.functions = build.link_owner(cls.root, cls.out, cls.obj, 'cosf')
        cls.words = list(struct.unpack('>88I', cls.data))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def assemble(self, text, label):
        path = self.out / (label + '.s')
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], check=True, capture_output=True)
        return obj

    def test_01_direct_owner_screens_and_both_padders(self):
        self.assertEqual((self.diagnostics, self.functions['cosf']['size']), ('', 340))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.words[-3:], [0, 0, 0])
        self.assertEqual(normalized_pools(self.obj), {'.rodata': None, '.data': None})
        self.assertFalse(any(word >> 26 == 9 and word >> 21 & 31 == 29 and word >> 16 & 31 == 29 for word in self.words))
        self.assertEqual(sum(word >> 26 == 57 for word in self.words), 1)
        with (self.root / source.PATHS['guards']).open() as stream:
            self.assertFalse(any(row['function'] == 'cosf' for row in csv.DictReader(stream)))
        old, warnings = build.compile_owner(self.root, self.out, (self.out / 'before-cosf').read_text(), 'cosine-placeholder')
        old_data, old_functions = build.link_owner(self.root, self.out, old, 'cosf')
        self.assertEqual((warnings, old_functions['cosf']['size']), ('', 20))
        before = (self.out / 'before-elf').read_bytes()
        at = sine.image.elf_slot_offset(before, ENTRY, SLOT)
        self.assertEqual(before[at:at + 20], old_data[:20])
        for i, assembly in enumerate((
                pad_c_object.emit_padded_assembly(self.obj, self.root / 'conker/retail_layout.us.txt', 'cosf'),
                emit_padded_assembly(self.obj, self.root / source.PATHS['cosf-asm'], filename='cosf'))):
            padded, _ = build.link_owner(self.root, self.out, self.assemble(assembly, 'cosine-padder-' + str(i)), 'cosf')
            self.assertEqual(padded, self.data)
        rows = json.loads((self.out / 'sdk-copy-screens.json').read_text())
        self.assertEqual(len(rows), 18)
        self.assertEqual([row['label'] for row in rows if not row['differences'] and not row['uncompared_slot_words']], ['cosine-2', 'cosine-6'])
        self.receipt('owner', code_words=85, slot_words=88, frame=0, guards=0, warnings=0, pools=0,
                     both_padders=True, full_screens=18, exact_forms=2)

    def test_02_independent_original_and_rebased_links(self):
        original = self.assemble((self.root / source.PATHS['cosf-asm']).read_text() + '\n.type cosf,@function\n.size cosf,340\n', 'cosine-original')
        anchors = nm_anchors(self.root / source.PATHS['elf'])
        _, _, relocations = parse_object(self.obj)
        used = {symbol for entries in relocations.values() for _, symbol in entries}
        for delta in (0, 0x9000):
            results = []
            for label, obj in (('c', self.obj), ('retail', original)):
                script = self.out / ('rebase-' + label + '-' + str(delta) + '.ld')
                script.write_text('SECTIONS { .text 0x%X : { *(.text) } }\n' % (ENTRY + delta))
                elf = script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', 'cosf',
                    *['--defsym=%s=0x%X' % (name, anchors[name] + delta) for name in sorted(used)],
                    '-o', str(elf), str(obj)], check=True, capture_output=True)
                results.append(sections(elf)['.text'][1])
            self.assertEqual(results[0], results[1])
            if delta == 0:
                self.assertEqual(results[0], self.data)
        self.receipt('rebase', comparisons=4, code_and_data_rebased=True, independent_retail_assembly=True)

    def test_03_mips_float_boundaries_mutable_inverse_and_complete_state(self):
        coverage, cases = set(), 0
        for inverse in INVERSES:
            for word in sine.inputs():
                for phase in (0, 8):
                    models = [CosineOracle(words, fixture(word, phase, inverse), word, phase).run() for words in (self.retail, self.words)]
                    for model in models:
                        self.assertEqual(model.f[0], reference(word, inverse), (hex(word), hex(inverse)))
                        self.assertEqual(sine.read(model.memory, sine.machine.STACK + phase), word)
                        self.assertEqual(model.calls, [])
                        self.assertEqual(len(model.stores), 1)
                        coverage.update(model.visits)
                    self.assertEqual(sine.machine.complete_state(models[0]), sine.machine.complete_state(models[1]))
                    cases += 1
        missing = set(range(ENTRY, ENTRY + 340, 4)) - coverage
        self.assertEqual(missing, {ENTRY + offset for offset in (0x4C, 0x84, 0x12C)})
        self.receipt('mips', paired_cases=cases, inverse_modes=2, reachable_code_words=len(coverage),
                     dead_duplicate_offsets=[0x4C, 0x84, 0x12C], full_available_state=True, no_FCSR_or_exception_claim=True)

    def test_04_fired_memory_prefixes(self):
        cases = 0
        for inverse in INVERSES:
            for word in (0, sine.bits(0.5), sine.bits(-0.5), sine.bits(math.pi), sine.bits(-math.pi), 0x7F810001, 0x7F800000):
                for phase in (0, 8):
                    full = CosineOracle(self.retail, fixture(word, phase, inverse), word, phase).run()
                    for cut in range(full.accesses):
                        models = [CosineOracle(words, fixture(word, phase, inverse), word, phase, fault=cut) for words in (self.retail, self.words)]
                        for model in models:
                            with self.assertRaises(sine.faults.AccessBoundary):
                                model.run()
                            self.assertEqual(model.accesses, cut)
                        self.assertEqual(sine.machine.complete_state(models[0]), sine.machine.complete_state(models[1]))
                        self.assertEqual((models[0].current_pc, models[0].delay_of), (models[1].current_pc, models[1].delay_of))
                        cases += 1
        self.receipt('faults', fired_prefixes=cases, actual_PC_and_integer_FP_delay_identity=True)

    def test_05_native32_and_effective_algorithm_controls(self):
        prelude = 'f32 D_80085EA0,D_80085EA4,D_80085EA8,D_80085EAC,D_80098D70[5];\n'
        body = source.body().split('extern f32 D_80085EA0', 1)[1]
        body = 'extern f32 D_80085EA0' + body
        cases = 0
        for inverse in INVERSES:
            assignments = [('D_80085EA0', inverse), ('D_80085EA4', 0x40490FDC), ('D_80085EA8', 0x330885A3), ('D_80085EAC', 0)]
            assignments += [('D_80098D70[%d]' % i, value) for i, value in enumerate(sine.COEFFICIENTS)]
            initialize = '\n' + '\n'.join('u.u=0x%Xu;%s=u.f;' % (value, name) for name, value in assignments) + '\n'
            expected = lambda word, value=inverse: reference(word, value)
            cases += self.native(body, 'selected-' + hex(inverse), function='cosf', expected_fn=expected, prelude=prelude, initialize=initialize)
            if inverse == INVERSES[0]:
                controls = {'absolute': body.replace('absolute = angle > 0 ? angle : -angle;', 'absolute = angle;'),
                            'half-period': body.replace('periods -= 0.5f;', 'periods -= 0.25f;'),
                            'parity': body.replace('(period & 1) == 0', '(period & 1) != 0'),
                            'pi-tail': body.replace('reduced = reduced - periods * D_80085EA8;', 'reduced = reduced;'),
                            'nan': body.replace('return D_8002C920;', 'return D_80085EAC;')}
                for label, control in controls.items():
                    self.native(control, label, 1, function='cosf', expected_fn=expected, prelude=prelude, initialize=initialize)
        self.receipt('native', cases_per_profile=cases, profiles=['O2', 'O0'], controls=list(controls),
                     i386_return_only_NaN_probe=True, MIPS_word='7F810000', i386_word='7FC10000',
                     no_native_raw_MIPS_NaN_FCSR_or_gameplay_claim=True)

    def test_06_connected_frustum_both_recovered_trig_bodies(self):
        frustum = list(struct.unpack_from('>61I', self.rom, 0x486DC))
        sine_retail = list(struct.unpack_from('>104I', self.rom, sine.ROM))
        sine_obj, warnings = build.compile_owner(self.root, self.out, (self.root / source.PATHS['sinf']).read_text(), 'retained-sine')
        sine_data, _ = build.link_owner(self.root, self.out, sine_obj, 'sinf')
        self.assertEqual(warnings, '')
        self.assertEqual(sine_data, self.rom[sine.ROM:sine.ROM + 416])
        recovered_sine = list(struct.unpack('>104I', sine_data))
        cases = 0
        for x, y in sine.planes.ANGLES:
            for index in (0, 1, 0xFFFFFFFF):
                for phase in (0, 8):
                    memory, view, args, _ = sine.planes.fixture(index, x, y, 0, phase)
                    for address, value in {**sine.GLOBALS, **sine.COS_GLOBALS}.items():
                        sine.put(memory, address, value)
                    horizontal = sine.operation(sine.operation(x, 0x3F000000, 'mul') ^ 0x80000000, 0x3C8EFA35, 'mul')
                    vertical = sine.operation(sine.operation(y, 0x3F000000, 'mul'), 0x3C8EFA35, 'mul')
                    expected = ((0x88, reference(horizontal)), (0x94, reference(horizontal) ^ 0x80000000),
                        (0x90, sine.reference(horizontal)), (0x9C, sine.reference(horizontal)), (0x98, 0), (0x8C, 0),
                        (0xA0, 0), (0xAC, 0), (0xA4, reference(vertical) ^ 0x80000000), (0xB0, reference(vertical)),
                        (0xA8, sine.reference(vertical) ^ 0x80000000), (0xB4, sine.reference(vertical) ^ 0x80000000))
                    models = []
                    for cosine, sin in ((self.retail, sine_retail), (self.words, recovered_sine)):
                        connected = {**dict(zip(range(ENTRY, ENTRY + SLOT, 4), cosine)),
                                     **dict(zip(range(sine.ENTRY, sine.ENTRY + 416, 4), sin))}
                        model = CosineOracle(frustum, memory, phase=phase, entry=sine.planes.source.ENTRY, arguments=args, connected=connected).run()
                        self.assertEqual(model.calls, [(ENTRY, horizontal), (sine.ENTRY, horizontal), (ENTRY, vertical), (sine.ENTRY, vertical)])
                        for offset, value in expected:
                            self.assertEqual(sine.read(model.memory, view + offset), value)
                        models.append(model)
                    self.assertEqual(sine.machine.complete_state(models[0]), sine.machine.complete_state(models[1]))
                    cases += 1
        self.receipt('connected', paired_cases=cases, both_recovered_trig_bodies=True,
                     no_trig_return_mocks=True, no_runtime_camera_or_culling_acceptance=True)

    def test_07_installed_source_and_closed_literal_image(self):
        source.freeze(self.root, self.out)
        self.assertEqual((self.root / source.PATHS['cosf']).read_text(), source.body())
        self.assertEqual(hashlib.sha256((self.root / source.PATHS['cosf']).read_bytes()).hexdigest(), checkpoint.AFTER['cosf'])
        for key, path in source.PATHS.items():
            if key not in ('elf', 'cosf'):
                self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes(), key)
        before = (self.out / 'before-elf').read_bytes()
        current = (self.root / source.PATHS['elf']).read_bytes()
        self.assertEqual(current, expected_image(before, self.rom[ROM:ROM + SLOT]),
                         'Only cosine slot, public extent and two closed symbol/string groups may change')
        data = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        at = sine.image.elf_slot_offset(before, ENTRY, SLOT)
        self.receipt('image', ELF_sha256=hashlib.sha256(current).hexdigest(),
                     changed_slot_bytes=sum(a != b for a, b in zip(before[at:at + SLOT], current[at:at + SLOT])),
                     extent_before=20, extent_after=340, exact_symbol_groups=2, non_target_symbol_definition_changes=0,
                     every_other_ELF_byte_fixed=True, protected_data=data)

    def test_08_effective_current_and_immutable_input_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key, relative in source.PATHS.items():
            path = self.root / relative
            bad = rb(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p, value=bad: value if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_07_installed_source_and_closed_literal_image()
        path = self.root / source.PATHS['cosf']
        with patch.object(Path, 'read_text', lambda p, *a, **k: rt(p, *a, **k) + '\n' if p == path else rt(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_installed_source_and_closed_literal_image()
        path = self.out / 'before-cosf'
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(ValueError, 'immutable cosine input'):
                source.freeze(self.root, self.out)

    def test_09_pinned_inverse_unknown_inputs_and_corrupt_capture(self):
        self.test_07_installed_source_and_closed_literal_image()
        checkpoint.freeze_after(self.root)
        for relative, key in checkpoint.PATHS.items():
            data = (self.root / relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(data, relative, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(data, self.root / relative, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(data + b'\n', relative, self.root), data + b'\n')
        rb = Path.read_bytes
        path = self.out / 'after-cosf'
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(AssertionError, 'Game cosine fixture'):
                checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
