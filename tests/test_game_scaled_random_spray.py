"""Whole counted spray: physical packets, escaped outputs, induction and native ABI."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_scaled_random_spray as source
from tools.experiments import game_scaled_random_spray_proof as proof
from tools.pad_generated_object import parse_object
from tools import pad_generated_object as padder
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import game_scaled_random_spray_oracle as guest
from tools.tests import test_game_record_random_drag as prior


def controls():
    return {
        'skip-single': source.SELECTED.replace('if (count > 0)', 'if (count > 1)'),
        'short-loop': source.SELECTED.replace('while (index != count)', 'while (index + 1 < count)'),
        'wrong-direction-flag': source.SELECTED.replace('func_15170034(0x40,', 'func_15170034(0,'),
        'wrong-vertical-scale': source.SELECTED.replace('2.0f * scale', 'scale'),
        'wrong-z-source': source.SELECTED.replace('velocityZ = directionZ * scale', 'velocityZ = directionX * scale'),
        'swapped-coordinates': source.SELECTED.replace('func_1516D4E8(x, y, z,', 'func_1516D4E8(x, z, y,'),
        'missing-escaped-write': source.SELECTED.replace('            directionX = velocityX;\n', ''),
        'wrong-type': source.SELECTED.replace('z, 0x2F,', 'z, 0x2E,'),
        'byte-context': source.SELECTED.replace('flags, context);', 'flags, (u8)context);'),
    }


class ScaledRandomSprayTests(unittest.TestCase):
    test_09_all_801_archive_fingerprints = prior.RecordRandomDragTests.test_09_all_801_archive_fingerprints

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>119I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / ('qualification-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_complete_body_padding_and_all_owner_neighbors(self):
        self.assertEqual(self.words + [0], self.truth)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['real_raw_differences']), (118, 248, 47))
        old_obj, diagnostic = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostic, '')
        old, new = parse_object(old_obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda obj, f: {at - f['value']: rows for at, rows in obj[2].items()
                if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(old_obj), normalized_pools(self.obj))
        raw, rel = source.raw_target(self.obj)
        self.assertEqual(sorted(source.ORDER), list(range(118)))
        for at, old_index in enumerate(source.ORDER):
            before = struct.unpack_from('>I', raw, old_index * 4)[0]
            after = struct.unpack_from('>I', source.normalize(raw, rel), at * 4)[0]
            if before != after:
                mask = sum(31 << shift for shift in source.allocation.register_fields(before))
                self.assertEqual(before & ~mask, after & ~mask)
        self.assertEqual(parse_object(self.padded)[1][source.FUNCTION]['size'], 472)
        self.receipt('shape', body_words=118, slot_words=119, symbol_size=472, slot_bytes=476,
            guards=118, identity=71, transforming=47, all_operations_retained=True,
            one_automatic_padding_NOP=True, no_home_frame_constant_branch_or_call_binding_changes=True,
            neighbors_unchanged=len(old[1]) - 1, pools_unchanged=True)

    def test_02_arbitrary_loop_obligations_and_effective_negatives(self):
        result = proof.prove(self.raw_words, self.words)
        for at, mask in ((35, 4), (42, 1 << 11), (51, 1 << 11), (83, 1 << 16), (98, 4), (101, 1)):
            bad = list(self.words)
            bad[at] ^= mask
            with self.assertRaises(ValueError, msg=str(at)):
                proof.prove(self.raw_words, bad)
        equivalent = list(self.words)
        word = equivalent[42]
        equivalent[42] = word & ~((31 << 11) | (31 << 16)) | (word >> 11 & 31) << 16 | (word >> 16 & 31) << 11
        proof.prove(self.raw_words, equivalent)
        self.receipt('proof', **result, effective_instruction_negatives=6,
            finite_multiply_commutation_control_accepted=True)

    def test_03_whole_loops_physical_packets_and_escaped_objects(self):
        visits, cases = set(), 0
        for count, scale, flags, pattern, phase, mode in itertools.product((-3, 0, 1, 2, 5),
                (0.0, 0.25, 1.0, -0.5, 2.0), (0, 1, 128, 0xABCDEF81), range(3), (0, 8), range(5)):
            memory, args = guest.fixture(count, scale, flags, pattern)
            models = [guest.SprayOracle(words, memory, args, phase, mode).run()
                for words in (self.words, self.truth, self.raw_words)]
            self.assertEqual(guest.state(models[0]), guest.state(models[1]))
            expected = guest.reference(args, mode)
            for model in models:
                self.assertEqual((model.calls, model.packets, model.observed), expected)
            self.assertEqual(guest.public(models[0].memory), guest.public(models[2].memory))
            visits |= models[0].visits
            cases += 1
        self.assertEqual(cases, 3000)
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 472, 4)))
        self.receipt('semantics', cases=cases, all_118_body_words_visited=True,
            all_31_physical_factory_words=True, partial_direction_writes_and_factory_home_poison=True,
            raw_public_not_raw_private_claim=True, incoming_home_overwrite_guest_only=True)

    def test_04_fired_fault_prefixes_empty_reads_and_invalid_guest_only_cases(self):
        pairs = 0
        for count, phase, mode in itertools.product((-3, 1, 3), (0, 8), (0, 2, 4)):
            memory, args = guest.fixture(count, -0.5, pattern=2)
            whole = guest.SprayOracle(self.truth, memory, args, phase, mode).run()
            for fault in range(whole.accesses):
                models = [guest.SprayOracle(words, memory, args, phase, mode, fault=fault)
                    for words in (self.words, self.truth)]
                for model in models:
                    with self.assertRaises(guest.AccessFault):
                        model.run()
                self.assertEqual(guest.state(models[0]), guest.state(models[1]))
                pairs += 1
        for count in (-2147483648, -1, 0):
            memory, args = guest.fixture(count)
            for words in (self.words, self.truth, self.raw_words):
                model = guest.SprayOracle(words, memory, args)
                for at in range(guest.STACK + 16, guest.STACK + 28):
                    del model.memory[at]
                model.run()
                self.assertFalse(model.calls)
        for scale in (float('nan'), float('inf'), -float('inf'), 1.0e30):
            memory, args = guest.fixture(1, scale)
            models = [guest.SprayOracle(words, memory, args).run() for words in (self.words, self.truth)]
            self.assertEqual(guest.state(models[0]), guest.state(models[1]))
        self.receipt('faults', fired_prefix_pairs=pairs, empty_count_skips_all_three_stack_inputs=True,
            invalid_conversion_singletons=4, guest_only_not_native_C_or_hardware=True)

    def test_05_all_raw_and_actual_padder_word_binding_corruptions(self):
        raw, rel = source.raw_target(self.obj)
        parsed = parse_object(self.obj)
        start = parsed[1][source.FUNCTION]['value']
        for i in range(118):
            bad = bytearray(raw)
            bad[i * 4] ^= 1
            with self.assertRaisesRegex(ValueError, 'Unknown scaled-spray compiler'):
                source.normalize(bytes(bad), rel)
            tx = bytearray(parsed[0])
            tx[start + i * 4] ^= 1
            with patch.object(padder, 'parse_object', return_value=(bytes(tx), parsed[1], parsed[2])):
                with self.assertRaisesRegex(ValueError, 'stale word patch'):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'],
                        filename=source.OWNER, word_patches_path=self.out / 'qualified-guards.csv')
            bad_rel = dict(parsed[2])
            bad_rel[start + i * 4] = [('R_MIPS_32', 'wrong')]
            with patch.object(padder, 'parse_object', return_value=(parsed[0], parsed[1], bad_rel)):
                with self.assertRaisesRegex(ValueError, 'relocation'):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'],
                        filename=source.OWNER, word_patches_path=self.out / 'qualified-guards.csv')
        for at in rel:
            bad = dict(rel)
            bad[at] = [('R_MIPS_26', 'wrong')]
            with self.assertRaises(ValueError):
                source.normalize(raw, bad)
        with self.assertRaisesRegex(ValueError, 'guard predecessor'):
            source.guard_manifest((self.out / 'before-guards').read_bytes() + b'\n', raw, rel)
        self.receipt('corruptions', raw_flips=118, padder_word_flips=118, padder_binding_flips=118,
            changed_actual_bindings=2, complete_predecessor_closed=True)

    def test_06_effective_compiled_guest_negatives(self):
        effective = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED, name)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            different = False
            for count, mode in itertools.product((1, 3), (0, 4)):
                memory, args = guest.fixture(count, 2.0, pattern=2)
                try:
                    model = guest.SprayOracle(words, memory, args, mode=mode).run()
                except AssertionError:
                    self.assertEqual(name, 'wrong-direction-flag')
                    different = True
                else:
                    different |= (model.calls, model.packets, model.observed) != guest.reference(args, mode)
            self.assertTrue(different, name)
            effective.append(name)
        self.receipt('compiled-controls', effective=effective)

    def test_07_three_original_caller_windows_and_word_coordinate_ABI(self):
        target = struct.pack('>I', 0x0C000000 | (source.ENTRY >> 2 & 0x3FFFFFF))
        self.assertEqual([i for i in range(0, len(self.rom) - 3, 4) if self.rom[i:i + 4] == target],
            [0xF13B8, 0x1975F4, 0x197800])
        cases = 0
        for rom, entry, kind, count in ((0x1975AC, 0x1516A0FC, 0, 4),
                (0x1977B8, 0x1516A308, 1, 4), (0xF1370, 0x150C3EC0, 2, 10)):
            words = list(struct.unpack_from('>20I', self.rom, rom))
            for phase in (0, 8):
                memory, args = guest.fixture(1)
                actor = 0x28000
                memory.update({actor + i: 0 for i in range(256)})
                x, y, z = 50000.75, -60000.25, 32768.5
                for at, value in ((0x90, x), (0x98, z), (0xAC, 1.5), (0x14, x), (0x18, y), (0x1C, z)):
                    guest.put(memory, actor + at, guest.bits(value), 4)
                guest.put(memory, actor + 0xC, 0x81, 1)
                guest.put(memory, actor + 1, 0xFE, 1)
                model = guest.SprayOracle(words, memory, args, phase=phase, entry=entry, stop_entry=True)
                model.r[16] = actor
                model.f[4 if kind == 0 else 6] = guest.bits(y)
                model.f[18] = guest.bits(20.0)
                with self.assertRaises(guest.edge.CallBoundary):
                    model.run()
                scale = 2000.0 if kind == 2 else 300.0
                expected = (50000, (-59980 & 0xFFFFFFFF), 32768, count, guest.bits(scale),
                    255 if kind == 2 else 0x81, 0 if kind == 2 else 0xFE)
                self.assertEqual(model.entry_args, expected)
                cases += 1
        self.receipt('callers', windows=3, captured_ABI_cases=cases, full_word_float_truncations_before_callee_narrowing=True,
            complete_callers_not_claimed_restored=True)

    def test_10_native32_coordinate_bits_and_escaped_provider_contract(self):
        before = (self.out / 'before-preset_owner').read_text()
        prototype = source.build.body(before, 'func_1516D4E8').split('{', 1)[0]
        factory = prototype + '{u32 p[31]={' + ','.join('arg%d' % i for i in range(31)) + r'''};u32 i;
 if(n>=8){error=1;return;}for(i=0;i<31;i++)got[n][i]=p[i];
 for(i=0;i<3;i++)observed[n][i]=word(*out[i]);n++;
 if(mode==3||mode==4){*out[0]=rounded(*out[0]+0.5f);*out[1]=rounded(*out[1]-0.25f);*out[2]=-*out[2];}}
'''
        harness = r'''typedef unsigned char u8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;
static u32 got[8][31],observed[8][3],n,directions,mode,error;static f32 *out[3];
static const f32 samples[3][3]={{0.25f,-0.5f,1.5f},{-1.75f,0.375f,-0.0f},{32767.25f,-12345.5f,-32768.5f}};
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static __attribute__((noinline,noclone)) f32 rounded(f32 x){volatile f32 y=x;return y;}
static void func_15170034(s32 flags,f32*x,f32*y,f32*z){u32 j=directions++%3;
 if(flags!=64)error=2;out[0]=x;out[1]=y;out[2]=z;*x=samples[j][0];
 if(!((mode==1||mode==4)&&directions>1)){*y=samples[j][1];*z=samples[j][2];}}
FACTORY
BODY
static void(*volatile invoke)(s32,s32,s32,s32,f32,u8,s32)=func_151709B4;
static int check(u32 v,s32 count,u32 m){u32 i,j,k,p[31],expectedCount=count>0?(u32)count:0;
 s32 x=(s32)(0xABCD0000u|v),y=(s32)(0x12340000u|((v+0x5555u)&65535u)),z=(s32)(0xFEDC0000u|(v^0xAAAAu));
 u32 context=v*1103515245u+12345u;u8 flags=(u8)v;f32 scale[4]={0.0f,0.5f,-1.25f,2.0f},homes[3]={0,0,0},values[3],factors[3];s32 fx,fz,fy;
 n=directions=error=0;mode=m;invoke(x,y,z,count,scale[v&3],flags,(s32)context);
 if(error)return 20;if(n!=expectedCount||directions!=expectedCount)return 21;
 factors[0]=factors[2]=scale[v&3];factors[1]=rounded(scale[v&3]+scale[v&3]);
 for(i=0;i<expectedCount;i++){
 for(j=0;j<3;j++)values[j]=(i&&(m==1||m==4)&&j)?homes[j]:samples[i%3][j];
 for(j=0;j<3;j++){values[j]=rounded(values[j]*factors[j]);if(observed[i][j]!=word(values[j]))return 23;}
 fx=(s32)values[0];fy=(s32)values[1];fz=(s32)values[2];for(k=0;k<31;k++)p[k]=0;
 p[0]=(u32)(s32)(s16)x;p[1]=(u32)(s32)(s16)y;p[2]=(u32)(s32)(s16)z;
 p[3]=47;p[5]=p[6]=p[7]=p[9]=255;p[12]=7;p[13]=(u8)(fx>>8);p[14]=(u8)fx;p[15]=(u8)(fz>>8);p[16]=(u8)fz;
 p[23]=p[24]=512;p[25]=40;p[26]=(u32)(s32)(s16)fy;p[29]=flags;p[30]=context;
 for(k=0;k<31;k++)if(got[i][k]!=p[k])return 22;
 for(j=0;j<3;j++)homes[j]=values[j];if(m==3||m==4){homes[0]=rounded(homes[0]+0.5f);homes[1]=rounded(homes[1]-0.25f);homes[2]=-homes[2];}}
 return 0;}
static int run(void){u32 v,c,m;const s32 counts[4]={-1,0,1,3};const u32 modes[4]={0,1,3,4};int r;
 if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(s16)!=2)return 24;
 for(v=0;v<65536;v++)for(c=0;c<4;c++)for(m=0;m<4;m++){r=check(v,counts[c],modes[m]);if(r)return r;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''
        exits = {}
        for name, body, profile, valid in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace('FACTORY', factory).replace('BODY', body))
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-msse2', '-mfpmath=sse', '-mstackrealign',
                '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie',
                '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation']
            if valid:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            result = subprocess.run([*command, str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=60)
            self.assertIn(result.returncode, (0,) if valid else (20, 21, 22, 23), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=1048576, all_65536_coordinate_bit_patterns_each=True,
            correct_seven_argument_word_coordinate_ABI=True, all_flags_and_word_context=True,
            formal_factory_fields_and_escaped_float_observations=True, UBSan_selected=True,
            effective_negatives=len(controls()), exits=exits, no_physical_upper_bits_or_fault_FCSR_claim=True)

    def test_11_independent_original_raw_normalized_rebases(self):
        raw, rel = source.raw_target(self.obj)
        normalized = source.normalize(raw, rel)
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1]
        path = self.out / 'original-rebase.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n.type '
            + source.FUNCTION + ', @function\nglabel ' + source.FUNCTION + '\n' + original
            + '\n.size ' + source.FUNCTION + ', . - ' + source.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        tx, fs, rs = parse_object(path.with_suffix('.o'))
        f = fs[source.FUNCTION]
        original_raw = tx[f['value']:f['value'] + f['size']]
        original_rel = {at - f['value']: rows for at, rows in rs.items() if f['value'] <= at < f['value'] + f['size']}
        self.assertEqual(len(original_raw), 476)
        cases = 0
        for delta in (0, 0x10000, -0x10000):
            entry, direction, factory = source.ENTRY + delta, source.DIRECTION - delta, source.FACTORY - delta
            bindings = dict(func_15170034=direction, func_1516D4E8=factory)
            streams = [source.link_target(self.out, 'rebase-%X-%d' % (entry, i), data, rows, entry, bindings)
                for i, (data, rows) in enumerate(((original_raw, original_rel), (raw, rel), (normalized, rel)))]
            self.assertEqual(streams[0], streams[2] + [0])
            for count, phase, mode in itertools.product((-1, 0, 1, 3), (0, 8), (0, 4)):
                memory, args = guest.fixture(count, -0.5, pattern=2)
                expected = list(guest.reference(args, mode))
                expected[0] = [(factory, *row[1:]) if row[0] == source.FACTORY else row for row in expected[0]]
                models = [guest.SprayOracle(words, memory, args, phase, mode, entry=entry,
                    direction=direction, factory=factory).run() for words in streams]
                self.assertEqual(guest.state(models[0]), guest.state(models[2]))
                for model in models:
                    self.assertEqual((model.calls, model.packets, model.observed), tuple(expected))
                cases += 1
        self.receipt('rebases', independent_original_raw_normalized_links=3, cases=cases,
            all_call_bindings_and_padding_equal=True)

    def test_12_actual_direction_trig_factory_and_allocator_chain(self):
        image = (self.out / 'before-elf').read_bytes()
        connected = {}
        for address, rom, size in ((source.DIRECTION, 0x19D4E4, 164), (source.FACTORY, 0x19A998, 400),
                (0x15167A68, 0x194F18, 112), (0x150489B0, 0x75E60, 144), (0x15048A40, 0x75EF0, 48)):
            data = image[elf_slot_offset(image, address, size):][:size]
            self.assertEqual(data, self.rom[rom:rom + size])
            connected.update(zip(range(address, address + size, 4), struct.unpack('>%dI' % (size // 4), data)))
        table = image[elf_slot_offset(image, 0x8009A220, 260):][:260]
        self.assertEqual(table, self.rom[0x23ECE0:0x23ECE0 + 260])
        self.assertEqual(self.rom.find(table), 0x23ECE0)
        self.assertEqual(self.rom.find(table, 0x23ECE1), -1)
        values = struct.unpack('>65I', table)
        def trig(sine, angle):
            angle = (angle - 64) & 255 if sine else angle
            folded = angle if angle <= 64 else 128 - angle if angle <= 128 else angle - 128 if angle <= 192 else 256 - angle
            return guest.floating(values[folded] ^ (0x80000000 if 64 < angle <= 192 else 0))
        cases = 0
        for count, scale, randoms, phase, fail, pattern in itertools.product((-3, 0, 1, 4, 10),
                (0.0, 0.5, -1.25, 2000.0), guest.edge.SAMPLES, (0, 8), (False, True), (0, 2)):
            memory, args = guest.fixture(count, scale, pattern=pattern)
            memory.update({0x8009A220 + i: value for i, value in enumerate(table)})
            memory.update({0x30000 + i: (i * 13 + 0xA5) & 255 for i in range(1024)})
            def provider(number, old, mode):
                polar, azimuth = randoms[((number - 1) * 2) % 3] & 63, randoms[((number - 1) * 2 + 1) % 3] & 255
                radius = trig(True, polar)
                return (guest.bits(guest.rounded(radius * trig(True, azimuth))),
                    guest.bits(trig(False, polar)), guest.bits(guest.rounded(radius * trig(False, azimuth))))
            _, packets, observed = guest.reference(args, provider=provider)
            models = []
            for words in (self.words, self.truth, self.raw_words):
                model = guest.SprayOracle(words, memory, args, phase=phase, connected=connected, allocation_fail=fail)
                model.randoms = randoms
                model.run()
                self.assertEqual((model.packets, model.observed), (packets, observed))
                models.append(model)
            self.assertEqual(guest.state(models[0]), guest.state(models[1]))
            self.assertEqual(guest.public(models[0].memory), guest.public(models[2].memory))
            cases += 1
        self.receipt('connected', cases=cases, actual_current_connected_words=217, trig_table_ROM=0x23ECE0,
            real_direction_trig_table_factory_allocator=True, allocation_failure=True,
            RNG_heap_and_registration_opaque=True, no_full_gameplay_or_hardware_claim=True)

    def test_08_all_69_frozen_live_inputs_and_capture_corruptions(self):
        source.freeze(self.root, self.out)
        expected = source.expected_inputs(self.root, self.out)
        self.assertEqual(len(source.PATHS), 69)
        for key, path in source.PATHS.items():
            before = (self.out / ('before-' + key)).read_bytes()
            self.assertEqual(hashlib.sha256(before).hexdigest(), source.BASELINE[key])
            self.assertIn((self.root / path).read_bytes(), (before, expected.get(key, before)), key)
        rb = Path.read_bytes
        for key in source.PATHS:
            target = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        self.receipt('inputs', protected_inputs=69, all_capture_corruptions_rejected=True,
            expected_after={key: hashlib.sha256(data).hexdigest() for key, data in expected.items()})


if __name__ == '__main__':
    unittest.main()
