"""Direct direction writer: initialized homes, aliases, real trig and native32."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_random_unit_vector as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import MaskOracle, AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_record_fade_callback import state
from tools.tests import test_game_table_fade_match as archive

OUTPUT, OTHER = 0x20000, 0x21000
RANDOMS = ((0, 0), (0xFFFFFFFF, 0x80000000), (0x123456AB, 0xFEDCBA98), (0x87654321, 0x7FFFFFFF))


def fixture(flags=0, alias=0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-512, 256)}
    for base in (OUTPUT, OTHER):
        memory.update({base + i: 0xA5 for i in range(-16, 32)})
    offsets = ((0, 4, 8), (0, 0, 0), (0, 0, 8), (0, 4, 0))[alias]
    return memory, (flags, *(OUTPUT + i for i in offsets))


def provider(target, angle):
    return bits((angle - 128) / (128.0 if target == source.COSINE else 64.0))


def reference(memory, args, randoms, mode=0, trig=provider):
    memory, calls = dict(memory), []
    flags, x, y, z = args
    mask = 63 if flags & 64 else 127
    calls.append((source.RANDOM,))
    if mode == 1:
        x, y, z = OTHER, OTHER + 4, OTHER + 8
    first = randoms[0] & mask
    calls.append((source.COSINE, first))
    put(memory, y, trig(source.COSINE, first))
    first = 128 if mode == 2 else first
    calls.append((source.SINE, first))
    radius = floating(trig(source.SINE, first))
    calls.append((source.RANDOM,))
    second = randoms[1] & 255
    calls.append((source.COSINE, second))
    cosine = floating(trig(source.COSINE, second))
    calls.append((source.SINE, second))
    put(memory, x, bits(radius * floating(trig(source.SINE, second))))
    put(memory, z, bits(radius * cosine))
    return {a: v for a, v in memory.items() if a < STACK - 512 or a >= STACK + 256}, calls


class VectorOracle(MaskOracle):
    def __init__(self, words, memory, args, randoms, phase=0, mode=0, fault=None, connected=None):
        super().__init__(words, memory, phase=phase, mode=mode, fault=fault,
            entry=source.ENTRY, arguments=args, connected=connected)
        self.randoms, self.number, self.trigs = randoms, 0, 0

    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 7:
            self.f[word >> 6 & 31] = self.f[word >> 11 & 31] ^ 0x80000000
        else:
            super().execute(word)

    def record_call(self, target):
        assert target in (source.RANDOM, source.SINE, source.COSINE), hex(target)
        args = () if target == source.RANDOM else self.arguments(1)
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        if target == source.RANDOM:
            value = self.randoms[self.number]
            self.number += 1
            result = None
            if self.number == 1 and self.mode == 1:
                for i in range(3):
                    self.put(STACK + self.phase + 4 + i * 4, OTHER + i * 4, 4)
        else:
            self.trigs += 1
            result, value = provider(target, self.r[4]), 0xABCD0000 + self.trigs
            if self.trigs == 1 and self.mode == 2:
                self.put(STACK + self.phase - 0x14, 0xABCDEF80, 4)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = value
        if result is not None:
            self.f[0] = result


def controls():
    return {
        'wrong-mask': source.SELECTED.replace('mask = 0x3F;', 'mask = 0x7F;'),
        'wrong-flag': source.SELECTED.replace('flags & 0x40', 'flags & 0x20'),
        'reused-random': source.SELECTED.replace('randomWord = func_150ADA20() & 0xFF;', 'randomWord = randomWord & 0xFF;'),
        'narrow-azimuth': source.SELECTED.replace('func_150ADA20() & 0xFF;', 'func_150ADA20() & 0x7F;'),
        'wrong-output': source.SELECTED.replace('*y = func_150489B0', '*x = func_150489B0'),
        'wrong-product': source.SELECTED.replace('*z = radius * azimuthCosine;', '*z = radius * azimuthSine;'),
    }


class RandomUnitVectorTests(unittest.TestCase):
    test_09_all_original_801_archive_fingerprints = archive.TableFadeMatchTests.test_08_all_original_801_archive_fingerprints

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>41I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_raw_padding_neighbors_and_fail_closed_gate(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences'], self.row['diagnostics']), (41, 48, 0, ''))
        obj, diagnostics = source.build.compile_owner(self.root, self.out, (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            rel = lambda o, f: [(p - f['value'], r) for p, r in o[2].items() if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(rel(old, f), rel(new, g), name)
        self.assertEqual(normalized_pools(obj), normalized_pools(self.obj))
        for count, difference, frame, diagnostic in ((42, 0, 48, ''), (41, 1, 48, ''), (41, 0, 40, ''), (41, 0, 48, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=count, differences=difference, frame=frame, diagnostics=diagnostic))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner((self.out / 'before-preset_owner').read_text()))
        self.receipt('owner', exact_raw_and_padded_words=41, frame=48, unchanged_neighbors=len(old[1]) - 1,
            relative_relocations_pools_guards_profiles_fixed=True)

    def test_02_full_private_state_flags_aliases_and_physical_live_homes(self):
        count, visits = 0, set()
        for flags in range(256):
            for randoms in RANDOMS:
                for alias in range(4):
                    for phase in (0, 8):
                        for mode in range(3):
                            memory, args = fixture(flags | 0xABCD0000, alias)
                            models = [VectorOracle(w, memory, args, randoms, phase, mode).run() for w in (self.words, self.truth)]
                            self.assertEqual(state(models[0]), state(models[1]))
                            public = {a: v for a, v in models[0].memory.items() if a < STACK - 512 or a >= STACK + 256}
                            self.assertEqual((public, models[0].calls), reference(memory, args, randoms, mode))
                            visits |= models[0].visits
                            count += 1
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 164, 4)))
        self.receipt('abi', paired_cases=count, all_flag_bytes=True, all_words_visited=True,
            all_literal_private_state_equal=True, output_alias_patterns=4, phases=[0, 8],
            home_writes_and_stack_word_mutation_are_guest_only=True)

    def test_03_every_fired_memory_fault_prefix(self):
        count = 0
        for flags in (0, 64):
            for phase in (0, 8):
                for mode in range(3):
                    memory, args = fixture(flags)
                    whole = VectorOracle(self.truth, memory, args, RANDOMS[2], phase, mode).run()
                    for fault in range(whole.accesses):
                        models = [VectorOracle(w, memory, args, RANDOMS[2], phase, mode, fault) for w in (self.words, self.truth)]
                        for model in models:
                            with self.assertRaises(AccessFault):
                                model.run()
                        self.assertEqual(state(models[0]), state(models[1]))
                        count += 1
        self.receipt('faults', paired_fired_memory_cuts=count, literal_state_equal=True, no_native_fault_or_hardware_claim=True)

    def test_04_effective_compiled_semantic_controls(self):
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED, name)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '', name)
            failed = False
            for flags in (0, 32, 64):
                memory, args = fixture(flags)
                model = VectorOracle(words, memory, args, (0xFF, 0x81)).run()
                public = {a: v for a, v in model.memory.items() if a < STACK - 512 or a >= STACK + 256}
                failed |= (public, model.calls) != reference(memory, args, (0xFF, 0x81))
            self.assertTrue(failed, name)
        self.receipt('controls', effective_compiled_semantic_negatives=list(controls()))

    def test_05_native32_O2_O0_initialized_words_and_aliases(self):
        harness = r'''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef float f32;
static u32 samples[2],number,trace[6],count;static f32 output[8],expected[8];
__attribute__((noinline,noclone)) s32 func_150ADA20(void){trace[count++]=0x10000;return(s32)samples[number++];}
__attribute__((noinline,noclone)) f32 func_150489B0(u8 a){trace[count++]=0x20000+a;return((s32)a-128)/128.0f;}
__attribute__((noinline,noclone)) f32 func_15048A40(u8 a){trace[count++]=0x30000+a;return((s32)a-128)/64.0f;}
BODY
static void (*volatile invoke)(s32,f32*,f32*,f32*)=func_15170034;
static int check(u32 flags,u32 a,u32 b,u32 alias){u32 i,first=a&((flags&64)?63:127),second=b&255;
 u32 offsets[4][3]={{0,1,2},{0,0,0},{0,0,2},{0,1,0}},*p=offsets[alias];
 f32 radius=((s32)first-128)/64.0f,cs=((s32)second-128)/128.0f,sn=((s32)second-128)/64.0f;
 u32 want[6]={0x10000,0x20000+first,0x30000+first,0x10000,0x20000+second,0x30000+second};
 for(i=0;i<8;i++)output[i]=expected[i]=(f32)(i+100);
 expected[p[1]]=((s32)first-128)/128.0f;expected[p[0]]=radius*sn;expected[p[2]]=radius*cs;
 samples[0]=a;samples[1]=b;number=count=0;invoke((s32)flags,output+p[0],output+p[1],output+p[2]);
 if(number!=2||count!=6)return 10;for(i=0;i<6;i++)if(trace[i]!=want[i])return 11;
 for(i=0;i<8;i++)if(output[i]!=expected[i])return 12;return 0;}
static int run(void){u32 i,j,k;int r;if(sizeof(void*)!=4||sizeof(s32)!=4)return 13;
 for(i=0;i<256;i++)for(j=0;j<16;j++)for(k=0;k<4;k++){
  r=check(i|0xABCD0000u,i*1664525u+j*1013904223u,(255u-i)*1103515245u+j*12345u,k);if(r)return r;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''
        exits = {}
        for name, body, profile, ok in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + n, b, '-O2', False) for n, b in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace('BODY', body))
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-msse2', '-mfpmath=sse',
                '-mstackrealign', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie',
                '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation']
            if ok:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            else:
                command += ['-Wno-unused-parameter', '-Wno-unused-but-set-variable']
            result = subprocess.run([*command, str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            self.assertIn(result.returncode, (0,) if ok else (10, 11, 12), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=16384, selected_UBSan=True, effective_controls=6,
            exits=exits, guest_home_mutations_not_native_C=True)

    def test_06_independent_original_and_C_relocations(self):
        text, functions, rel = parse_object(self.obj)
        symbols = {'func_150ADA20': source.RANDOM, 'func_150489B0': source.COSINE, 'func_15048A40': source.SINE}
        emitted, missing = emit_function(text, functions[source.FUNCTION], rel, source.FUNCTION, symbols)
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for name, body in (('selected', emitted), ('original', 'glabel ' + source.FUNCTION + '\n' + original)):
            path = self.out / (name + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        for index, delta in enumerate((0, 0x10000, -0x10000)):
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + delta))
            outputs = []
            for name in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (name, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % (n, v - delta) for n, v in symbols.items()],
                    '-o', str(elf), str(self.out / (name + '-reloc.o'))], check=True, capture_output=True)
                outputs.append(list(struct.unpack_from('>41I', sections(elf)['.text'][1])))
            expected = [0x0C000000 | ((((w & 0x3FFFFFF) << 2) - delta) >> 2 & 0x3FFFFFF) if w >> 26 == 3 else w for w in self.truth]
            self.assertEqual(outputs, [expected, expected])
        self.receipt('rebases', independent_original_C_links=3, all_six_calls_and_all_41_words_equal=True)

    def test_07_actual_current_byte_trig_helpers_and_table(self):
        elf = (self.root / source.PATHS['elf']).read_bytes()
        code = {}
        for address, size in ((source.COSINE, 144), (source.SINE, 48)):
            offset = elf_slot_offset(elf, address, size)
            data = elf[offset:offset + size]
            rom = address - 0x15000000 + 0x2D4B0
            self.assertEqual(data, self.rom[rom:rom + size])
            code.update(zip(range(address, address + size, 4), struct.unpack('>%dI' % (size // 4), data)))
        offset = elf_slot_offset(elf, 0x8009A220, 260)
        table = elf[offset:offset + 260]
        self.assertEqual(self.rom.count(table), 1)
        values = struct.unpack('>65I', table)

        def trig(target, angle):
            angle = (angle - 64) & 255 if target == source.SINE else angle
            folded = angle if angle <= 64 else 128 - angle if angle <= 128 else angle - 128 if angle <= 192 else 256 - angle
            return values[folded] ^ (0x80000000 if 64 < angle <= 192 else 0)

        count = 0
        for first in range(128):
            for second in (0, 1, 63, 64, 65, 127, 128, 129, 191, 192, 193, 255):
                memory, args = fixture(0)
                memory.update({0x8009A220 + i: b for i, b in enumerate(table)})
                pair = [VectorOracle(w, memory, args, (first, second), connected=code).run() for w in (self.words, self.truth)]
                self.assertEqual(state(pair[0]), state(pair[1]))
                public = {a: v for a, v in pair[0].memory.items() if a < STACK - 512 or a >= STACK + 256}
                self.assertEqual(public, reference(memory, args, (first, second), trig=trig)[0])
                count += 1
        self.receipt('trig', connected_pairs=count, current_helper_words_including_return_delay=48, table_words=65,
            complete_quadrant_edges=True, RNG_is_opaque=True, not_full_gameplay=True)

    def test_08_frozen_predecessor_and_independent_prediction(self):
        source.freeze(self.root, self.out)
        expected = source.expected_inputs(self.root, self.out)
        self.receipt('prediction', changed_paths={key: hashlib.sha256(value).hexdigest() for key, value in expected.items()},
            exact_ELF_bytes=len(expected['elf']), anticipated_changed_bytes=sum(a != b for a, b in zip(
                (self.out / 'before-elf').read_bytes(), expected['elf'])))


if __name__ == '__main__':
    unittest.main()
