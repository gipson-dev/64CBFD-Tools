"""Directional burst: both physical packets, ordered proof and native ABI."""
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_directional_burst_match as source
from tools.experiments import game_directional_burst_proof as proof
from tools.experiments.game_actor_classifier_candidates import sections
from tools import pad_generated_object as padder
from tools.pad_generated_object import parse_object
from tools.tests import game_directional_burst_oracle as guest
from tools.tests import test_game_quad_edge_emitter as edge
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset


def controls():
    body = source.SELECTED
    return {
        'unsigned-remainder': body.replace('func_151EF610() % 50', '(u32)func_151EF610() % 50U'),
        'wrong-default': body.replace('if (compact == 0)', 'if (compact != 0)', 1),
        'byte-mode': body.replace('compact == 0', '(u8)compact == 0').replace('compact != 0', '(u8)compact != 0'),
        'wrong-polar-helper': body.replace('polarCosine = func_150489B0', 'polarCosine = func_15048A40'),
        'wrong-negation': body.replace('negativeYawSine = -func_', 'negativeYawSine = func_'),
        'wrong-scale': body.replace('256.0f', '128.0f'),
        'wrong-record-type': body.replace('z, 0x2A,', 'z, 0x29,'),
        'word-default-load': body.replace('angle = D_800CC34A;', 'angle = *(u32 *)&D_800CC34A;'),
    }


class DirectionalBurstMatchTests(unittest.TestCase):
    test_10_all_801_archive_fingerprints = edge.QuadEdgeEmitterTests.test_10_all_original_801_archive_fingerprints

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>184I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / ('qualification-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_owner_neighbors_padding_and_closed_operation_identity(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual((self.row['raw_words'], self.row['raw_differences'], self.row['frame']), (185, 97, 256))
        self.assertEqual((self.row['guards_added'], self.row['identity_guards']), (185, 67))
        raw, rel = source.raw_target(self.obj)
        self.assertEqual((hashlib.sha256(raw).hexdigest(), rel), (source.RAW_SHA256, source.RELOCATIONS))
        with self.assertRaises(ValueError) as overflow:
            padder.emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'], filename=source.OWNER,
                word_patches_path=self.out / 'before-guards')
        self.assertIn(source.FUNCTION, str(overflow.exception))
        before, diagnostic = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostic, '')
        old, new = parse_object(before), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'])
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']])
            rels = lambda obj, f: {at - f['value']: rows for at, rows in obj[2].items() if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(rels(old, f), rels(new, g))
        self.assertEqual(normalized_pools(before), normalized_pools(self.obj))
        normalized, moved = source.normalize(raw, rel)
        a, b = struct.unpack('>185I', raw), struct.unpack('>184I', normalized)
        self.assertEqual(sorted(source.ORDER), [i for i in range(185) if i != 32])
        self.assertEqual(a[32], 0x44805000)
        for at, old_index in enumerate(source.ORDER):
            value = a[old_index]
            mask = sum(31 << shift for shift in source.register_fields(value))
            if value >> 21 & 31 == 29 and value >> 26 in (35, 43) and value & 65535 == 0xD0:
                value = value & ~65535 | 0xD4
            if value >> 26 in (4, 5):
                mask |= 65535
            self.assertEqual(value & ~mask, b[at] & ~mask)
        rows = [row for row in csv.DictReader(io.StringIO((self.out / 'qualified-guards.csv').read_text())) if row['function'] == source.FUNCTION]
        self.assertEqual([row['offset'] for row in rows if row['omit'] == 'true'], ['0x80'])
        self.assertTrue(all(not row['insert_after'] for row in rows))
        self.assertEqual(len(moved), 8)
        self.receipt('shape', unchanged_neighbors=len(old[1]) - 1, raw_words=185, normalized_words=184,
            raw_differences=97, identity_guards=67, retained_operations=184, duplicate_zero_transfer_omitted=1,
            no_opcode_or_constant_replacement_except_private_home_and_branch_distances=True)

    def test_02_ordered_value_graph_and_effective_instruction_controls(self):
        result = proof.prove(self.raw_words, self.words)
        self.assertTrue(result['no_commutative_FP_or_constant_arithmetic_lemma_used'])
        effective = []
        for name, old, new in (
                ('unsigned-divide', 0x0041001A, 0x0041001B),
                ('wrong-default-width', 0x94E7C34A, 0x90E7C34A),
                ('wrong-negation', 0x46000307, 0x46000306),
                ('wrong-flags-home', 0x93AE0117, 0x93AE0114),
                ('wrong-context-home', 0x8FAF0118, 0x8FAF0110)):
            words = list(self.words)
            words[words.index(old)] = new
            with self.assertRaises(ValueError, msg=name):
                proof.prove(self.raw_words, words)
            effective.append(name)
        words = list(self.words)
        at = words.index(0x46001082)
        words[at] = 0x46020082
        with self.assertRaises(ValueError):
            proof.prove(self.raw_words, words)
        effective.append('ordered-multiply-operands')
        legal = list(self.words)
        legal[2], legal[3] = legal[3], legal[2]
        proof.prove(self.raw_words, legal)
        self.receipt('proof', **result, effective_instruction_controls=effective,
            independent_save_permutation_accepted=True)

    def test_03_all_184_words_private_states_and_independent_packets(self):
        cases, visited = 0, set()
        for compact, angle, random, pattern, phase, mode in itertools.product(
                (0, 1, 0x12340100, 0xFFFFFFFF), (0, 1, 64, 128, 255, 0xABCDEF81),
                (0, 1, 49, 50, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 0x12345678), range(3), (0, 8), range(4)):
            memory, args = guest.fixture(compact, angle, pattern=pattern)
            wanted, calls, packet = guest.reference(memory, args, random, phase, mode)
            models = [guest.BurstOracle(words, memory, args, random, phase, mode).run() for words in (self.words, self.truth)]
            self.assertEqual(guest.state(models[0]), guest.state(models[1]))
            self.assertEqual(models[0].calls, calls)
            self.assertEqual(models[0].packets, [packet])
            self.assertEqual(guest.public(models[0].memory), wanted)
            visited |= models[0].visits
            cases += 1
        self.assertEqual(cases, 4608)
        self.assertEqual(visited, set(range(source.ENTRY, source.ENTRY + 736, 4)))
        self.receipt('private', pairs=cases, all_184_words_visited=True, complete_literal_state_equal=True,
            all_31_and_49_physical_words=True, incoming_home_and_mode_flips_guest_only=True)

    def test_04_all_fired_memory_prefixes_and_yaw_home_poison(self):
        pairs = 0
        for compact, phase, mode in itertools.product((0, 0x12340100), (0, 8), range(4)):
            memory, args = guest.fixture(compact, pattern=2)
            whole = guest.BurstOracle(self.truth, memory, args, 0xFFFFFFFF, phase, mode).run()
            for cut in range(whole.accesses):
                models = [guest.BurstOracle(words, memory, args, 0xFFFFFFFF, phase, mode, fault=cut) for words in (self.words, self.truth)]
                for model in models:
                    with self.assertRaises(guest.AccessFault):
                        model.run()
                self.assertEqual(guest.state(models[0]), guest.state(models[1]))
                pairs += 1
        class Writer(guest.BurstOracle):
            def hook(model, target):
                super().hook(target)
                if target == source.previous.COSINE and model.trig_count == 1:
                    model.put(model.r[29] + 0xD4, 0xABCD00FE, 4)
        for compact in (0, 1):
            memory, args = guest.fixture(compact)
            models = [Writer(words, memory, args, 0xFFFFFFFF).run() for words in (self.words, self.truth, self.raw_words)]
            self.assertEqual(guest.state(models[0]), guest.state(models[1]))
            self.assertNotEqual(models[0].calls, models[2].calls)
            self.assertEqual(models[0].calls[2], (source.previous.SINE, 0xABCD00FE))
        self.receipt('faults', fired_prefix_pairs=pairs, exact_literal_fault_state=True,
            yaw_home_guest_poison_pairs=2, raw_home_difference_effective=True,
            no_portable_C_home_poison_claim=True)

    def test_05_actual_padder_and_all_word_binding_corruptions(self):
        raw, rel = source.raw_target(self.obj)
        parsed = parse_object(self.obj)
        start = parsed[1][source.FUNCTION]['value']
        for i in range(185):
            bad = bytearray(raw)
            bad[i * 4] ^= 1
            with self.assertRaisesRegex(ValueError, 'Unknown burst compiler'):
                source.normalize(bytes(bad), rel)
            text = bytearray(parsed[0])
            text[start + i * 4] ^= 1
            with patch.object(padder, 'parse_object', return_value=(bytes(text), parsed[1], parsed[2])):
                with self.assertRaisesRegex(ValueError, 'stale word patch'):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'], filename=source.OWNER,
                        word_patches_path=self.out / 'qualified-guards.csv')
            changed = dict(parsed[2])
            changed[start + i * 4] = [('R_MIPS_32', 'wrong')]
            with patch.object(padder, 'parse_object', return_value=(parsed[0], parsed[1], changed)):
                with self.assertRaisesRegex(ValueError, 'relocation'):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'], filename=source.OWNER,
                        word_patches_path=self.out / 'qualified-guards.csv')
        for at in rel:
            changed = dict(rel)
            changed[at] = [('R_MIPS_26', 'wrong')]
            with self.assertRaisesRegex(ValueError, 'Unknown burst compiler'):
                source.normalize(raw, changed)
        self.receipt('corruptions', raw_word_flips=185, production_padder_word_flips=185,
            production_padder_binding_flips=185, actual_external_bindings=len(rel))

    def test_06_effective_compiled_guest_negatives(self):
        effective = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED)
            _, words, row = source.previous.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            different = False
            for compact in (0, 0x12340100):
                memory, args = guest.fixture(compact, angle=0xFFFF0081, pattern=2)
                model = guest.BurstOracle(words, memory, args, 0xFFFFFFFF)
                try:
                    model.run()
                except AssertionError:
                    self.assertEqual(name, 'word-default-load')
                    different = True
                else:
                    different |= model.calls != guest.reference(memory, args, 0xFFFFFFFF)[1]
            self.assertTrue(different, name)
            effective.append(name)
        self.receipt('compiled-controls', effective_guest_negatives=effective, wide_default_unaligned_guest_only=True)

    def test_07_independent_original_raw_normalized_links(self):
        raw, rel = source.raw_target(self.obj)
        normalized, moved = source.normalize(raw, rel)
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        path = self.out / 'original-rebase.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n.type ' + source.FUNCTION
            + ', @function\nglabel ' + source.FUNCTION + '\n' + original + '\n.size ' + source.FUNCTION + ', . - ' + source.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        tx, fs, rs = parse_object(path.with_suffix('.o'))
        f = fs[source.FUNCTION]
        original_raw = tx[f['value']:f['value'] + f['size']]
        original_rel = {at - f['value']: rows for at, rows in rs.items() if f['value'] <= at < f['value'] + f['size']}
        pairs = 0
        for number, delta, default in ((0, 0, source.previous.DEFAULT_ANGLE), (1, 0x10000, 0x80318002), (2, -0x10000, 0x80427FFE)):
            entry = source.ENTRY + delta
            mapping = dict(RANDOM=source.previous.RANDOM - delta, COSINE=source.previous.COSINE - delta,
                SINE=source.previous.SINE - delta, SMALL=source.previous.SMALL - delta, LARGE=source.previous.LARGE - delta,
                DEFAULT_ANGLE=default, ENTRY=entry)
            bindings = dict(D_800CC34A=default, func_151EF610=mapping['RANDOM'], func_150489B0=mapping['COSINE'],
                func_15048A40=mapping['SINE'], func_1516D4E8=mapping['SMALL'], func_1516D99C=mapping['LARGE'])
            bodies = [source.link_target(self.out, '%s-rebase-%d' % (name, number), body, rows, entry, bindings)
                for name, body, rows in (('original', original_raw, original_rel), ('normalized', normalized, moved), ('raw', raw, rel))]
            self.assertEqual(bodies[0], bodies[1])
            with patch.multiple(source.previous, **mapping):
                proof.prove(bodies[2], bodies[1])
                for compact, mode in itertools.product((0, 0x12340100), range(4)):
                    memory, args = guest.fixture(compact, pattern=2)
                    models = [guest.BurstOracle(words, memory, args, 0xFFFFFFFF, mode=mode, entry=entry).run() for words in bodies]
                    self.assertEqual(guest.state(models[0]), guest.state(models[1]))
                    for model in models:
                        self.assertEqual(model.calls, guest.reference(memory, args, 0xFFFFFFFF, mode=mode)[1])
                    pairs += 1
        self.receipt('rebases', independent_three_stream_links=3, private_pairs=pairs,
            all_184_normalized_words_and_six_call_sites=True, default_HI_LO_signed_carry_tested=True)

    def test_08_actual_current_rng_trig_factories_and_allocator(self):
        image = (self.out / 'before-elf').read_bytes()
        connected = {}
        for address, rom, size in ((source.previous.RANDOM, 0x21CAC0, 44), (source.previous.COSINE, 0x75E60, 144),
                (source.previous.SINE, 0x75EF0, 48), (source.previous.SMALL, 0x19A998, 400),
                (source.previous.LARGE, 0x19AE4C, 500), (0x15167A68, 0x194F18, 112)):
            data = image[elf_slot_offset(image, address, size):][:size]
            self.assertEqual(data, self.rom[rom:rom + size])
            connected.update(zip(range(address, address + size, 4), struct.unpack('>%dI' % (size // 4), data)))
        table = image[elf_slot_offset(image, 0x8009A220, 260):][:260]
        values = struct.unpack('>65I', table)
        def trig(target, angle):
            angle = (angle - 64) & 255 if target == source.previous.SINE else angle
            folded = angle if angle <= 64 else 128 - angle if angle <= 128 else angle - 128 if angle <= 192 else 256 - angle
            return values[folded] ^ (0x80000000 if 64 < angle <= 192 else 0)
        pairs = 0
        for seed, angle, compact, phase, fail in itertools.product((0, 1, 0xFFFFFFFF, 0x80000001, 0x12345678, 0x7FFFFFFF),
                (0, 63, 64, 128, 193, 255), (0, 1, 0x12340100, 0xFFFFFFFF), (0, 8), (False, True)):
            memory, args = guest.fixture(compact, angle, default=angle, pattern=2)
            memory.update({0x8009A220 + i: value for i, value in enumerate(table)})
            memory.update({0x30000 + i: (i * 13 + 0xA5) & 255 for i in range(1024)})
            guest.put(memory, 0x80091970, seed)
            random = (((seed * 4 + 2) & 0xFFFFFFFF) * ((seed * 4 + 3) & 0xFFFFFFFF) & 0xFFFFFFFF) >> 2
            models = [guest.BurstOracle(words, memory, args, phase=phase, connected=connected, allocation_fail=fail).run()
                for words in (self.words, self.truth)]
            self.assertEqual(guest.state(models[0]), guest.state(models[1]))
            self.assertEqual(models[0].packets, [guest.reference(memory, args, random, phase, trig=trig)[2]])
            self.assertEqual(guest.read(models[0].memory, 0x80091970), random)
            pairs += 1
        self.receipt('connected-chain', pairs=pairs, actual_current_connected_words=312, actual_rng_seed_transition=True,
            real_trig_table_and_both_current_factories=True, heap_and_registration_opaque=True,
            allocation_failure_exercised=True, no_gameplay_or_hardware_claim=True)

    def test_09_original_three_caller_windows_and_all_inputs(self):
        jal = struct.pack('>I', 0x0C000000 | (source.ENTRY >> 2 & 0x3FFFFFF))
        self.assertEqual([i for i in range(0, len(self.rom) - 3, 4) if self.rom[i:i + 4] == jal], [0x1A9A48, 0x1A9AE4, 0x1AA1B4])
        cases = 0
        for rom, entry, count, compact in ((0x1A9A1C, 0x1517C56C, 13, 0), (0x1A9AB8, 0x1517C608, 13, 0),
                (0x1AA18C, 0x1517CCDC, 12, 1)):
            words = list(struct.unpack_from('>%dI' % count, self.rom, rom))
            for phase, y in itertools.product((0, 8), (-32768, -1, 32767)):
                memory, args = guest.fixture()
                points = 0x24000
                for i, value in enumerate((-123, y, 321)):
                    guest.put(memory, points + i * 2, value, 2)
                guest.put(memory, 0x25000, points)
                model = guest.BurstOracle(words, memory, args, phase=phase, entry=entry)
                model.r[23], model.r[19], model.r[2], model.r[25] = 0x25000, 0, points, 0
                with self.assertRaises(edge.CallBoundary):
                    model.run()
                self.assertEqual(model.entry_args, (-123 & 0xFFFFFFFF, (y + 68) & 0xFFFFFFFF, 321, 0, compact, 255, 0))
                cases += 1
        source.freeze(self.root, self.out)
        expected = source.expected_inputs(self.root, self.out)
        for key, path in source.PATHS.items():
            before = (self.out / ('before-' + key)).read_bytes()
            self.assertEqual(hashlib.sha256(before).hexdigest(), source.BASELINE[key], key)
            self.assertIn((self.root / path).read_bytes(), (before, expected.get(key, before)), key)
        rb = Path.read_bytes
        for key in source.PATHS:
            target = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        self.receipt('inputs-and-callers', original_caller_windows=3, captured_ABI_cases=cases,
            immutable_inputs=len(source.PATHS), every_capture_flip_rejected=True,
            expected_after={key: hashlib.sha256(value).hexdigest() for key, value in expected.items()},
            current_large_caller_not_restored=True, installed_image_requires_separate_gate=True)

    def test_11_native32_exhaustive_coordinate_bits_both_factories(self):
        before = (self.out / 'before-preset_owner').read_text()
        factories = []
        for name, count in (('func_1516D4E8', 31), ('func_1516D99C', 49)):
            prototype = source.build.body(before, name).split('{', 1)[0]
            factories.append(prototype + '{u32 p[%d]={' % count + ','.join('arg%d' % i for i in range(count))
                + '};u32 i;gotCount=%d;for(i=0;i<%d;i++)got[i]=p[i];}\n' % (count, count))
        harness = r'''typedef unsigned char u8;typedef short s16;typedef unsigned short u16;
typedef int s32;typedef unsigned int u32;typedef float f32;
u16 D_800CC34A;static u32 rngWord,got[49],gotCount,order[5],orderCount;
static s32 func_151EF610(void){order[orderCount++]=0;D_800CC34A=0x4321;return(s32)rngWord;}
static f32 func_150489B0(u8 a){order[orderCount++]=1;return(f32)((s32)a-128)/128.0f;}
static f32 func_15048A40(u8 a){order[orderCount++]=2;return(f32)((s32)a-128)/64.0f;}
static __attribute__((noinline,noclone)) f32 rounded(f32 x){volatile f32 y=x;return y;}
FACTORIES
BODY
static void(*volatile invoke)(s16,s16,s16,s32,s32,u8,s32)=func_15170500;
static int check(u32 value,u32 compact,u32 variant){
 s16 x=(s16)value,y=(s16)(value+0x5555),z=(s16)(value^0xAAAA);
 u32 angle=0xABCD0000u|value,context=value*1103515245u+12345u,wanted[49],i,n=compact?31:49;
 u8 flags=(u8)value,yaw,polar;f32 c,s,p,vx,vz;s32 random,fx,fz;
 D_800CC34A=(u16)(value^0xAACD);yaw=(u8)(compact?angle:D_800CC34A);
 rngWord=variant?value*1664525u+1013904223u:(u32)((s32)value-32768);random=(s32)rngWord;
 polar=(u8)(random%50);c=rounded((f32)((s32)yaw-128)/128.0f);
 s=rounded((f32)((s32)yaw-128)/64.0f);p=rounded((f32)((s32)polar-128)/128.0f);
 vx=rounded(c*p);vz=rounded(-s*p);vx=rounded(vx+vx);vz=rounded(vz+vz);
 fx=(s32)rounded(vx*256.0f);fz=(s32)rounded(vz*256.0f);
 for(i=0;i<49;i++)wanted[i]=0;wanted[0]=(u32)(s32)x;wanted[1]=(u32)(s32)y;wanted[2]=(u32)(s32)z;
 wanted[3]=42;wanted[5]=wanted[6]=wanted[7]=255;wanted[12]=6;
 wanted[13]=(u8)(fx>>8);wanted[14]=(u8)fx;wanted[15]=(u8)(fz>>8);wanted[16]=(u8)fz;
 if(compact){wanted[22]=1;wanted[23]=512;wanted[24]=358;wanted[25]=255;wanted[26]=(u32)(s32)(s16)-50;
 wanted[29]=flags;wanted[30]=context;}else{wanted[27]=512;wanted[28]=358;wanted[31]=20;
 wanted[34]=wanted[35]=255;wanted[36]=(u32)(s32)(s16)-50;wanted[37]=200;wanted[38]=9;wanted[39]=1;
 wanted[41]=1;wanted[42]=50;wanted[43]=20;wanted[47]=flags;wanted[48]=context;}
 orderCount=gotCount=0;invoke(x,y,z,(s32)angle,compact?(s32)0x12340100u:0,flags,(s32)context);
 if(orderCount!=4||order[0]!=0||order[1]!=1||order[2]!=2||order[3]!=1)return 10;
 if(gotCount!=n)return 11;for(i=0;i<n;i++)if(got[i]!=wanted[i])return 12;
 if(D_800CC34A!=0x4321)return 13;return 0;}
static int run(void){u32 v,c,r;int result;if(sizeof(void*)!=4||sizeof(s16)!=2||sizeof(s32)!=4)return 14;
 for(v=0;v<65536;v++)for(c=0;c<2;c++)for(r=0;r<2;r++){result=check(v,c,r);if(result)return result;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''
        negatives = {name: body for name, body in controls().items() if name != 'word-default-load'}
        exits = {}
        for name, body, profile, valid in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in negatives.items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace('FACTORIES', ''.join(factories)).replace('BODY', body))
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-msse2', '-mfpmath=sse',
                '-mstackrealign', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie',
                '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation']
            if valid:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            result = subprocess.run([*command, str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=40)
            self.assertIn(result.returncode, (0,) if valid else (10, 11, 12, 13), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=262144, all_65536_coordinate_bit_patterns_each=True,
            seven_argument_typed_function_pointer=True, both_formally_projected_factory_packets=True,
            all_flag_bytes_high_mode_angle_context_and_signed_randoms=True, UBSan_selected=True,
            effective_native_negatives=len(negatives), exits=exits, no_guest_stack_fault_FCSR_claim=True)

    def test_12_fired_compiler_frame_observation(self):
        from tools.experiments import game_table_fade_frame as observer
        e = source.previous
        before = (self.out / 'before-preset_owner').read_text()
        declarations = e.DECLARATIONS + ''.join(source.build.body(before, name).split('{', 1)[0].strip() + ';\n'
            for name in ('func_1516D4E8', 'func_1516D99C')) + 'f32 func_150489B0(u8);\nf32 func_15048A40(u8);\n'
        with patch.object(observer, 'source', e), patch.object(e, 'DECLARATIONS', declarations):
            receipt = observer.trace(self.root, self.out, 'selected-frame', source.SELECTED)
        self.assertTrue(receipt['code_unchanged'] and receipt['standalone_equals_complete_owner'])
        self.assertEqual([row['frame'] for row in receipt['events']], [0, 8, 208, 256])
        self.assertEqual((receipt['events'][-1]['locals'], receipt['events'][-1]['outgoing'],
            receipt['events'][-1]['saved'], receipt['events'][-1]['temporary']), (48, 200, 8, 0))
        self.assertTrue(all(row.endswith(' code=0') for row in receipt['completed_exits']))
        definitions = {stage: [row['length'] for row in rows if row['name'] == 'def' and row['storage'] == 'M']
            for stage, rows in receipt['records'].items()}
        self.assertEqual(definitions, dict(frontend=[41], optimizer=[48]))
        self.receipt('compiler-frame', definitions=definitions, events=receipt['events'],
            normal_and_traced_full_objects_and_pools_equal=True, producer_consumer_driver_exits=receipt['completed_exits'])


if __name__ == '__main__':
    unittest.main()
