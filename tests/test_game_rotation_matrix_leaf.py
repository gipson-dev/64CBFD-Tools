"""Original slot, split frame, finite math, C-screen boundary and actual callers."""
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_rotation_matrix_leaf as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_rotation_matrix_leaf_oracle as model
from tools.tests import test_game_actor_mask_scan_match as faults
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools import pad_c_object


def native_program(body, constants):
    literal = lambda values: '{' + ','.join('0x%Xu' % value for value in values) + '}'
    rows = []
    for index, mode in itertools.product(range(128), (0, 1)):
        memory = model.fixture(constants)
        angles = model.angles(index)
        output, calls = model.reference(memory, (model.OUTPUT, *angles), index)
        rows.append('{%d,%d,%s,%s,%s,%s}' % (index, mode, literal(angles),
            literal([call[1] for call in calls]), literal([model.provider(index, i) for i in range(6)]), literal(output)))
    return r'''
typedef unsigned int u32;typedef int s32;typedef float f32;
typedef struct{u32 index,mode,input[3],args[6],returns[6],expected[16];}Case;
static Case cases[]={''' + ',\n'.join(rows) + r'''};
static Case *current;static u32 outputData[24],calls,error;
static f32 D_8009F6C0;
static f32 floating(u32 word){union{u32 u;f32 f;}v;v.u=word;return v.f;}
static u32 bits(f32 value){union{u32 u;f32 f;}v;v.f=value;return v.u;}
static f32 math_call(f32 x,u32 kind){u32 index=calls++;
 if(index>=6){error=1;return 0;}
 if(kind!=(index&1) || bits(x)!=current->args[index])error=1;
 if(current->mode && index==0)D_8009F6C0=0.5f;
 return floating(current->returns[index]);
}
f32 func_150AD780(f32 x){return math_call(x,0);}
f32 func_150AD78C(f32 x){return math_call(x,1);}
''' + body + r'''
static int check(void){u32 n,i;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  current=&cases[n];calls=error=0;D_8009F6C0=floating(0x3C8EFA35u);
  for(i=0;i<24;i++)outputData[i]=0xA55A1234u;
  func_150A8050((f32 (*)[4])(outputData+4),floating(current->input[0]),floating(current->input[1]),floating(current->input[2]));
  if(error || calls!=6)return 2;
  for(i=0;i<24;i++)if(outputData[i]!=(i>=4&&i<20?current->expected[i-4]:0xA55A1234u))return 3;
 }
 return 0;
}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");for(;;){}}
'''


class RotationMatrixLeafTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>84I', cls.rom, source.ROM))
        addresses = (model.FACTOR, *range(model.COEFFICIENTS, model.COEFFICIENTS + 48, 4))
        cls.constants = {at: struct.unpack_from('>I', cls.before, elf_slot_offset(cls.before, at, 4))[0] for at in addresses}
        cls.math_words = list(struct.unpack_from('>76I', cls.before, elf_slot_offset(cls.before, model.COS, 304)))
        if cls.math_words != list(struct.unpack_from('>76I', cls.rom, 0xDAC30)):
            raise ValueError('Current math helpers are not retail')

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_original_words_padding_frame_relocations_and_C_screen_boundary(self):
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.row['sp_adjustments'], [(4, -48), (144, 16), (320, 32)])
        self.assertEqual(self.words[-1], 0)
        data, fs, rel = parse_object(self.obj)
        f = fs[source.FUNCTION]
        self.assertEqual(f['size'], 336)
        relative = {at - f['value']: value for at, value in rel.items() if f['value'] <= at < f['value'] + f['size']}
        self.assertEqual(relative, {32: [('R_MIPS_HI16', 'D_8009F6C0')], 36: [('R_MIPS_LO16', 'D_8009F6C0')],
            60: [('R_MIPS_26', 'func_150AD780')], 72: [('R_MIPS_26', 'func_150AD78C')],
            88: [('R_MIPS_26', 'func_150AD780')], 100: [('R_MIPS_26', 'func_150AD78C')],
            116: [('R_MIPS_26', 'func_150AD780')], 128: [('R_MIPS_26', 'func_150AD78C')]})
        assembly = emit_padded_assembly(self.obj, self.root / source.PATHS['angles_original'], filename=source.OWNER,
            word_patches_path=self.root / source.PATHS['guards'])
        path = self.out / 'generated-padded.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + assembly)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], capture_output=True, check=True)
        emitted, functions = build.link_owner(self.root, self.out, obj, source.OWNER)
        f = functions[source.FUNCTION]
        self.assertEqual(emitted[f['value']:f['value'] + 336], struct.pack('>84I', *self.retail))
        screens = json.loads((self.out / 'screens.json').read_text())
        self.assertEqual([(r['body_words'], r['differences']) for r in screens], [(87, 83), (87, 83), (135, 133), (135, 133), (84, 0)])
        self.assertTrue(all(not r['diagnostics'] for r in screens))
        self.receipt('shape', instruction_words=83, alignment_nops=1, unchanged_relocations=8,
            both_production_padders_exact=True, C_profiles_rejected=4, no_new_guards_or_profiles=True,
            assembly_restoration_not_a_C_match=True)

    def test_02_guest_formula_packets_saved_lifetimes_and_coefficient_snapshot(self):
        count, coverage = 0, set()
        for index, phase, mode in itertools.product(range(128), (0, 8), (0, 1)):
            memory = model.fixture(self.constants)
            args = (model.OUTPUT, *model.angles(index))
            expected, calls = model.reference(memory, args, index)
            pair = [model.RotationOracle(words, memory, args, phase, index, mode).run() for words in (self.retail, self.words)]
            self.assertEqual(model.state(pair[0]), model.state(pair[1]))
            self.assertEqual(pair[1].calls, calls)
            for i, value in enumerate(expected):
                self.assertEqual(model.read(pair[1].memory, model.OUTPUT + i * 4), value)
            if mode:
                self.assertEqual(model.read(pair[1].memory, model.FACTOR), model.bits(0.5))
            coverage.update(pair[1].visits)
            count += 1
        self.assertEqual(len(coverage), 83)
        self.receipt('guest', cases=count, all_83_instructions_reached=True, alignment_nop_not_dispatched=True,
            full_modeled_private_states_and_all_even_odd_saved_FP_preserved=True,
            cached_coefficient_six_ordered_FP_packets_and_partial_frame_release=True)

    def test_03_fired_access_prefixes_and_effective_returned_word_controls(self):
        count = 0
        for index, phase in itertools.product((0, 1, 31), (0, 8)):
            memory = model.fixture(self.constants)
            args = (model.OUTPUT, *model.angles(index))
            accesses = model.RotationOracle(self.retail, memory, args, phase, index).run().accesses
            for cut in range(accesses):
                pair = [model.RotationOracle(words, memory, args, phase, index, fault=cut) for words in (self.retail, self.words)]
                for instance in pair:
                    with self.assertRaises(faults.AccessFault):
                        instance.run()
                    self.assertEqual(instance.accesses, cut)
                self.assertEqual(model.state(pair[0]), model.state(pair[1]))
                count += 1
        negatives = ((60, 0x0D42B5E0, 0x0D42B5E3), (152, 0x4600D107, 0x4600D106), (328, 0xE492003C, 0xAC80003C))
        for offset, expected, wrong in negatives:
            words = list(self.words)
            self.assertEqual(words[offset // 4], expected)
            words[offset // 4] = wrong
            witness = None
            for index in range(16):
                memory = model.fixture(self.constants)
                args = (model.OUTPUT, *model.angles(index))
                values, calls = model.reference(memory, args, index)
                actual = model.RotationOracle(words, memory, args, index=index).run()
                if actual.calls != calls or [model.read(actual.memory, model.OUTPUT + i * 4) for i in range(16)] != values:
                    witness = index
                    break
            self.assertIsNotNone(witness)
        self.receipt('prefixes-controls', paired_fired_access_cuts=count, complete_modeled_states_equal=True,
            returned_call_sign_homogeneous_controls=3, not_hardware_exceptions_or_FCSR_equivalence=True)

    def test_04_uninstalled_semantic_C_native_and_effective_controls(self):
        statuses = {}
        controls = dict(selected=source.SEMANTIC_C,
            wrong_factor=source.SEMANTIC_C.replace('factor = D_8009F6C0;', 'factor = D_8009F6C0 * 2.0f;'),
            wrong_sign=source.SEMANTIC_C.replace('= -sinP;', '= sinP;'),
            missing_identity=source.SEMANTIC_C.replace('matrix[3][3] = 1.0f;', 'matrix[3][3] = 0.0f;'))
        for label, body in controls.items():
            path = self.out / ('native-' + label + '.c')
            path.write_text(native_program(body, self.constants))
            result = []
            for profile in ('O2', 'O0'):
                binary = path.with_suffix('.' + profile)
                compiled = subprocess.run(['cc', '-m32', '-' + profile, '-msse2', '-mfpmath=sse', '-mstackrealign',
                    '-ffp-contract=off', '-std=c11', '-fno-strict-aliasing', '-fno-builtin', '-ffreestanding',
                    '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                    str(path), '-o', str(binary)], capture_output=True, text=True)
                self.assertEqual((compiled.returncode, compiled.stderr), (0, ''))
                result.append(subprocess.run([str(binary)], capture_output=True).returncode)
            self.assertEqual(result, [0, 0] if label == 'selected' else [2, 2] if label == 'wrong_factor' else [3, 3])
            statuses[label] = result
        self.receipt('native', finite_cases_per_profile=256, profiles=['O2', 'O0'], zero_diagnostics=True,
            semantic_C_uninstalled_not_a_byte_match=True, modeled_FP_providers_and_output_canaries=True,
            returned_controls=statuses)

    def test_05_actual_fallthrough_math_and_independent_finite_polynomial(self):
        connected = {model.COS + i * 4: word for i, word in enumerate(self.math_words)}
        count = 0
        for index, phase in itertools.product(range(128), (0, 8)):
            memory = model.fixture(self.constants)
            args = (model.OUTPUT, *model.angles(index))
            expected, calls = model.reference(memory, args, actual=True)
            pair = [model.RotationOracle(words, memory, args, phase, connected=connected).run() for words in (self.retail, self.words)]
            self.assertEqual(model.state(pair[0]), model.state(pair[1]))
            self.assertEqual(pair[1].calls, calls)
            self.assertEqual([model.read(pair[1].memory, model.OUTPUT + i * 4) for i in range(16)], expected)
            count += 1
        self.receipt('math', connected_cases=count, actual_math_span_words=76, cosine_fallthrough_to_sine=True,
            original_coefficient_words=13, finite_exact_polynomial_order_and_RNE_integer_reduction=True,
            no_standard_library_substitutions_or_full_FCSR_hardware_claim=True)

    def connected(self, rotation):
        helpers = {source.ENTRY + i * 4: word for i, word in enumerate(rotation)}
        helpers.update({model.COS + i * 4: word for i, word in enumerate(self.math_words)})
        obj, diagnostics = build.compile_owner(self.root, self.out, (self.out / 'before-builder_owner').read_text(), 'builder-owner')
        self.assertEqual(diagnostics, '')
        assembly = emit_padded_assembly(obj, self.root / source.PATHS['builder_original'], filename='generated_13D350',
            word_patches_path=self.root / source.PATHS['guards'])
        path = self.out / 'builder-padded.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + assembly)
        padded = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], capture_output=True, check=True)
        data, fs = build.link_owner(self.root, self.out, padded, 'generated_13D350')
        for name, count, rom in (('func_1511490C', 40, 0x141DBC), ('func_151148A8', 25, 0x141D58), ('func_151149AC', 28, 0x141E5C)):
            f = fs[name]
            words = list(struct.unpack_from('>%dI' % count, data, f['value']))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            helpers.update({int(name[5:], 16) + i * 4: word for i, word in enumerate(words)})
        for address, rom, count in ((model.world.SCALE, 0xD5160, 20), (model.world.MULTIPLY, 0xD4EF8, 78),
                                    (model.world.POINT, 0xD4E10, 40)):
            offset = elf_slot_offset(self.before, address, count * 4)
            self.assertEqual(self.before[offset:offset + count * 4], self.rom[rom:rom + count * 4])
            helpers.update({address + i * 4: word for i, word in enumerate(struct.unpack_from('>%dI' % count, self.before, offset))})
        return helpers

    def test_06_complete_builder_and_position_chains_with_no_opaque_providers(self):
        helpers = [self.connected(words) for words in (self.retail, self.words)]
        counts = [0, 0]
        for index, phase in itertools.product(range(64), (0, 8)):
            memory = model.world.fixture(index)
            for address, value in self.constants.items():
                model.put(memory, address, value)
            model.put(memory, 0x800DBEF0, 1)
            model.put(memory, 0x800DBEF4, model.world.ACTOR)
            model.put(memory, model.world.ACTOR + 0x72, 0x81, 1)
            expected = model.builder_reference(memory)
            pair = [model.ChainOracle([mapping[model.world.source.ENTRY + i * 4] for i in range(40)], memory,
                (model.OUTPUT, model.world.ACTOR), phase=phase, entry=model.world.source.ENTRY, connected=mapping).run()
                for mapping in helpers]
            self.assertEqual(model.state(pair[0]), model.state(pair[1]))
            self.assertEqual([model.read(pair[1].memory, model.OUTPUT + i * 4) for i in range(16)], expected)
            counts[0] += 1
            parent = list(struct.unpack_from('>51I', self.before, elf_slot_offset(self.before, model.world.POSITION, 204)))
            pair = [model.ChainOracle(parent, memory, (model.world.OBJECT,), phase=phase,
                entry=model.world.POSITION, connected=mapping).run() for mapping in helpers]
            self.assertEqual(model.state(pair[0]), model.state(pair[1]))
            for axis in range(3):
                terms = [model.fp(expected[axis + row * 4], model.bits(value), 'mul')
                         for row, value in enumerate((-3.0, 223.0, 549.0))]
                result = model.fp(model.fp(terms[0], terms[1], 'add'), model.fp(terms[2], expected[axis + 12], 'add'), 'add')
                self.assertEqual(model.read(pair[1].memory, model.world.OBJECT + 0x10 + axis * 2, 2), math.trunc(model.floating(result)) & 65535)
            counts[1] += 1
        self.receipt('chains', builder_cases=counts[0], position_cases=counts[1], actual_instructions_all_providers=True,
            freshly_compiled_builder_angle_wrapper_lookup=True, original_math_scale_product_point_connected=True,
            no_opaque_lookup_rotation_or_math_callbacks=True, finite_RNE_low_word_model_not_runtime_acceptance=True)

    def test_07_independent_original_assembly_and_three_symbol_rebases(self):
        data, fs, rel = parse_object(self.obj)
        anchors = {'D_8009F6C0': model.FACTOR, 'func_150AD780': model.COS, 'func_150AD78C': model.SIN}
        assembly, unresolved = emit_function(data, fs[source.FUNCTION], rel, source.FUNCTION, anchors)
        self.assertEqual(unresolved, [])
        texts = dict(selected=assembly, original=(self.out / 'before-angles_original').read_text())
        for label, text in texts.items():
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], capture_output=True, check=True)
        for index, delta, factor in ((0, 0, model.FACTOR), (1, 0x10000, 0x80207FFC), (2, -0x10000, 0x80318004)):
            outputs = []
            for label in texts:
                script = self.out / ('rebase-%d.ld' % index)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + delta))
                values = dict(anchors, D_8009F6C0=factor, func_150AD780=model.COS - delta, func_150AD78C=model.SIN - delta)
                elf = self.out / ('%s-rebase-%d.elf' % (label, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % pair for pair in values.items()], '-o', str(elf), str(self.out / (label + '-reloc.o'))], capture_output=True, check=True)
                outputs.append(sections(elf)['.text'][1][:336])
            self.assertEqual(outputs[0], outputs[1])
        self.receipt('rebases', independent_pairs=3, original_assembly_reference=True,
            signed_low_constant_carry_and_six_call_relocations=True, C_credit=False)


if __name__ == '__main__':
    unittest.main()
