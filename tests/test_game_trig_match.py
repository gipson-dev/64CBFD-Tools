"""Direct Game sine qualification; cosine screens remain non-installed."""
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

from tools.experiments import game_trig_candidates as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_record_constructor_match as image
from tools.tests import test_game_view_frustum_planes as planes
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.test_game_point_transform_match import put, read
from tools.check_game_data_layout import audit_layout
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests import game_sine_checkpoint as checkpoint

ENTRY, ROM, CODE = source.TARGETS['sinf'][0], source.TARGETS['sinf'][1], 416
GLOBALS = {0x80085EB0: 0x3EA2F984, 0x80085EB4: 0x40490FDC,
           0x80085EB8: 0x330885A3, 0x80085EBC: 0, 0x8002C920: 0x7F810000}
COEFFICIENTS = (0x3F800000, 0xBE2AAAA6, 0x3C088769, 0xB94FB7FD, 0x362EDEFA)
SINE_SOURCE_SHA = 'ae271497692ea1a00abd96bcfed9209458cf8ea694b0df385aa5dddf9fc1a679'
SERIALIZATION = (
    (('D_800A5698', 'D_800A1398'), (1, 0),
     ((0x800A5698, 0, 16, 0, 65521), (0x800A1398, 0, 16, 0, 65521))),
    (('D_800A569C', 'D_800A139C'), (1, 0),
     ((0x800A569C, 0, 16, 0, 65521), (0x800A139C, 0, 16, 0, 65521))),
)
for _i, _value in enumerate(COEFFICIENTS):
    GLOBALS[0x80098D90 + _i * 4] = _value
COS_GLOBALS = {0x80085EA0: 0x3EA2F984, 0x80085EA4: 0x40490FDC,
               0x80085EA8: 0x330885A3, 0x80085EAC: 0}
for _i, _value in enumerate(COEFFICIENTS):
    COS_GLOBALS[0x80098D70 + _i * 4] = _value


def inputs():
    values = {0, 0x80000000, 0x7F800000, 0xFF800000, 0x7F810001, 0xFFC12345}
    for exponent in range(512):
        for fraction in (0, 1, 0x3FFFFF):
            for sign in (0, 0x80000000):
                values.add(exponent << 22 | fraction | sign)
    for value in (-1000.0, -math.pi, -math.pi / 2, -0.5, 0.5, math.pi / 2, math.pi, 1000.0):
        word = bits(value)
        values.update(((word - 1) & 0xFFFFFFFF, word, (word + 1) & 0xFFFFFFFF))
    values.update((i * 1664525 + 1013904223) & 0xFFFFFFFF for i in range(256))
    return sorted(values)


def operation(left, right, op):
    a, b = floating(left), floating(right)
    return bits({'add': lambda: a + b, 'sub': lambda: a - b, 'mul': lambda: a * b}[op]())


def reference(word, cosine=False):
    exponent = word >> 22 & 0x1FF
    if exponent >= 0x136:
        return 0x7F810000 if word & 0x7F800000 == 0x7F800000 and word & 0x7FFFFF else 0
    if not cosine and exponent < 0xE6:
        return word
    reduced, parity = word, 0
    if cosine or exponent >= 0xFF:
        if cosine and not floating(word) > 0.0:
            reduced ^= 0x80000000
        scaled = operation(reduced, 0x3EA2F984, 'mul')
        if cosine:
            scaled = operation(scaled, 0x3F000000, 'add')
        rounded = operation(scaled, 0x3F000000, 'add' if floating(scaled) >= 0 else 'sub')
        period = math.trunc(floating(rounded))
        parity = period & 1
        periods = bits(float(period))
        if cosine:
            periods = operation(periods, 0x3F000000, 'sub')
        for scale in (0x40490FDC, 0x330885A3):
            reduced = operation(reduced, operation(periods, scale, 'mul'), 'sub')
    squared = operation(reduced, reduced, 'mul')
    polynomial = COEFFICIENTS[4]
    for coefficient in reversed(COEFFICIENTS[1:4]):
        polynomial = operation(operation(polynomial, squared, 'mul'), coefficient, 'add')
    result = operation(operation(operation(reduced, squared, 'mul'), polynomial, 'mul'), reduced, 'add')
    return result ^ (0x80000000 if parity else 0)


def fixture(word, phase=0):
    memory = {machine.STACK + i: (i * 13 + 0xA5) & 255 for i in range(-0x100, 0x100)}
    for address, value in GLOBALS.items():
        put(memory, address, value)
    return memory


def expected_image(before, retail):
    expected = bytearray(before)
    at = image.elf_slot_offset(before, ENTRY, CODE)
    expected[at:at + CODE] = retail
    with patch.object(image.screen, 'ENTRY', ENTRY):
        size = image.elf_symbol_size_offset(before, 'sinf')
    assert struct.unpack_from('>I', before, size)[0] == 20
    struct.pack_into('>I', expected, size, CODE)
    types = {name: (offset, fields) for offset, name, fields, _ in symbol_rows(before)
             if name in ('D_80085EB0', 'D_80085EB4', 'D_80085EB8', 'D_80085EBC', 'D_80098D90', 'D_8002C920')}
    assert len(types) == 6
    for name, (offset, fields) in types.items():
        assert fields[1:] == (int(name[2:], 16), 0, 16, 0, 4 if name == 'D_8002C920' else 65521)
        expected[offset + 12] = 17
    with patch.object(machine, 'SERIALIZATION', SERIALIZATION):
        machine.apply_burst_symbol_serialization(expected)
    return bytes(expected)


class TrigOracle(machine.BurstOracle):
    def __init__(self, words, memory, word=0, phase=0, entry=ENTRY, arguments=(), connected=None, fault=None):
        super().__init__(words, memory, phase=phase, entry=entry, arguments=arguments,
                         connected=connected, symbols={'unused': 0})
        self.f[12] = word
        self.current_pc, self.delay_of, self.root_fault = None, None, fault
        self.code = faults.TrackedCode(self.code, self)

    def execute(self, word):
        op, rs, rt, rd, shift, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        if op == 0 and fn == 3:
            self.r[rd] = signed(self.r[rt]) >> shift & 0xFFFFFFFF
        elif op == 17 and rs == 16 and fn == 13:
            self.f[shift] = math.trunc(floating(self.f[rd])) & 0xFFFFFFFF
        else:
            super().execute(word)

    def access(self):
        if self.own_instruction:
            if self.accesses == self.root_fault:
                raise faults.AccessBoundary
            self.accesses += 1

    def record_call(self, target):
        self.calls.append((target, self.f[12]))
        self.events.append(('CALL', target, self.f[12]))

    def hook(self, target):
        raise AssertionError('Unmodeled trig call: ' + hex(target))


class GameTrigMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>104I', cls.rom, ROM))
        cls.obj, cls.diagnostics = build.compile_owner(cls.root, cls.out, source.body('sinf'), 'qualified-sine')
        cls.data, cls.functions = build.link_owner(cls.root, cls.out, cls.obj, 'sinf')
        cls.words = list(struct.unpack('>104I', cls.data))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def assemble(self, text, label):
        path = self.out / (label + '.s')
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], check=True, capture_output=True)
        return obj

    def test_01_direct_complete_owner_and_both_padders(self):
        self.assertEqual(self.diagnostics, '')
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.functions['sinf']['size'], 416)
        text, functions, relocations = parse_object(self.obj)
        self.assertEqual(set(functions), {'sinf'})
        self.assertEqual(normalized_pools(self.obj), {'.rodata': None, '.data': None})
        old, warnings = build.compile_owner(self.root, self.out, (self.out / 'before-sinf').read_text(), 'sine-placeholder')
        old_data, old_functions = build.link_owner(self.root, self.out, old, 'sinf')
        self.assertEqual((warnings, old_functions['sinf']['size']), ('', 20))
        before = (self.out / 'before-elf').read_bytes()
        offset = image.elf_slot_offset(before, ENTRY, CODE)
        self.assertEqual(before[offset:offset + 20], old_data[:20])
        self.assertFalse(any(word >> 26 == 9 and word >> 21 & 31 == 29 and word >> 16 & 31 == 29 for word in self.words))
        with (self.root / source.PATHS['guards']).open() as stream:
            self.assertFalse(any(row['function'] in source.TARGETS for row in csv.DictReader(stream)))
        original = self.root / source.PATHS['sinf-asm']
        padded = (pad_c_object.emit_padded_assembly(self.obj, self.root / 'conker/retail_layout.us.txt', 'sinf'),
                  emit_padded_assembly(self.obj, original, filename='sinf'))
        for i, assembly in enumerate(padded):
            obj = self.assemble(assembly, 'sine-padder-' + str(i))
            data, _ = build.link_owner(self.root, self.out, obj, 'sinf')
            self.assertEqual(data, self.data)
        self.receipt('sine-owner', words=104, frame=0, guards=0, pools=0, warnings=0,
                     original_unpadded_profile=True, both_private_padders=True, relocations=relocations)

    def test_02_independent_original_and_symbol_rebases(self):
        original = self.assemble((self.root / source.PATHS['sinf-asm']).read_text() + '\n.type sinf,@function\n.size sinf,416\n', 'sine-original')
        anchors = nm_anchors(self.root / source.PATHS['elf'])
        text, _, relocations = parse_object(self.obj)
        used = {symbol for entries in relocations.values() for _, symbol in entries}
        for delta in (0, 0x9000):
            data = []
            for label, obj in (('c', self.obj), ('retail', original)):
                script = self.out / ('sine-rebase-' + label + '-' + str(delta) + '.ld')
                script.write_text('SECTIONS { .text 0x%X : { *(.text) } }\n' % (ENTRY + delta))
                elf = script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', 'sinf',
                    *['--defsym=%s=0x%X' % (name, anchors[name] + delta) for name in sorted(used)],
                    '-o', str(elf), str(obj)], check=True, capture_output=True)
                data.append(sections(elf)['.text'][1])
            self.assertEqual(data[0], data[1])
            if delta == 0:
                self.assertEqual(data[0], self.data)
        self.receipt('sine-rebase', comparisons=4, independent_retail_assembly=True, data_and_code_rebased=True)

    def test_03_mips_boundaries_full_state_and_reachable_coverage(self):
        coverage, cases = set(), 0
        for word in inputs():
            for phase in (0, 8):
                models = [TrigOracle(words, fixture(word, phase), word, phase).run() for words in (self.retail, self.words)]
                for model in models:
                    self.assertEqual(model.f[0], reference(word), hex(word))
                    self.assertEqual(read(model.memory, machine.STACK + phase), word)
                    self.assertEqual(model.calls, [])
                    self.assertEqual(len(model.stores), 1)
                    coverage.update(model.visits)
                self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
                cases += 1
        missing = set(range(ENTRY, ENTRY + CODE, 4)) - coverage
        self.assertEqual(missing, {ENTRY + 0xCC})
        self.receipt('sine-mips', cases=cases, reachable_words=len(coverage), dead_duplicate_offsets=[0xCC],
                     full_available_state=True, no_FCSR_or_exception_claim=True)

    def test_04_fired_memory_fault_prefixes(self):
        cases = 0
        for word in (0, bits(0.5), bits(-0.5), bits(math.pi), bits(-math.pi), 0x7F810001, 0x7F800000):
            for phase in (0, 8):
                full = TrigOracle(self.retail, fixture(word, phase), word, phase).run()
                for cut in range(full.accesses):
                    models = [TrigOracle(words, fixture(word, phase), word, phase, fault=cut) for words in (self.retail, self.words)]
                    for model in models:
                        with self.assertRaises(faults.AccessBoundary):
                            model.run()
                        self.assertEqual(model.accesses, cut)
                    self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
                    self.assertEqual((models[0].current_pc, models[0].delay_of), (models[1].current_pc, models[1].delay_of))
                    cases += 1
        self.receipt('sine-faults', fired_prefixes=cases, actual_pc_and_delay_identity=True)

    def native(self, body, label, expected_status=0):
        values = inputs()
        # i386 returns floats through x87, which quiets the retail signaling NaN.
        # The independent return-only probe below must establish this ABI effect.
        expected = [0x7FC10000 if reference(value) == 0x7F810000 else reference(value) for value in values]
        declarations = 'typedef unsigned int u32; typedef int s32; typedef float f32;\n'
        declarations += 'f32 D_80085EB0,D_80085EB4,D_80085EB8,D_80085EBC,D_8002C920,D_80098D90[5];\n'
        definitions = 'static u32 values[]={' + ','.join('0x%Xu' % v for v in values) + '};\n'
        definitions += 'static u32 expected[]={' + ','.join('0x%Xu' % v for v in expected) + '};\n'
        assignments = [('D_80085EB0', 0x3EA2F984), ('D_80085EB4', 0x40490FDC), ('D_80085EB8', 0x330885A3),
                       ('D_80085EBC', 0), ('D_8002C920', 0x7F810000)]
        assignments += [('D_80098D90[%d]' % i, v) for i, v in enumerate(COEFFICIENTS)]
        init = '\n'.join('u.u=0x%Xu; %s=u.f;' % (value, name) for name, value in assignments)
        probe = '__attribute__((noipa)) f32 abi_return(void) { return D_8002C920; }\n'
        program = declarations + definitions + body + probe + '\nint main(void) { union {u32 u; f32 f;} u,r; u32 i;\n' + init
        program += '\nif(*(u32 *)&D_8002C920!=0x7F810000u){return 80;}\nr.f=abi_return();\nif(r.u!=0x7FC10000u){return 81;}\n'
        program += '\nfor(i=0;i<sizeof(values)/sizeof(values[0]);i++){u.u=values[i];r.f=sinf(u.f);if(r.u!=expected[i]){u32 mismatch[3]={values[i],expected[i],r.u};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(mismatch),"d"(12):"memory");return 1;}}return 0;}\n'
        program += 'void _start(void) { int result=main(); __asm__ volatile("int $0x80" : : "a"(1), "b"(result)); __builtin_unreachable(); }\n'
        path = self.out / ('native-' + label + '.c')
        path.write_text(program)
        for profile in ('-O2', '-O0'):
            binary = path.with_suffix('.' + profile[1:])
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-msse2', '-mfpmath=sse', '-mstackrealign',
                '-fno-builtin', '-fno-strict-aliasing', '-ffp-contract=off', '-ffreestanding', '-static',
                '-fno-stack-protector', '-fno-pie', '-no-pie', '-nostdlib', '-Wall', '-Wextra', '-Werror',
                '-Wl,-e,_start', '-o', str(binary), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            run = subprocess.run([str(binary)], capture_output=True)
            self.assertEqual(run.returncode, expected_status, label + profile + ' ' + run.stdout.hex())
        return len(values)

    def test_05_native32_and_effective_algorithm_controls(self):
        cases = self.native(source.SIN, 'selected')
        controls = {'cutoff': source.SIN.replace('0xE6', '0xFF'),
                    'parity': source.SIN.replace('(period & 1) == 0', '(period & 1) != 0'),
                    'pi-tail': source.SIN.replace('reduced = reduced - periods * D_80085EB8;', 'reduced = reduced;'),
                    'nan': source.SIN.replace('return D_8002C920;', 'return D_80085EBC;')}
        for label, body in controls.items():
            self.native(body, label, 1)
        self.receipt('sine-native', cases_per_profile=cases, profiles=['O2', 'O0'], controls=list(controls),
                     SSE2_binary32=True, independent_i386_return_only_probe=True,
                     MIPS_NaN_word='7F810000', i386_x87_return_word='7FC10000',
                     no_native_raw_MIPS_NaN_FCSR_or_gameplay_claim=True)

    def test_06_connected_frustum_real_sine_and_retail_cosine(self):
        frustum = list(struct.unpack_from('>61I', self.rom, 0x486DC))
        cosine = list(struct.unpack_from('>88I', self.rom, 0x750B0))
        coverage, cases = set(), 0
        connected_cos = dict(zip(range(planes.COS, planes.COS + 352, 4), cosine))
        for x, y in planes.ANGLES:
            for index in (0, 1, 0xFFFFFFFF):
                for phase in (0, 8):
                    memory, view, args, _ = planes.fixture(index, x, y, 0, phase)
                    for address, value in {**GLOBALS, **COS_GLOBALS}.items():
                        put(memory, address, value)
                    horizontal = operation(operation(x, 0x3F000000, 'mul') ^ 0x80000000, 0x3C8EFA35, 'mul')
                    vertical = operation(operation(y, 0x3F000000, 'mul'), 0x3C8EFA35, 'mul')
                    expected = ((0x88, reference(horizontal, True)), (0x94, reference(horizontal, True) ^ 0x80000000),
                        (0x90, reference(horizontal)), (0x9C, reference(horizontal)), (0x98, 0), (0x8C, 0),
                        (0xA0, 0), (0xAC, 0), (0xA4, reference(vertical, True) ^ 0x80000000),
                        (0xB0, reference(vertical, True)), (0xA8, reference(vertical) ^ 0x80000000),
                        (0xB4, reference(vertical) ^ 0x80000000))
                    models = []
                    for sine in (self.retail, self.words):
                        connected = {**connected_cos, **dict(zip(range(ENTRY, ENTRY + CODE, 4), sine))}
                        model = TrigOracle(frustum, memory, phase=phase, entry=planes.source.ENTRY, arguments=args, connected=connected).run()
                        self.assertEqual(model.calls, [(planes.COS, horizontal), (planes.SIN, horizontal),
                                                      (planes.COS, vertical), (planes.SIN, vertical)])
                        for offset, value in expected:
                            self.assertEqual(read(model.memory, view + offset), value)
                        coverage.update(model.visits)
                        models.append(model)
                    self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
                    cases += 1
        self.receipt('sine-connected', cases=cases, real_sine_instructions=True, retail_cosine_instructions=True,
                     production_cosine_still_stub=True, no_runtime_camera_or_culling_acceptance=True)

    def test_07_installed_closed_image_and_controls(self):
        source.freeze(self.root, self.out)
        self.assertEqual((self.root / source.PATHS['sinf']).read_text(), source.body('sinf'))
        self.assertEqual(hashlib.sha256((self.root / source.PATHS['sinf']).read_bytes()).hexdigest(), SINE_SOURCE_SHA)
        for key, path in source.PATHS.items():
            if key not in ('elf', 'sinf'):
                self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes(), key)
        before = (self.out / 'before-elf').read_bytes()
        expected = expected_image(before, self.rom[ROM:ROM + CODE])
        at = image.elf_slot_offset(before, ENTRY, CODE)
        current = (self.root / source.PATHS['elf']).read_bytes()
        self.assertEqual(current, expected, 'Only sine slot, extent, six type annotations and two closed symbol permutations may change')
        data = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('sine-image', ELF_sha256=hashlib.sha256(current).hexdigest(),
                     sine_sha256=hashlib.sha256((self.root / source.PATHS['sinf']).read_bytes()).hexdigest(),
                     changed_slot_bytes=sum(a != b for a, b in zip(before[at:at + CODE], current[at:at + CODE])),
                     symbol_extent_before=20, symbol_extent_after=416,
                     data_symbol_type_annotations=6, exact_adjacent_symbol_permutations=2, other_ELF_bytes_fixed=True)

    def test_08_effective_installed_and_frozen_input_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key, relative in source.PATHS.items():
            path = self.root / relative
            bad = rb(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p, value=bad: value if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_07_installed_closed_image_and_controls()
        path = self.root / source.PATHS['sinf']
        with patch.object(Path, 'read_text', lambda p, *a, **k: rt(p, *a, **k) + '\n' if p == path else rt(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_installed_closed_image_and_controls()
        path = self.out / 'before-sinf'
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(ValueError, 'immutable trig input'):
                source.freeze(self.root, self.out)

    def test_09_pinned_inverse_unknown_inputs_and_corrupt_capture(self):
        self.test_07_installed_closed_image_and_controls()
        checkpoint.freeze_after(self.root)
        for relative, key in checkpoint.PATHS.items():
            data = (self.root / relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(data, relative, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(data, self.root / relative, self.root), checkpoint.fixture(self.root, 'before', key))
            self.assertEqual(checkpoint.previous_input(data + b'\n', relative, self.root), data + b'\n')
        rb = Path.read_bytes
        path = self.out / 'after-sinf'
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(AssertionError, 'Game sine fixture'):
                checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
