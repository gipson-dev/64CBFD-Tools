"""Full codec refill, dynamic callback ABI, helper contracts and closed image."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_codec_input_refill_candidates as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function, nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_record_constructor_match as image
from tools.tests.test_game_one_shot_timer_match import canonical_symbols
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import signed
from tools.check_game_data_layout import audit_layout
from tools.tests import codec_refill_checkpoint as checkpoint
from tools.tests import codec_frame_dispatch_checkpoint

ENTRY, DECODER, READ, READ2, COPY, ZERO = 0x151F7F60, 0x21000, 0x18001000, 0x18002000, 0x10023A10, 0x100226F0


def fixture(position, request, clock=0xFFFFFFF8):
    memory = {machine.STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    memory.update({DECODER + i: (i * 13 + 0xA5) & 255 for i in range(-16, 0x3FA0)})
    for offset, value in ((0, 0x12345678), (4, READ), (0x18, clock),
            (0x201C, position), (0x2020, 0x12345678), (0x3F88, request)):
        put(memory, DECODER + offset, value)
    return memory


def helper_effects(memory, role, mode):
    if role == COPY and mode == 3:
        put(memory, DECODER + 0x201C, read(memory, DECODER + 0x201C) + 2)
        put(memory, DECODER + 0x2020, read(memory, DECODER + 0x2020) + 16)
    if role == COPY and mode == 5:
        put(memory, DECODER, 0x87654321)
        put(memory, DECODER + 4, READ2)
    if role in (READ, READ2) and mode == 1:
        put(memory, DECODER + 0x3F88, 0)
    if role in (READ, READ2) and mode == 2:
        for offset, value in ((0x3F88, 4), (0x201C, 7), (0x18, 0xFFFFFFF8)):
            put(memory, DECODER + offset, value)
    if role == ZERO and mode == 4:
        for offset, value in ((0x3F88, 3), (0x201C, 9), (0x18, 0xFFFFFFFF)):
            put(memory, DECODER + offset, value)


def reference(memory, result, mode):
    output, calls = dict(memory), []
    position = signed(read(output, DECODER + 0x201C))
    request = signed(read(output, DECODER + 0x3F88))
    if signed((position + request) & 0xFFFFFFFF) >= 0x1FFC:
        calls.append((COPY, (DECODER + 0x101C, DECODER + 0x1C, 0x1000)))
        saved = [output[DECODER + 0x101C + i] for i in range(0x1000)]
        for i, byte in enumerate(saved):
            output[DECODER + 0x1C + i] = byte
        helper_effects(output, COPY, mode)
        put(output, DECODER + 0x201C, read(output, DECODER + 0x201C) - 0x1000)
        put(output, DECODER + 0x2020, read(output, DECODER + 0x2020) - 0x8000)
    callback, opaque = read(output, DECODER + 4), read(output, DECODER)
    address = DECODER + signed(read(output, DECODER + 0x201C)) + 0x1C
    request = signed(read(output, DECODER + 0x3F88))
    calls.append((callback, (opaque, address, request & 0xFFFFFFFF, 0xFFFFFFFF)))
    for i in range(max(0, result)):
        output[address + i] = (i * 7 + 0x51) & 255
    helper_effects(output, callback, mode)
    request = signed(read(output, DECODER + 0x3F88))
    if result < request:
        address, count = DECODER + 0x1C + result, request - result
        calls.append((ZERO, (address, count)))
        for i in range(count):
            output[address + i] = 0
        helper_effects(output, ZERO, mode)
    request = read(output, DECODER + 0x3F88)
    put(output, DECODER + 0x18, read(output, DECODER + 0x18) + request)
    put(output, DECODER + 0x201C, read(output, DECODER + 0x201C) + request)
    returned = (read(output, DECODER + 0x201C) - read(output, DECODER + 0x3F88)) & 0xFFFFFFFF
    return output, calls, returned


class RefillOracle(machine.BurstOracle):
    def __init__(self, words, memory, result=0, mode=0, phase=0, fault=None):
        super().__init__(words, memory, actor=DECODER, phase=phase, mode=mode,
            entry=ENTRY, arguments=(DECODER,), symbols={'unused': 0})
        self.result, self.current_pc, self.delay_of, self.root_fault = result, None, None, fault
        self.code = faults.TrackedCode(self.code, self)

    def access(self):
        if self.own_instruction and ENTRY <= self.current_pc < ENTRY + 296:
            if self.accesses == self.root_fault:
                raise faults.AccessBoundary
            self.accesses += 1

    def record_call(self, target):
        assert target in (COPY, ZERO, READ, READ2), hex(target)
        args = tuple(self.arguments(4 if target in (READ, READ2) else 3 if target == COPY else 2))
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        args = self.calls[-1][1]
        if target == COPY:
            pointer, destination, count = args
            payload = [self.get(pointer + i, 1) for i in range(count)]
            for i, byte in enumerate(payload):
                self.put(destination + i, byte, 1)
        elif target == ZERO:
            destination, count = args
            for i in range(count):
                self.put(destination + i, 0, 1)
        else:
            for i in range(max(0, self.result)):
                self.put(args[1] + i, (i * 7 + 0x51) & 255, 1)
        helper_effects(self.memory, target, self.mode)
        # Ordinary o32 helpers may destroy argument registers and argument homes.
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = self.result & 0xFFFFFFFF if target in (READ, READ2) else 0x11223344


class CodecInputRefillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.out.mkdir(exist_ok=True)
        source.freeze(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>74I', cls.rom, 0x225410))
        cls.original = cls.root / 'conker/asm/nonmatchings/game_221290/func_151F7F60.s'

    def assemble(self, text, label):
        path = self.out / (label + '.s')
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)],
            capture_output=True, text=True, check=True)
        return obj

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_complete_profiles_neighbors_pools_and_both_padders(self):
        before = (self.out / 'before-owner').read_text()
        objects = {}
        counts = {}
        for label, flags in (('O2', ('-O2', '-g3')), ('g', ('-g',))):
            old, w0 = build.compile_owner(self.root, self.out, before, 'owner-before-' + label, flags)
            new, w1 = build.compile_owner(self.root, self.out, source.recover(before), 'owner-after-' + label, flags)
            t0, f0, r0 = parse_object(old)
            t1, f1, r1 = parse_object(new)
            self.assertEqual(set(f0), set(f1))
            for name in set(f0) - {source.FUNCTION}:
                a, b = f0[name], f1[name]
                self.assertEqual(a['size'], b['size'], name)
                self.assertEqual(t0[a['value']:a['value'] + a['size']], t1[b['value']:b['value'] + b['size']], name)
                relative = lambda table, info: {at - info['value']: value for at, value in table.items()
                    if info['value'] <= at < info['value'] + info['size']}
                self.assertEqual(relative(r0, a), relative(r1, b), name)
            self.assertEqual(normalized_pools(old), normalized_pools(new), label)
            self.assertLessEqual(w1.count('cfe: Warning'), w0.count('cfe: Warning'))
            objects[label] = new
            counts[label] = len(f0) - 1
        raw, functions = build.link_owner(self.root, self.out, objects['g'], source.OWNER)
        info = functions[source.FUNCTION]
        self.assertEqual(info['size'], 296)
        words = list(struct.unpack('>74I', raw[info['value']:info['value'] + 296]))
        self.assertEqual([i for i, (a, b) in enumerate(zip(words, self.retail)) if a != b], [35])
        self.assertEqual((words[35], self.retail[35]), (0x018A2821, 0x014C2821))
        guards = self.out / 'guards.csv'
        guards.write_bytes((self.out / 'before-guards').read_bytes() + source.GUARD_ROWS.encode())
        makefile = source.recover_makefile((self.out / 'before-makefile').read_text())
        start = makefile.index('CODEC_RETAIL_G_FUNCTIONS :=')
        selected = makefile[start:makefile.index('\n$(BUILD_DIR)', start)].split(':=', 1)[1].replace('\\', '').split()
        self.assertEqual(len(selected), 8)
        self.assertIn(source.FUNCTION, selected)
        overrides = {name: objects['g'] for name in selected}
        primary = pad_c_object.emit_padded_assembly(objects['O2'], self.root / 'conker/retail_layout.us.txt', source.OWNER,
            function_objects=overrides, word_patches_path=guards)
        primary_obj = self.assemble(primary, 'primary-padded')
        text, f, r = parse_object(objects['g'])
        extracted, unresolved = emit_function(text, f[source.FUNCTION], r, source.FUNCTION, nm_anchors(self.root / 'conker/build/conker.us.elf'))
        self.assertFalse(unresolved)
        compact = self.assemble(extracted, 'selected-compact')
        selected_guards = self.out / 'selected-guards.csv'
        selected_guards.write_text(guards.read_text().splitlines()[0] + '\n' + source.GUARD_ROWS)
        generated = emit_padded_assembly(compact, self.original, filename=source.OWNER, word_patches_path=selected_guards)
        generated_obj = self.assemble(generated, 'generated-padded')
        for artifact in (primary_obj, generated_obj):
            data, funcs = build.link_owner(self.root, self.out, artifact, source.OWNER)
            at = funcs[source.FUNCTION]['value']
            self.assertEqual(data[at:at + 296], self.rom[0x225410:0x225538])
        self.receipt('owners', profiles=counts, raw_words=74, raw_different_words=1,
            final_exact_words=74, guards=1, mixed_production_profile=True, both_padders=True,
            normalized_pools_and_neighbor_relocations_fixed=True)

    def qualified_words(self):
        text, functions = build.link_owner(self.root, self.out, self.out / 'generated-padded.o', source.OWNER)
        at = functions[source.FUNCTION]['value']
        return list(struct.unpack('>74I', text[at:at + 296]))

    def test_02_original_and_rebased_independent_links(self):
        original = self.assemble(self.original.read_text() + '\n.type ' + source.FUNCTION + ',@function\n.size ' + source.FUNCTION + ',296\n', 'original-retail')
        anchors = nm_anchors(self.root / 'conker/build/conker.us.elf')
        anchors.update(build.load_symbol_addrs(str(self.root / 'conker/symbol_addrs.us.txt')))
        for phase, base in enumerate((ENTRY, 0x16108000)):
            spans = []
            for index, artifact in enumerate((original, self.out / 'primary-padded.o', self.out / 'generated-padded.o')):
                text, f, r = parse_object(artifact)
                asm, unresolved = emit_function(text, f[source.FUNCTION], r, source.FUNCTION, anchors)
                self.assertFalse(unresolved)
                single = self.assemble(asm, 'rebase-input-%d-%d' % (phase, index))
                symbols = {symbol for at, entries in r.items() if f[source.FUNCTION]['value'] <= at < f[source.FUNCTION]['value'] + 296 for _, symbol in entries}
                values = {symbol: 0x17008000 + i * 4 for i, symbol in enumerate(sorted(symbols))} if phase else {symbol: anchors[symbol] for symbol in symbols}
                script = single.with_suffix('.ld')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % base)
                elf = single.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in values.items()], '-o', str(elf), str(single)], capture_output=True, text=True, check=True)
                spans.append(sections(elf)['.text'][1][:296])
            self.assertEqual(spans[0], spans[1])
            self.assertEqual(spans[0], spans[2])

    def test_03_mips_copy_short_read_reload_and_call_abi(self):
        words, cases, seen = self.qualified_words(), 0, set()
        for position, request, choice, mode, phase in itertools.product((0, 1, 4092, 4096, 7928, 8187, 8188),
                (0, 1, 4, 256, 4096), range(4), range(6), (0, 8)):
            result = (-1, 0, max(0, request - 1), request)[choice]
            memory = fixture(position, request)
            expected, calls, returned = reference(memory, result, mode)
            models = [RefillOracle(body, memory, result, mode, phase).run() for body in (self.retail, words)]
            for model in models:
                self.assertEqual(model.calls, calls)
                self.assertEqual(model.r[2], returned)
                self.assertEqual({a: v for a, v in model.memory.items() if DECODER - 16 <= a < DECODER + 0x3FA0},
                    {a: v for a, v in expected.items() if DECODER - 16 <= a < DECODER + 0x3FA0})
            self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
            seen.update(models[0].visits)
            cases += 1
        self.assertEqual(seen, set(range(ENTRY, ENTRY + 296, 4)) - {ENTRY + 68 * 4, ENTRY + 69 * 4})
        self.receipt('mips', cases=cases, reached_words=len(seen), unreachable_words=[68, 69],
            compaction_and_short_read=True, dynamic_callback_and_field_updates=True,
            original_zero_fill_address_retained=True, all_call_arguments_and_saved_registers=True,
            complete_instruction_state_equal=True, helpers_are_bounded_contract_hooks=True)

    def test_04_all_fired_root_fault_prefixes(self):
        words, cuts = self.qualified_words(), 0
        for position, request, result, mode in ((0, 256, 0, 0), (8187, 4, -1, 0),
                (4092, 4096, 4, 2), (8188, 256, 1, 5), (0, 4, 0, 4)):
            memory = fixture(position, request)
            completed = RefillOracle(self.retail, memory, result, mode).run()
            for cut in range(completed.accesses):
                models = [RefillOracle(body, memory, result, mode, fault=cut) for body in (self.retail, words)]
                for model in models:
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
                self.assertEqual((models[0].current_pc, models[0].delay_of), (models[1].current_pc, models[1].delay_of))
                cuts += 1
        self.receipt('faults', fired_prefixes=cuts, actual_root_memory_instructions=True,
            helpers_are_atomic_bounded_contracts=True, no_C_fault_semantics_claim=True)

    def test_05_effective_compiled_argument_and_guard_controls(self):
        before = (self.out / 'before-owner').read_text()
        body = source.BODY.replace('        -1);', '        0);')
        self.assertNotEqual(body, source.BODY)
        obj, _ = build.compile_owner(self.root, self.out, source.recover(before, body), 'negative-read-mode', ('-g',))
        raw, functions = build.link_owner(self.root, self.out, obj, source.OWNER)
        info = functions[source.FUNCTION]
        negative = list(struct.unpack('>74I', raw[info['value']:info['value'] + 296]))
        model = RefillOracle(negative, fixture(0, 4), 4).run()
        self.assertEqual(model.calls[0][1][-1], 0)
        self.assertNotEqual(negative, self.retail)
        text, f, r = parse_object(self.out / 'owner-after-g.o')
        for old, new in (('0x018A2821,0x014C2821', '0x018A2820,0x014C2821'),
                (',-,-,Normalize', ',R_MIPS_LO16:bcopy,-,Normalize')):
            bad = self.out / 'negative-guards.csv'
            rows = source.GUARD_ROWS.replace(old, new)
            self.assertNotEqual(rows, source.GUARD_ROWS)
            bad.write_text((self.out / 'selected-guards.csv').read_text().splitlines()[0] + '\n' + rows)
            with self.assertRaises(ValueError):
                emit_padded_assembly(self.out / 'selected-compact.o', self.original, filename=source.OWNER, word_patches_path=bad)

    def test_06_native32_full_window_callbacks_and_zero_fill_controls(self):
        native = r'''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef s32 (*func_151F6FD0_ReadFunc)(s32,void *,s32,s32);
void bcopy(const void *,void *,s32);void bzero(void *,s32);
static u8 storage[0x3FC0],expected[0x3FC0];static u8 *decoder;
static s32 outcome,mode,error,n,en;static u32 log[3][5],wanted[3][5];
static u32 get(u8 *p,int offset){return *(u32 *)(p+offset);}
static void set(u8 *p,int offset,u32 value){*(u32 *)(p+offset)=value;}
static s32 readerA(s32,void *,s32,s32);static s32 readerB(s32,void *,s32,s32);
static void effects(u8 *p,int role){
 if(role==1&&mode==3){set(p,0x201C,get(p,0x201C)+2);set(p,0x2020,get(p,0x2020)+16);}
 if(role==1&&mode==5){set(p,0,0x87654321);set(p,4,(u32)readerB);}
 if(role>=3&&mode==1)set(p,0x3F88,0);
 if(role>=3&&mode==2){set(p,0x3F88,4);set(p,0x201C,7);set(p,0x18,0xFFFFFFF8);}
 if(role==2&&mode==4){set(p,0x3F88,3);set(p,0x201C,9);set(p,0x18,0xFFFFFFFF);}}
static void event(u32 role,u32 a,u32 b,u32 c,u32 d){
 u32 row[5]={role,a,b,c,d};int i;if(n>=3){error=1;return;}
 for(i=0;i<5;i++){log[n][i]=row[i];if(n>=en||wanted[n][i]!=row[i])error=1;}n++;}
void bcopy(const void *pointer,void *destination,s32 size){int i;
 event(1,(u32)((const u8 *)pointer-decoder),(u32)((u8 *)destination-decoder),(u32)size,0);
 for(i=0;i<size;i++)((u8 *)destination)[i]=((const u8 *)pointer)[i];effects(decoder,1);}
void bzero(void *destination,s32 size){int i;
 event(2,(u32)((u8 *)destination-decoder),(u32)size,0,0);
 for(i=0;i<size;i++)((u8 *)destination)[i]=0;effects(decoder,2);}
static s32 reading(s32 opaque,void *destination,s32 size,s32 command,int role){int i;
 event((u32)role,(u32)opaque,(u32)((u8 *)destination-decoder),(u32)size,(u32)command);
 for(i=0;i<outcome;i++)((u8 *)destination)[i]=(u8)(i*7+0x51);effects(decoder,role);return outcome;}
static s32 readerA(s32 a,void *b,s32 c,s32 d){return reading(a,b,c,d,3);}
static s32 readerB(s32 a,void *b,s32 c,s32 d){return reading(a,b,c,d,4);}
''' + source.BODY + r'''
static void want(u32 role,u32 a,u32 b,u32 c,u32 d){
 wanted[en][0]=role;wanted[en][1]=a;wanted[en][2]=b;wanted[en][3]=c;wanted[en][4]=d;en++;}
static u32 ref(u8 *p){s32 position,request;u32 address,i,count,reader;
 position=(s32)get(p,0x201C);request=(s32)get(p,0x3F88);
 if((s32)((u32)position+(u32)request)>=0x1FFC){
  want(1,0x101C,0x1C,0x1000,0);for(i=0;i<0x1000;i++)p[0x1C+i]=p[0x101C+i];
  effects(p,1);set(p,0x201C,get(p,0x201C)-0x1000);set(p,0x2020,get(p,0x2020)-0x8000);}
 reader=get(p,4)==(u32)readerB?4:3;address=0x1C+get(p,0x201C);request=(s32)get(p,0x3F88);
 want(reader,get(p,0),address,(u32)request,0xFFFFFFFF);
 for(i=0;i<(u32)(outcome>0?outcome:0);i++)p[address+i]=(u8)(i*7+0x51);effects(p,(int)reader);
 request=(s32)get(p,0x3F88);if(outcome<request){address=0x1C+(u32)outcome;count=(u32)request-(u32)outcome;
  want(2,address,count,0,0);for(i=0;i<count;i++)p[address+i]=0;effects(p,2);}
 set(p,0x18,get(p,0x18)+get(p,0x3F88));set(p,0x201C,get(p,0x201C)+get(p,0x3F88));
 return get(p,0x201C)-get(p,0x3F88);}
static int run(void){int positions[7]={0,1,4092,4096,7928,8187,8188},requests[5]={0,1,4,256,4096};
 int pi,ri,choice,phase,i;u8 *p;u32 expectedReturn,returned;
 if(sizeof(void *)!=4||sizeof(s32)!=4)return 80;
 for(pi=0;pi<7;pi++)for(ri=0;ri<5;ri++)for(choice=0;choice<4;choice++)for(mode=0;mode<6;mode++)for(phase=0;phase<2;phase++){
  decoder=storage+16+phase*4;p=expected+16+phase*4;
  for(i=0;i<(int)sizeof(storage);i++)storage[i]=(u8)(i*13+0xA5);
  set(decoder,0,0x12345678);set(decoder,4,(u32)readerA);set(decoder,0x18,0xFFFFFFF8);
  set(decoder,0x201C,(u32)positions[pi]);set(decoder,0x2020,0x12345678);set(decoder,0x3F88,(u32)requests[ri]);
  for(i=0;i<(int)sizeof(storage);i++)expected[i]=storage[i];
  outcome=choice==0?-1:choice==1?0:choice==2?(requests[ri]>0?requests[ri]-1:0):requests[ri];
  error=n=en=0;expectedReturn=ref(p);returned=(u32)func_151F7F60(decoder);
  if(error||n!=en||returned!=expectedReturn)return 1;
  for(i=0;i<(int)sizeof(storage);i++)if(storage[i]!=expected[i])return 2;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        zero = source.BODY.replace('bzero((char *)decoder + bytesRead + 0x1C,',
            'bzero((char *)decoder + bytesRead + *(s32 *)((char *)decoder + 0x201C) + 0x1C,')
        for label, profile, body, status in (('O2', '-O2', source.BODY, 0), ('O0', '-O0', source.BODY, 0),
                ('negative-command', '-O2', source.BODY.replace('        -1);', '        0);'), 1),
                ('negative-zero-address', '-O2', zero, 1)):
            path = self.out / ('native-' + label + '.c')
            path.write_text(native.replace(source.BODY, body))
            binary = path.with_suffix('')
            result = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing', '-fwrapv', '-fno-builtin',
                '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra',
                '-Werror', '-Wno-misleading-indentation', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([str(binary)], capture_output=True).returncode, status, label)
        self.receipt('native', cases_per_profile=1680, profiles=['O2', 'O0'], native32_required=True,
            all_context_and_window_bytes_compared=True, callback_copy_zero_calls_compared=True,
            negative_read_mode_and_zero_address_controls_fired=True, signed_arithmetic_wrap_profile=True,
            little_endian_native_field_access_not_guest_endian_evidence=True)

    def test_07_installed_source_profile_guards_progress_and_closed_image(self):
        source.freeze(self.root, self.out)
        for filename in ('conker/src/game_221290.c', 'conker/Makefile'):
            raw = (self.root / filename).read_bytes()
            self.assertEqual((self.root / filename).read_text(), raw.decode().replace('\r\n', '\n'))
        self.assertEqual(codec_frame_dispatch_checkpoint.previous_input((self.root / 'conker/src/game_221290.c').read_bytes(), 'conker/src/game_221290.c', self.root).decode(), source.recover((self.out / 'before-owner').read_text()))
        self.assertEqual(codec_frame_dispatch_checkpoint.previous_input((self.root / 'conker/Makefile').read_bytes(), 'conker/Makefile', self.root).decode(), source.recover_makefile((self.out / 'before-makefile').read_text()))
        self.assertEqual(codec_frame_dispatch_checkpoint.previous_input((self.root / 'conker/retail_word_patches.us.csv').read_bytes(), 'conker/retail_word_patches.us.csv', self.root),
            (self.out / 'before-guards').read_bytes() + source.GUARD_ROWS.encode())
        self.assertEqual(codec_frame_dispatch_checkpoint.previous_input((self.root / 'conker/progress.csv').read_bytes(), 'conker/progress.csv', self.root), (self.out / 'before-progress').read_bytes())
        before = (self.out / 'before-elf').read_bytes()
        current = codec_frame_dispatch_checkpoint.previous_input((self.root / 'conker/build/conker.us.elf').read_bytes(), 'conker/build/conker.us.elf', self.root)
        expected = bytearray(before)
        at = image.elf_slot_offset(before, ENTRY, 296)
        expected[at:at + 296] = self.rom[0x225410:0x225538]
        with patch.object(image.screen, 'ENTRY', ENTRY):
            size = image.elf_symbol_size_offset(before, source.FUNCTION)
        self.assertEqual(struct.unpack_from('>I', before, size)[0], 12)
        struct.pack_into('>I', expected, size, 296)
        self.assertEqual(current, bytes(expected), 'Only the refill slot and its symbol extent may change')
        symbols = canonical_symbols(before)
        old = next(row for row in symbols if row[0] == source.FUNCTION)
        symbols[old] -= 1
        symbols[(old[0], old[1], 296, *old[3:])] += 1
        self.assertEqual(+symbols, canonical_symbols(current))
        data = audit_layout(self.root / 'conker/build/conker.us.elf', self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('image', ELF_sha256=hashlib.sha256(current).hexdigest(),
            changed_slot_bytes=sum(a != b for a, b in zip(before[at:at + 296], expected[at:at + 296])),
            single_function_extent_change=True, every_other_ELF_byte_fixed=True, new_guards=1,
            progress_unchanged=True, only_one_new_g_profile_selection=True, protected_data=data)

    def test_08_effective_installed_and_immutable_input_controls(self):
        read_bytes, read_text = Path.read_bytes, Path.read_text
        for filename in ('conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv', 'conker/progress.csv'):
            path = self.root / filename
            bad = read_bytes(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p, value=bad: value if p == path else read_bytes(p)):
                with self.assertRaises(AssertionError):
                    self.test_07_installed_source_profile_guards_progress_and_closed_image()
        for filename in ('conker/src/game_221290.c', 'conker/Makefile'):
            path = self.root / filename
            bad = read_text(path) + '\n'
            with patch.object(Path, 'read_text', lambda p, *a, value=bad, **k: value if p == path else read_text(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_07_installed_source_profile_guards_progress_and_closed_image()
        path = self.out / 'before-owner'
        with patch.object(Path, 'read_bytes', lambda p: b'bad baseline' if p == path else read_bytes(p)):
            with self.assertRaisesRegex(ValueError, 'immutable refill input'):
                self.test_07_installed_source_profile_guards_progress_and_closed_image()

    def test_09_pinned_inverse_and_unrecognized_input_controls(self):
        self.test_07_installed_source_profile_guards_progress_and_closed_image()
        intermediate = self.out / 'after-owner'
        if intermediate.exists():
            self.assertEqual(hashlib.sha256(intermediate.read_bytes()).hexdigest(),
                '4ca8e22a4bc37b88e3c43aca4c06cd963666e68d6d571d1dfe1a1be99405577a')
        checkpoint.freeze_after(self.root)
        for path, key in checkpoint.PATHS.items():
            data = (self.root / path).read_bytes()
            self.assertEqual(checkpoint.previous_input(data, path, self.root), checkpoint.fixture(self.root, 'before', key))
            bad = data + b'\n'
            self.assertEqual(checkpoint.previous_input(bad, path, self.root), bad)


if __name__ == '__main__':
    unittest.main()
