"""Retail ABI and candidate rejection; this does not install or credit a match."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_paired_record_event as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import MaskOracle, AccessFault, CallBoundary
from tools.tests.test_game_owner_actor_update_match import put
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_dual_factory_preset import state
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests import test_game_record_factory as factory


def signed16(value):
    value &= 65535
    return value if value < 32768 else value - 65536


def saved_values(args):
    # Shift-by-12 followed by signed division keeps the signed low 16 result.
    return [signed16(args[0]), signed16(args[1]), signed16(args[2]), args[4] & 255,
        args[6] & 255, signed16(args[7]), signed16(args[8]), args[3] & 65535,
        args[9] & 255, signed16(args[5])]


def changed_saved(call):
    return [0x87650080 + call * 0x1000 + i * 0x10003 for i in range(10)]


def changed_inputs(call):
    return [0xC5000100 + call * 0x100 + i for i in range(17)]


def packet(args, saved, second=False):
    p = [0] * 49
    for i, value in ((0, signed16(saved[0])), (1, signed16(saved[1])), (2, signed16(saved[2])),
            (3, 13), (5, 103), (6, 23), (7, 13), (10, 18), (12, 2), (13, saved[3]),
            (15, saved[4]), (19, args[11 if second else 10]), (27, saved[5]), (28, saved[5]),
            (29, saved[6]), (30, saved[6]), (31, saved[7]), (32, saved[8]), (33, 20),
            (34, 255), (35, 16), (36, saved[9]), (37, 200), (38, 1), (39, 6 if second else 0),
            (41, 1), (47, args[15] & 255), (48, args[16])):
        p[i] = value & 0xFFFFFFFF
    return tuple(p)


def expected(args, mode=0, callee=source.CALLEE, event=source.EVENT, callback=source.CALLBACK):
    saved = saved_values(args)
    calls = [(callee, *packet(args, saved))]
    incoming = changed_inputs(1) if mode == 1 else args
    if mode == 2:
        saved = changed_saved(1)
    calls.append((callee, *packet(incoming, saved, True)))
    if mode == 1:
        incoming = changed_inputs(2)
    elif mode == 2:
        saved = changed_saved(2)
    calls.append((event, 7, *(signed16(v) & 0xFFFFFFFF for v in saved[:3]),
        0x36B0, 1000, 100, callback, incoming[3], 0, 0, 0))
    return calls


class PairedOracle(MaskOracle):
    def __init__(self, words, args, phase=0, mode=0, fault=None, entry=source.ENTRY,
            callee=source.CALLEE, event=source.EVENT):
        memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-768, 0x800)}
        for i, value in enumerate(args[4:], 4):
            put(memory, STACK + phase + i * 4, value)
        super().__init__(words, memory, phase=phase, mode=mode, fault=fault, entry=entry, arguments=args)
        self.callee, self.event = callee, event

    def record_call(self, target):
        assert target in (self.callee, self.event), hex(target)
        args = self.arguments(49 if target == self.callee else 12)
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        if target == self.callee:
            call = len(self.calls)
            if self.mode == 1:
                for i, value in enumerate(changed_inputs(call)):
                    self.put(STACK + self.phase + i * 4, value, 4)
            elif self.mode == 2:
                for i, value in enumerate(changed_saved(call)):
                    self.put(STACK + self.phase - (i + 1) * 4, value, 4)
            elif self.mode == 3:
                for i in range(4):
                    self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0xABCD0000 + len(self.calls)


class PairedEventCandidateTests(unittest.TestCase):
    def test_scope_recovery_and_fail_closed_direct_gate(self):
        self.assertEqual(len(source.PATHS), 57)
        self.assertEqual(len(set(source.PATHS.values())), 57)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        for words, differences, frame, diagnostic in ((200, 0, 248, ''), (199, 1, 248, ''),
                (199, 0, 256, ''), (199, 0, 248, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=words,
                    differences=differences, frame=frame, diagnostics=diagnostic))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))
        before = 's32 func_1516F548() {\n    return 0;\n}\nvoid other(void) { }\n'
        self.assertTrue(source.recovered_owner(before).endswith('void other(void) { }\n'))
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))
        prefix = source.SELECTED.split('/* Submit', 1)[0]
        for name, body in source.candidates().items():
            self.assertTrue(body.startswith(prefix), name)
            self.assertIn('arg12, s32 arg13, s32 arg14,', body, name)
            self.assertNotIn('volatile', body, name)


class PairedEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)
        cls.body = source.candidates()['initial_inputs']
        cls.obj, cls.words, cls.row = source.measure(cls.root, cls.out, 'tested-candidate', cls.body)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>199I', cls.rom, source.ROM))
        original = (cls.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        path = cls.out / 'original-reloc.s'
        path.write_text('.include "' + str(cls.root / 'conker/include/asm_processor_prelude.inc') + '"\n'
            + '.type ' + source.FUNCTION + ', @function\n'
            + 'glabel ' + source.FUNCTION + '\n' + original
            + '.size ' + source.FUNCTION + ', .-' + source.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
            check=True, capture_output=True)
        data, functions = source.build.link_owner(cls.root, cls.out, path.with_suffix('.o'), source.OWNER)
        f = functions[source.FUNCTION]
        cls.assembled = list(struct.unpack_from('>199I', data, f['value']))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_original_binding_uninstalled_candidate_and_all_57_inputs(self):
        self.assertEqual(self.assembled, self.truth)
        self.assertEqual((self.row['words'], self.row['differences'], self.row['frame'], self.row['diagnostics']), (199, 162, 248, ''))
        with self.assertRaisesRegex(ValueError, 'not a direct match'):
            source.qualify(self.root, self.out)
        for key, path in source.PATHS.items():
            payload = (self.root / path).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), source.BASELINE[key], key)
            self.assertEqual(payload, (self.out / ('before-' + key)).read_bytes(), key)
        self.assertIn('s32 func_1516F548() {\n    return 0;\n}', (self.root / source.PATHS['preset_owner']).read_text())
        self.receipt('uninstalled', original_assembled_words=199, candidate=self.row,
            all_57_current_inputs_unchanged=True, production_remains_stub=True,
            added_guards=0, changed_profiles=0, credited_functions=0)

    def test_02_three_packets_signed_widths_live_inputs_and_private_homes(self):
        cases = [(0,) * 17, (0xFFFFFFFF,) * 17,
            tuple((0x80000000, 0xFFFF8000, 0x1234FFFF, 0xFEDCBA98, 0xABCD0080)[i % 5] for i in range(17))]
        cases += [tuple((n * 1664525 + j * 0x1020304 + 1013904223) & 0xFFFFFFFF for j in range(17)) for n in range(256)]
        visits, private_rejections = set(), 0
        for args in cases:
            for phase in (0, 8):
                for mode in range(4):
                    pair = [PairedOracle(w, args, phase, mode).run() for w in (self.truth, self.assembled)]
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    self.assertEqual(pair[0].calls, expected(args, mode))
                    self.assertEqual(pair[0].r[29], STACK + phase)
                    self.assertEqual(pair[0].r[2], 0xABCD0003)
                    visits |= pair[0].visits
                    candidate = PairedOracle(self.words, args, phase, mode).run()
                    if mode == 2:
                        self.assertNotEqual(candidate.calls, expected(args, mode))
                        private_rejections += 1
                    else:
                        self.assertEqual(candidate.calls, expected(args, mode))
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 796, 4)))
        self.receipt('packets', original_cases=len(cases) * 8, factory_words_each=49, event_words=12,
            full_199_word_coverage=True, original_private_state_equal=True,
            candidate_normal_live_input_and_outgoing_clobber_cases=len(cases) * 6,
            candidate_private_home_rejections=private_rejections,
            physical_private_writes_not_portable_C_or_gameplay_claim=True)

    def test_03_every_fired_original_memory_fault_prefix(self):
        args = tuple((0x87654321 + i * 0x1020304) & 0xFFFFFFFF for i in range(17))
        count = 0
        for phase in (0, 8):
            for mode in range(4):
                whole = PairedOracle(self.truth, args, phase, mode).run()
                for fault in range(whole.accesses):
                    pair = [PairedOracle(w, args, phase, mode, fault) for w in (self.truth, self.assembled)]
                    for model in pair:
                        with self.assertRaises(AccessFault):
                            model.run()
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    count += 1
        self.receipt('prefixes', fired_original_faults=count, original_source_and_ROM_prefixes_equal=True,
            no_candidate_prefix_equivalence_claim=True)

    def test_04_both_original_17_slot_caller_windows(self):
        class Caller(MaskOracle):
            def record_call(model, target):
                self.assertEqual(target, source.ENTRY)
                model.calls.append((target, *model.arguments(17)))
                raise CallBoundary
        image = (self.root / source.PATHS['elf']).read_bytes()
        sites = [(0x150270C8, 0x54578, 43), (0x15027174, 0x54624, 48)]
        expected_args = [(123, 12, -8, 0xABCD1234, 6, 0xB00, 3, 200, 50, 10, 6, 7, 190, 190, 190, 128, 0),
            (76, 478, -8, 0xABCD1234, -11, 0x800, -5, 200, 50, 10, 6, 7, 190, 190, 190, 128, 0)]
        for index, (entry, rom, count) in enumerate(sites):
            words = list(struct.unpack_from('>%dI' % count, self.rom, rom))
            current = list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(sum(a == b for a, b in zip(current, words)), 0)
            for phase in (0, 8):
                memory = {STACK + j: 0xA5 for j in range(-256, 0x900)}
                values = {0x684: .5, 0x698: -8.25} if index == 0 else {0x6A0: 100.25, 0x69C: 2.25, 0x684: .5, 0x680: .25}
                for offset, value in values.items():
                    put(memory, STACK + phase + offset, struct.unpack('>I', struct.pack('>f', value))[0])
                put(memory, STACK + phase + 0x6A8, 0xABCD1234)
                put(memory, STACK + phase + 0xE0, 0x80)
                put(memory, STACK + phase + 0x40, 0)
                memory[STACK + phase + 0x773] = 0x80
                model = Caller(words, memory, phase=phase, entry=entry, arguments=(0, 0, 0, 0))
                if index == 0:
                    for reg, value in ((18, 123.75), (6, 2.25), (10, 10.5), (2, 12.0), (0, .25)):
                        model.f[reg] = struct.unpack('>I', struct.pack('>f', value))[0]
                else:
                    model.r[16] = (-8) & 0xFFFFFFFF
                with self.assertRaises(CallBoundary):
                    model.run()
                self.assertEqual(model.calls, [(source.ENTRY, *(v & 0xFFFFFFFF for v in expected_args[index]))])
        self.receipt('callers', original_windows=2, fired_cases=4, all_17_physical_slots_checked=True,
            slots_12_13_14_unused_by_target_but_supplied=True,
            current_linked_windows_placeholders=True, prepared_dependencies_not_full_caller_execution=True)

    def test_05_current_factory_chain_and_event_packet_boundary(self):
        image = (self.root / source.PATHS['elf']).read_bytes()
        symbols = {row[1]: row[2] for row in symbol_rows(image)}
        for name, entry, rom, count in (('func_1000FA64', source.EVENT, 0xFA64, 109),
                ('func_1000EBC4', source.CALLBACK, 0xEBC4, 24)):
            self.assertEqual(symbols[name][1:3], (entry, count * 4))
            self.assertEqual(image[elf_slot_offset(image, entry, count * 4):][:count * 4], self.rom[rom:rom + count * 4])
        connected = {}
        for entry, rom, count in ((source.CALLEE, 0x19AE4C, 125), (0x15167A68, 0x194F18, 28)):
            words = list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        class Chain(factory.FactoryOracle):
            def record_call(model, target):
                if target == source.EVENT:
                    args = model.arguments(12)
                    model.calls.append((target, *args))
                    model.events.append(('CALL', target, args))
                else:
                    factory.FactoryOracle.record_call(model, target)
            def hook(model, target):
                if target == source.EVENT:
                    model.r[2] = 0xABCD0003
                else:
                    if target == factory.ALLOCATE:
                        model.result = model.results[model.allocation]
                        model.allocation += 1
                    factory.FactoryOracle.hook(model, target)
        cases = 0
        for n in range(32):
            args = tuple((n * 1664525 + i * 0x1020304 + 1013904223) & 0xFFFFFFFF for i in range(17))
            for results in ((0, 0), (factory.RECORD, 0), (0, factory.RECORD + 128), (factory.RECORD, factory.RECORD + 128)):
                for words in (self.truth, self.words):
                    model = Chain(words, args, phase=(n & 1) * 8, entry=source.ENTRY, connected=connected, chain=True)
                    model.results, model.allocation = results, 0
                    model.memory.update({factory.RECORD + 128 + j: (j * 13 + 0xC5) & 255 for j in range(-16, 96)})
                    model.run()
                    calls = [c for c in model.calls if c[0] in (source.CALLEE, source.EVENT)]
                    self.assertEqual(calls, expected(args))
                    self.assertEqual(model.allocation, 2)
                    for index, result in enumerate(results):
                        if not result:
                            continue
                        p = packet(args, saved_values(args), bool(index))
                        memory = factory.fixture(p)
                        memory.update({result + j: (j * 13 + 0xC5) & 255 for j in range(-16, 96)})
                        reference = factory.reference(memory, p, result)[0]
                        for at in range(result + 14, result + 76):
                            self.assertEqual(model.memory[at], reference[at])
                cases += 1
        self.receipt('chain', original_candidate_pairs=cases, real_factory_allocator_words=[125, 28],
            independent_null_success_pairs=4, initialized_record_fields_checked=True,
            linked_event_callback_symbols_and_exact_words=[109, 24],
            event_provider_opaque_callback_address_bound=True, no_Init_queue_callback_or_gameplay_execution_claim=True)

    def test_06_all_immutable_predecessor_corruptions(self):
        rb = Path.read_bytes
        for key in source.PATHS:
            path = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        manifest = self.out / 'baseline.json'
        rt = Path.read_text
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == manifest else rt(p, *a, **kw)):
            with self.assertRaisesRegex(ValueError, 'manifest'):
                source.freeze(self.root, self.out)
        self.receipt('capture-controls', before_capture_corruptions=57, changed_manifest_rejected=True)

    def test_07_native_32_bit_packets_and_effective_semantic_controls(self):
        declarations = ','.join('s32 a%d' % i for i in range(49))
        values = ','.join('(u32)a%d' % i for i in range(49))
        args = ','.join('(s32)original[%d]' % i for i in range(17))
        harness = '''typedef signed char s8; typedef unsigned char u8;
typedef short s16; typedef unsigned short u16; typedef int s32; typedef unsigned int u32;
typedef struct { s32 unused; } struct00;
static u32 captured[3][49], original[17], count;
static void func_1516D99C(DECL){u32 p[49]={VALUES};u32 i;
 if(count<2)for(i=0;i<49;i++)captured[count][i]=p[i];count++;}
s32 func_1000EBC4(struct00 *a,s32 b,s32 c,s32 d){return 0;}
u16 func_1000FA64(u16 a0,s16 a1,s16 a2,s16 a3,s32 a4,u16 a5,s16 a6,s32 a7,void *a8,s32 a9,s32 a10,s32 a11){
 u32 p[12]={a0,(u32)(s32)a1,(u32)(s32)a2,(u32)(s32)a3,(u32)a4,a5,(u32)(s32)a6,(u32)a7,(u32)a8,(u32)a9,(u32)a10,(u32)a11};
 u32 i;if(count==2)for(i=0;i<12;i++)captured[2][i]=p[i];count++;return 0;}
BODY
static void (*volatile invoke)(TYPES)=func_1516F548;
static int check(u32 n){u32 i,k,p[49];count=0;
 for(i=0;i<17;i++)original[i]=0x87650000u+i*0x1020304u+n;
 invoke(ARGS);if(count!=3)return 10;
 for(k=0;k<2;k++){
  for(i=0;i<49;i++)p[i]=0;
  p[0]=(u32)(s32)(s16)original[0];p[1]=(u32)(s32)(s16)original[1];p[2]=(u32)(s32)(s16)original[2];
  p[3]=13;p[5]=103;p[6]=23;p[7]=13;p[10]=18;p[12]=2;
  p[13]=original[4]&255;p[15]=original[6]&255;p[19]=original[10+k];
  p[27]=p[28]=(u32)(s32)(s16)original[7];p[29]=p[30]=(u32)(s32)(s16)original[8];
  p[31]=original[3]&65535;p[32]=original[9]&255;p[33]=20;p[34]=255;p[35]=16;
  p[36]=(u32)(s32)(s16)original[5];p[37]=200;p[38]=1;p[39]=k?6:0;p[41]=1;
  p[47]=original[15]&255;p[48]=original[16];
  for(i=0;i<49;i++)if(p[i]!=captured[k][i])return 11;
 }
 for(i=0;i<12;i++)p[i]=0;p[0]=7;
 p[1]=(u32)(s32)(s16)original[0];p[2]=(u32)(s32)(s16)original[1];p[3]=(u32)(s32)(s16)original[2];
 p[4]=0x36B0;p[5]=1000;p[6]=100;p[7]=(u32)func_1000EBC4;p[8]=original[3];
 for(i=0;i<12;i++)if(p[i]!=captured[2][i])return 12;return 0;}
static int run(void){u32 i;int r;if(sizeof(void*)!=4||sizeof(s32)!=4)return 13;
 for(i=0;i<65536;i++){r=check(i);if(r)return r;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''.replace('DECL', declarations).replace('VALUES', values).replace('TYPES', ','.join(['s32'] * 17)).replace('ARGS', args)
        controls = {
            'wrong-last-slot': self.body.replace('(u8)(&arg15)[0], arg16', '(u8)(&arg15)[0], arg14'),
            'wrong-byte-slot': self.body.replace('(u8)arg15, arg16', '(u8)arg12, arg16'),
            'narrow-live-context': self.body.replace('(void *)arg3', '(void *)(u32)(u16)arg3'),
            'unsigned-coordinate': self.body.replace('x = (s16)arg0;', 'x = (u16)arg0;').replace('(s16)(&x)[0]', '(u16)(&x)[0]'),
            'wrong-second-type': self.body.replace('0, 0, 0, arg11,', '0, 0, 0, arg10,'),
            'wrong-width': self.body.replace('(u32)arg7 << 12', '(u32)arg8 << 12'),
            'wrong-callback': self.body.replace('(s32)func_1000EBC4,', '0,'),
        }
        runs = [('O2', self.body, '-O2', True), ('O0', self.body, '-O0', True)]
        runs += [('negative-' + name, body, '-O2', False) for name, body in controls.items()]
        exits = {}
        for name, body, profile, success in runs:
            if not success:
                self.assertNotEqual(body, self.body, name)
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace('BODY', body))
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-ffreestanding', '-nostdlib', '-static',
                '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter', str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            exits[name] = result.returncode
            if success:
                self.assertEqual(result.returncode, 0, name)
            else:
                self.assertIn(result.returncode, (10, 11, 12), name)
        self.receipt('native', cases_each_O2_O0=65536, effective_negative_controls=len(controls),
            all_49_49_12_packet_words_checked=True, source_expression_capture_provider_not_production_factory_ABI=True,
            no_physical_home_write_or_instruction_equivalence_claim=True, controlled_exits=exits)

    def test_08_other_owner_functions_relocations_and_pools_unchanged(self):
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
            reloc = lambda o, f: [(at - f['value'], value) for at, value in o[2].items()
                if f['value'] <= at < f['value'] + f['size']]
            self.assertEqual(reloc(old, f), reloc(new, g), name)
        self.assertEqual(normalized_pools(old_obj), normalized_pools(self.obj))
        self.receipt('neighbors', unchanged_neighbors=len(old[1]) - 1, raw_bytes_sizes_relative_relocations_and_pools_equal=True,
            target_still_nonmatching_and_uninstalled=True)

    def test_09_independent_rebases_of_both_call_targets_and_callback(self):
        data, functions, rel = parse_object(self.obj)
        emitted, missing = emit_function(data, functions[source.FUNCTION], rel, source.FUNCTION,
            {'func_1516D99C': source.CALLEE, 'func_1000FA64': source.EVENT, 'func_1000EBC4': source.CALLBACK})
        self.assertEqual(missing, [])
        path = self.out / 'candidate-reloc.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + emitted)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        args = tuple((0x87654321 + i * 0x1020304) & 0xFFFFFFFF for i in range(17))
        for index, delta in enumerate((0, 0x10000, -0x10000)):
            entry, callee, event = source.ENTRY + delta, source.CALLEE - delta, source.EVENT + index * 0x10000
            callback = (0x10007FFC, 0x10018004, 0x1000F000)[index]
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            outputs = []
            for name in ('original', 'candidate'):
                elf = self.out / ('%s-rebase-%d.elf' % (name, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=func_1516D99C=0x%X' % callee, '--defsym=func_1000FA64=0x%X' % event,
                    '--defsym=func_1000EBC4=0x%X' % callback, '-o', str(elf), str(self.out / (name + '-reloc.o'))],
                    check=True, capture_output=True)
                outputs.append(list(struct.unpack_from('>199I', sections(elf)['.text'][1])))
            predicted = list(self.truth)
            sites = [i for i, word in enumerate(predicted) if word >> 26 == 3]
            self.assertEqual(sites, [102, 174, 193])
            for at, target in zip(sites, (callee, callee, event)):
                predicted[at] = 0x0C000000 | (target >> 2 & 0x3FFFFFF)
            self.assertEqual(predicted[177:179], [0x3C0E1001, 0x25CEEBC4])
            predicted[177] = 0x3C0E0000 | ((callback + 0x8000) >> 16 & 65535)
            predicted[178] = 0x25CE0000 | (callback & 65535)
            self.assertEqual(outputs[0], predicted)
            self.assertNotEqual(outputs[1], outputs[0])
            for words in outputs:
                model = PairedOracle(words, args, entry=entry, callee=callee, event=event).run()
                self.assertEqual(model.calls, expected(args, callee=callee, event=event, callback=callback))
        self.receipt('rebases', independent_source_ROM_rebases=3, callback_signed_low_carry_cases=True,
            original_and_candidate_normal_packets_checked=True, candidate_instruction_mismatch_retained=True)


if __name__ == '__main__':
    unittest.main()
