"""Full packed fields, live optional selector, call lifetime, native C and actual helpers."""
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_small_record_factory as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import MaskOracle, AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset

RECORD, BINDING, HEAP, REGISTER, BUILDER = 0x20000, 0x22000, 0x10003C6C, 0x15168A4C, 0x15044964
FIRST = [(14, 0, 2), (16, 1, 2), (18, 2, 2)] + [(i + 26, i + 3, 1) for i in range(10)]
REST = [(20, 23, 2), (22, 24, 2)]


def fixture(args, phase=0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-768, 512)}
    for base in (RECORD, BINDING):
        memory.update({base + i: (i * 13 + 0xC5) & 255 for i in range(-16, 96)})
    for i, value in enumerate(args[4:], 4):
        put(memory, STACK + phase + i * 4, value)
    return memory


def provider_effects(memory, incoming, record, mode, second=False):
    if mode:
        for i in range(4):
            put(memory, incoming - 56 + i * 4, 0xB5000000 + i + (16 if second else 0))
        if not second:
            for i in (0, 1, 2, 13, 25, 26, 28):
                put(memory, incoming + i * 4, (0xA5F1E3C7 + i * 65539) & 0xFFFFFFFF)
        else:
            put(memory, record + 0x2B, 0x6D, 1)
            put(memory, record + 0x30, 0xDEADBEEF)


def reference(memory, args, result, binding=BINDING, phase=0, mode=0):
    memory, incoming, calls = dict(memory), STACK + phase, []
    load = lambda i, n: read(memory, incoming + i * 4 + 4 - n, n)
    put(memory, incoming - 12, 0xDEAD0000)
    for i, value in enumerate(args[:4]):
        put(memory, incoming + i * 4, value)
    calls.append((source.ALLOCATOR, 103 if load(27, 4) else 18, load(30, 4), 52, 0, load(29, 1), 1))
    put(memory, incoming - 36, 1)
    put(memory, incoming - 40, calls[0][5])
    provider_effects(memory, incoming, result, mode)
    if not result:
        return memory, calls
    for offset, i, n in FIRST + REST:
        put(memory, result + offset, load(i, n), n)
    byte25 = load(25, 1)
    put(memory, result + 36, byte25, 1)
    half26 = load(26, 2)
    put(memory, result + 37, 0, 1)
    put(memory, result + 24, half26, 2)
    for i in range(13, 16):
        put(memory, result + 38 + i - 13, load(i, 1), 1)
    byte16, selector = load(16, 1), load(28, 4)
    put(memory, result + 41, byte16, 1)
    for i in range(17, 23):
        put(memory, result + 42 + i - 17, load(i, 1), 1)
    if selector:
        args2 = (0xFFFFFFFF, 0, selector, 20, 20, 20, 0, result + 14, result + 20)
        calls.append((source.SECONDARY, *args2))
        for i, value in enumerate(args2[4:], 4):
            put(memory, incoming - 56 + i * 4, value)
        put(memory, incoming - 4, result)
        provider_effects(memory, incoming, result, mode, True)
        put(memory, result + 48, binding)
    else:
        put(memory, result + 48, 0)
    return memory, calls


class SmallFactoryOracle(MaskOracle):
    def __init__(self, words, args, result=RECORD, binding=BINDING, phase=0, mode=0, fault=None,
            entry=source.ENTRY, allocator=source.ALLOCATOR, secondary=source.SECONDARY, connected=None):
        super().__init__(words, fixture(args, phase), phase=phase, mode=mode, fault=fault,
            entry=entry, arguments=args, connected=connected)
        self.result, self.binding, self.incoming = result, binding, STACK + phase
        self.allocator, self.secondary = allocator, secondary

    def record_call(self, target):
        counts = {self.allocator: 6, self.secondary: 9, HEAP: 5, REGISTER: 2, BUILDER: 8}
        assert target in counts
        args = self.arguments(counts[target])
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        assert target in (self.allocator, self.secondary, HEAP, REGISTER, BUILDER)
        if target == self.allocator:
            provider_effects(self.memory, self.incoming, self.result, self.mode)
        elif target == self.secondary:
            provider_effects(self.memory, self.incoming, self.result, self.mode, True)
        elif target == REGISTER:
            self.put(self.result, self.arguments(2)[1], 1)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = self.binding if target in (self.secondary, BUILDER) else self.result


def state(model):
    return (model.memory, model.r, model.f, model.events, model.calls, model.accesses)


def controls():
    return {
        'wrong-kind': source.SELECTED.replace('kind = 0x67;', 'kind = 0x66;'),
        'wrong-size': source.SELECTED.replace('arg30, 0x34,', 'arg30, 0x30,'),
        'wrong-halfword': source.SELECTED.replace('(record + 0x14) = arg23;', '(record + 0x14) = arg24;'),
        'wrong-pointer': source.SELECTED.replace('(s16 *)(record + 0x14)', '(s16 *)(record + 0x16)'),
        'inverted-secondary': source.SELECTED.replace('if (arg28 != 0)', 'if (arg28 == 0)'),
        'missing-clear': source.SELECTED.replace('record[0x25] = 0;', 'record[0x25] = 1;'),
    }


class SmallRecordFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>100I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_full_direct_slot_actual_padder_and_all_copied_neighbors(self):
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
        self.receipt('owner', words=100, raw_and_padded_differences=0, guards_added=0,
            unchanged_neighbors=29, existing_large_factory_and_wrapper_fixed=True,
            relative_relocations_and_pools_fixed=True, flags=['-O2', '-g3'])

    def test_02_complete_fields_live_selector_nulls_and_both_provider_effects(self):
        count, aliases = 0, 0
        for i in range(96):
            args = [(i * 1664525 + j * 0x1234F1 + 1013904223) & 0xFFFFFFFF for j in range(31)]
            args[27], args[28] = (0, 1, 0x80000000, 0xFFFFFFFF)[i % 4], (0, 1, 0x80000000)[i % 3]
            for phase in (0, 8):
                for result in (0, RECORD, STACK + phase, STACK + phase + 0x50):
                    for binding in (0, BINDING):
                        for mode in (0, 1):
                            models = [SmallFactoryOracle(w, args, result, binding, phase, mode).run() for w in (self.words, self.truth)]
                            self.assertEqual(state(models[0]), state(models[1]))
                            expected = reference(fixture(args, phase), args, result, binding, phase, mode)
                            self.assertEqual((models[0].memory, models[0].calls), expected,
                                (i, phase, result, binding, mode))
                            count += 1
                            aliases += result not in (0, RECORD)
        self.receipt('fields', cases=count, stack_alias_cases=aliases, all_31_inputs=True,
            primary_and_secondary_nulls=True, live_incoming_homes_and_early_optional_selector=True,
            secondary_provider_clobbers_pointer_register_and_destination=True, frame=56,
            real_saved_record_at_sp34_and_final_pointer_store=True, guest_model_not_hardware=True)

    def test_03_all_fired_guest_access_fault_prefixes(self):
        total = 0
        for selector in (0, 7):
            args = [(0x87654321 + i * 0x1020304) & 0xFFFFFFFF for i in range(31)]
            args[28] = selector
            for phase in (0, 8):
                for result in (0, RECORD, STACK + phase + 0x50):
                    whole = SmallFactoryOracle(self.words, args, result, phase=phase).run()
                    for fault in range(whole.accesses):
                        pair = [SmallFactoryOracle(w, args, result, phase=phase, fault=fault) for w in (self.words, self.truth)]
                        for model in pair:
                            with self.assertRaises(AccessFault):
                                model.run()
                        self.assertEqual(state(pair[0]), state(pair[1]))
                        total += 1
        self.receipt('prefixes', paired_fired_guest_memory_faults=total,
            private_pointer_lifetime_and_both_call_delays=True, not_portable_C_fault_semantics=True)

    def test_04_six_effective_compiled_semantic_negatives(self):
        for name, body in controls().items():
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            self.assertGreater(row['differences'], 0)
            failures = 0
            for selector in (0, 7):
                args = [(0x87654321 + i * 0x1020304) & 0xFFFFFFFF for i in range(31)]
                args[27], args[28] = 1, selector
                model = SmallFactoryOracle(words, args).run()
                failures += (model.memory, model.calls) != reference(fixture(args), args, RECORD)
            self.assertGreater(failures, 0, name)
        self.receipt('controls', six_effective_compiled_semantic_negatives=True)

    def test_05_actual_native32_C_two_profiles_and_six_negatives(self):
        args = ','.join('values[%d]' % i for i in range(31))
        checks = []
        for offset, index, size in FIRST + REST + [(36, 25, 1), (24, 26, 2)] + [
                (38 + i - 13, i, 1) for i in range(13, 23) if i != 18]:
            checks.append('if(*(u%d*)(record+%d)!=(u%d)values[%d])return 11;' % (size * 8, offset, size * 8, index))
        fixture_c = '''typedef unsigned char u8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;
#define NULL ((void*)0)
struct PositionScaleRecord71820;
static u8 storage[96] __attribute__((aligned(16))),secondary[32];static u8 *record=storage+16;
static u32 first[6],second[9],count1,count2;static int null1,null2;
__attribute__((noinline,noclone)) void *func_15167A68(s32 a,s32 b,s32 c,s32 d,u8 e,u8 f){
 first[0]=(u32)a;first[1]=(u32)b;first[2]=(u32)c;first[3]=(u32)d;first[4]=e;first[5]=f;count1++;return null1?NULL:record;}
__attribute__((noinline,noclone)) struct PositionScaleRecord71820 *func_150448D0(s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,s16 *h,s16 *j){
 second[0]=(u32)a;second[1]=(u32)b;second[2]=(u32)c;second[3]=(u32)d;second[4]=(u32)e;second[5]=(u32)f;second[6]=(u32)g;second[7]=(u32)h;second[8]=(u32)j;
 count2++;record[0x2B]=0x6D;*(u32*)(record+0x30)=0xDEADBEEFu;
 return null2?NULL:(struct PositionScaleRecord71820*)secondary;}
''' + source.SELECTED + '''
static void invoke(u32 values[31]){func_1516D4E8(''' + args + ''');}
static int run(void){u32 i,j,values[31];if(sizeof(void*)!=4||sizeof(s32)!=4)return 12;
 for(i=0;i<4096;i++){
  for(j=0;j<96;j++)storage[j]=0xA5;
  for(j=0;j<31;j++)values[j]=i*1664525u+j*0x1234F1u+1013904223u;
  values[27]=(i&1)?0x80000000u:0;values[28]=(i&2)?0x87654321u:0;
  null1=(i&15)==15;null2=(i&4)!=0;count1=count2=0;invoke(values);
  if(count1!=1||first[0]!=(values[27]?103u:18u)||first[1]!=values[30]||first[2]!=52||first[3]||first[4]!=(values[29]&255)||first[5]!=1)return 10;
  if(null1){if(count2)return 13;for(j=0;j<96;j++)if(storage[j]!=0xA5)return 14;continue;}
''' + '\n'.join(checks) + '''
  if(record[37])return 15;
  if(values[28]){
   if(count2!=1||second[0]!=0xFFFFFFFFu||second[1]||second[2]!=values[28]||second[3]!=20||second[4]!=20||second[5]!=20||second[6]||second[7]!=(u32)(record+14)||second[8]!=(u32)(record+20))return 16;
   if(record[43]!=0x6D||*(u32*)(record+48)!=(null2?0:(u32)secondary))return 17;
  }else{if(count2||*(u32*)(record+48)||record[43]!=(u8)values[18])return 18;}
  for(j=0;j<16;j++)if(storage[j]!=0xA5||storage[68+j]!=0xA5)return 19;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        for name, body, profile, ok in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + n, b, '-O2', False) for n, b in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(fixture_c.replace(source.SELECTED, body))
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-ffreestanding',
                '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter', str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], capture_output=True, timeout=30)
            self.assertEqual(result.returncode == 0, ok, (name, result.returncode))
        self.receipt('native', actual_selected_C=True, cases_per_O2_O0=4096,
            six_effective_negatives=True, native32_not_guest_or_alias_acceptance=True)

    def test_06_independent_original_assembly_and_three_call_rebases(self):
        raw, fs, rel = parse_object(self.obj)
        text, missing = emit_function(raw, fs[source.FUNCTION], rel, source.FUNCTION,
            {'func_15167A68': source.ALLOCATOR, 'func_150448D0': source.SECONDARY})
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
                    '--defsym=func_15167A68=0x%X' % (source.ALLOCATOR - delta),
                    '--defsym=func_150448D0=0x%X' % (source.SECONDARY + delta * 2),
                    '-o', str(elf), str(self.out / (label + '-reloc.o'))], capture_output=True, check=True)
                outputs.append(sections(elf)['.text'][1][:400])
            self.assertEqual(outputs[0], outputs[1])
            args = [(0x87654321 + i * 65539) & 0xFFFFFFFF for i in range(31)]
            model = SmallFactoryOracle(list(struct.unpack('>100I', outputs[0])), args,
                entry=source.ENTRY + delta, allocator=source.ALLOCATOR - delta, secondary=source.SECONDARY + delta * 2).run()
            expected = reference(fixture(args), args, RECORD)[1]
            expected = [(source.ALLOCATOR - delta if c[0] == source.ALLOCATOR else source.SECONDARY + delta * 2, *c[1:]) for c in expected]
            self.assertEqual(model.calls, expected)
        self.receipt('rebases', independent_original_text_and_two_call_target_pairs=3, direct_C=True)

    def test_07_actual_allocator_and_position_scale_helpers(self):
        before = (self.out / 'before-elf').read_bytes()
        connected = {}
        for entry, offset, count in ((source.ALLOCATOR, 0x194F18, 28), (source.SECONDARY, 0x71D80, 37)):
            words = list(struct.unpack_from('>%dI' % count, before, elf_slot_offset(before, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, offset)))
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        for i in range(128):
            args = [(i * 1664525 + j * 0x1020304 + 1013904223) & 0xFFFFFFFF for j in range(31)]
            args[27], args[28] = i & 1, 0 if i % 3 == 0 else 0x87654321
            result, binding = (0 if i % 8 == 0 else RECORD), (0 if i % 4 == 0 else BINDING)
            model = SmallFactoryOracle(self.words, args, result, binding, connected=connected).run()
            kind = 103 if args[27] else 18
            self.assertEqual(model.calls[0], (source.ALLOCATOR, kind, args[30], 52, 0, args[29] & 255, 1))
            self.assertEqual(model.calls[1], (HEAP, 52, 1, 0, 0, 1))
            if not result:
                self.assertEqual(len(model.calls), 2)
                continue
            self.assertEqual(model.calls[2], (REGISTER, RECORD, kind))
            if args[28]:
                self.assertEqual(model.calls[3], (source.SECONDARY, 0xFFFFFFFF, 0, args[28], 20, 20, 20, 0, RECORD + 14, RECORD + 20))
                self.assertEqual(model.calls[4], (BUILDER, 32, 1, 0xFFFFFFFF, 0, args[28], 0, 0, 0))
                self.assertEqual(len(model.calls), 5)
                self.assertEqual(read(model.memory, RECORD + 48), binding)
                if binding:
                    for offset in (16, 18, 20):
                        self.assertEqual(read(model.memory, BINDING + offset, 2), 20)
                    self.assertEqual(read(model.memory, BINDING + 22, 1), 0)
                    self.assertEqual(read(model.memory, BINDING + 24), RECORD + 14)
                    self.assertEqual(read(model.memory, BINDING + 28), RECORD + 20)
            else:
                self.assertEqual(len(model.calls), 3)
                self.assertEqual(read(model.memory, RECORD + 48), 0)
            self.assertEqual(model.memory[RECORD], kind)
            self.assertEqual(model.memory[RECORD + 1], args[30] & 255)
            self.assertEqual(model.memory[RECORD + 12], args[29] & 255)
        self.receipt('chain', actual_factory_allocator_secondary_cases=128, actual_helper_words=[28, 37],
            lower_heap_registration_and_record_builder_are_opaque=True, no_gameplay_claim=True)


if __name__ == '__main__':
    unittest.main()
