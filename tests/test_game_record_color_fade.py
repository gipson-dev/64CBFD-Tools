"""Qualify color-fade semantics while rejecting its nonmatching compiler shape."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_color_fade as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_record_fade_callback as fade
from tools.tests import test_game_packed_record_updater as updater
from tools.tests import test_game_table_fade_match as archive

RECORD, BINDING = fade.RECORD, fade.BINDING


def fixture(value=128, active=0, delta=1, shift=3, width=1024, height=512,
        dx=-1, dy=-2, phase=25, record=RECORD, stack_phase=0, binding=BINDING, step=source.STEP):
    memory = fade.fixture(value, active, delta, record, stack_phase, step, binding)
    for offset, data, size in ((0x23, 4, 1), (0x14, width, 2), (0x16, height, 2),
            (0x2D, dx, 1), (0x2E, dy, 1), (0x2F, shift, 1), (0x2C, phase, 1)):
        put(memory, record + offset, data, size)
    for i, value in enumerate((255, 128, 0, 128, 255, 128)):
        put(memory, record + 0x26 + i, value, 1)
    return memory


def reference(memory, record=RECORD, step=source.STEP):
    memory = dict(memory)
    value, active = read(memory, record + 0x1F, 1), read(memory, record + 0x24, 1)
    if active:
        if value != 255:
            value = min(255, fade.signed(value + read(memory, step) * 16))
            put(memory, record + 0x1F, value, 1)
    elif value:
        count = read(memory, record + 0x2F, 1) % 32
        value = max(0, fade.signed(value - read(memory, step) * (2 ** count)))
        put(memory, record + 0x1F, value, 1)
    if read(memory, record + 0x24, 1) == 0 and value == 0:
        return fade.external(memory), 1
    dx = read(memory, record + 0x2D, 1)
    dx -= 256 if dx & 128 else 0
    width = fade.short(read(memory, record + 0x14, 2))
    put(memory, record + 0x14, width + dx * read(memory, step), 2)
    width = fade.short(read(memory, record + 0x14, 2))
    dy = read(memory, record + 0x2E, 1)
    dy -= 256 if dy & 128 else 0
    height = fade.short(read(memory, record + 0x16, 2))
    put(memory, record + 0x16, height + dy * read(memory, step), 2)
    if width <= 0:
        put(memory, record + 0x16, 0, 2)
        put(memory, record + 0x14, 0, 2)
        return fade.external(memory), 1
    phase = min(127, fade.signed(read(memory, record + 0x2C, 1) + read(memory, step)))
    coefficient = fade.signed(phase * 2)
    put(memory, record + 0x2C, phase, 1)
    for source_offset, target_offset, output in ((0x26, 0x29, 0x1C), (0x27, 0x2A, 0x1D), (0x28, 0x2B, 0x1E)):
        start, end = read(memory, record + source_offset, 1), read(memory, record + target_offset, 1)
        interpolation = fade.signed((end - start) * coefficient) // 256
        put(memory, record + output, start + interpolation, 1)
    return fade.external(memory), 0


class ColorOracle(updater.UpdaterOracle):
    def __init__(self, words, memory, record=RECORD, phase=0, fault=None,
            entry=source.ENTRY, step=source.STEP, connected=None):
        super().__init__(words, memory, record=record, phase=phase, fault=fault,
            symbols=dict(delta=step, table=source.TABLE, remove=source.REMOVE), entry=entry, connected=connected)


def controls():
    return {
        'truncated-fade': source.SELECTED.replace('value = (s32)((u32)value', 'value = (u8)(s32)((u32)value'),
        'wide-load': source.SELECTED.replace('value = record[0x1F];', 'value = *(u32 *)(record + 0x1C);'),
        'wide-store': source.SELECTED.replace('record[0x1F] = value;', '*(u32 *)(record + 0x1C) = value;'),
        'unsigned-step': source.SELECTED.replace('*(s8 *)(record + 0x2D)', '*(u8 *)(record + 0x2D)'),
        'height-test': source.SELECTED.replace('width <= 0 || width <= 0', 'width <= 0 || *(s16 *)(record + 0x16) <= 0'),
        'signed-target': source.SELECTED.replace('(s32)record[0x29]', '(s32)(s8)record[0x29]'),
        'byte-completion': source.SELECTED.replace('record[0x24] == 0 && value == 0', 'record[0x24] == 0 && record[0x1F] == 0'),
        'unsigned-height-step': source.SELECTED.replace('*(s8 *)(record + 0x2E)', '*(u8 *)(record + 0x2E)'),
    }


class ColorCandidateTests(unittest.TestCase):
    def test_scope_placeholder_and_strict_match_gate(self):
        self.assertEqual(len(source.PATHS), 57)
        self.assertEqual(len(set(source.PATHS.values())), 57)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        for count, differences, frame, diagnostic in ((98, 0, 0, ''), (97, 1, 0, ''),
                (97, 0, 16, ''), (97, 0, 0, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=count,
                    differences=differences, frame=frame, diagnostics=diagnostic))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))
        before = 's32 func_1516FBCC() {\n    return 0;\n}\nvoid other(void) {}\n'
        self.assertTrue(source.recovered_owner(before).endswith('void other(void) {}\n'))
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))


class ColorFadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.words, cls.row = source.measure(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>97I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_08_all_original_801_archive_fingerprints = archive.TableFadeMatchTests.test_08_all_original_801_archive_fingerprints

    def test_01_real_shape_padder_rejection_and_29_unchanged_neighbors(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['diagnostics']), (98, 0, ''))
        self.assertGreater(self.row['differences'], 0)
        with self.assertRaisesRegex(ValueError, 'not a direct match'):
            source.qualify(self.root, self.out)
        with self.assertRaisesRegex(ValueError, 'patched func_1516FBCC is 0x188 bytes but its retail span is only 0x184'):
            emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'],
                filename=source.OWNER, word_patches_path=self.out / 'before-guards')
        old_obj, diagnostics = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(old_obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            rel = lambda o, f: [(p - f['value'], r) for p, r in o[2].items() if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(rel(old, f), rel(new, g), name)
        self.assertEqual(normalized_pools(old_obj), normalized_pools(self.obj))
        self.receipt('owner', selected_words=98, selected_differences=self.row['differences'], retail_words=97,
            match_gate_and_actual_padder_reject=True, neighbors=len(old[1]) - 1, pools_relocations_fixed=True)

    def test_02_full_values_steps_shift_counts_and_unsigned_interpolation(self):
        inputs = [dict(value=v, active=(0, 1, 128, 255)[(v + d) % 4], delta=delta,
            shift=(0, 1, 3, 15, 31, 32, 63, 255)[(v * 3 + d) % 8],
            width=fade.short(v * 317 + d * 101), height=fade.short(v * 65539 - d),
            dx=v, dy=v ^ 255, phase=v ^ 127) for v in range(256) for d, delta in enumerate(fade.STEPS)]
        inputs += [dict(value=128, active=0, delta=1, shift=n, dx=0, dy=0) for n in range(256)]
        inputs += [dict(value=255, active=1, delta=0, phase=n, dx=0, dy=0) for n in range(256)]
        inputs += [dict(value=8, active=0, delta=0xFFFFFFE1, shift=3, dx=0, dy=0),
            dict(value=255, active=1, delta=0, height=-1, dx=0, dy=0)]
        visits, private_differences = set(), 0
        for i, args in enumerate(inputs):
            memory = fixture(**args)
            models = [ColorOracle(w, memory, phase=(i & 1) * 8).run() for w in (self.words, self.truth)]
            expected = reference(memory)
            for model in models:
                self.assertEqual((fade.external(model.memory), model.r[2]), expected, args)
                self.assertEqual(model.calls, [])
                self.assertEqual(model.r[29], STACK + (i & 1) * 8)
            visits |= models[1].visits
            private_differences += fade.state(models[0]) != fade.state(models[1])
        # Both consecutive tests use the same unchanged width; FCC0 is dead.
        unreachable = source.ENTRY + 0xF4
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 388, 4)) - {unreachable})
        self.assertGreater(private_differences, 0)
        special, result = reference(fixture(value=8, active=0, delta=0xFFFFFFE1, shift=3, dx=0, dy=0))
        self.assertEqual((special[RECORD + 0x1F], result), (0, 0))
        self.receipt('semantics', paired_cases=len(inputs), full_byte_shift_counts_and_phase_values=True,
            original_reachable_words_visited=96, unreachable_original_word=unreachable,
            independent_public_reference_equal=True,
            private_different_cases=private_differences, no_private_parity_claim=True)

    def test_03_bounded_global_aliases_and_fired_private_prefix_rejections(self):
        aliases = 0
        for offset in (0, 0x14, 0x1C, 0x24, 0x2C):
            record = source.STEP - offset
            for delta in (0, 1, 0xFFFFFFFF, 0x80000000):
                memory = fixture(value=64, active=1, delta=delta, record=record)
                for words in (self.words, self.truth):
                    model = ColorOracle(words, memory, record=record).run()
                    self.assertEqual((fade.external(model.memory), model.r[2]), reference(memory, record))
                aliases += 1
        memory = fixture(value=128, active=0, delta=1, shift=32)
        complete = [ColorOracle(w, memory).run() for w in (self.words, self.truth)]
        different, faults = 0, 0
        for fault in range(min(m.accesses for m in complete)):
            pair = [ColorOracle(w, memory, fault=fault) for w in (self.words, self.truth)]
            for model in pair:
                with self.assertRaises(AccessFault):
                    model.run()
            different += fade.state(pair[0]) != fade.state(pair[1])
            faults += 1
        self.assertGreater(different, 0)
        self.receipt('aliases-and-prefixes', bounded_guest_alias_pairs=aliases, fired_prefix_pairs=faults,
            differing_prefixes=different, these_reject_private_parity_not_a_passing_fault_match=True)

    def test_04_eight_effective_guest_negatives_and_unmasked_shape_only(self):
        cases = [dict(value=8, active=0, delta=0xFFFFFFE1, shift=3, dx=0, dy=0),
            dict(value=255, active=1, delta=0, height=-1, dx=0, dy=0),
            dict(value=250, active=1, delta=1), dict(value=128, active=0, delta=1, shift=0),
            dict(value=255, active=1, delta=1, width=0, dx=0),
            dict(value=255, active=1, delta=1, phase=0, dx=-1),
            dict(value=255, active=1, delta=0x08000001, dx=0, dy=0),
            dict(value=1, active=0, delta=1, shift=3)]
        effective = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            failed = False
            for args in cases:
                memory = fixture(**args)
                model = ColorOracle(words, memory).run()
                failed |= (fade.external(model.memory), model.r[2]) != reference(memory)
            self.assertTrue(failed, name)
            effective.append(name)
        _, _, unmasked = source.measure(self.root, self.out, 'unmasked-diagnostic',
            source.SELECTED.replace('(record[0x2F] & 31)', 'record[0x2F]'))
        self.assertEqual(unmasked['words'], 97)
        self.assertGreater(unmasked['differences'], 0)
        self.receipt('controls', effective_compiled_guest=effective, unmasked_diagnostic=unmasked,
            unmasked_not_selected_or_credited_as_defined_portable_C=True)

    def test_05_native32_defined_math_O2_O0_and_eight_negatives(self):
        harness = r'''typedef signed char s8;typedef unsigned char u8;typedef short s16;typedef unsigned short u16;
typedef int s32;typedef unsigned int u32;typedef long long s64;typedef unsigned long long u64;
static s32 D_800BE9E4;static u8 record[96] __attribute__((aligned(8))),expected[96] __attribute__((aligned(8)));
BODY
static s32 (*volatile invoke)(u8*)=func_1516FBCC;
static s64 signed32(u32 n){return n&0x80000000u?(s64)n-4294967296LL:(s64)n;}
static int ref(u32 d){u32 v=expected[31],flag=expected[36],phase;int i;s64 w,h,k,product;
 if(flag){if(v!=255){v=(u32)((u64)v+((u64)d*16));if(signed32(v)>255)v=255;expected[31]=(u8)v;}}
 else if(v){v=(u32)((u64)v-((u64)d*(1ULL<<(expected[47]%32))));if(signed32(v)<0)v=0;expected[31]=(u8)v;}
 if(!flag&&!v)return 1;
 w=(s64)*(s16*)(expected+20)+(s64)(s8)expected[45]*d;*(u16*)(expected+20)=(u16)w;
 h=(s64)*(s16*)(expected+22)+(s64)(s8)expected[46]*d;*(u16*)(expected+22)=(u16)h;
 if(*(s16*)(expected+20)<=0){*(u16*)(expected+20)=*(u16*)(expected+22)=0;return 1;}
 phase=(u32)((u64)expected[44]+d);if(signed32(phase)>=128)phase=127;k=signed32(phase*2u);expected[44]=(u8)phase;
 for(i=0;i<3;i++){product=signed32((u32)(((s64)expected[41+i]-expected[38+i])*k));
  product=product>=0?product/256:-((-product+255)/256);expected[28+i]=(u8)(product+expected[38+i]);}return 0;}
static int check(u32 n,u32 flag,u32 special){u32 i,d;int want,got;
 static const u32 steps[]={0,1,2,15,16,31,0xFFFFFFFFu,0xFFFFFFE1u,0x80000000u,0x7FFFFFFFu,0x10000000u,0x40000001u};
 for(i=0;i<96;i++)record[i]=(u8)(i*13+n);record[31]=(u8)n;record[36]=(u8)flag;record[47]=(u8)(n>>8);
 *(u16*)(record+20)=(u16)(1024+n*317);*(u16*)(record+22)=(u16)(n*65539u);d=steps[(n*7+flag*3)%12];
 if(special==1){record[31]=8;record[36]=0;record[47]=3;record[45]=record[46]=0;*(u16*)(record+20)=1024;d=0xFFFFFFE1u;}
 if(special==2){record[31]=255;record[36]=1;record[45]=record[46]=0;*(u16*)(record+20)=1024;*(u16*)(record+22)=65535;d=0;}
 for(i=0;i<96;i++)expected[i]=record[i];want=ref(d);D_800BE9E4=(s32)d;got=invoke(record);
 if(got!=want)return 10;for(i=0;i<96;i++)if(record[i]!=expected[i])return 11;return 0;}
static int run(void){u32 n,f;int r;if(sizeof(void*)!=4||sizeof(s32)!=4)return 12;
 r=check(0,0,1);if(r)return r;r=check(0,0,2);if(r)return r;
 for(n=0;n<65536;n++)for(f=0;f<2;f++){r=check(n,f,0);if(r)return r;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''
        exits = {}
        for name, body, profile, ok in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace('BODY', body))
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-ffreestanding', '-nostdlib',
                '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter']
            if ok:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            result = subprocess.run([*command, str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=60)
            exits[name] = result.returncode
            self.assertIn(result.returncode, (0,) if ok else (10, 11), name)
        self.receipt('native', cases_per_O2_O0=131074, selected_UBSan_trap_profiles_exit_zero=True,
            eight_effective_native_negatives=True,
            controlled_exits=exits, no_native_private_or_hardware_claim=True)

    def test_06_three_independent_rebases_preserve_public_semantics_not_words(self):
        raw, functions, rel = parse_object(self.obj)
        emitted, missing = emit_function(raw, functions[source.FUNCTION], rel, source.FUNCTION, {'D_800BE9E4': source.STEP})
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for name, body in (('selected', emitted), ('original', 'glabel ' + source.FUNCTION + '\n' + original)):
            path = self.out / (name + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        for index, delta, step in ((0, 0, source.STEP), (1, 0x10000, 0x80207FFC), (2, -0x10000, 0x80318004)):
            entry = source.ENTRY + delta
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            for name, count in (('selected', 98), ('original', 97)):
                elf = self.out / ('%s-rebase-%d.elf' % (name, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=D_800BE9E4=0x%X' % step, '-o', str(elf), str(self.out / (name + '-reloc.o'))], check=True, capture_output=True)
                words = list(struct.unpack_from('>%dI' % count, sections(elf)['.text'][1]))
                for shift in (0, 31, 32, 255):
                    memory = fixture(shift=shift, delta=0xFFFFFFE1, dx=0, step=step)
                    model = ColorOracle(words, memory, entry=entry, step=step).run()
                    self.assertEqual((fade.external(model.memory), model.r[2]), reference(memory, step=step))
        self.receipt('rebases', independently_assembled_original_and_C=3, signed_low_carry=True,
            public_semantics_equal=True, byte_or_private_equality_not_claimed=True)

    def test_07_staged_callback_with_current_dispatcher_and_cleanup(self):
        image = (self.root / source.PATHS['elf']).read_bytes()
        table = image[elf_slot_offset(image, source.TABLE, 36):][:36]
        self.assertEqual(table, self.rom[0x231660:0x231660 + 36])
        self.assertEqual(struct.unpack_from('>I', table, 16)[0], source.ENTRY)
        stub = image[elf_slot_offset(image, source.ENTRY, 12):][:12]
        self.assertEqual(stub, struct.pack('>3I', 0x00001025, 0x03E00008, 0))
        bodies = {}
        for entry, rom, count in ((source.CALLER, 0x19AB28, 48), (source.REMOVE, 0x196BDC, 28)):
            words = list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            bodies[entry] = words
        count, completions = 0, 0
        for i in range(32):
            for binding in (0, BINDING):
                for phase in (0, 8):
                    memory = fixture(value=i * 37 & 255, active=i % 4, delta=fade.STEPS[i % 12],
                        shift=i * 9 & 255, width=i * 317, dx=i ^ 255, binding=binding)
                    expected = dict(memory)
                    counter = read(expected, RECORD + 0x24, 1)
                    if counter:
                        put(expected, RECORD + 0x24, max(0, fade.signed(counter - read(expected, source.STEP))), 1)
                    public, done = reference(expected)
                    expected.update(public)
                    calls = [(source.ENTRY, RECORD)]
                    if done:
                        if binding:
                            put(expected, binding + 4, 0, 2)
                        calls += [(source.REMOVE, RECORD), (updater.UNLINK, RECORD)]
                        put(expected, RECORD, 0, 1)
                        completions += 1
                    else:
                        fixed = fade.short(read(expected, RECORD + 0x10, 2)) * 256 + read(expected, RECORD + 0x25, 1)
                        fixed = fade.signed(fixed + fade.short(read(expected, RECORD + 0x18, 2)) * read(expected, source.STEP))
                        put(expected, RECORD + 0x10, fixed >> 8, 2)
                        put(expected, RECORD + 0x25, fixed, 1)
                    for words in (self.words, self.truth):
                        connected = dict(zip(range(source.REMOVE, source.REMOVE + 112, 4), bodies[source.REMOVE]))
                        connected.update(zip(range(source.ENTRY, source.ENTRY + len(words) * 4, 4), words))
                        model = ColorOracle(bodies[source.CALLER], memory, phase=phase, entry=source.CALLER, connected=connected).run()
                        self.assertEqual(fade.external(model.memory), fade.external(expected))
                        self.assertEqual(model.calls, calls)
                        if done:
                            self.assertEqual(model.unlink_lifetime, [0 if binding else None])
                    count += 1
        self.assertGreater(completions, 0)
        self.assertLess(completions, count)
        self.receipt('staged-chain', paired_cases=count, cleanup_cases=completions, current_exact_bodies=[48, 28],
            current_table_slot=4, actual_current_callback_is_still_a_stub=True,
            candidate_and_ROM_inserted_only_into_oracle=True, lower_unlink_opaque=True,
            no_current_callback_execution_or_gameplay_claim=True)

    def test_09_all_57_production_states_remain_unchanged(self):
        for key, relative in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / relative).read_bytes()).hexdigest(), source.BASELINE[key], key)
        self.receipt('production', all_57_inputs_fixed=True, no_source_guard_profile_ELF_or_progress_adoption=True)


if __name__ == '__main__':
    unittest.main()
