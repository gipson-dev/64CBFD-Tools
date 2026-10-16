"""Qualify loop-provenance controls and the complete uninstalled caller wrapper."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_quad_edge_lifetime as lifetime
from tools.experiments import game_quad_edge_frame as fitting
from tools.experiments import game_quad_edge_wrapper as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import test_game_quad_edge_emitter as edge
from tools.tests.game_owner_pool import normalized_pools


def packet_reference(memory, args, phase=0):
    centers = [edge.rounded(float(edge.short(edge.read(memory, args[0] + 0x10 + i * 2, 2)))
        + edge.floating(args[i + 3])) for i in range(3)]
    x, y, z = centers
    width, depth = map(edge.floating, args[1:3])
    right, left, front, back = (edge.rounded(width + x), edge.rounded(x - width),
        edge.rounded(depth + z), edge.rounded(z - depth))
    quad = tuple(map(edge.bits, (right, y, front, left, y, front, left, y, back, right, y, back)))
    packet = (edge.STACK + phase - 0x30, edge.bits(x), edge.bits(z), args[7], args[10],
        args[6], args[8], args[9], args[11] & 255, args[12])
    return packet, quad


class WrapperOracle(edge.EdgeOracle):
    def __init__(self, words, memory, args, phase=0, fault=None, entry=source.ENTRY):
        super().__init__(words, memory, args, phase=phase, fault=fault, entry=entry)
        self.quads = []

    def record_call(self, target):
        if target != source.CALLEE:
            raise AssertionError(('unexpected wrapper target', hex(target)))
        args = self.arguments(10)
        self.quads.append(tuple(edge.read(self.memory, args[0] + i * 4) for i in range(12)))
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0xAABBCCDD


def fixture(coords=(-32768, -1, 32767), values=(10.0, 20.0, 0.5, -1.25, 3.5), pattern=0):
    memory, _ = edge.fixture(bytes(33))
    actor = 0x24000
    memory.update({actor + i: (i * 7 + 0xA5) & 255 for i in range(-16, 48)})
    for i, coordinate in enumerate(coords):
        edge.put(memory, actor + 0x10 + i * 2, coordinate, 2)
    words = ((0, 0, 0, 0, 0, 0), (2, 0xFFFFFF85, 2, 3, 0xABCD0080, 0x87654321),
        (0xFFFFFFFF, 0x12345678, 0x80000000, 0x7FFFFFFF, 0xFFFF00FF, 0xFFFFFFFF),
        (0x12345678, 0xABCDEF00, 0xFFFFFFFF, 0, 0x12345601, 1))[pattern]
    kind, preset, nx, nz, flags, context = words
    return memory, (actor, *map(edge.bits, values), kind, preset, nx, nz, edge.bits(-0.5 + pattern), flags, context)


def controls():
    body = source.SELECTED
    return {
        'unsigned-coordinates': body.replace('*(s16 *)', '*(u16 *)'),
        'float-coordinates': body.replace('*(s16 *)', '*(f32 *)'),
        'wrong-corner': body.replace('quad[6] = leftX;', 'quad[6] = rightX;'),
        'wrong-z-coordinate': body.replace('actor + 0x14', 'actor + 0x12'),
        'narrow-preset': body.replace('centerX, centerZ, preset, scale', 'centerX, centerZ, (u8)preset, scale'),
        'swapped-counts': body.replace('xCount, zCount, flags, context);', 'zCount, xCount, flags, context);'),
        'integer-scale': body.replace('s32 zCount, f32 scale', 's32 zCount, s32 scale'),
        'wrong-origin': body.replace('func_151700D8(quad, centerX, centerZ', 'func_151700D8(quad, centerY, centerZ'),
    }


class QuadEdgePathRecoveryTests(unittest.TestCase):
    test_09_all_801_archive_fingerprints = edge.QuadEdgeEmitterTests.test_10_all_original_801_archive_fingerprints
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.words, cls.row = source.measure(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>61I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / ('qualification-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_scope_neighbors_and_actual_installation_rejection(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences'], self.row['diagnostics']), (63, 128, 61, ''))
        with self.assertRaisesRegex(ValueError, 'not a direct match'):
            source.qualify(self.root, self.out)
        with self.assertRaises(ValueError) as overflow:
            emit_padded_assembly(self.obj, self.root / source.PATHS['edge_wrapper_original'],
                filename=source.OWNER, word_patches_path=self.out / 'before-guards')
        self.assertIn(source.FUNCTION, str(overflow.exception))
        old_obj, diagnostic = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-edge_wrapper_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostic, '')
        old, new = parse_object(old_obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'])
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']])
            rel = lambda o, f: [(at - f['value'], entries) for at, entries in o[2].items()
                if f['value'] <= at < f['value'] + f['size']]
            self.assertEqual(rel(old, f), rel(new, g))
        self.assertEqual(normalized_pools(old_obj), normalized_pools(self.obj))
        self.receipt('shape', words=63, retail_words=61, frame=128, differences=61,
            unchanged_neighbors=len(old[1]) - 1, installation_and_actual_padder_rejected=True)

    def test_02_complete_thirteen_input_packet_and_quad(self):
        cases, private_different, visits = 0, 0, set()
        for coords in itertools.product((-32768, -1, 0, 1, 32767), repeat=3):
            for values in ((10., 20., .5, -1.25, 3.5), (-100., -40., -17.5, 0., 123.25)):
                for pattern in range(4):
                    for phase in (0, 8):
                        memory, args = fixture(coords, values, pattern)
                        wanted, quad = packet_reference(memory, args, phase)
                        models = [WrapperOracle(w, memory, args, phase).run() for w in (self.truth, self.words)]
                        for model in models:
                            self.assertEqual(model.calls, [(source.CALLEE, *wanted)])
                            self.assertEqual(model.quads, [quad])
                            self.assertEqual(edge.public(model.memory), edge.public(memory))
                        private_different += edge.state(models[0]) != edge.state(models[1])
                        visits |= models[0].visits
                        cases += 1
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 244, 4)))
        self.assertEqual(private_different, cases)
        self.receipt('public', pairs=cases, complete_13_inputs_10_output_words_12_quad_words=True,
            all_retail_words_executed=True, private_different=private_different,
            preset_full_word_flags_low_byte_scale_float=True, emitter_is_an_opaque_provider=True)

    def test_03_effective_compiled_negatives(self):
        memory, args = fixture(pattern=1)
        wanted, quad = packet_reference(memory, args)
        effective = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            model = WrapperOracle(words, memory, args)
            try:
                model.run()
            except AssertionError:
                self.assertEqual(name, 'float-coordinates')
            else:
                self.assertNotEqual((model.calls, model.quads), ([(source.CALLEE, *wanted)], [quad]), name)
            effective.append(name)
        self.receipt('controls', effective_compiled_guest_negatives=effective)

    def test_04_fired_fault_prefixes_not_claimed_equal(self):
        cuts, paired, different, original_only, candidate_only = 0, 0, 0, 0, 0
        for phase in (0, 8):
            memory, args = fixture(pattern=2)
            whole = [WrapperOracle(w, memory, args, phase).run() for w in (self.truth, self.words)]
            for fault in range(max(m.accesses for m in whole)):
                models = [WrapperOracle(w, memory, args, phase, fault=fault) for w in (self.truth, self.words)]
                fired = []
                for model, normal in zip(models, whole):
                    fired.append(fault < normal.accesses)
                    if fired[-1]:
                        with self.assertRaises(edge.AccessFault):
                            model.run()
                        cuts += 1
                    else:
                        model.run()
                if all(fired):
                    paired += 1
                    different += edge.state(models[0]) != edge.state(models[1])
                else:
                    original_only += fired[0]
                    candidate_only += fired[1]
        self.assertGreater(different, 0)
        self.receipt('faults', fired=cuts, paired=paired, privately_different=different,
            original_only=original_only, candidate_only=candidate_only, not_literal_fault_equivalence=True)

    def test_05_immutable_inputs_and_frozen_capture_controls(self):
        for key, path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), source.BASELINE[key], key)
        rb = Path.read_bytes
        for key in source.PATHS:
            target = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            source.recovered_owner(source.recovered_owner((self.out / 'before-edge_wrapper_owner').read_text()))
        self.receipt('inputs', immutable=len(source.PATHS), every_capture_flip_rejected=True,
            unknown_placeholder_rejected=True, no_production_change=True)

    def test_06_emitter_loop_state_provenance_and_effective_home_poison(self):
        bodies = dict(lifetime.candidates())
        root, out = self.root, self.root / lifetime.BUILD
        _, advance, row = lifetime.source.measure(root, out, 'qualified-advance', bodies['advance-edge'])
        self.assertEqual((row['words'], row['frame'], row['differences']), (264, 400, 183))
        for at, word in ((0x10C, 0xAFA40104), (0x114, 0xAFB80104), (0x3C4, 0x8FA20104)):
            self.assertEqual(advance[at // 4], word)
        record = fitting.trace(root, out, 'advance-edge', bodies['advance-edge'])
        defs = {stage: [r['length'] for r in rows if r['name'] == 'def' and r['storage'] == 'M']
            for stage, rows in record['records'].items()}
        self.assertEqual(defs, dict(frontend=[136], optimizer=[176]))
        self.assertTrue(record['code_unchanged'] and record['standalone_equals_complete_owner'])
        self.assertEqual([e['frame'] for e in record['events']], [0, 96, 224, 400])
        self.assertTrue(all(not e['pool'] and not e['temporary'] for e in record['events']))
        truth = list(struct.unpack_from('>266I', self.rom, lifetime.source.ROM))
        memory, args = edge.fixture(self.rom[0x2316B4:0x2316B4 + 33])

        class Writer(edge.EdgeOracle):
            def hook(model, target):
                super().hook(target)
                if target == lifetime.source.FACTORY and model.factory_count == 1:
                    model.put(model.r[29] + 0x18C, 2, 4)

        wanted = edge.EdgeOracle(truth, memory, args, edge.SAMPLES[2]).run().packets
        for words in (truth, advance):
            model = Writer(words, memory, args, edge.SAMPLES[2]).run()
            self.assertEqual(model.packets, wanted)
        _, wrong, _ = lifetime.source.measure(root, out, 'negative-addressed-edge', bodies['advance-home-read'])
        model = Writer(wrong, memory, args, edge.SAMPLES[2]).run()
        self.assertEqual((len(wanted), len(model.packets)), (10, 5))
        self.assertNotEqual(model.packets, wanted)
        self.receipt('loop-provenance', frontend=136, uopt=176, anonymous_increment=40, frame=400,
            no_UGEN_temporary=True, original_and_direct_advance_packets=10,
            addressed_update_control_packets=5, private_home_poison_is_guest_only=True,
            ordinary_addressed_update_is_not_the_retail_dead_edge_lifetime=True)

    def test_07_independent_original_and_C_relocations(self):
        text, functions, relocations = parse_object(self.obj)
        emitted, missing = emit_function(text, functions[source.FUNCTION], relocations, source.FUNCTION,
            dict(func_151700D8=source.CALLEE))
        self.assertEqual(missing, [])
        original = (self.out / 'before-edge_wrapper_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for name, body in (('selected', emitted), ('original', 'glabel ' + source.FUNCTION + '\n' + original)):
            path = self.out / (name + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        pairs = 0
        for number, delta in enumerate((0, 0x10000, -0x10000)):
            entry, callee = source.ENTRY + delta, source.CALLEE - delta
            script = self.out / ('rebase-%d.ld' % number)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for name, length in (('original', 61), ('selected', 63)):
                elf = self.out / ('%s-rebase-%d.elf' % (name, number))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=func_151700D8=0x%X' % callee, '-o', str(elf), str(self.out / (name + '-reloc.o'))], check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % length, sections(elf)['.text'][1])))
            if number == 0:
                self.assertEqual(bodies, [self.truth, self.words])
            with patch.object(source, 'CALLEE', callee):
                for pattern in range(4):
                    for phase in (0, 8):
                        memory, args = fixture(pattern=pattern)
                        packet, quad = packet_reference(memory, args, phase)
                        for words in bodies:
                            model = WrapperOracle(words, memory, args, phase, entry=entry).run()
                            self.assertEqual(model.calls, [(callee, *packet)])
                            self.assertEqual(model.quads, [quad])
                        pairs += 1
        self.receipt('rebases', independent_links=3, public_pairs=pairs,
            original_61_words_anchored=True, C_not_literal_match=True)

    def test_08_native32_O2_O0_all_signed_coordinate_patterns(self):
        harness = r'''typedef unsigned char u8;typedef short s16;typedef unsigned short u16;
typedef int s32;typedef unsigned int u32;typedef float f32;
DECLARATIONS
static u32 captured[22],callCount;
static u32 bits(f32 v){union{f32 f;u32 u;}p;p.f=v;return p.u;}
void func_151700D8(f32*q,f32 x,f32 z,s32 p,f32 s,s32 k,s32 nx,s32 nz,u8 f,s32 c){
 u32 i;callCount++;for(i=0;i<12;i++)captured[i]=bits(q[i]);captured[12]=bits(x);captured[13]=bits(z);
 captured[14]=(u32)p;captured[15]=bits(s);captured[16]=(u32)k;captured[17]=(u32)nx;captured[18]=(u32)nz;
 captured[19]=f;captured[20]=(u32)c;captured[21]=(u32)q;}
BODY
static void(*volatile invoke)(u8*,f32,f32,f32,f32,f32,s32,s32,s32,s32,f32,u8,s32)=func_151717FC;
static int run(void){static s16 actor[12];static const f32 scales[4]={-.5f,.25f,1.0f,2.0f};
 u32 i,j,k,wanted[21],p,kind,nx,nz,flag,context;f32 width,depth,ox,oy,oz,x,y,z,right,left,front,back,scale;
 if(sizeof(void*)!=4||sizeof(f32)!=4||sizeof(s16)!=2)return 9;
 for(i=0;i<65536;i++)for(j=0;j<4;j++){
  actor[8]=(s16)i;actor[9]=(s16)~i;actor[10]=(s16)(i*17u);width=j&1?-10.0f:10.0f;depth=j&2?-20.0f:20.0f;
  ox=.5f;oy=-1.25f;oz=3.5f;scale=scales[j];x=(f32)actor[8]+ox;y=(f32)actor[9]+oy;z=(f32)actor[10]+oz;
  right=width+x;left=x-width;front=depth+z;back=z-depth;
  wanted[0]=bits(right);wanted[1]=bits(y);wanted[2]=bits(front);wanted[3]=bits(left);wanted[4]=bits(y);wanted[5]=bits(front);
  wanted[6]=bits(left);wanted[7]=bits(y);wanted[8]=bits(back);wanted[9]=bits(right);wanted[10]=bits(y);wanted[11]=bits(back);
  p=0xABCD0000u+i;kind=~i;nx=i-32768u;nz=i;flag=i&255;context=0x87654321u^i;
  wanted[12]=bits(x);wanted[13]=bits(z);wanted[14]=p;wanted[15]=bits(scale);wanted[16]=kind;
  wanted[17]=nx;wanted[18]=nz;wanted[19]=flag;wanted[20]=context;
  callCount=0;invoke((u8*)actor,width,depth,ox,oy,oz,(s32)kind,(s32)p,(s32)nx,(s32)nz,scale,(u8)flag,(s32)context);
  if(callCount!=1||!captured[21]||(captured[21]&3))return 10;
  for(k=0;k<21;k++)if(captured[k]!=wanted[k])return 11;
 }return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''
        negatives = controls()
        exits = {}
        variants = [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
            (name, negatives[name], '-O2', False) for name in ('unsigned-coordinates', 'wrong-corner', 'narrow-preset')]
        for label, body, profile, valid in variants:
            path = self.out / ('native-' + label + '.c')
            path.write_text(harness.replace('DECLARATIONS', source.DECLARATIONS).replace('BODY', body))
            # Kernel entry is not a C call; realign before GCC's SSE stack stores.
            command = ['gcc', '-m32', '-msse2', '-mfpmath=sse', '-ffp-contract=off', profile,
                '-mstackrealign', '-fno-pie', '-no-pie', '-ffreestanding', '-nostdlib', '-fno-stack-protector']
            if valid:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            subprocess.run(command + ['-o', str(path.with_suffix('.elf')), str(path)], check=True, capture_output=True)
            result = subprocess.run([str(path.with_suffix('.elf'))], capture_output=True)
            exits[label] = result.returncode
            self.assertEqual(result.returncode == 0, valid, label)
        self.receipt('native', cases_per_O2_O0=262144, all_16_bit_patterns_each_coordinate=True,
            complete_quad_and_formal_packet=True, selected_UBSan=True, exits=exits,
            finite_float_domain_only=True, no_private_stack_or_guest_fault_claim=True)

    def test_10_word_preset_interface_retains_complete_emitted_owner(self):
        bodies = dict(lifetime.candidates())
        original, _, baseline = lifetime.source.measure(self.root, self.root / lifetime.BUILD,
            'preset-byte-interface', bodies['named-homes'])
        word, _, row = lifetime.source.measure(self.root, self.root / lifetime.BUILD,
            'preset-word-interface', bodies['word-preset'])
        self.assertEqual((row['words'], row['frame'], row['differences']), (266, 400, 137))
        self.assertEqual(row['diagnostics'], '')
        self.assertEqual(parse_object(original), parse_object(word))
        self.assertEqual(normalized_pools(original), normalized_pools(word))
        self.assertIn('f32 originZ, s32 preset', bodies['word-preset'])
        self.assertIn('presetByte = (u8)preset;', bodies['word-preset'])
        self.assertEqual(baseline['differences'], row['differences'])
        self.receipt('preset-interface', physical_input_word_preserved=True,
            per_edge_byte_interpretation=True, complete_owner_text_functions_relocations_pools_unchanged=True,
            wrapper_full_word_control_effective=True, not_additional_matching_credit=True)


if __name__ == '__main__':
    unittest.main()
