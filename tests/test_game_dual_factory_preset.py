"""Two complete packets, live homes, saved snapshot, real factories and retail callers."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_dual_factory_preset as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_factory_preset_wrapper import state as basic_state
from tools.tests.test_game_actor_mask_scan_match import MaskOracle, AccessFault, CallBoundary
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_record_factory as factory
from tools.tests import test_game_table_fade_match as prior


def packet(args, second=False, saved=None):
    p = [0] * 49
    for i, value in ((0, 3), (3, 43), (5, 255), (6, 255), (7, 255), (12, 2),
            (19, 3 if second else 2), (27, 80), (28, 80), (31, 7 if second else args[1]),
            (32, 4), (33, 4), (34, args[0] & 255 if saved is None else saved),
            (35, args[2] if second else 16), (38, 129), (39, 5 if second else 4),
            (41, 1), (45, 1), (46, args[3] if second else 0), (47, args[4] & 255), (48, args[5])):
        p[i] = value & 0xFFFFFFFF
    return tuple(p)


def expected(args, mode=0):
    incoming = list(args)
    saved = args[0] & 255
    if mode == 2:
        incoming = [0xC5000100 + i for i in range(6)]
    elif mode == 3:
        saved = 0x876543A5
        incoming[4] = 0xFF123480
    return [(source.CALLEE, *packet(args)), (source.CALLEE, *packet(incoming, True, saved))]


def state(model):
    return basic_state(model), model.lo, model.condition, model.writes, model.visits


class DualOracle(MaskOracle):
    def __init__(self, words, args, phase=0, mode=0, fault=None, entry=source.ENTRY, callee=source.CALLEE):
        memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-768, 0x800)}
        for i, value in enumerate(args[4:], 4):
            put(memory, STACK + phase + i * 4, value)
        super().__init__(words, memory, phase=phase, mode=mode, fault=fault, entry=entry, arguments=args)
        self.callee = callee

    def record_call(self, target):
        assert target == self.callee
        args = self.arguments(49)
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        assert target == self.callee
        if self.mode == 1:
            for i in range(4):
                self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        if len(self.calls) == 1:
            if self.mode == 2:
                for i in range(6):
                    self.put(STACK + self.phase + i * 4, 0xC5000100 + i, 4)
            elif self.mode == 3:
                self.put(STACK + self.phase - 4, 0x876543A5, 4)
                self.put(STACK + self.phase + 16, 0xFF123480, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0xABCD0000 + len(self.calls)


def controls():
    return {
        'narrow-arg1': source.SELECTED.replace('0, 0, arg1,', '0, 0, (u16)arg1,'),
        'narrow-arg2': source.SELECTED.replace('(&firstType)[0], arg2,', '(&firstType)[0], (u8)arg2,'),
        'narrow-arg3': source.SELECTED.replace('1, arg3,', '1, (u8)arg3,'),
        'wrong-snapshot': source.SELECTED.replace('firstType = (u8)arg0;', 'firstType = (u8)arg1;'),
        'wide-fifth': source.SELECTED.replace('1, 0, (u8)arg4,', '1, 0, arg4,'),
        'wrong-preset': source.SELECTED.replace('0x2B,', '0x2A,'),
        'wrong-second': source.SELECTED.replace('0, 0, 0, 3, 0, 0, 0, 0,', '0, 0, 0, 2, 0, 0, 0, 0,'),
        'wrong-last': source.SELECTED.replace('(u8)(&arg4)[0], arg5', '(u8)(&arg4)[0], arg0'),
    }


class DualPresetCandidateTests(unittest.TestCase):
    def test_scope_and_strict_direct_match_gate(self):
        self.assertEqual(len(source.PATHS), 55)
        self.assertEqual(len(set(source.PATHS.values())), 55)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        for words, differences, frame, diagnostic in ((149, 0, 216, ''), (148, 2, 216, ''), (148, 0, 224, ''), (148, 0, 216, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=words, differences=differences, frame=frame, diagnostics=diagnostic))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))
        before = 's32 func_1516F2F8() {\n    return 0;\n}\nvoid other(void) { }\n'
        self.assertTrue(source.recovered_owner(before).endswith('void other(void) { }\n'))
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))
        self.assertNotIn('volatile', source.SELECTED)


class DualPresetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>148I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_08_all_original_801_archive_fingerprints = prior.TableFadeMatchTests.test_08_all_original_801_archive_fingerprints

    def test_01_direct_words_real_padder_and_all_owner_neighbors(self):
        self.assertEqual(self.words, self.truth)
        old_obj, diagnostic = source.build.compile_owner(self.root, self.out, (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostic, '')
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
        self.receipt('owner', raw_and_production_padded_exact_words=148, frame=216, unchanged_neighbors=29,
            relative_relocations_and_pools_fixed=True, guards_added=0, profile_changes=0)

    def test_02_both_full_packets_all_private_state_and_provider_clobbers(self):
        cases = [(0,) * 6, (0xFFFFFFFF,) * 6, (0x80000000, 0xFFFF0000, 0xFFFFFF80, 0x7FFFFFFF, 0xFFFF0080, 0x12345678)]
        cases += [tuple((i * 1664525 + j * 0x1020304 + 1013904223) & 0xFFFFFFFF for j in range(6))
            for i in range(512)]
        visits = set()
        for args in cases:
            for phase in (0, 8):
                for mode in range(4):
                    pair = [DualOracle(w, args, phase, mode).run() for w in (self.words, self.truth)]
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    self.assertEqual(pair[0].calls, expected(args, mode))
                    self.assertEqual(pair[0].r[2], 0xABCD0002)
                    self.assertEqual(pair[0].r[29], STACK + phase)
                    calls = [i for i, e in enumerate(pair[0].events) if e[0] == 'CALL']
                    self.assertEqual(pair[0].events[calls[0] - 1], ('W', STACK + phase - 216 + 124, 4, args[1]))
                    second_last = expected(args, mode)[1][-1]
                    self.assertEqual(pair[0].events[calls[1] - 1], ('W', STACK + phase - 216 + 192, 4, second_last))
                    visits |= pair[0].visits
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 592, 4)))
        self.receipt('abi', paired_cases=len(cases) * 8, packet_words_each=49, calls_per_case=2,
            all_148_words_visited=True, full_literal_private_state_equal=True, phases=[0, 8],
            live_input_homes_and_saved_snapshot_home=True, both_final_packet_words_in_call_delays=True,
            physical_provider_home_writes_not_portable_C_or_hardware_claim=True)

    def test_03_every_fired_guest_memory_fault_prefix(self):
        args = (0x87654321, 0xFEDCBA98, 0xFFFFFF80, 0x12345678, 0xFFFF00A5, 0x7FFFFFFF)
        count = 0
        for phase in (0, 8):
            for mode in (0, 2, 3):
                whole = DualOracle(self.truth, args, phase, mode).run()
                for fault in range(whole.accesses):
                    pair = [DualOracle(w, args, phase, mode, fault) for w in (self.words, self.truth)]
                    for model in pair:
                        with self.assertRaises(AccessFault):
                            model.run()
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    count += 1
        self.receipt('prefixes', paired_fired_faults=count, full_literal_prefixes_equal=True,
            no_affine_private_or_portable_C_fault_claim=True)

    def test_04_compiled_width_controls_and_guest_only_home_controls(self):
        args = (0x87654321, 0xFEDCBA98, 0xFFFFFF80, 0x12345678, 0xFFFF00A5, 0x7FFFFFFF)
        variants = dict(controls(), cached_fifth=source.SELECTED.replace('(u8)(&arg4)[0]', '(u8)arg4'),
            cached_snapshot=source.SELECTED.replace('(&firstType)[0], arg2', 'firstType, arg2'))
        effective, native_only = [], {}
        for name, body in variants.items():
            self.assertNotEqual(body, source.SELECTED)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            failed = any(DualOracle(words, args, mode=mode).run().calls != expected(args, mode) for mode in (0, 2, 3))
            if failed:
                self.assertGreater(row['differences'], 0)
                effective.append(name)
            else:
                self.assertIn(name, ('narrow-arg1', 'narrow-arg2', 'narrow-arg3'), name)
                native_only[name] = row['differences']
        self.assertTrue({'cached_fifth', 'cached_snapshot'}.issubset(effective))
        self.receipt('controls', effective_compiled_guest_controls=effective, native_only_narrowing_controls=native_only,
            no_guards_applied_to_any_mutant=True)

    def test_05_native32_two_full_packets_at_O2_O0_and_all_eight_negatives(self):
        params = ','.join('u32 p%d' % i for i in range(49))
        capture = ','.join('p%d' % i for i in range(49))
        harness = '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef unsigned short u16;
static u32 captured[2][49],count,original[6];
__attribute__((noinline,noclone)) void func_1516D99C(''' + params + '''){
 u32 v[49]={''' + capture + '''};u32 i;if(count<2)for(i=0;i<49;i++)captured[count][i]=v[i];count++;
}
''' + source.SELECTED + '''
static void (*volatile invoke)(s32,s32,s32,s32,s32,s32)=func_1516F2F8;
static int check(u32 n){u32 i,k,p[49];count=0;
 for(i=0;i<6;i++)original[i]=0x87650000u+i*0x1020304u+n;
 invoke((s32)original[0],(s32)original[1],(s32)original[2],(s32)original[3],(s32)original[4],(s32)original[5]);
 if(count!=2)return 10;for(k=0;k<2;k++){
  for(i=0;i<49;i++)p[i]=0;p[0]=3;p[3]=43;p[5]=p[6]=p[7]=255;p[12]=2;p[19]=2+k;
  p[27]=p[28]=80;p[31]=k?7:original[1];p[32]=p[33]=4;p[34]=original[0]&255;
  p[35]=k?original[2]:16;p[38]=129;p[39]=4+k;p[41]=p[45]=1;p[46]=k?original[3]:0;
  p[47]=original[4]&255;p[48]=original[5];for(i=0;i<49;i++)if(p[i]!=captured[k][i])return 11;
 }return 0;}
static int run(void){u32 i;int r;if(sizeof(void*)!=4||sizeof(s32)!=4)return 12;
 for(i=0;i<65536;i++){r=check(i);if(r)return r;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''
        for name, body, profile, ok in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace(source.SELECTED, body))
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-ffreestanding',
                '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter', str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            self.assertEqual(result.returncode == 0, ok, (name, result.returncode))
        self.receipt('native', cases_per_O2_O0=65536, full_49_word_capture_provider=True,
            eight_effective_native_negatives=True, guest_home_mutations_not_claimed_native=True)

    def test_06_independent_original_and_three_call_rebases(self):
        data, functions, rel = parse_object(self.obj)
        emitted, missing = emit_function(data, functions[source.FUNCTION], rel, source.FUNCTION, {'func_1516D99C': source.CALLEE})
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for name, body in dict(selected=emitted, original='glabel ' + source.FUNCTION + '\n' + original).items():
            path = self.out / (name + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        for index, delta in enumerate((0, 0x10000, -0x10000)):
            entry, callee = source.ENTRY + delta, source.CALLEE - delta
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            outputs = []
            for name in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (name, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=func_1516D99C=0x%X' % callee, '-o', str(elf), str(self.out / (name + '-reloc.o'))], check=True, capture_output=True)
                outputs.append(list(struct.unpack_from('>148I', sections(elf)['.text'][1])))
            self.assertEqual(outputs[0], outputs[1])
            args = (0x87654321, 0xFEDCBA98, 0xFFFFFF80, 0x12345678, 0xFFFF00A5, 0x7FFFFFFF)
            model = DualOracle(outputs[0], args, entry=entry, callee=callee).run()
            self.assertEqual(model.calls, [(callee, *p[1:]) for p in expected(args)])
        self.receipt('rebases', independent_original_C_pairs=3, full_148_word_equality=True, both_call_bindings_rebased=True)

    def test_07_current_real_factories_allocator_and_two_allocation_results(self):
        image = (self.root / source.PATHS['elf']).read_bytes()
        connected = {}
        for entry, rom, count in ((source.CALLEE, 0x19AE4C, 125), (0x15167A68, 0x194F18, 28)):
            words = list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        class Chain(factory.FactoryOracle):
            def hook(model, target):
                if target == factory.ALLOCATE:
                    model.result = model.results[model.allocation]
                    model.allocation += 1
                factory.FactoryOracle.hook(model, target)
        cases = 0
        for i in range(64):
            args = tuple((i * 1664525 + j * 0x1020304 + 1013904223) & 0xFFFFFFFF for j in range(6))
            for results in ((0, 0), (factory.RECORD, 0), (0, factory.RECORD + 128), (factory.RECORD, factory.RECORD + 128)):
                pair = []
                for words in (self.words, self.truth):
                    model = Chain(words, args, phase=(i & 1) * 8, entry=source.ENTRY, connected=connected, chain=True)
                    model.results, model.allocation = results, 0
                    model.memory.update({factory.RECORD + 128 + j: (j * 13 + 0xC5) & 255 for j in range(-16, 96)})
                    pair.append(model.run())
                self.assertEqual(state(pair[0]), state(pair[1]))
                self.assertEqual([c for c in pair[0].calls if c[0] == source.CALLEE], expected(args))
                self.assertEqual(pair[0].allocation, 2)
                for index, result in enumerate(results):
                    if not result:
                        continue
                    p = packet(args, bool(index))
                    memory = factory.fixture(p)
                    memory.update({result + j: (j * 13 + 0xC5) & 255 for j in range(-16, 96)})
                    reference_record = factory.reference(memory, p, result)[0]
                    for at in range(result + 14, result + 76):
                        self.assertEqual(pair[0].memory[at], reference_record[at])
                    self.assertEqual(pair[0].memory[result], 17)
                    self.assertEqual(pair[0].memory[result + 1], args[5] & 255)
                    self.assertEqual(pair[0].memory[result + 12], args[4] & 255)
                cases += 1
        self.receipt('chain', paired_cases=cases, real_factory_and_allocator_words=[125, 28], independent_null_success_pairs=4,
            both_full_packets_and_initialized_records_checked=True, lower_heap_registration_opaque=True)

    def test_09_all_five_original_caller_windows_and_current_placeholder_boundary(self):
        class Caller(MaskOracle):
            def record_call(model, target):
                self.assertEqual(target, source.ENTRY)
                model.calls.append((target, *model.arguments(6)))
                raise CallBoundary
        image = (self.root / source.PATHS['elf']).read_bytes()
        sites = [(0x15028650, 0x55B00, 7, None), (0x1506DFE4, 0x9B494, 9, (30, 20, 2)),
            (0x1506E010, 0x9B4C0, 9, (18, 12, 2)), (0x1506E03C, 0x9B4EC, 9, (60, 120, 2)),
            (0x1506E0A8, 0x9B558, 9, (18, 12, 0))]
        cases = 0
        for entry, rom, count, constants in sites:
            words = list(struct.unpack_from('>%dI' % count, self.rom, rom))
            current = list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(sum(a == b for a, b in zip(current, words)), 0)
            self.assertEqual(words[-2], 0x0D45BCBE)
            for phase in (0, 8):
                memory = {STACK + j: 0xA5 for j in range(-256, 0x800)}
                memory[0x800C3E78] = 0x80
                put(memory, STACK + phase + 0x770, 0xFF1234A5)
                model = Caller(words, memory, phase=phase, entry=entry, arguments=(0, 0x87654321))
                model.lo = 0xFFFFFFFE
                with self.assertRaises(CallBoundary):
                    model.run()
                args = (0xFFFFFFFE, 0x87654321, 0x87654321, 0, 0xFF1234A5, 0) if constants is None else (128, *constants, 255, 0)
                self.assertEqual(model.calls, [(source.ENTRY, *args)])
                cases += 1
        self.receipt('callers', original_windows=5, fired_boundary_cases=cases, six_full_physical_inputs_verified=True,
            all_five_linked_windows_currently_placeholders=True, no_current_or_full_caller_gameplay_claim=True)


if __name__ == '__main__':
    unittest.main()
