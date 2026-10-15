"""Direct builder words, ordered fields, aliased storage and real helper consumers."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_world_matrix as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_actor_world_matrix_oracle as model
from tools.tests import test_game_actor_mask_scan_match as machine
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object
from tools import pad_c_object


def controls():
    return dict(unsigned_coordinates=source.SELECTED.replace('*(s16 *)', '*(u16 *)'),
        missing_height=source.SELECTED.replace('*(f32 *)(actor + 0x18) + ', ''),
        reversed_product=source.SELECTED.replace('func_150A7A48(scale, matrix, matrix)',
                                              'func_150A7A48(matrix, scale, matrix)'))


def native_actor(memory):
    output = bytearray(memory[model.ACTOR + i] for i in range(192))
    for offset in (0, 4, 8, 0x18, 0x2C, 0x30, 0x34):
        struct.pack_into('<I', output, offset, model.read(memory, model.ACTOR + offset))
    for offset in (0x10, 0x12, 0x14):
        struct.pack_into('<H', output, offset, model.read(memory, model.ACTOR + offset, 2))
    return output


def native_program(body):
    literal = lambda values: '{' + ','.join('0x%Xu' % value for value in values) + '}'
    rows = []
    for pattern, mode in itertools.product(range(128), range(3)):
        memory = model.fixture(pattern)
        expected, calls = model.reference(memory, pattern, mode)
        rows.append('{%d,%d,%s,%s,%s,%s,%s}' % (pattern, mode, literal(native_actor(memory)),
            literal(native_actor(expected)), literal(model.orientation(pattern)),
            literal([model.read(expected, model.OUTPUT + i * 4) for i in range(16)]), literal(calls[1][2:])))
    return r'''
typedef unsigned char u8;typedef unsigned short u16;typedef short s16;
typedef unsigned int u32;typedef int s32;typedef float f32;
typedef struct{u32 pattern,mode;u8 initial[192],expected[192];u32 rotation[16],wanted[16],scale[3];}Case;
static Case cases[]={''' + ',\n'.join(rows) + r'''};
static union{u32 align;u8 bytes[192];}actor;
static u32 outputData[24];static Case *current;static int stage,error;static f32 *privateScale;
#define output ((f32 (*)[4])(outputData+4))
static f32 floating(u32 word){union{u32 u;f32 f;}v;v.u=word;return v.f;}
static u32 bits(f32 value){union{u32 u;f32 f;}v;v.f=value;return v.u;}
void func_151148A8(f32 matrix[4][4],f32 *angles){int i;
 if(stage++!=0 || matrix!=output || angles!=(f32*)actor.bytes)error=1;
 for(i=0;i<16;i++)((f32*)matrix)[i]=floating(current->rotation[i]);
 if(current->mode==1){s16 values[3]={-123,456,-789};for(i=0;i<3;i++){
  *(s16*)(actor.bytes+0x10+i*2)=values[i];*(f32*)(actor.bytes+0x2C+i*4)=(f32)(i+1)*0.5f;}
  *(f32*)(actor.bytes+0x18)=-3.75f;
 }
}
void func_150A7CB0(f32 matrix[4][4],f32 x,f32 y,f32 z){int i;
 if(stage++!=1 || bits(x)!=current->scale[0] || bits(y)!=current->scale[1] || bits(z)!=current->scale[2])error=2;
 privateScale=(f32*)matrix;
 for(i=0;i<16;i++)privateScale[i]=i==0?x:i==5?y:i==10?z:i==15?1.0f:0.0f;
 if(current->mode==2){output[0][0]=7.0f;*(f32*)(actor.bytes+0x2C)=9.0f;}
}
void func_150A7A48(f32 left[4][4],f32 right[4][4],f32 product[4][4]){
 f32 cached[4][4],row[4],value;int i,j,k;
 if(stage++!=2 || (f32*)left!=privateScale || right!=output || product!=output){error=3;return;}
 for(i=0;i<4;i++)for(j=0;j<4;j++)cached[i][j]=right[i][j];
 for(i=0;i<4;i++){
  for(k=0;k<4;k++)row[k]=left[i][k];
  for(j=0;j<4;j++){value=row[0]*cached[0][j];for(k=1;k<4;k++)value+=row[k]*cached[k][j];product[i][j]=value;}
 }
}
''' + body + r'''
static int check(void){u32 n,i;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  current=&cases[n];stage=error=0;privateScale=(f32*)0;
  for(i=0;i<192;i++)actor.bytes[i]=current->initial[i];
  for(i=0;i<24;i++)outputData[i]=0xA55A1234u;
  func_1511490C(output,actor.bytes);
  if(error || stage!=3)return 2;
  for(i=0;i<192;i++)if(actor.bytes[i]!=current->expected[i])return 3;
  for(i=0;i<24;i++)if(outputData[i]!=(i>=4&&i<20?current->wanted[i-4]:0xA55A1234u))return 4;
 }
 return 0;
}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");for(;;){}}
'''


class ActorWorldMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>40I', cls.rom, source.ROM))
        cls.before = (cls.out / 'before-builder_owner').read_text()

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_direct_body_owner_neighbors_pools_and_zero_guard_changes(self):
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['diagnostics']), (40, 96, ''))
        obj, diagnostics = build.compile_owner(self.root, self.out, self.before, 'old-owner')
        self.assertEqual(diagnostics, '')
        a, af, ar = parse_object(obj)
        b, bf, br = parse_object(self.obj)
        self.assertEqual(af.keys(), bf.keys())
        relative = lambda relocations, f: {at - f['value']: value for at, value in relocations.items()
            if f['value'] <= at < f['value'] + f['size']}
        for name in af.keys() - {source.FUNCTION}:
            x, y = af[name], bf[name]
            self.assertEqual((x['size'], a[x['value']:x['value'] + x['size']], relative(ar, x)),
                             (y['size'], b[y['value']:y['value'] + y['size']], relative(br, y)), name)
        self.assertEqual(normalized_pools(obj), normalized_pools(self.obj))
        f = bf[source.FUNCTION]
        self.assertEqual(relative(br, f), {28: [('R_MIPS_26', 'func_151148A8')],
            116: [('R_MIPS_26', 'func_150A7CB0')], 132: [('R_MIPS_26', 'func_150A7A48')]})
        self.assertNotIn((',' + source.FUNCTION + ',').encode(), (self.out / 'before-guards').read_bytes())
        self.receipt('shape-owner', direct_words=40, frame=96, relocations=3, guards_added=0,
            raw_neighbors=len(af) - 1, all_neighbor_bytes_sizes_relative_relocations_and_pools_fixed=True,
            full_owner_zero_diagnostics=True, production_generated_padder_exact=True)

    def test_02_guest_signed_fields_effects_alias_order_and_full_private_state(self):
        count, coverage = 0, set()
        for pattern, mode, destination, phase in itertools.product(range(128), range(3),
                (model.OUTPUT, model.ACTOR, model.ACTOR + 16, model.ACTOR + 32), (0, 8)):
            memory = model.fixture(pattern)
            expected, calls = model.reference(memory, pattern, mode, destination, model.STACK + phase)
            pair = [model.WorldMatrixOracle(words, memory, pattern, mode, destination, phase).run()
                    for words in (self.retail, self.words)]
            self.assertEqual(model.state(pair[0]), model.state(pair[1]))
            self.assertEqual(model.external(pair[1].memory), model.external(expected))
            self.assertEqual(pair[1].calls, calls)
            coverage.update(pair[1].visits)
            count += 1
        self.assertEqual(len(coverage), 40)
        self.receipt('guest', cases=count, all_40_words_reached=True, full_modeled_private_states_equal=True,
            signed_extrema_height_live_scales_signed_zero_and_three_output_actor_aliases=True,
            alias_cases_guest_only_not_portable_C_claim=True)

    def test_03_all_fired_parent_access_cuts(self):
        count = 0
        for pattern, mode, destination, phase in itertools.product((0, 1, 127), range(3),
                (model.OUTPUT, model.ACTOR + 16), (0, 8)):
            memory = model.fixture(pattern)
            accesses = model.WorldMatrixOracle(self.retail, memory, pattern, mode, destination, phase).run().accesses
            for cut in range(accesses):
                pair = [model.WorldMatrixOracle(words, memory, pattern, mode, destination, phase, fault=cut)
                        for words in (self.retail, self.words)]
                for instance in pair:
                    with self.assertRaises(machine.AccessFault):
                        instance.run()
                    self.assertEqual(instance.accesses, cut)
                self.assertEqual(model.state(pair[0]), model.state(pair[1]))
                count += 1
        self.receipt('prefixes', paired_fired_parent_access_cuts=count, all_complete_modeled_states_equal=True,
            observer_hooks_not_guest_accesses_and_not_hardware_exceptions=True)

    def test_04_native_real_C_and_effective_guest_returned_controls(self):
        statuses, witnesses = {}, {}
        for label, body in dict(selected=source.SELECTED, **controls()).items():
            if label != 'selected':
                _, negative, _ = source.measure(self.root, self.out, 'negative-' + label, body)
                witness = None
                for pattern, mode in itertools.product(range(128), range(3)):
                    memory = model.fixture(pattern)
                    expected, calls = model.reference(memory, pattern, mode)
                    actual = model.WorldMatrixOracle(negative, memory, pattern, mode).run()
                    if model.external(actual.memory) != model.external(expected) or actual.calls != calls:
                        witness = (pattern, mode)
                        break
                self.assertIsNotNone(witness, label)
                witnesses[label] = witness
            path = self.out / ('native-' + label + '.c')
            path.write_text(native_program(body))
            result = []
            for profile in ('O2', 'O0'):
                binary = path.with_suffix('.' + profile)
                compiled = subprocess.run(['cc', '-m32', '-' + profile, '-msse2', '-mfpmath=sse', '-mstackrealign', '-ffp-contract=off',
                    '-std=c11', '-fno-strict-aliasing', '-fno-builtin', '-ffreestanding', '-nostdlib', '-static',
                    '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                    str(path), '-o', str(binary)], capture_output=True, text=True)
                self.assertEqual((compiled.returncode, compiled.stderr), (0, ''))
                result.append(subprocess.run([str(binary)], capture_output=True).returncode)
            if label == 'selected':
                self.assertEqual(result, [0, 0])
            else:
                self.assertTrue(all(code in (2, 3, 4) for code in result), (label, result))
            statuses[label] = result
        self.receipt('native', cases_per_profile=384, profiles=['O2', 'O0'], zero_diagnostics=True,
            explicit_numeric_halfword_FP_endian_bridges=True, all_actor_bytes_and_output_canaries=True,
            rounded_SSE_single_precision_and_bounded_product_model=True,
            guest_returned_witnesses=witnesses, native_returned_controls=statuses)

    def helpers(self):
        from tools.tests.test_game_record_constructor_match import elf_slot_offset
        before = (self.out / 'before-elf').read_bytes()
        obj, diagnostics = build.compile_owner(self.root, self.out, (self.out / 'before-scale_owner').read_text(), 'scale-owner')
        self.assertEqual(diagnostics, '')
        assembly = pad_c_object.emit_padded_assembly(obj, self.root / source.PATHS['layout'], 'game_D5160',
            word_patches_path=self.root / source.PATHS['guards'])
        path = self.out / 'scale-padded.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + assembly)
        padded = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], capture_output=True, check=True)
        data, fs = build.link_owner(self.root, self.out, padded, 'game_D5160')
        scale = fs['func_150A7CB0']
        scale_words = list(struct.unpack_from('>20I', data, scale['value']))
        self.assertEqual(scale_words, list(struct.unpack_from('>20I', self.rom, 0xD5160)))
        data, fs = build.link_owner(self.root, self.out, self.padded, source.OWNER)
        angle = fs['func_151148A8']
        angle_words = list(struct.unpack_from('>25I', data, angle['value']))
        self.assertEqual(angle_words, list(struct.unpack_from('>25I', self.rom, 0x141D58)))
        helpers = {}
        for address, rom, count, words in ((model.ANGLES, 0x141D58, 25, angle_words),
                (model.SCALE, 0xD5160, 20, scale_words), (model.MULTIPLY, 0xD4EF8, 78, None),
                (model.POINT, 0xD4E10, 40, None)):
            truth = self.rom[rom:rom + count * 4]
            offset = elf_slot_offset(before, address, count * 4)
            self.assertEqual(before[offset:offset + count * 4], truth)
            if words is None:
                words = list(struct.unpack('>%dI' % count, truth))
            helpers.update({address + i * 4: word for i, word in enumerate(words)})
        return helpers

    def test_05_actual_C_angle_scale_and_assembly_product_connections(self):
        helpers = self.helpers()
        count = 0
        for pattern, phase in itertools.product(range(128), (0, 8)):
            memory = model.fixture(pattern)
            expected, _ = model.reference(memory, pattern, incoming=model.STACK + phase)
            pair = [model.WorldMatrixOracle(words, memory, pattern, phase=phase, connected=helpers).run()
                    for words in (self.retail, self.words)]
            self.assertEqual(model.state(pair[0]), model.state(pair[1]))
            self.assertEqual(model.external(pair[1].memory), model.external(expected))
            self.assertEqual(pair[1].leaf_calls, 2)
            count += 1
        self.receipt('helpers', guest_cases=count, freshly_compiled_angle_wrapper_words=25,
            freshly_compiled_scale_slot_words=20, existing_scale_schedule_guards=3,
            actual_product_body_words=76, product_alignment_nops=2,
            two_rotation_leaf_providers_explicitly_modeled=True)

    def test_06_actual_position_consumer_builder_and_point_chain(self):
        from tools.tests.test_game_record_constructor_match import elf_slot_offset
        before = (self.out / 'before-elf').read_bytes()
        offset = elf_slot_offset(before, model.POSITION, 204)
        parent = list(struct.unpack_from('>51I', before, offset))
        self.assertEqual(parent, list(struct.unpack_from('>51I', self.rom, 0x14C7CC)))
        helpers = self.helpers()
        count = 0
        for pattern, phase in itertools.product(range(128), (0, 8)):
            memory = model.fixture(pattern)
            expected = model.position_reference(memory, pattern, phase)
            pair = []
            for words in (self.retail, self.words):
                connected = dict(helpers)
                connected.update({source.ENTRY + i * 4: word for i, word in enumerate(words)})
                pair.append(model.WorldMatrixOracle(parent, memory, pattern, phase=phase, connected=connected,
                    entry=model.POSITION, arguments=(model.OBJECT,)).run())
            self.assertEqual(model.state(pair[0]), model.state(pair[1]))
            self.assertEqual(model.external(pair[1].memory), model.external(expected))
            count += 1
        # The empty builder does not initialize the caller's seeded private matrix.
        stub = list(struct.unpack_from('>3I', before, elf_slot_offset(before, source.ENTRY, 12)))
        failures = 0
        for pattern in range(8):
            connected = dict(helpers)
            connected.update({source.ENTRY + i * 4: word for i, word in enumerate(stub)})
            memory = model.fixture(pattern)
            for i in range(16):
                model.put(memory, model.STACK - 72 + i * 4, model.bits(1.0) if i in (0, 5, 10, 15) else 0)
            actual = model.WorldMatrixOracle(parent, memory, pattern, connected=connected,
                entry=model.POSITION, arguments=(model.OBJECT,)).run()
            failures += model.external(actual.memory) != model.external(model.position_reference(memory, pattern, 0))
        self.assertGreater(failures, 0)
        self.assertEqual(build.body((self.out / 'before-angles_owner').read_text(), 'func_150A8050'),
            'void func_150A8050(f32 mtx[4][4], f32 arg1, f32 arg2, f32 arg3) {\n}')
        self.receipt('consumer', connected_guest_cases=count, parent_words=51, builder_words=40,
            point_assembly_words=40, empty_builder_negative_failures=failures,
            actor_lookup_and_rotation_leaf_modeled=True, rotation_leaf_still_production_stub=True,
            not_complete_gameplay_or_host_acceptance=True)

    def test_07_independent_original_assembly_and_three_rebases(self):
        data, fs, rel = parse_object(self.obj)
        anchors = {'func_151148A8': model.ANGLES, 'func_150A7CB0': model.SCALE, 'func_150A7A48': model.MULTIPLY}
        assembly, unresolved = emit_function(data, fs[source.FUNCTION], rel, source.FUNCTION, anchors)
        self.assertEqual(unresolved, [])
        original = (self.out / 'before-builder_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1]
        original = 'glabel ' + source.FUNCTION + '\n' + original.split('endlabel ' + source.FUNCTION, 1)[0] + 'endlabel ' + source.FUNCTION + '\n'
        for label, text in (('original', original), ('selected', assembly)):
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], capture_output=True, check=True)
        for index, delta in enumerate((0, 0x10000, -0x20000)):
            outputs = []
            for label in ('original', 'selected'):
                script = self.out / ('rebase-%d.ld' % index)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + delta))
                elf = self.out / ('%s-rebase-%d.elf' % (label, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % (name, address - delta * 2) for name, address in anchors.items()],
                    '-o', str(elf), str(self.out / (label + '-reloc.o'))], capture_output=True, check=True)
                outputs.append(sections(elf)['.text'][1][:160])
            self.assertEqual(outputs[0], outputs[1])
        self.receipt('rebases', independent_original_assembly_pairs=3, three_call_relocations=True, guards=0)


if __name__ == '__main__':
    unittest.main()
