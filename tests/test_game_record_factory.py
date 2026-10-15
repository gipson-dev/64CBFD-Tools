"""Packed factory fields, null/provider/alias cases, ordering, native C and call chain."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_record_factory as source
from tools.experiments import game_factory_preset_wrapper as wrapper
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import MaskOracle, AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_factory_preset_wrapper import packet
from tools.tests.test_game_record_constructor_match import elf_slot_offset

RECORD, ALLOCATE, REGISTER = 0x20000, 0x10003C6C, 0x15168A4C
STORES = [(14, 0, 2), (16, 1, 2), (18, 2, 2), (20, 27, 2), (22, 28, 2), (24, 29, 2), (26, 30, 2)]
STORES += [(off, arg, 1) for off, arg in zip(
    (36, 37, 38, 39, 40, 42, 43, 44, 41, *range(45, 59)),
    (3, 4, 5, 6, 7, 9, 10, 11, 8, *range(12, 26)))]


def fixture(args, phase=0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-640, 512)}
    memory.update({RECORD + i: (i * 13 + 0xC5) & 255 for i in range(-16, 96)})
    for i, value in enumerate(args[4:], 4):
        put(memory, STACK + phase + i * 4, value)
    return memory


def effects(memory, incoming, mode):
    if mode == 1:
        for i in (0, 1, 2, 26, 31, 39, 41, 44):
            put(memory, incoming + i * 4, (0x80A5F1E3 + i * 65539) & 0xFFFFFFFF)


def reference(memory, args, result, phase=0, mode=0):
    memory, incoming, events = dict(memory), STACK + phase, []

    def load(index, size):
        return read(memory, incoming + index * 4 + 4 - size, size)

    def store(offset, value, size=1):
        put(memory, result + offset, value, size)
        events.append((result + offset, size, value & ((1 << (size * 8)) - 1)))

    put(memory, incoming - 4, 0xDEAD0000)
    for i, value in enumerate(args[:4]):
        put(memory, incoming + i * 4, value)
    call = (source.CALLEE, 102 if load(44, 4) else 17, load(48, 4), 76, 0, load(47, 1), 1)
    put(memory, incoming - 12, 1)
    put(memory, incoming - 16, call[5])
    # The provider may write incoming homes; field loads after the call stay live.
    effects(memory, incoming, mode)
    load(0, 2)  # The null-check delay slot reads this home on either path.
    if result:
        for offset, index, size in STORES:
            store(offset, load(index, size), size)
        shared, byte26 = load(31, 2), load(26, 1)
        store(32, shared, 2)
        store(60, shared)
        store(59, byte26)
        for offset, index in zip(range(61, 65), range(32, 36)):
            store(offset, load(index, 1))
        store(28, load(36, 2), 2)
        store(30, load(37, 2), 2)
        value = load(38, 2)
        store(34, value, 2)
        byte39 = load(39, 1)
        store(66, 0)
        store(65, byte39)
        store(67, load(40, 1))
        variant, limited = load(44, 4), load(41, 1)
        if variant and limited >= 4:
            put(memory, incoming + 41 * 4 + 3, 3, 1)
        store(68, load(41, 1))
        for offset, index in ((69, 42), (70, 43), (71, 45), (72, 46)):
            store(offset, load(index, 1))
    return memory, call, events


class FactoryOracle(MaskOracle):
    def __init__(self, words, args, result=RECORD, phase=0, mode=0, fault=None,
            entry=source.ENTRY, callee=source.CALLEE, connected=None, chain=False):
        super().__init__(words, fixture(args, phase), phase=phase, mode=mode, fault=fault,
            entry=entry, arguments=args, connected=connected)
        self.result, self.callee = result, callee
        self.incoming = STACK + phase

    def record_call(self, target):
        count = 49 if target == source.ENTRY else 6 if target == self.callee else 5 if target == ALLOCATE else 2
        assert target in (source.ENTRY, self.callee, ALLOCATE, REGISTER)
        self.calls.append((target, *self.arguments(count)))
        self.events.append(('CALL', target, self.arguments(count)))

    def hook(self, target):
        assert target in (self.callee, ALLOCATE, REGISTER)
        if target == self.callee:
            effects(self.memory, self.incoming, self.mode)
        if target == REGISTER:
            self.put(self.result, self.arguments(2)[1], 1)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = self.result


def state(model):
    return (model.memory, model.r, model.f, model.events, model.calls, model.accesses)


def controls():
    return {
        'wrong-kind': source.SELECTED.replace('kind = 0x66;', 'kind = 0x65;'),
        'wrong-size': source.SELECTED.replace('arg48, 0x4C,', 'arg48, 0x48,'),
        'wrong-byte': source.SELECTED.replace('record[0x2A] = arg9;', 'record[0x2A] = arg8;'),
        'wrong-halfword': source.SELECTED.replace('(record + 0x14) = arg27;', '(record + 0x14) = arg28;'),
        'wrong-limit': source.SELECTED.replace('arg41 >= 4', 'arg41 >= 5'),
        'missing-clear': source.SELECTED.replace('record[0x42] = 0;', 'record[0x42] = 1;'),
    }


class RecordFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>125I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_full_slot_guards_neighbor_owner_and_fail_closed_controls(self):
        self.assertEqual(self.words, self.truth)
        before, diagnostics = build.compile_owner(self.root, self.out,
            (self.out / 'before-preset_owner').read_text(), 'before')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(before), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            rel = lambda o, f: [(p - f['value'], r) for p, r in o[2].items() if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(rel(old, f), rel(new, g), name)
        self.assertEqual(normalized_pools(before), normalized_pools(self.obj))
        f = new[1][source.FUNCTION]
        raw = new[0][f['value']:f['value'] + f['size']]
        for i in range(125):
            bad = bytearray(raw)
            bad[i * 4] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(bad), source.RELOCATIONS)
        with self.assertRaises(ValueError):
            source.normalize(raw, {68: [('R_MIPS_26', 'func_15167A69')]})
        guard_bytes = source.guard_manifest((self.out / 'before-guards').read_bytes())
        self.assertTrue(guard_bytes.startswith((self.out / 'before-guards').read_bytes()))
        with self.assertRaises(ValueError):
            source.guard_manifest(guard_bytes)
        self.receipt('owner', raw_words=125, raw_differences=6, guarded_differences=0, guards=6,
            unchanged_neighbors=29, caller_raw_words=78, caller_differences=0,
            all_125_raw_word_flips_and_relocation_rejected=True, pools_and_neighbor_relocations_fixed=True)

    def test_02_all_fields_null_high_bits_live_provider_and_guest_aliases(self):
        cases = []
        for i in range(128):
            args = [(i * 1664525 + j * 0x1234F1 + 1013904223) & 0xFFFFFFFF for j in range(49)]
            args[44], args[41] = (0, 1, 0x80000000, 0xFFFFFFFF)[i % 4], (0, 1, 3, 4, 5, 127, 128, 255)[i % 8]
            cases.append(tuple(args))
        count, aliases = 0, 0
        for args in cases:
            for phase in (0, 8):
                for result in (0, RECORD, STACK + phase, STACK + phase + 0x70):
                    for mode in (0, 1):
                        memory = fixture(args, phase)
                        expected, call, writes = reference(memory, args, result, phase, mode)
                        models = [FactoryOracle(w, args, result, phase, mode).run() for w in (self.words, self.truth)]
                        self.assertEqual(state(models[0]), state(models[1]))
                        self.assertEqual(models[0].memory, expected, (args[41], args[44], phase, result, mode))
                        self.assertEqual(models[0].calls, [call])
                        actual = [event[1:] for event in models[0].events
                            if event[0] == 'W' and result and result <= event[1] < result + 76]
                        if result == RECORD:
                            self.assertEqual(actual, writes)
                        count += 1
                        aliases += result not in (0, RECORD)
        self.receipt('fields', cases=count, guest_stack_alias_cases=aliases, all_49_inputs_and_packed_fields=True,
            null_and_both_stack_phases=True, post_provider_homes_live=True,
            full_word_kind_and_context_and_low_byte_flag=True, model_not_hardware_runtime=True)

    def test_03_all_guest_access_fault_prefixes_and_raw_schedule_domain(self):
        args = tuple((0x87654321 + i * 0x1020304) & 0xFFFFFFFF for i in range(49))
        pairs = 0
        for phase in (0, 8):
            for result in (0, RECORD, STACK + phase + 0x70):
                whole = FactoryOracle(self.words, args, result, phase, 1).run()
                for fault in range(whole.accesses):
                    models = [FactoryOracle(w, args, result, phase, 1, fault) for w in (self.words, self.truth)]
                    for model in models:
                        with self.assertRaises(AccessFault):
                            model.run()
                    self.assertEqual(state(models[0]), state(models[1]))
                    pairs += 1
        raw = FactoryOracle(self.raw, args).run()
        fixed = FactoryOracle(self.words, args).run()
        self.assertEqual(raw.memory, fixed.memory)
        self.assertEqual(raw.calls, fixed.calls)
        self.assertNotEqual(raw.events, fixed.events)
        self.receipt('prefixes', paired_fired_guest_access_faults=pairs,
            raw_and_guarded_heap_results_equal_but_access_order_differs=True,
            only_guarded_guest_order_has_retail_alias_and_fault_qualification=True)

    def test_04_six_effective_semantic_controls_without_guarding_them(self):
        args = [(0x87654321 + i * 0x1020304) & 0xFFFFFFFF for i in range(49)]
        args[41], args[44] = 4, 1
        wanted = reference(fixture(args), args, RECORD)
        for name, body in controls().items():
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            model = FactoryOracle(words[source.FUNCTION], args).run()
            self.assertNotEqual((model.memory, model.calls), (wanted[0], [wanted[1]]), name)
        self.receipt('controls', six_effective_compiled_semantic_negatives=True, no_guards_on_mutants=True)

    def test_05_native32_selected_body_with_endianness_invariant_flag_words(self):
        params = 'u32 values[49]'
        arguments = ','.join('values[%d]' % i for i in range(49))
        checks = []
        for offset, index, size in STORES + [(32, 31, 2), (60, 31, 1), (59, 26, 1)] + [
                (offset, index, 1) for offset, index in zip(range(61, 65), range(32, 36))] + [
                (28, 36, 2), (30, 37, 2), (34, 38, 2), (65, 39, 1), (67, 40, 1),
                (69, 42, 1), (70, 43, 1), (71, 45, 1), (72, 46, 1)]:
            checks.append('if(*(u%d*)(record+%d)!=(u%d)values[%d])return 11;' % (size * 8, offset, size * 8, index))
        fixture_c = '''typedef unsigned char u8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;
#define NULL ((void*)0)
static u8 storage[112] __attribute__((aligned(16)));static u8 *record=storage+16;
static u32 count,failed,captured[6];static int null_result;
__attribute__((noinline,noclone)) void *func_15167A68(s32 a,s32 b,s32 c,s32 d,u8 e,u8 f){
 captured[0]=(u32)a;captured[1]=(u32)b;captured[2]=(u32)c;captured[3]=(u32)d;captured[4]=e;captured[5]=f;
 count++;return null_result?NULL:record;}
''' + source.SELECTED + '''
static void invoke(''' + params + '''){func_1516D99C(''' + arguments + ''');}
static int run(void){u32 i,j,values[49];if(sizeof(void*)!=4||sizeof(s32)!=4)return 12;
 for(i=0;i<4096;i++){
  for(j=0;j<112;j++)storage[j]=0xA5;
  for(j=0;j<49;j++)values[j]=i*1664525u+j*0x1234F1u+1013904223u;
  values[44]=(i&1)?0x80000000u:0;values[41]=(i>>1)&255;
  values[47]=(i&255)*0x01010101u;
  count=failed=0;null_result=(i&7)==7;invoke(values);
  if(count!=1||captured[0]!=(values[44]?102u:17u)||captured[1]!=values[48]||captured[2]!=76||captured[3]||captured[4]!=(values[47]&255)||captured[5]!=1)return 10;
  if(null_result){for(j=0;j<112;j++)if(storage[j]!=0xA5)return 13;continue;}
''' + '\n'.join(checks) + '''
  if(record[66]||record[68]!=(values[44]&&((u8)values[41]>=4)?3:(u8)values[41]))return 14;
  for(j=0;j<16;j++)if(storage[j]!=0xA5||storage[92+j]!=0xA5)return 15;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        for name, body, flag, ok in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + n, b, '-O2', False) for n, b in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(fixture_c.replace(source.SELECTED, body))
            result = subprocess.run(['cc', '-m32', flag, '-std=c11', '-fno-strict-aliasing', '-ffreestanding',
                '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter', str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], capture_output=True, timeout=30)
            self.assertEqual(result.returncode == 0, ok, (name, result.returncode))
        self.receipt('native', actual_selected_C=True, cases_per_O2_O0=4096, six_effective_negatives=True,
            flag_word_has_replicated_bytes_for_host_endianness=True,
            arbitrary_flag_high_bits_qualified_in_guest_not_native=True, no_native_stack_alias_claim=True)

    def test_06_original_assembly_and_three_independent_call_rebases(self):
        raw, fs, rel = parse_object(self.obj)
        f = fs[source.FUNCTION]
        words = source.normalize(raw[f['value']:f['value'] + f['size']], source.RELOCATIONS)
        patched = bytearray(raw)
        struct.pack_into('>125I', patched, f['value'], *words)
        text, missing = emit_function(bytes(patched), f, rel, source.FUNCTION, {'func_15167A68': source.CALLEE})
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for label, body in dict(selected=text, original='glabel ' + source.FUNCTION + '\n' + original).items():
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], capture_output=True, check=True)
        for index, delta in enumerate((0, 0x10000, -0x10000)):
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + delta))
            outputs = []
            for label in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (label, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=func_15167A68=0x%X' % (source.CALLEE - delta), '-o', str(elf), str(self.out / (label + '-reloc.o'))], capture_output=True, check=True)
                outputs.append(sections(elf)['.text'][1][:500])
            self.assertEqual(outputs[0], outputs[1])
        self.receipt('rebases', independent_original_assembly_pairs=3, guarded_words_not_direct_C=True)

    def test_07_actual_wrapper_factory_and_current_allocator_chain(self):
        before = (self.out / 'before-elf').read_bytes()
        allocator = list(struct.unpack_from('>28I', before, elf_slot_offset(before, source.CALLEE, 112)))
        self.assertEqual(allocator, list(struct.unpack_from('>28I', self.rom, 0x194F18)))
        wrapped = list(struct.unpack_from('>78I', before, elf_slot_offset(before, wrapper.ENTRY, 312)))
        self.assertEqual(wrapped, list(struct.unpack_from('>78I', self.rom, wrapper.ROM)))
        connected = dict(zip(range(source.ENTRY, source.ENTRY + 500, 4), self.words))
        connected.update(zip(range(source.CALLEE, source.CALLEE + 112, 4), allocator))
        for i in range(128):
            args = tuple((i * 1664525 + j * 0x1020304 + 1013904223) & 0xFFFFFFFF for j in range(4))
            result = 0 if i % 4 == 0 else RECORD
            model = FactoryOracle(wrapped, args, result, entry=wrapper.ENTRY, connected=connected, chain=True).run()
            self.assertEqual(model.calls[0], (source.ENTRY, *packet(args)))
            self.assertEqual(model.calls[1], (source.CALLEE, 17, args[3], 76, 0, args[2] & 255, 1))
            self.assertEqual(model.calls[2], (ALLOCATE, 76, 1, 0, 0, 1))
            self.assertEqual(len(model.calls), 3 if not result else 4)
            if result:
                expected = reference(fixture(packet(args)), packet(args), result)[0]
                for address in range(RECORD + 14, RECORD + 76):
                    self.assertEqual(model.memory[address], expected[address])
                self.assertEqual(model.memory[RECORD], 17)
                self.assertEqual(model.memory[RECORD + 1], args[3] & 255)
                self.assertEqual(model.memory[RECORD + 12], args[2] & 255)
        self.receipt('chain', actual_wrapper_factory_allocator_cases=128, allocator_words=28,
            only_heap_and_registration_are_opaque=True, no_full_gameplay_acceptance=True)


if __name__ == '__main__':
    unittest.main()
