"""Attachment-position frame, field widths, provider packets and literal owner gates."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_special_object_position as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import test_game_actor_mask_scan_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object

OBJECT, ACTOR, CATEGORY = 0x20000, 0x22000, 0x800BE9F0
LOOKUP, MATRIX, POINT = 0x151149AC, 0x1511490C, 0x150A7960
VECTORS = ((-1.75, 0.75, 32767.75), (-32768.0, -0.0, 1.99),
           (65535.0, -65535.0, 123.875), (2147483520.0, -2147483648.0, -123.875))


def fixture(kind=0x8005, category=0x35, selector=0xAB81):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x200, 0x100)}
    for base in (OBJECT, ACTOR):
        memory.update({base + i: (i * 13 + 0x5A) & 255 for i in range(-16, 0xB0)})
    put(memory, OBJECT + 0x54, kind, 2)
    put(memory, OBJECT + 0x3E, selector, 2)
    put(memory, CATEGORY, category)
    return memory


def external(memory):
    return {a: b for a, b in memory.items() if not STACK - 0x200 <= a < STACK + 0x100}


def matrix_values(pattern):
    return [float(1 if i in (0, 5, 10, 15) else (pattern * (i - 11) if i in (12, 13, 14) else 0))
            for i in range(16)]


def transformed(pattern):
    # Independent row-vector formula with each retail single-precision rounding.
    m = matrix_values(pattern)
    f32 = lambda value: floating(bits(value))
    return tuple(f32(f32(f32(m[i] * -3.0) + f32(m[i + 4] * 223.0)) +
                     f32(f32(m[i + 8] * 549.0) + m[i + 12])) for i in range(3))


class PositionOracle(machine.MaskOracle):
    def __init__(self, words, memory, result=ACTOR, vector=VECTORS[0], phase=0,
                 effect=False, pattern=0, connected=None, fault=None):
        super().__init__(words, memory, phase=phase, entry=source.ENTRY,
                         arguments=(OBJECT,), connected=connected, fault=fault)
        self.result, self.vector, self.effect, self.pattern = result, vector, effect, pattern
        self.current_pc = self.delay_of = None
        self.code = faults.TrackedCode(self.code, self)

    def record_call(self, target):
        assert target in (LOOKUP, MATRIX, POINT), hex(target)
        args = self.arguments({LOOKUP: 1, MATRIX: 2, POINT: 7}[target])
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        args = self.calls[-1][1:]
        result = None
        if target == LOOKUP:
            assert args[0] <= 255
            result = self.result
            if self.effect:
                put(self.memory, OBJECT + 0x54, 0, 2)
                put(self.memory, OBJECT + 0x3E, 0, 2)
                put(self.memory, CATEGORY, 0)
        elif target == MATRIX:
            assert args[1] == self.result
            for i, value in enumerate(matrix_values(self.pattern)):
                self.put(args[0] + i * 4, bits(value), 4)
        else:
            assert target == POINT
            assert args[1:4] == tuple(map(bits, (-3.0, 223.0, 549.0)))
            assert args[4:] == (args[0] - 4, args[0] - 8, args[0] - 12)
            for address, value in zip(args[4:], self.vector):
                self.put(address, bits(value), 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        if result is not None:
            self.r[2] = result


def state(instance):
    return (instance.r, instance.f, instance.memory, instance.events, instance.calls,
            instance.lo, instance.condition, instance.current_pc, instance.delay_of, instance.accesses)


def native_program(body):
    prefix = r'''
typedef unsigned char u8; typedef unsigned short u16; typedef short s16;
typedef int s32; typedef unsigned int u32; typedef float f32;
#define NULL ((void*)0)
static union { u32 align; u8 bytes[192]; } objectData, actorData;
static s32 D_800BE9F0, stage, error, found, effect;
static u32 wantedSelector;
static f32 output[3];
static u8 *func_151149AC(u32 selector) {
 if(stage++!=0 || selector!=wantedSelector)error=1;
 if(effect){*(u16*)(objectData.bytes+0x54)=0;*(u16*)(objectData.bytes+0x3E)=0;D_800BE9F0=0;}
 return found?actorData.bytes:NULL;
}
static void func_1511490C(f32 m[4][4],u8 *actor) {
 int i;if(stage++!=1 || actor!=actorData.bytes)error=2;
 for(i=0;i<16;i++)((f32*)m)[i]=(f32)(i+1);
}
static void func_150A7960(f32 m[4][4],f32 x,f32 y,f32 z,f32 *ox,f32 *oy,f32 *oz) {
 int i;if(stage++!=2 || x!=-3.0f || y!=223.0f || z!=549.0f)error=3;
 for(i=0;i<16;i++)if(((f32*)m)[i]!=(f32)(i+1))error=4;
 if(ox==oy || ox==oz || oy==oz)error=5;
 *ox=output[0];*oy=output[1];*oz=output[2];
}
'''
    suffix = r'''
static int check(void) {
 static u16 kinds[]={0x8005,0,0x8006,0xFFFF};
 static s32 categories[]={0x35,0,0x135,-1};
 static f32 vectors[2][3]={{-1.75f,0.75f,32767.75f},{-32768.0f,-0.0f,1.99f}};
 int k,c,s,v,e,f,i,active;u8 expected[192];
 for(k=0;k<4;k++)for(c=0;c<4;c++)for(s=0;s<256;s++)for(v=0;v<2;v++)for(e=0;e<2;e++)for(f=0;f<2;f++){
  for(i=0;i<192;i++)objectData.bytes[i]=expected[i]=(u8)(i*13+0x5A);
  *(u16*)(objectData.bytes+0x54)=*(u16*)(expected+0x54)=kinds[k];
  *(u16*)(objectData.bytes+0x3E)=*(u16*)(expected+0x3E)=(u16)(0xAB00+s);
  D_800BE9F0=categories[c];found=f;effect=e;stage=error=0;wantedSelector=(u32)s;
  for(i=0;i<3;i++)output[i]=vectors[v][i];
  active=k==0 && c==0;
  if(active && e){*(u16*)(expected+0x54)=0;*(u16*)(expected+0x3E)=0;}
  if(active && f)for(i=0;i<3;i++)*(s16*)(expected+0x10+i*2)=(s16)(s32)vectors[v][i];
  func_1511F31C(objectData.bytes);
  if(error || stage!=(active?(f?3:1):0))return 2;
  for(i=0;i<192;i++)if(objectData.bytes[i]!=expected[i])return 3;
 }
 return 0;
}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");for(;;){}}
'''
    return prefix + body + suffix


class SpecialObjectPositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>51I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_literal_words_frame_only_guards_and_fail_closed_inputs(self):
        self.assertEqual(self.words, self.retail)
        self.assertEqual([(i * 4, a, b) for i, (a, b) in enumerate(zip(self.raw_words, self.words)) if a != b], list(source.GUARDS))
        self.assertEqual((self.row['frame'], self.row['diagnostics']), (136, ''))
        data, fs, relocations = parse_object(self.obj)
        f = fs[source.FUNCTION]
        raw = data[f['value']:f['value'] + f['size']]
        relative = {at - f['value']: value for at, value in relocations.items() if f['value'] <= at < f['value'] + f['size']}
        self.assertEqual(relative, source.RELOCATIONS)
        for i in range(204):
            bad = bytearray(raw)
            bad[i] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(bad), relative)
        for key in relative:
            bad = dict(relative)
            del bad[key]
            with self.assertRaises(ValueError):
                source.normalize(raw, bad)
        guards = source.guard_manifest((self.out / 'before-guards').read_bytes())
        with self.assertRaises(ValueError):
            source.guard_manifest(guards)
        self.assertEqual(len(guards.splitlines()) - len((self.out / 'before-guards').read_bytes().splitlines()), 2)
        self.receipt('shape', raw_words=51, raw_differences=2, raw_frame=136,
            normalized_frame=144, full_slot_words=51, guards=2, five_relocations_fixed=True,
            every_raw_byte_flip_rejected=204, relocation_deletions_rejected=5, no_fake_locals_or_profile_changes=True)

    def test_02_complete_owner_neighbors_pools_and_generated_padder(self):
        before = (self.out / 'before-position_owner').read_text()
        obj, diagnostics = build.compile_owner(self.root, self.out, before, 'old-owner')
        self.assertEqual(diagnostics, '')
        a, af, ar = parse_object(obj)
        b, bf, br = parse_object(self.obj)
        relative = lambda rel, f: {at - f['value']: value for at, value in rel.items() if f['value'] <= at < f['value'] + f['size']}
        self.assertEqual(af.keys(), bf.keys())
        for name in af.keys() - {source.FUNCTION}:
            x, y = af[name], bf[name]
            self.assertEqual((x['size'], a[x['value']:x['value'] + x['size']], relative(ar, x)),
                             (y['size'], b[y['value']:y['value'] + y['size']], relative(br, y)), name)
        self.assertEqual(normalized_pools(obj), normalized_pools(self.obj))
        self.receipt('owner', raw_neighbors=len(af) - 1, all_bytes_sizes_relative_relocations_and_pools_fixed=True,
            actual_generated_padder_exact=True, zero_diagnostics=True)

    def test_03_guest_gates_selector_all_coordinates_and_full_private_state(self):
        count, coverage = 0, set()
        for kind, category, selector, result, vector, phase, effect in itertools.product(
                (0x8005, 0, 0x8006, 0xFFFF), (0x35, 0, 0x135, 0xFFFFFFFF),
                (0, 1, 0x80, 0xFF, 0xAB81), (0, ACTOR), VECTORS, (0, 8), (False, True)):
            memory = fixture(kind, category, selector)
            pair = [PositionOracle(words, memory, result, vector, phase, effect).run() for words in (self.retail, self.words)]
            self.assertEqual(state(pair[0]), state(pair[1]))
            expected = dict(memory)
            active = kind == 0x8005 and category == 0x35
            if active and effect:
                put(expected, OBJECT + 0x54, 0, 2)
                put(expected, OBJECT + 0x3E, 0, 2)
                put(expected, CATEGORY, 0)
            if active and result:
                for offset, value in zip((0x10, 0x12, 0x14), vector):
                    put(expected, OBJECT + offset, math.trunc(value) & 65535, 2)
            self.assertEqual(external(pair[1].memory), external(expected))
            self.assertEqual([call[0] for call in pair[1].calls], [] if not active else [LOOKUP, MATRIX, POINT] if result else [LOOKUP])
            if active:
                self.assertEqual(pair[1].calls[0], (LOOKUP, selector & 255))
            coverage.update(pair[1].visits)
            count += 1
        self.assertEqual(len(coverage), 51)
        raw = PositionOracle(self.raw_words, fixture()).run()
        retail = PositionOracle(self.retail, fixture()).run()
        self.assertEqual(external(raw.memory), external(retail.memory))
        self.assertNotEqual(state(raw), state(retail))
        self.receipt('guest', cases=count, all_51_words_reached=True, normalized_full_modeled_private_states=True,
            raw_public_equal_but_private_frame_differs=True, full_word_category_and_unsigned_halfword_gates=True,
            no_nonfinite_FCSR_or_hardware_claim=True)

    def test_04_fired_access_prefixes_and_unconditional_selector(self):
        count = 0
        for kind, category, result, phase in itertools.product((0, 0x8005), (0, 0x35), (0, ACTOR), (0, 8)):
            memory = fixture(kind, category)
            normal = PositionOracle(self.retail, memory, result=result, phase=phase).run()
            for cut in range(normal.accesses):
                pair = [PositionOracle(words, memory, result=result, phase=phase, fault=cut) for words in (self.retail, self.words)]
                for instance in pair:
                    with self.assertRaises(machine.AccessFault):
                        instance.run()
                    self.assertEqual(instance.accesses, cut)
                self.assertEqual(state(pair[0]), state(pair[1]))
                count += 1
        missing = fixture(kind=0)
        del missing[OBJECT + 0x3E]
        with self.assertRaisesRegex(AssertionError, 'unmapped read'):
            PositionOracle(self.words, missing).run()
        # A failed kind gate does not read the global category.
        missing = fixture(kind=0)
        for address in range(CATEGORY, CATEGORY + 4):
            del missing[address]
        self.assertEqual(PositionOracle(self.words, missing).run().calls, [])
        self.receipt('prefixes', paired_fired_access_cuts=count, all_complete_modeled_states_equal=True,
            mandatory_selector_read_and_conditional_category_read=True, not_hardware_exceptions=True)

    def test_05_native_actual_C_and_effective_returned_controls(self):
        controls = dict(selected=source.SELECTED,
            wrong_kind=source.SELECTED.replace('== 0x8005', '== 0x8006'),
            wrong_category=source.SELECTED.replace('== 0x35', '== 0x135'),
            selector_high_byte=source.SELECTED.replace('selector & 0xFF', 'selector >> 8'),
            wrong_point=source.SELECTED.replace('223.0f', '224.0f'),
            wrong_coordinate=source.SELECTED.replace('= (s16)(s32)z;', '= (s16)(s32)y;'))
        statuses = {}
        for label, body in controls.items():
            path = self.out / ('native-' + label + '.c')
            path.write_text(native_program(body))
            result = []
            for profile in ('O2', 'O0'):
                binary = path.with_suffix('.' + profile)
                command = ['cc', '-m32', '-' + profile, '-std=c11', '-fno-strict-aliasing', '-fno-builtin',
                    '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                    '-Wall', '-Wextra', '-Werror', str(path), '-o', str(binary)]
                compiled = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual((compiled.returncode, compiled.stderr), (0, ''))
                result.append(subprocess.run([str(binary)], capture_output=True).returncode)
            self.assertEqual(result, [0, 0] if label == 'selected' else [2, 2] if label != 'wrong_coordinate' else [3, 3])
            statuses[label] = result
        self.receipt('native', cases_per_profile=32768, profiles=['O2', 'O0'], zero_diagnostics=True,
            all_256_selector_bytes_and_two_finite_short_range_vectors=True,
            all_object_bytes_and_canaries=True, returned_controls=statuses,
            opaque_matrix_builder_not_actual_helper_or_native_private_frame=True)

    def test_06_actual_point_transform_connection_and_matrix_stub_boundary(self):
        before = (self.out / 'before-elf').read_bytes()
        from tools.tests.test_game_record_constructor_match import elf_slot_offset
        offset = elf_slot_offset(before, POINT, 160)
        point = list(struct.unpack_from('>40I', before, offset))
        self.assertEqual(point, list(struct.unpack_from('>40I', self.rom, 0xD4E10)))
        connected = {POINT + i * 4: word for i, word in enumerate(point)}
        count = 0
        for pattern, phase in itertools.product(range(-8, 9), (0, 8)):
            pair = [PositionOracle(words, fixture(), vector=transformed(pattern), pattern=pattern,
                phase=phase, connected=connected).run() for words in (self.retail, self.words)]
            self.assertEqual(state(pair[0]), state(pair[1]))
            for index, value in enumerate(transformed(pattern)):
                self.assertEqual(read(pair[1].memory, OBJECT + 0x10 + index * 2, 2), math.trunc(value) & 65535)
            count += 1
        owner = self.root / 'conker/src/game/generated_13D350.c'
        self.assertEqual(hashlib.sha256(owner.read_bytes()).hexdigest(), 'df497d2d221b68cc528b5266cdea3a568d9bc6a5b41a0780d5f458fe9ab8b10a')
        self.assertEqual(build.body(owner.read_text(), 'func_1511490C'), 's32 func_1511490C() {\n    return 0;\n}')
        self.receipt('connections', actual_retail_point_transform_words=40, guest_cases=count,
            matrix_builder_still_production_stub=True, matrix_builder_modeled_not_actual_gameplay=True)

    def test_07_original_assembly_and_independent_relocations(self):
        data, functions, relocations = parse_object(self.padded)
        anchors = {'D_800BE9F0': CATEGORY, 'func_151149AC': LOOKUP, 'func_1511490C': MATRIX, 'func_150A7960': POINT}
        selected, unresolved = emit_function(data, functions[source.FUNCTION], relocations, source.FUNCTION, anchors)
        self.assertEqual(unresolved, [])
        original = (self.out / 'before-position_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1]
        original = 'glabel ' + source.FUNCTION + '\n' + original.split('endlabel ' + source.FUNCTION, 1)[0] + 'endlabel ' + source.FUNCTION + '\n'
        for label, text in (('original', original), ('normalized', selected)):
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], capture_output=True, check=True)
        for index, delta, category in ((0, 0, CATEGORY), (1, 0x10000, 0x80207FFC), (2, 0x20000, 0x80318004)):
            values = {name: category if name.startswith('D_') else value + delta for name, value in anchors.items()}
            outputs = []
            for label in ('original', 'normalized'):
                script = self.out / ('rebase-%d.ld' % index)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + delta))
                elf = self.out / ('%s-rebase-%d.elf' % (label, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in values.items()], '-o', str(elf), str(self.out / (label + '-reloc.o'))],
                    capture_output=True, check=True)
                outputs.append(sections(elf)['.text'][1][:204])
            self.assertEqual(outputs[0], outputs[1])
        self.receipt('rebases', independent_original_assembly_pairs=3, signed_low_carry_and_call_targets=True)


if __name__ == '__main__':
    unittest.main()
