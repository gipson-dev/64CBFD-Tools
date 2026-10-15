"""Live callback state, word wrap, release ordering, prefixes, native C and real cleanup."""
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_packed_record_updater as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import MaskOracle, AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_small_record_factory import SmallFactoryOracle
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle

RECORD, BINDING, OTHER = 0x20000, 0x22000, 0x24000
UNLINK, DEFAULT, DESTRUCTOR, TYPE_TABLE = 0x151696DC, 0x15169804, 0x15301000, 0x8008B4D0
TARGETS = (0x1516E8CC, 0x1516ECAC, 0x1516F024, 0x1516F9C4, 0x1516FBCC,
    0x1516FD50, 0x151707E0, 0x1516A648, 0x150BF0F4)
SYMBOLS = {'table': source.TABLE, 'delta': source.DELTA, 'remove': source.REMOVE}


def short(value):
    return (value & 65535) - (65536 if value & 32768 else 0)


def fixture(counter=7, delta=1, selector=0, y=-12345, fraction=255, velocity=-2345,
        binding=BINDING, record=RECORD, phase=0, symbols=None):
    symbols = symbols or SYMBOLS
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-512, 512)}
    for base in (record, BINDING, OTHER):
        memory.update({base + i: (i * 13 + 0xC5) & 255 for i in range(-16, 96)})
    for i in range(256):
        put(memory, symbols['table'] + i * 4, TARGETS[i % 9])
    put(memory, symbols['delta'], delta)
    for offset, value, size in ((0, 18, 1), (16, y, 2), (24, velocity, 2),
            (35, selector, 1), (36, counter, 1), (37, fraction, 1), (48, binding, 4)):
        put(memory, record + offset, value, size)
    for kind in (0, 1, 2, 18, 103):
        put(memory, TYPE_TABLE + kind * 52, DESTRUCTOR)
    return memory


def callback_effects(memory, record, mode, symbols):
    if mode == 1:
        for address, value, n in ((record + 16, -1234, 2), (record + 24, -321, 2),
                (record + 37, 0xA5, 1), (record + 48, OTHER, 4), (symbols['delta'], 0x87654321, 4)):
            put(memory, address, value, n)
    elif mode == 2:
        put(memory, symbols['delta'], 0x80000000)
        put(memory, record + 48, 0)
        put(memory, record + 35, 255, 1)
    elif mode == 3:
        put(memory, record + 48, record + 12)
        put(memory, symbols['delta'], 0x7FFFFFFF)
    elif mode == 4:
        index = read(memory, record + 35, 1)
        put(memory, symbols['table'] + index * 4, DESTRUCTOR)
        put(memory, record + 36, 0, 1)


def reference(memory, result=0, mode=0, record=RECORD, phase=0, symbols=None):
    symbols, memory = symbols or SYMBOLS, dict(memory)
    incoming, calls = STACK + phase, []
    put(memory, incoming - 4, 0xDEAD0000)
    counter = read(memory, record + 36, 1)
    if counter:
        difference = (counter - read(memory, symbols['delta'])) & 0xFFFFFFFF
        put(memory, record + 36, 0 if difference & 0x80000000 else difference, 1)
    put(memory, incoming, record)
    target = read(memory, symbols['table'] + read(memory, record + 35, 1) * 4)
    calls.append((target, record))
    callback_effects(memory, record, mode, symbols)
    for i in range(4):
        put(memory, incoming - 24 + i * 4, 0xB5000000 + i)
    if result & 0xFFFFFFFF == 1:
        binding = read(memory, record + 48)
        if binding:
            put(memory, binding + 4, 0, 2)
        calls.append((symbols['remove'], record))
        put(memory, record + 47, 0x6D, 1)
        for i in range(4):
            put(memory, incoming - 24 + i * 4, 0xC5000000 + i)
    else:
        delta = read(memory, symbols['delta'])
        velocity, position = short(read(memory, record + 24, 2)), short(read(memory, record + 16, 2))
        value = ((position * 256 + read(memory, record + 37, 1)) + velocity * delta) & 0xFFFFFFFF
        put(memory, record + 16, signed(value) >> 8, 2)
        put(memory, record + 37, value, 1)
    return memory, calls


class UpdaterOracle(MaskOracle):
    def __init__(self, words, memory, result=0, mode=0, record=RECORD, phase=0,
            fault=None, symbols=None, entry=source.ENTRY, connected=None, release_type=0):
        super().__init__(words, memory, phase=phase, mode=mode, fault=fault, entry=entry,
            arguments=(record,), connected=connected)
        self.result, self.record, self.symbols = result & 0xFFFFFFFF, record, symbols or SYMBOLS
        self.release_type = release_type
        self.unlink_lifetime = []

    def execute(self, word):
        if word >> 26 != 32:
            return super().execute(word)
        self.dispatched_word, self.own_instruction = word, True
        try:
            CopyOracle.execute(self, word)
        finally:
            self.own_instruction = False

    def record_call(self, target):
        self.calls.append((target, *self.arguments(1)))
        self.events.append(('CALL', target, self.arguments(1)))

    def hook(self, target):
        if target == self.symbols['remove']:
            self.put(self.record + 47, 0x6D, 1)
        elif target == UNLINK:
            binding = self.peek(self.record + 48, 4)
            self.unlink_lifetime.append(None if not binding else self.peek(binding + 4, 2))
            self.put(self.record, self.release_type, 1)
        elif target in (DEFAULT, DESTRUCTOR):
            self.put(self.record + 47, 0x6D, 1)
        else:
            callback_effects(self.memory, self.record, self.mode, self.symbols)
        for i in range(4):
            self.put(self.r[29] + i * 4,
                (0xC5000000 if target == self.symbols['remove'] else 0xB5000000) + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = self.result if target not in (self.symbols['remove'], UNLINK, DEFAULT, DESTRUCTOR) else 0xC5000002


def state(model):
    return (model.memory, model.r, model.f, model.events, model.calls, model.accesses)


def controls():
    return {
        'truthy-callback': source.SELECTED.replace('](record) == 1', '](record) != 0'),
        'signed-counter': source.SELECTED.replace('s32 value = record[0x24]', 's32 value = (s8)record[0x24]'),
        'cached-delta': source.SELECTED.replace('    s32 value =', '    s32 cachedDelta = D_800BE9E4;\n    s32 value =').replace(
            '*(s16 *)(record + 0x18) * (u32)D_800BE9E4', '*(s16 *)(record + 0x18) * (u32)cachedDelta'),
        'stale-binding': source.SELECTED.replace('    u8 *binding;', '    u8 *binding = *(u8 **)(record + 0x30);').replace(
            '        binding = *(u8 **)(record + 0x30);\n', ''),
        'word-clear': source.SELECTED.replace('*(s16 *)(binding + 4)', '*(s32 *)(binding + 4)'),
        'lost-fraction': source.SELECTED.replace('record[0x25] = fixed;', 'record[0x25] = 0;'),
    }


class PackedRecordUpdaterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>48I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_exact_slot_closed_register_change_and_unchanged_owner(self):
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
        for i in range(48):
            bad = bytearray(raw)
            bad[i * 4] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(bad), source.RELOCATIONS)
        for at in source.RELOCATIONS:
            bad = dict(source.RELOCATIONS)
            bad.pop(at)
            with self.assertRaises(ValueError):
                source.normalize(raw, bad)
        first, second, third = source.GUARDS
        a, b = first[1:]
        self.assertEqual((a >> 11 & 31, b >> 11 & 31), (3, 14))
        self.assertEqual((a >> 21 & 31, a >> 16 & 31), (b >> 16 & 31, b >> 21 & 31))
        self.assertEqual(second[2], (second[1] & ~(31 << 16)) | 14 << 16)
        self.assertEqual(third[2], (third[1] & ~(31 << 16)) | 14 << 16)
        self.receipt('owner', words=48, raw_differences=3, guarded_differences=0, guards=3,
            unchanged_neighbors=29, pools_and_relative_relocations_fixed=True,
            all_48_word_flips_and_seven_missing_relocations_rejected=True,
            only_V1_to_T6_final_lifetime_and_commutative_addu=True)

    def test_02_word_wrap_callbacks_live_state_aliases_and_raw_semantics(self):
        count = 0
        deltas = (0, 1, 255, 256, 0xFFFFFFFF, 0xFFFF0000, 0x80000000, 0x7FFFFFFF, 0x87654321)
        for i in range(256):
            result = (0, 1, 2, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF)[i % 6]
            for phase in (0, 8):
                for record in (RECORD, STACK + phase + 32, source.DELTA - 16):
                    mode = i % 5
                    memory = fixture(i, deltas[i % 9], i, short(i * 65539), i ^ 255, short(i * 317),
                        (0, BINDING, record + 12)[i % 3], record, phase)
                    models = [UpdaterOracle(w, memory, result, mode, record, phase).run()
                        for w in (self.words, self.truth, self.raw)]
                    self.assertEqual(state(models[0]), state(models[1]))
                    self.assertEqual((models[0].memory, models[0].calls), reference(memory, result, mode, record, phase))
                    self.assertEqual((models[2].memory, models[2].events, models[2].calls),
                        (models[0].memory, models[0].events, models[0].calls))
                    count += 1
        memory = fixture(0)
        model = UpdaterOracle(self.words, memory, 1).run()
        self.assertFalse(any(e[0] == 'R' and e[1] == source.DELTA for e in model.events))
        self.receipt('semantics', cases=count, all_byte_counters_and_selectors=True,
            arbitrary_wrapping_signed_word_deltas=True, post_callback_fields_binding_and_delta_live=True,
            record_stack_and_global_aliases=True, raw_and_guarded_access_memory_call_traces_equal=True,
            zero_counter_remove_path_never_reads_delta=True, fixture_table_256_backed_not_runtime_validity=True)

    def test_03_all_fired_guest_access_fault_prefixes(self):
        count = 0
        for result in (0, 1, 2):
            for phase in (0, 8):
                for counter in (0, 255):
                    memory = fixture(counter, 0x80000000, phase=phase)
                    whole = UpdaterOracle(self.words, memory, result, 1, phase=phase).run()
                    for fault in range(whole.accesses):
                        pair = [UpdaterOracle(w, memory, result, 1, phase=phase, fault=fault) for w in (self.words, self.truth)]
                        for model in pair:
                            with self.assertRaises(AccessFault):
                                model.run()
                        self.assertEqual(state(pair[0]), state(pair[1]))
                        count += 1
        self.receipt('prefixes', paired_fired_guest_access_faults=count,
            only_emitted_guest_order_not_portable_C_or_hardware_acceptance=True)

    def test_04_six_effective_compiled_semantic_controls_without_matching_guards(self):
        for name, body in controls().items():
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            failures = 0
            for result in (0, 1, 2):
                for mode in (0, 1):
                    memory = fixture(255, 1)
                    model = UpdaterOracle(words, memory, result, mode).run()
                    failures += (model.memory, model.calls) != reference(memory, result, mode)
            self.assertGreater(failures, 0, name)
        self.receipt('controls', six_effective_compiled_negatives=True, mutants_receive_no_matching_guards=True)

    def test_05_actual_native32_C_all_counter_bytes_and_wrap_boundaries(self):
        fixture_c = '''typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned short u16;typedef int s32;typedef unsigned int u32;
typedef struct {u8 byte;} struct102;
#define NULL ((void*)0)
static u8 storage[96] __attribute__((aligned(16))),first[16],second[16];static u8 *record=storage+16;
static s32 D_800BE9E4;static u32 mode,expectedCounter,cbCount,removeCount,indexValue;static s32 returnValue;static int error;
static s32 callback(u8 *r,u32 id){cbCount++;if(r!=record||id!=indexValue%3||r[36]!=expectedCounter)error=1;
 if(mode==1){*(s16*)(r+16)=-1234;*(s16*)(r+24)=-321;r[37]=0xA5;*(u8**)(r+48)=second;D_800BE9E4=(s32)0x87654321u;}
 if(mode==2){D_800BE9E4=(s32)0x80000000u;*(u8**)(r+48)=NULL;r[35]=255;}
 if(mode==3){*(u8**)(r+48)=r+12;D_800BE9E4=0x7FFFFFFF;}return returnValue;}
static s32 cb0(u8*r){return callback(r,0);}static s32 cb1(u8*r){return callback(r,1);}static s32 cb2(u8*r){return callback(r,2);}
static s32 (*D_8008CBA0[256])(u8*);
static void func_1516972C(struct102 *r){u8 *p=(u8*)r,*b=*(u8**)(p+48);removeCount++;
 if(p!=record||(b&&*(u16*)(b+4)))error=1;p[47]=0x6D;}
''' + source.SELECTED + '''
static void (*volatile invoke)(u8*)=func_1516D678;
static int run(void){u32 i,j,counter,delta,difference,word;int y,velocity;u8 fraction,*binding;
 static const u32 deltas[]={0,1,255,256,0xFFFFFFFFu,0xFFFF0000u,0x80000000u,0x7FFFFFFFu,0x87654321u};
 static const s32 results[]={0,1,2,-1,(s32)0x80000000u,0x7FFFFFFF};
 if(sizeof(void*)!=4||sizeof(s32)!=4)return 10;
 for(j=0;j<256;j++)D_8008CBA0[j]=j%3==0?cb0:j%3==1?cb1:cb2;
 for(i=0;i<4096;i++){
  for(j=0;j<96;j++)storage[j]=0xA5;
  for(j=0;j<16;j++){first[j]=0x35;second[j]=0x57;}
  counter=i&255;indexValue=(i*17)&255;mode=(i/5)%4;delta=deltas[(i>>2)%9];returnValue=results[(i>>4)%6];
  y=(s16)(i*317u);velocity=(s16)(i*65539u);fraction=(u8)(i^255);binding=i%3==0?NULL:i%3==1?first:record+12;
  record[35]=(u8)indexValue;record[36]=(u8)counter;record[37]=fraction;*(s16*)(record+16)=(s16)y;*(s16*)(record+24)=(s16)velocity;*(u8**)(record+48)=binding;
  difference=counter-delta;expectedCounter=counter?((difference&0x80000000u)?0:difference&255):0;
  D_800BE9E4=(s32)delta;cbCount=removeCount=0;error=0;invoke(record);
  if(error||cbCount!=1)return 11;
  if(mode==1){y=-1234;velocity=-321;fraction=0xA5;binding=second;delta=0x87654321u;}
  if(mode==2){binding=NULL;delta=0x80000000u;}
  if(mode==3){binding=record+12;delta=0x7FFFFFFFu;}
  if(returnValue==1){if(removeCount!=1||record[47]!=0x6D)return 12;if(binding==record+12)y=0;
   if(*(s16*)(record+16)!=(s16)y||record[37]!=fraction)return 13;
   if(first[6]!=0x35||first[7]!=0x35||second[6]!=0x57||second[7]!=0x57||record[18]!=0xA5||record[19]!=0xA5)return 14;
  }else{if(removeCount)return 15;word=(u32)(y*256+(u32)fraction)+(u32)velocity*delta;
   if(*(s16*)(record+16)!=(s16)((s32)word>>8)||record[37]!=(u8)word)return 16;}
  for(j=0;j<16;j++)if(storage[j]!=0xA5||storage[80+j]!=0xA5)return 17;
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
            six_effective_compiled_negatives=True, no_signed_overflow_or_negative_left_shift_relaxation=True,
            host32_not_guest_stack_alias_or_hardware_acceptance=True)

    def test_06_original_assembly_and_three_independent_symbol_rebases(self):
        raw, fs, rel = parse_object(self.obj)
        f = fs[source.FUNCTION]
        normalized = source.normalize(raw[f['value']:f['value'] + f['size']], source.RELOCATIONS)
        data = bytearray(raw)
        struct.pack_into('>48I', data, f['value'], *normalized)
        anchors = {'D_800BE9E4': source.DELTA, 'D_8008CBA0': source.TABLE, 'func_1516972C': source.REMOVE}
        text, missing = emit_function(bytes(data), f, rel, source.FUNCTION, anchors)
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for label, body in dict(selected=text, original='glabel ' + source.FUNCTION + '\n' + original).items():
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], capture_output=True, check=True)
        for index, delta, table, step in ((0, 0, source.TABLE, source.DELTA),
                (1, 0x10000, 0x80207FFC, 0x80318004), (2, -0x10000, 0x80418004, 0x80507FFC)):
            values = dict(D_8008CBA0=table, D_800BE9E4=step, func_1516972C=source.REMOVE - delta)
            symbols = dict(table=table, delta=step, remove=values['func_1516972C'])
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + delta))
            outputs = []
            for label in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (label, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % pair for pair in values.items()], '-o', str(elf), str(self.out / (label + '-reloc.o'))], capture_output=True, check=True)
                outputs.append(sections(elf)['.text'][1][:192])
            self.assertEqual(outputs[0], outputs[1])
            memory = fixture(symbols=symbols)
            words = list(struct.unpack('>48I', outputs[0]))
            for result in (0, 1):
                model = UpdaterOracle(words, memory, result, symbols=symbols, entry=source.ENTRY + delta).run()
                self.assertEqual((model.memory, model.calls), reference(memory, result, symbols=symbols))
        self.receipt('rebases', independent_original_text_table_delta_remove_pairs=3,
            signed_low_carry_and_both_paths_checked=True, guarded_not_direct_C=True)

    def test_07_actual_constructor_then_updater_and_installed_cleanup(self):
        before = (self.out / 'before-elf').read_bytes()
        constructor_entry, allocator_entry, secondary_entry = 0x1516D4E8, 0x15167A68, 0x150448D0
        connected_create = {}
        constructor = None
        for entry, offset, count in ((constructor_entry, 0x19A998, 100), (allocator_entry, 0x194F18, 28),
                (secondary_entry, 0x71D80, 37), (source.REMOVE, 0x196BDC, 28)):
            words = list(struct.unpack_from('>%dI' % count, before, elf_slot_offset(before, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, offset)))
            if entry == constructor_entry:
                constructor = words
            elif entry != source.REMOVE:
                connected_create.update(zip(range(entry, entry + count * 4, 4), words))
            else:
                cleanup = dict(zip(range(entry, entry + count * 4, 4), words))
        self.assertEqual(tuple(struct.unpack_from('>9I', self.rom, 0x231660)), TARGETS)
        for i in range(128):
            args = [0] * 31
            args[1], args[12], args[25], args[26] = i * 317, i % 9, i & 255, i * 29
            args[27], args[28] = i & 1, i % 3 != 0
            made = SmallFactoryOracle(constructor, args, RECORD, BINDING, connected=connected_create).run()
            memory = fixture(delta=(i % 7) - 3)
            for base, length in ((RECORD, 64), (BINDING, 32)):
                for j in range(length):
                    memory[base + j] = made.memory[base + j]
            release_type = i % 3
            pointer = DESTRUCTOR if i & 4 else 0
            put(memory, TYPE_TABLE + release_type * 52, pointer)
            result = 1 if i & 1 else 0
            model = UpdaterOracle(self.words, memory, result, connected=cleanup, release_type=release_type).run()
            self.assertEqual(model.calls[0], (TARGETS[i % 9], RECORD))
            if result:
                expected = [(TARGETS[i % 9], RECORD), (source.REMOVE, RECORD), (UNLINK, RECORD)]
                if release_type >= 2:
                    expected.append((DESTRUCTOR if pointer else DEFAULT, RECORD))
                self.assertEqual(model.calls, expected)
                self.assertEqual(model.unlink_lifetime, [None if not args[28] else 0])
            else:
                expected = reference(memory, result)
                self.assertEqual(model.calls, expected[1])
                for base, length in ((RECORD, 64), (BINDING, 32)):
                    for j in range(length):
                        self.assertEqual(model.memory[base + j], expected[0][base + j])
        self.receipt('chain', actual_constructor_allocator_binding_updater_cleanup_cases=128,
            actual_words=[100, 28, 37, 48, 28], actual_nine_entry_dispatch_table=True,
            only_lower_heap_registration_builder_callback_unlink_and_destructors_are_opaque=True,
            unlink_observes_halfword_lifetime_clear_before_cleanup=True, no_gameplay_claim=True)


if __name__ == '__main__':
    unittest.main()
