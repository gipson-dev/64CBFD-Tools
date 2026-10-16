"""Callback 6: full-word fade, signed random drag, closed temporary allocation."""
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

from tools.experiments import game_record_random_drag as source
from tools.pad_generated_object import parse_object
from tools import pad_generated_object as padder
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import game_record_random_drag_oracle as guest
from tools.tests import test_game_directional_burst_match as prior


def controls():
    return {
        'byte-fade': source.SELECTED.replace('value = (s32)((u32)value', 'value = (u8)(s32)((u32)value'),
        'byte-completion': source.SELECTED.replace('record[0x24] == 0 && value == 0', 'record[0x24] == 0 && record[0x1F] == 0'),
        'signed-startup': source.SELECTED.replace('(u32)func_150ADA20() % 25U', 'func_150ADA20() % 25'),
        'unsigned-drag': source.SELECTED.replace('func_151EF610() % 32', '(u32)func_151EF610() % 32U'),
        'wrong-clamp': source.SELECTED.replace('value = 254;', 'value = 255;'),
        'wrong-threshold': source.SELECTED.replace('>= 2001', '>= 1921'),
        'xz-threshold': source.SELECTED.replace('high * 256 + low', '(s32)*(s8 *)(record + 0x28) * 256 + record[0x29]'),
        'wide-clear': source.SELECTED.replace('*(s16 *)(record + 0x18) = 0;', '*(s32 *)(record + 0x18) = 0;'),
        'cached-mode': source.SELECTED.replace('    s8 high;', '    u8 flags = record[0x2F];\n    s8 high;').replace(
            'if (record[0x2F] != 0)', 'if (flags != 0)'),
    }


class RecordRandomDragTests(unittest.TestCase):
    test_09_all_801_archive_fingerprints = prior.DirectionalBurstMatchTests.test_10_all_801_archive_fingerprints

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>117I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / ('qualification-' + name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_actual_padder_all_neighbors_and_register_only_plan(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (117, 40, 13))
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
            relative = lambda o, f: {at - f['value']: rows for at, rows in o[2].items()
                if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(old_obj), normalized_pools(self.obj))
        raw, rel = source.raw_target(self.obj)
        normalized = struct.unpack('>117I', source.normalize(raw, rel))
        for a, b in zip(struct.unpack('>117I', raw), normalized):
            if a == b:
                continue
            if a >> 26 in (10, 32, 36):
                shifts = (21, 16)
            else:
                self.assertEqual(a >> 26, 0)
                shifts = {0: (16, 11), 18: (11,), 25: (21, 16), 33: (21, 16, 11)}[a & 63]
            mask = sum(31 << shift for shift in shifts)
            self.assertEqual(a & ~mask, b & ~mask)
        rows = [row for row in csv.DictReader(io.StringIO((self.out / 'qualified-guards.csv').read_text()))
            if row['function'] == source.FUNCTION]
        self.assertEqual(len(rows), 117)
        self.assertEqual(sum(row['expected'] != row['replacement'] for row in rows), 13)
        self.assertTrue(all(row['omit'] == 'false' and not row['insert_after']
            and row['expected_relocations'] == row['replacement_relocations'] for row in rows))
        self.receipt('shape', raw_words=117, frame=40, raw_differences=13, exact_normalized_words=117,
            identity_guards=104, transforming_guards=13, no_instruction_home_branch_or_binding_changes=True,
            unchanged_neighbors=len(old[1]) - 1, pools_fixed=True)

    def test_02_dependency_proof_and_effective_mutants(self):
        result = source.prove_register_plan(self.raw_words, self.words)
        for at, field in ((51, 1 << 16), (75, 1), (78, 1 << 21), (80, 1 << 21), (86, 2 << 16), (87, 1)):
            bad = list(self.words)
            bad[at] ^= field
            with self.assertRaises(ValueError, msg=str(at)):
                source.prove_register_plan(self.raw_words, bad)
        equivalent = list(self.words)
        equivalent[86] ^= 1 << 16
        source.prove_register_plan(self.raw_words, equivalent)
        self.receipt('proof', **result, effective_dependency_mutants=6, equal_square_operand_control_accepted=True)

    def test_03_literal_private_raw_public_and_independent_reference(self):
        visits, cases = set(), 0
        for value, active, delta, flags, phase, mode in itertools.product(
                (0, 1, 31, 127, 254, 255), (0, 1),
                (0, 1, 2, 0xFFFFFFFF, 0x10000000, 0x80000000, 0x7FFFFFFF), (0, 1, 128, 255), (0, 8), range(6)):
            velocity = (-32768, -32, -31, 0, 31, 32, 32767)[cases % 7]
            randoms = ((0, 0), (1, 31), (0xFFFFFFFF, 0xFFFFFFE0), (0x80000000, 0x7FFFFFFF),
                (0x80000001, 0xABCDEF81))[cases % 5]
            lifetime = (0, 24, 25, 0xFFFFFFFF, 0x80000000)[cases % 5]
            memory = guest.fixture(value, active, delta, velocity, flags, phase)
            models = [guest.DragOracle(words, memory, phase=phase, mode=mode, randoms=randoms, lifetime=lifetime).run()
                for words in (self.words, self.truth, self.raw_words)]
            self.assertEqual(guest.state(models[0]), guest.state(models[1]))
            expected = guest.reference(memory, mode=mode, randoms=randoms, lifetime=lifetime)
            for model in models:
                self.assertEqual((guest.external(model.memory), model.calls, model.r[2]), expected)
            visits |= models[0].visits
            cases += 1
        self.assertEqual(cases, 4032)
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 468, 4)) - {source.ENTRY + 74 * 4})
        self.receipt('semantics', pairs=cases, all_116_reachable_words_visited=True,
            index_74_unreachable=True, raw_public_and_normalized_literal_state=True,
            opaque_provider_mutations_and_guest_only_store_and_home_controls=True)

    def test_04_fired_fault_prefixes_aliases_and_conditional_reads(self):
        pairs = 0
        for args, mode, phase in itertools.product(
                ((0, 0, 1, 0, 0), (0, 1, 1, 32, 1), (254, 1, 1, -32768, 0),
                 (1, 0, 0xFFFFFFFF, -32, 0)), (0, 1, 2, 4, 5), (0, 8)):
            memory = guest.fixture(*args, phase=phase)
            whole = guest.DragOracle(self.truth, memory, phase=phase, mode=mode).run()
            for fault in range(whole.accesses):
                models = [guest.DragOracle(words, memory, phase=phase, mode=mode, fault=fault)
                    for words in (self.words, self.truth)]
                for model in models:
                    with self.assertRaises(guest.AccessFault):
                        model.run()
                self.assertEqual(guest.state(models[0]), guest.state(models[1]))
                pairs += 1
        aliases = 0
        for record, args in itertools.product((source.STEP - 0x24, source.STEP - 0x1C, guest.RECORD + 4),
                ((1, 0, 0xFFFFFFFF, 31, 0), (254, 1, 0x12345678, -32768, 255))):
            memory = guest.fixture(*args, record=record)
            models = [guest.DragOracle(words, memory, record=record).run() for words in (self.words, self.truth, self.raw_words)]
            self.assertEqual(guest.state(models[0]), guest.state(models[1]))
            for model in models:
                self.assertEqual((guest.external(model.memory), model.calls, model.r[2]), guest.reference(memory, record=record))
            aliases += 1
        memory = guest.fixture(254, 1, flags=1)
        for at in range(source.STEP, source.STEP + 4):
            del memory[at]
        for at in (guest.RECORD + 0x26, guest.RECORD + 0x27):
            del memory[at]
        for words in (self.words, self.truth):
            self.assertEqual(guest.DragOracle(words, memory).run().r[2], 0)
        self.receipt('faults', fired_prefix_pairs=pairs, aliases=aliases,
            clamp_254_never_reads_step=True, flagged_mode_skips_velocity_loads=True,
            guest_only_fault_alias_and_store_probe_boundary=True)

    def test_05_every_raw_padder_word_and_binding_corruption(self):
        raw, rel = source.raw_target(self.obj)
        parsed = parse_object(self.obj)
        start = parsed[1][source.FUNCTION]['value']
        for i in range(117):
            bad = bytearray(raw)
            bad[i * 4] ^= 1
            with self.assertRaisesRegex(ValueError, 'Unknown random-drag words'):
                source.normalize(bytes(bad), rel)
            text = bytearray(parsed[0])
            text[start + i * 4] ^= 1
            with patch.object(padder, 'parse_object', return_value=(bytes(text), parsed[1], parsed[2])):
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
        self.receipt('corruptions', raw_flips=117, padder_word_flips=117, padder_binding_flips=117,
            all_external_bindings=len(rel), no_unchecked_instructions=True)

    def test_06_effective_compiled_negatives(self):
        cases = ((0, 1, 1, 32, 1, 1), (254, 1, 1, 32, 1, 0),
            (0, 1, 0x10000000, 31, 0, 0), (1, 0, 0xFFFFFFFF, 0, 0, 0),
            (255, 0, 1, 0, 1, 2), (1, 1, 1, -32768, 0, 0), (1, 1, 1, 31, 0, 0),
            (16, 0, 0xFFFFFFF1, 0, 0, 0), (255, 1, 1, 32, 1, 0))
        effective = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED, name)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            different = False
            for value, active, delta, velocity, flags, mode in cases:
                memory = guest.fixture(value, active, delta, velocity, flags)
                model = guest.DragOracle(words, memory, mode=mode).run()
                different |= (guest.external(model.memory), model.calls, model.r[2]) != guest.reference(memory, mode=mode)
            self.assertTrue(different, name)
            effective.append(name)
        self.receipt('compiled-controls', effective=effective)

    def test_07_three_independent_original_raw_normalized_links(self):
        raw, rel = source.raw_target(self.obj)
        normal = source.normalize(raw, rel)
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        path = self.out / 'original.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n.type '
            + source.FUNCTION + ', @function\nglabel ' + source.FUNCTION + '\n' + original
            + '\n.size ' + source.FUNCTION + ', . - ' + source.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        tx, fs, rs = parse_object(path.with_suffix('.o'))
        f = fs[source.FUNCTION]
        original_raw = tx[f['value']:f['value'] + f['size']]
        original_rel = {at - f['value']: rows for at, rows in rs.items() if f['value'] <= at < f['value'] + f['size']}
        pairs = 0
        for delta, step in ((0, source.STEP), (0x10000, 0x80318000), (-0x10000, 0x80427FFC)):
            entry = source.ENTRY + delta
            targets = {key: getattr(source, key) - delta for key in ('MOVE', 'SCALE_X', 'SCALE_Z', 'RANDOM', 'LIFETIME_RANDOM')}
            bindings = dict(D_800BE9E4=step, func_150ADA20=targets['LIFETIME_RANDOM'], func_151EF610=targets['RANDOM'],
                func_1516F864=targets['MOVE'], func_1516F8EC=targets['SCALE_X'], func_1516F91C=targets['SCALE_Z'])
            streams = [source.link_target(self.out, 'rebase-%X-%d' % (entry, i), data, rows, entry, bindings)
                for i, (data, rows) in enumerate(((original_raw, original_rel), (raw, rel), (normal, rel)))]
            self.assertEqual(streams[0], streams[2])
            for velocity, flags, active, value, phase in itertools.product((-32768, -32, 31, 32), (0, 1), (0, 1), (0, 254), (0, 8)):
                memory = guest.fixture(value, active, 1, velocity, flags, phase)
                guest.put(memory, step, 1, 4)
                kw = dict(phase=phase, entry=entry, step=step, **{k.lower(): v for k, v in targets.items()})
                models = [guest.DragOracle(words, memory, **kw).run() for words in streams]
                self.assertEqual(guest.state(models[0]), guest.state(models[2]))
                expected = guest.reference(memory, step=step, **{k.lower(): v for k, v in targets.items()})
                for model in models:
                    self.assertEqual((guest.external(model.memory), model.calls, model.r[2]), expected)
                pairs += 1
        self.receipt('rebases', independent_streams=3, links=3, cases=pairs, signed_low_carry=True)

    def test_08_all_inputs_and_capture_corruptions(self):
        source.freeze(self.root, self.out)
        expected = source.expected_inputs(self.root, self.out)
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
        self.receipt('inputs', protected_inputs=len(source.PATHS), all_fixture_corruptions_rejected=True,
            expected_after={key: hashlib.sha256(data).hexdigest() for key, data in expected.items()})


    def test_10_native32_all_packed_velocity_bits_and_effective_negatives(self):
        harness = r'''typedef unsigned char u8;typedef signed char s8;typedef short s16;
typedef unsigned int u32;typedef int s32;
static u32 storage[20],saved[20],logs[16][2],wantedLogs[16][2],rng[2],life;
static u8 *record=(u8*)storage;static u32 count,draw,mode,error;s32 D_800BE9E4;
static void event(u32 id,u32 arg){if(count>=16){error=1;return;}logs[count][0]=id;logs[count++][1]=arg;}
static s32 func_150ADA20(void){event(0,0);if(mode==1){record[0x1F]=231;D_800BE9E4=2;}return(s32)life;}
static s32 func_151EF610(void){event(2,0);return(s32)rng[(draw++)&1];}
static void func_1516F864(u8*p){if(p!=record)error=2;event(1,0);if(mode==2){p[0x2F]=0;p[0x26]=0;p[0x27]=32;D_800BE9E4=(s32)0x87654321u;}}
static void func_1516F8EC(u8*p,u32 a){if(p!=record)error=3;event(3,a);if(mode==3){p[0x2F]=0;p[0x26]=p[0x27]=0;}}
static void func_1516F91C(u8*p,u32 a){if(p!=record)error=4;event(4,a);}
BODY
static s32(*volatile invoke)(u8*)=func_151707E0;
static s32 reference(void){s32 value=record[0x1F],x;u32 sq,base;
 if(record[0x24]){if(!value)record[0x24]=(u32)func_150ADA20()%25u+200u;
 if(value!=254){value=(s32)((u32)value+(u32)D_800BE9E4*64u);if(value>=255)value=254;record[0x1F]=(u8)value;}}
 else if(value){value=(s32)((u32)value-(u32)D_800BE9E4*16u);if(value<0)value=0;record[0x1F]=(u8)value;}
 if(!record[0x24]&&!value)return 1;
 func_1516F864(record);x=(s32)(s8)record[0x26]*256+record[0x27];sq=(u32)(x*x)*2u;
 if(record[0x2F]||(s32)sq>=2001){base=record[0x2F]?230:220;
 func_1516F8EC(record,(u32)(func_151EF610()%32)+base);
 func_1516F91C(record,(u32)(func_151EF610()%32)+base);}
 record[0x18]=record[0x19]=0;return 0;}
static int check(u32 bits,u32 value,u32 active,u32 flags,u32 delta,u32 m){u32 i,j,wantedCount;int result,wanted;s32 step;
 for(i=0;i<20;i++)storage[i]=0xA5A5A5A5u;
 record[0x1F]=(u8)value;record[0x24]=(u8)active;record[0x2F]=(u8)flags;
 record[0x26]=(u8)(bits>>8);record[0x27]=(u8)bits;record[0x28]=0x80;record[0x29]=0xA5;
 for(i=0;i<20;i++)saved[i]=storage[i];D_800BE9E4=(s32)delta;mode=m;count=draw=error=0;
 life=bits*1103515245u+12345u;rng[0]=bits*1664525u+1013904223u;rng[1]=~rng[0];
 wanted=reference();wantedCount=count;step=D_800BE9E4;
 for(i=0;i<16;i++)for(j=0;j<2;j++)wantedLogs[i][j]=logs[i][j];
 {u32 expected[20];for(i=0;i<20;i++){expected[i]=storage[i];storage[i]=saved[i];}
 D_800BE9E4=(s32)delta;count=draw=error=0;result=invoke(record);
 if(error)return 101;if(result!=wanted)return 102;if(count!=wantedCount)return 103;
 if(step!=D_800BE9E4)return 104;for(i=0;i<count;i++)for(j=0;j<2;j++)if(logs[i][j]!=wantedLogs[i][j])return 103;
 for(i=0;i<20;i++)if(storage[i]!=expected[i])return 104;}return 0;}
static int run(void){u32 i,a,f,m,delta[8]={0,1,2,0xFFFFFFFFu,0xFFFFFFF1u,0x10000000u,0x80000000u,0x7FFFFFFFu};int r;
 if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(s16)!=2)return 105;
 r=check(0,16,0,0,0xFFFFFFF1u,0);if(r)return r;
 r=check(32,255,1,1,1,0);if(r)return r;
 for(i=0;i<65536;i++)for(a=0;a<2;a++)for(f=0;f<2;f++)for(m=0;m<4;m++){
 r=check(i,(i^(i>>8))&255,a?255:0,f?(i>>8):0,delta[i&7],m);if(r)return r;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''
        exits = {}
        for name, body, profile, valid in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace('BODY', body))
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-ffreestanding', '-nostdlib',
                '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation']
            if valid:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            result = subprocess.run([*command, str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=60)
            self.assertIn(result.returncode, (0,) if valid else (101, 102, 103, 104), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=1048578, all_65536_velocity_bits=True,
            all_byte_fade_values_and_flags=True, typed_one_pointer_callback=True,
            provider_mutations_and_full_word_256=True, UBSan_selected=True,
            effective_negatives=len(controls()), exits=exits)

    def test_12_guest_unsigned_multiply_high_and_low(self):
        for left, right, hi, lo in ((0, 0, 0, 0), (0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFE, 1),
                (0xFFFF8000, 0xFFFF8000, 0xFFFF0000, 0x40000000),
                (0x80000000, 2, 1, 0), (32767, 32767, 0, 1073676289)):
            model = guest.DragOracle(self.words, guest.fixture())
            model.r[4], model.r[5] = left, right
            model.execute(0x00850019)
            self.assertEqual((model.hi, model.lo), (hi, lo))
            model.execute(0x00001010)
            self.assertEqual(model.r[2], hi)
            model.execute(0x00001812)
            self.assertEqual(model.r[3], lo)
        self.receipt('multiply', unsigned_word_multiply_HI_LO_golden_cases=5,
            inherited_runner_high_half_completed_locally=True, no_shared_or_historical_runner_edits=True)

    def test_11_actual_slot6_wrapper_movement_scalers_and_rng(self):
        image = (self.out / 'before-elf').read_bytes()
        connected = {}
        spans = ((source.MOVE, 136), (source.SCALE_X, 48), (source.SCALE_Z, 48), (source.RANDOM, 44))
        for address, size in spans:
            rom = 0x21CAC0 if address == source.RANDOM else address - source.ENTRY + source.ROM
            data = image[elf_slot_offset(image, address, size):][:size]
            self.assertEqual(data, self.rom[rom:rom + size])
            connected.update(zip(range(address, address + size, 4), struct.unpack('>%dI' % (size // 4), data)))
        wrapper = list(struct.unpack_from('>48I', image, elf_slot_offset(image, 0x1516D678, 192)))
        self.assertEqual(struct.pack('>48I', *wrapper), self.rom[0x19AB28:0x19AB28 + 192])
        table = image[elf_slot_offset(image, 0x8008CBA0, 36):][:36]
        self.assertEqual(table, self.rom[0x231660:0x231684])
        self.assertEqual(struct.unpack_from('>I', table, 24)[0], source.ENTRY)
        cases = 0
        for seed, velocity, active, value, flags, phase, wrapped in itertools.product(
                (0, 1, 0xFFFFFFFF, 0x87654321), (-32768, -32, 0, 31, 32), (0, 3),
                (0, 16, 254), (0, 255), (0, 8), (False, True)):
            memory = guest.fixture(value, active, 1, velocity, flags, phase)
            memory.update({0x8008CBA0 + i: b for i, b in enumerate(table)})
            guest.put(memory, 0x80091970, seed, 4)
            prepared = dict(memory)
            if wrapped and active:
                guest.put(prepared, guest.RECORD + 0x24, active - 1, 1)
            randoms, next_seed = [], seed
            for _ in range(2):
                next_seed = (((next_seed * 4 + 2) & 0xFFFFFFFF) * ((next_seed * 4 + 3) & 0xFFFFFFFF) & 0xFFFFFFFF) >> 2
                randoms.append(next_seed)
            wanted, calls, done = guest.reference(prepared, randoms=randoms)
            wanted = dict(wanted)
            if not done:
                for pos, vel, frac in ((0xE, 0x26, 0x2A), (0x12, 0x28, 0x2B)):
                    fixed = guest.short(guest.read(prepared, guest.RECORD + vel, 2))
                    fixed = guest.signed(guest.short(guest.read(prepared, guest.RECORD + pos, 2)) * 256
                        + guest.read(prepared, guest.RECORD + frac, 1) + fixed)
                    guest.put(wanted, guest.RECORD + pos, fixed >> 8, 2)
                    guest.put(wanted, guest.RECORD + frac, fixed, 1)
                for target, record, scale in (row for row in calls if row[0] in (source.SCALE_X, source.SCALE_Z)):
                    at = record + (0x26 if target == source.SCALE_X else 0x28)
                    fixed = guest.short(guest.read(wanted, at, 2))
                    fixed = guest.signed(fixed * scale) >> 8
                    guest.put(wanted, at, fixed >> 8, 1)
                    guest.put(wanted, at + 1, fixed, 1)
            guest.put(wanted, 0x80091970, next_seed if any(row[0] == source.RANDOM for row in calls) else seed, 4)
            if wrapped:
                calls = [(source.ENTRY, guest.RECORD), *calls]
                if done:
                    guest.put(wanted, guest.fade.BINDING + 4, 0, 2)
                    guest.put(wanted, guest.RECORD + 0x2E, 0x6D, 1)
                    calls.append((0x1516972C, guest.RECORD))
            models = []
            for words in (self.words, self.truth, self.raw_words):
                code = dict(connected)
                if wrapped:
                    code.update(zip(range(source.ENTRY, source.ENTRY + 468, 4), words))
                model = guest.DragOracle(wrapper if wrapped else words, memory, phase=phase,
                    entry=0x1516D678 if wrapped else source.ENTRY, connected=code).run()
                self.assertEqual((guest.external(model.memory), model.calls), (wanted, calls))
                models.append(model)
            self.assertEqual(guest.state(models[0]), guest.state(models[1]))
            cases += 1
        self.receipt('connected', cases=cases, actual_helper_words=69, actual_wrapper_words=48,
            original_slot6_table=True, real_rng_seed_steps=True, both_movement_and_drag_components=True,
            lifetime_RNG_and_remove_provider_opaque=True, no_full_gameplay_acceptance=True)


if __name__ == '__main__':
    unittest.main()
