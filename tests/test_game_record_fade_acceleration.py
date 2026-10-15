"""Full-word fade, live signed acceleration, literal ABI/faults and real slot 5."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_fade_acceleration as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_record_fade_callback as fade
from tools.tests import test_game_packed_record_updater as updater
from tools.tests import test_game_table_fade_match as archive

RECORD, OTHER, BINDING = fade.RECORD, fade.OTHER, fade.BINDING


def fixture(value=128, active=1, delta=1, velocity=32767, acceleration=128,
        record=RECORD, phase=0, step=source.STEP, binding=BINDING):
    memory = fade.fixture(value, active, delta, record, phase, step, binding)
    put(memory, record + 0x23, 5, 1)
    put(memory, record + 0x18, velocity, 2)
    put(memory, record + 0x2C, acceleration, 1)
    put(memory, OTHER + 0x18, 0x8000, 2)
    put(memory, OTHER + 0x2C, 0xFF, 1)
    return memory


def prefix(memory, mode=0, record=RECORD, step=source.STEP):
    memory = dict(memory)
    value, enabled = read(memory, record + 0x1F, 1), read(memory, record + 0x24, 1)

    def byte_store():
        put(memory, record + 0x1F, value, 1)
        if mode == 3:
            put(memory, record + 0x24, not read(memory, record + 0x24, 1), 1)

    if enabled:
        if value != 255:
            value = min(255, fade.signed(value + read(memory, step) * 16))
            byte_store()
    else:
        if value:
            value = max(0, fade.signed(value - read(memory, step) * 8))
            byte_store()
        extent = fade.signed(value * 512) // 256
        put(memory, record + 0x16, extent, 2)
        put(memory, record + 0x14, extent, 2)
    return memory, read(memory, record + 0x24, 1) == 0 and value == 0


def accelerate(memory, record):
    value = read(memory, record + 0x2C, 1)
    value -= 256 if value & 128 else 0
    put(memory, record + 0x18, fade.short(read(memory, record + 0x18, 2)) + value, 2)


def reference(memory, mode=0, record=RECORD, step=source.STEP, move=source.MOVE):
    memory, done = prefix(memory, mode, record, step)
    if done:
        return fade.external(memory), [], 1
    if mode == 2:
        put(memory, record + 0x18, 0x7FFF, 2)
        put(memory, record + 0x2C, 0x80, 1)
        put(memory, step, 0x87654321)
    accelerate(memory, OTHER if mode == 1 else record)
    return fade.external(memory), [(move, record)], 0


class AccelerationOracle(fade.FadeOracle):
    def __init__(self, words, memory, phase=0, mode=0, fault=None, record=RECORD,
            entry=source.ENTRY, step=source.STEP, move=source.MOVE, connected=None):
        super().__init__(words, memory, phase, mode, fault, record, entry, step, move, connected=connected)

    def record_call(self, target):
        self.calls.append((target, *self.arguments(1)))
        self.events.append(('CALL', target, self.arguments(1)))

    def hook(self, target):
        if target != self.move:
            assert target in (updater.UNLINK, updater.DEFAULT, updater.DESTRUCTOR), hex(target)
            return updater.UpdaterOracle.hook(self, target)
        if self.mode == 1:
            self.put(STACK + self.phase, OTHER, 4)
        elif self.mode == 2:
            self.put(self.r[4] + 0x18, 0x7FFF, 2)
            self.put(self.r[4] + 0x2C, 0x80, 1)
            self.put(self.symbols['delta'], 0x87654321, 4)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.lo, self.condition, self.r[2] = 0x87654321, True, 0xABCD0001


def controls():
    tail = '*(s8 *)(record + 0x2C) + *(s16 *)(record + 0x18)'
    return {
        'truncated-fade': source.SELECTED.replace('value = (s32)((u32)value', 'value = (u8)(s32)((u32)value'),
        'wide-load': source.SELECTED.replace('s32 value = record[0x1F]', 's32 value = *(u32 *)(record + 0x1C)'),
        'wide-store': source.SELECTED.replace('record[0x1F] = value;', '*(u32 *)(record + 0x1C) = value;'),
        'wrong-pointer': source.SELECTED.replace('func_1516F864(record);', 'func_1516F864(record + 0x24);'),
        'unsigned-acceleration': source.SELECTED.replace('*(s8 *)(record + 0x2C)', '*(u8 *)(record + 0x2C)'),
        'halfword-acceleration': source.SELECTED.replace('*(s8 *)(record + 0x2C)', '*(s16 *)(record + 0x2C)'),
        'cached-tail': source.SELECTED.replace('    s32 extent;',
            '    s32 savedVelocity = *(s16 *)(record + 0x18);\n    s32 savedStep = *(s8 *)(record + 0x2C);\n    s32 extent;').replace(tail, 'savedStep + savedVelocity'),
        'byte-completion': source.SELECTED.replace('record[0x24] == 0 && value == 0', 'record[0x24] == 0 && record[0x1F] == 0'),
    }


def chain_reference(memory, release_type=0, record=RECORD):
    memory = dict(memory)
    counter = read(memory, record + 0x24, 1)
    if counter:
        put(memory, record + 0x24, max(0, fade.signed(counter - read(memory, source.STEP))), 1)
    memory, done = prefix(memory, record=record)
    calls = [(source.ENTRY, record)]
    if done:
        binding = read(memory, record + 0x30)
        if binding:
            put(memory, binding + 4, 0, 2)
        calls.extend(((source.REMOVE, record), (updater.UNLINK, record)))
        put(memory, record, release_type, 1)
        if release_type >= 2:
            target = read(memory, updater.TYPE_TABLE + release_type * 52) or updater.DEFAULT
            calls.append((target, record))
            put(memory, record + 47, 0x6D, 1)
    else:
        calls.append((source.MOVE, record))
        for position, velocity, fraction in ((0xE, 0x26, 0x2A), (0x12, 0x28, 0x2B)):
            high = read(memory, record + velocity, 1)
            packed = (high - (256 if high & 128 else 0)) * 256 + read(memory, record + velocity + 1, 1)
            fixed = fade.short(read(memory, record + position, 2)) * 256 + read(memory, record + fraction, 1)
            fixed = fade.signed(fixed + packed * read(memory, source.STEP))
            put(memory, record + position, fixed // 256, 2)
            put(memory, record + fraction, fixed, 1)
        accelerate(memory, record)
        fixed = fade.short(read(memory, record + 0x10, 2)) * 256 + read(memory, record + 0x25, 1)
        fixed = fade.signed(fixed + fade.short(read(memory, record + 0x18, 2)) * read(memory, source.STEP))
        put(memory, record + 0x10, fixed // 256, 2)
        put(memory, record + 0x25, fixed, 1)
    return fade.external(memory), calls, done


class AccelerationCandidateTests(unittest.TestCase):
    def test_scope_placeholder_and_direct_match_gate(self):
        self.assertEqual(len(source.PATHS), 57)
        self.assertEqual(len(set(source.PATHS.values())), 57)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        for count, differences, frame, diagnostic in ((52, 0, 24, ''), (51, 1, 24, ''), (51, 0, 32, ''), (51, 0, 24, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=count,
                    differences=differences, frame=frame, diagnostics=diagnostic))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))
        before = 's32 func_1516FD50() {\n    return 0;\n}\nvoid other(void) {}\n'
        self.assertTrue(source.recovered_owner(before).endswith('void other(void) {}\n'))
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))


class FadeAccelerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>51I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_09_all_original_801_archive_fingerprints = archive.TableFadeMatchTests.test_08_all_original_801_archive_fingerprints

    def test_01_direct_padded_and_all_29_owner_neighbors(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual((self.row['words'], self.row['differences'], self.row['frame'], self.row['diagnostics']), (51, 0, 24, ''))
        obj, diagnostic = source.build.compile_owner(self.root, self.out, (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostic, '')
        old, new = parse_object(obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda o, f: [(p - f['value'], r) for p, r in o[2].items() if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(obj), normalized_pools(self.obj))
        self.receipt('owner', raw_padded_words=51, frame=24, guards_added=0, profiles_changed=0,
            all_29_neighbor_bytes_sizes_relative_relocations_and_pools_fixed=True)

    def test_02_complete_private_state_clamps_and_live_tail_homes(self):
        cases = [(v, flag, delta) for v in (0, 1, 15, 16, 127, 128, 254, 255)
            for flag in (0, 1, 128, 255) for delta in (0, 1, 2, 0xFFFFFFFF, 0xFFFFFFE1, 0x80000000, 0x7FFFFFFF, 0x10000000)]
        cases += [(i & 255, (0, 1, 128, 255)[i & 3], (i * 1664525 + 1013904223) & 0xFFFFFFFF) for i in range(128)]
        visits = set()
        for i, args in enumerate(cases):
            for phase in (0, 8):
                for mode in range(4):
                    memory = fixture(*args, velocity=(0, 32767, -32768, -1)[i % 4], acceleration=i * 37 & 255, phase=phase)
                    pair = [AccelerationOracle(w, memory, phase, mode).run() for w in (self.words, self.truth)]
                    self.assertEqual(fade.state(pair[0]), fade.state(pair[1]))
                    self.assertEqual((fade.external(pair[0].memory), pair[0].calls, pair[0].r[2]), reference(memory, mode))
                    self.assertEqual(pair[0].r[29], STACK + phase)
                    visits |= pair[0].visits
                    if pair[0].calls:
                        call = next(j for j, event in enumerate(pair[0].events) if event[0] == 'CALL')
                        self.assertEqual(pair[0].events[call - 1], ('W', STACK + phase, 4, RECORD))
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 204, 4)))
        self.receipt('private', paired_cases=len(cases) * 8, all_51_words_visited=True,
            full_literal_and_independent_public_states_equal=True, record_saved_in_call_delay=True,
            physical_home_and_store_side_probes_not_portable_C_claim=True)

    def test_03_fired_fault_prefixes_and_conditional_narrow_reads(self):
        count = 0
        for args in ((0, 0, 1), (255, 1, 1), (254, 1, 1), (1, 0, 1), (8, 0, 0xFFFFFFE1), (16, 1, 0xFFFFFFFF)):
            for phase in (0, 8):
                for mode in range(4):
                    memory = fixture(*args, phase=phase)
                    whole = AccelerationOracle(self.truth, memory, phase, mode).run()
                    for fault in range(whole.accesses):
                        pair = [AccelerationOracle(w, memory, phase, mode, fault) for w in (self.words, self.truth)]
                        for model in pair:
                            with self.assertRaises(AccessFault):
                                model.run()
                        self.assertEqual(fade.state(pair[0]), fade.state(pair[1]))
                        count += 1
        for args in ((0, 0, 1), (255, 1, 1)):
            memory = fixture(*args)
            for at in range(source.STEP, source.STEP + 4):
                del memory[at]
            for words in (self.words, self.truth):
                model = AccelerationOracle(words, memory).run()
                self.assertFalse(any(e[0] == 'R' and e[1] == source.STEP for e in model.events))
        memory = fixture(255, 1)
        for offset in (0x1C, 0x1D, 0x1E, 0x2D):
            del memory[RECORD + offset]
        self.assertEqual(AccelerationOracle(self.words, memory).run().r[2], 0)
        self.receipt('faults', fired_literal_prefix_pairs=count, conditional_delta_and_byte_only_reads=True,
            opaque_providers_not_hardware_or_portable_C_fault_claim=True)

    def test_04_aliases_and_full_word_256_completion(self):
        count = 0
        for record in (RECORD + 4, source.STEP - 0x14, source.STEP - 0x24):
            for args in ((8, 0, 0xFFFFFFE1), (1, 0, 1), (255, 1, 0x12345678), (16, 1, 0xFFFFFFFF)):
                for mode in range(4):
                    memory = fixture(*args, record=record)
                    pair = [AccelerationOracle(w, memory, mode=mode, record=record).run() for w in (self.words, self.truth)]
                    self.assertEqual(fade.state(pair[0]), fade.state(pair[1]))
                    self.assertEqual((fade.external(pair[0].memory), pair[0].calls, pair[0].r[2]), reference(memory, mode, record))
                    count += 1
        model = AccelerationOracle(self.words, fixture(8, 0, 0xFFFFFFE1)).run()
        self.assertEqual((model.memory[RECORD + 0x1F], model.r[2], len(model.calls)), (0, 0, 1))
        self.receipt('aliases', bounded_guest_pairs=count, stored_zero_fullword_256_still_moves_and_accelerates=True)

    def test_05_eight_effective_compiled_guest_negatives(self):
        cases = ((250, 1, 1), (1, 0, 1), (8, 0, 0xFFFFFFE1), (128, 1, 0), (10, 0, 0), (255, 1, 0x08000001))
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            failed = False
            for args in cases:
                for mode in (0, 2):
                    memory = fixture(*args, velocity=100, acceleration=7)
                    model = AccelerationOracle(words, memory, mode=mode).run()
                    failed |= (fade.external(model.memory), model.calls, model.r[2]) != reference(memory, mode)
            self.assertTrue(failed, name)
        self.receipt('controls', effective_guest_negatives=8, each_has_public_mismatch=True)

    def test_06_independent_original_and_three_rebases(self):
        data, functions, rel = parse_object(self.obj)
        emitted, missing = emit_function(data, functions[source.FUNCTION], rel, source.FUNCTION,
            {'D_800BE9E4': source.STEP, 'func_1516F864': source.MOVE})
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for name, body in (('selected', emitted), ('original', 'glabel ' + source.FUNCTION + '\n' + original)):
            path = self.out / (name + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        for index, delta, step in ((0, 0, source.STEP), (1, 0x10000, 0x80207FFC), (2, -0x10000, 0x80318004)):
            entry, move, outputs = source.ENTRY + delta, source.MOVE - delta, []
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            for name in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (name, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=D_800BE9E4=0x%X' % step, '--defsym=func_1516F864=0x%X' % move,
                    '-o', str(elf), str(self.out / (name + '-reloc.o'))], check=True, capture_output=True)
                outputs.append(list(struct.unpack_from('>51I', sections(elf)['.text'][1])))
            expected = list(self.truth)
            for hi, lo in ((8, 9), (20, 21)):
                expected[hi] = expected[hi] & 0xFFFF0000 | ((step + 0x8000) >> 16 & 65535)
                expected[lo] = expected[lo] & 0xFFFF0000 | (step & 65535)
            expected[39] = 0x0C000000 | (move >> 2 & 0x3FFFFFF)
            self.assertEqual(outputs, [expected, expected])
            for mode in range(4):
                memory = fixture(8, 0, 0xFFFFFFE1, step=step)
                pair = [AccelerationOracle(w, memory, mode=mode, entry=entry, step=step, move=move).run() for w in outputs]
                self.assertEqual(fade.state(pair[0]), fade.state(pair[1]))
                self.assertEqual((fade.external(pair[0].memory), pair[0].calls, pair[0].r[2]), reference(memory, mode, step=step, move=move))
        self.receipt('rebases', original_C_pairs=3, two_HI_LO_pairs_signed_low_carry_and_call=True,
            all_51_words_and_private_states_equal=True)

    def test_07_native32_UBSan_live_provider_and_eight_negatives(self):
        harness = r'''typedef signed char s8;typedef unsigned char u8;typedef short s16;typedef unsigned short u16;
typedef int s32;typedef unsigned int u32;typedef long long s64;typedef unsigned long long u64;
static s32 D_800BE9E4;static u32 mode,count;static u8 *pointer;
static u8 record[96] __attribute__((aligned(8))),expected[96] __attribute__((aligned(8)));
static __attribute__((noinline,noclone)) void func_1516F864(u8 *p){pointer=p;count++;
 if(mode==2){*(u16*)(p+24)=32767;p[44]=128;D_800BE9E4=(s32)0x87654321u;}}
BODY
static s32 (*volatile invoke)(u8*)=func_1516FD50;
static int check(u32 v,u32 flag,u32 delta,u32 provider,u32 edge){u32 i,word=v,done,wantDelta=delta;s64 vel,acc;s32 got;
 static const u16 velocities[]={0,32767,32768,65535};
 for(i=0;i<96;i++)record[i]=(u8)(i*13+0xC5);record[31]=(u8)v;record[36]=(u8)flag;record[44]=(u8)v;*(u16*)(record+24)=velocities[edge];
 for(i=0;i<96;i++)expected[i]=record[i];
 if(flag){if(v!=255){word=(u32)((u64)v+((u64)delta*16));if(!(word&0x80000000u)&&word>255)word=255;expected[31]=(u8)word;}}
 else{if(v){word=(u32)((u64)v-((u64)delta*8));if(word&0x80000000u)word=0;expected[31]=(u8)word;}
  *(u16*)(expected+22)=(u16)(word*2);*(u16*)(expected+20)=(u16)(word*2);}
 done=flag==0&&word==0;
 if(!done){if(provider==2){*(u16*)(expected+24)=32767;expected[44]=128;wantDelta=0x87654321u;}
  vel=*(s16*)(expected+24);acc=expected[44];if(acc>=128)acc-=256;*(u16*)(expected+24)=(u16)(vel+acc);}
 mode=provider;count=0;pointer=0;D_800BE9E4=(s32)delta;got=invoke(record);
 if(got!=(s32)done)return 10;if(count!=(done?0u:1u))return 12;if(!done&&pointer!=record)return 13;
 for(i=0;i<96;i++)if(record[i]!=expected[i])return 11;if((u32)D_800BE9E4!=wantDelta)return 15;return 0;}
static int run(void){static const u32 steps[]={0,1,2,15,16,31,0xFFFFFFFFu,0xFFFFFFE1u,0x80000000u,0x7FFFFFFFu,0x10000000u,0x40000001u};
 static const u32 flags[]={0,1,128,255};u32 v,f,d,m;int r;if(sizeof(void*)!=4||sizeof(s32)!=4)return 14;
 for(v=0;v<256;v++)for(f=0;f<4;f++)for(d=0;d<12;d++)for(m=0;m<2;m++){r=check(v,flags[f],steps[d],m*2,(v+f+d)%4);if(r)return r;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''
        exits = {}
        for name, body, profile, ok in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace('BODY', body))
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-ffreestanding', '-nostdlib', '-static',
                '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter']
            if ok:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            result = subprocess.run([*command, str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            exits[name] = result.returncode
            self.assertIn(result.returncode, (0,) if ok else (10, 11, 12, 13, 15), name)
        self.receipt('native', cases_per_O2_O0=24576, all_fade_and_acceleration_bytes=True,
            signed_halfword_boundaries=True, live_provider_modes=[0, 2], selected_UBSan_exit_zero=True,
            effective_native_negatives=8, controlled_exits=exits, guest_home_mutation_not_claimed_native=True)

    def test_08_current_slot5_move_dispatcher_and_cleanup(self):
        image = (self.root / source.PATHS['elf']).read_bytes()
        table = image[elf_slot_offset(image, source.TABLE, 36):][:36]
        self.assertEqual(table, self.rom[0x231660:0x231660 + 36])
        self.assertEqual(struct.unpack('>9I', table), updater.TARGETS)
        self.assertEqual(struct.unpack_from('>I', table, 20)[0], source.ENTRY)
        current = image[elf_slot_offset(image, source.ENTRY, 204):][:204]
        installed = current == self.rom[source.ROM:source.ROM + 204]
        if not installed:
            self.assertEqual(current[:12], struct.pack('>3I', 0x00001025, 0x03E00008, 0))
        bodies, connected = {}, {}
        for entry, rom, words in ((source.CALLER, 0x19AB28, 48), (source.MOVE, 0x19CD14, 34), (source.REMOVE, 0x196BDC, 28)):
            body = list(struct.unpack_from('>%dI' % words, image, elf_slot_offset(image, entry, words * 4)))
            self.assertEqual(body, list(struct.unpack_from('>%dI' % words, self.rom, rom)))
            bodies[entry] = body
            if entry != source.CALLER:
                connected.update(zip(range(entry, entry + words * 4, 4), body))
        cases = [(0, 0, 1), (1, 0, 1), (8, 0, 0xFFFFFFE1), (255, 1, 1), (250, 1, 1)]
        cases += [(i * 37 & 255, (0, 1, 128, 255)[i & 3], fade.STEPS[i % 12]) for i in range(64)]
        count, completed, destructors, visits = 0, 0, set(), set()
        for i, args in enumerate(cases):
            for binding in (0, BINDING):
                for phase in (0, 8):
                    record = (RECORD, source.STEP - 0x14, source.STEP - 0x24)[i % 3]
                    memory = fixture(*args, acceleration=i * 37 & 255, record=record, phase=phase, binding=binding)
                    pointer = updater.DESTRUCTOR if i & 4 else 0
                    put(memory, updater.TYPE_TABLE + 2 * 52, pointer)
                    pair = []
                    for words in (self.words, self.truth):
                        code = dict(connected)
                        code.update(zip(range(source.ENTRY, source.ENTRY + 204, 4), words))
                        model = AccelerationOracle(bodies[source.CALLER], memory, phase=phase,
                            record=record, entry=source.CALLER, connected=code)
                        model.flip_store, model.release_type = False, i % 3
                        pair.append(model.run())
                    self.assertEqual(fade.state(pair[0]), fade.state(pair[1]))
                    expected, calls, done = chain_reference(memory, i % 3, record)
                    self.assertEqual((fade.external(pair[0].memory), pair[0].calls), (expected, calls))
                    if done:
                        completed += 1
                        self.assertEqual(pair[0].unlink_lifetime, [0 if binding else None])
                        if i % 3 == 2:
                            destructors.add(pointer or updater.DEFAULT)
                    visits |= pair[0].visits
                    count += 1
        self.assertGreater(completed, 0)
        self.assertLess(completed, count)
        self.assertEqual(destructors, {updater.DEFAULT, updater.DESTRUCTOR})
        for entry in (*bodies, source.ENTRY):
            self.assertIn(entry, visits)
        self.receipt('chain', paired_cases=count, cleanup_cases=completed, current_exact_words=[48, 51, 34, 28],
            slot=5, all_nine_pointers_fixed=True, installed_callback_exact=installed,
            only_staged_before_adoption=not installed, all_release_and_destructor_paths=True,
            independent_move_acceleration_Y_and_cleanup_reference=True, lower_unlink_destructors_opaque=True,
            no_full_gameplay_claim=True)


if __name__ == '__main__':
    unittest.main()
