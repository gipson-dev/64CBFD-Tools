"""Direct constructor words, public o32 ABI, bounded helpers and image closure."""
import hashlib
import csv
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_record_payload_constructor_candidates as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function, nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import signed
from tools.check_game_data_layout import audit_layout
from tools.tests import record_payload_constructor_checkpoint as checkpoint

CREATED, DESCRIPTOR, PAYLOAD, TABLE = 0x20000, 0x21000, 0x22000, 0x23000
ALLOC, COPY, VIEW, ATTR, RESOURCE, FOOTER = 0x15167A68, 0x10022EC0, 0x1513FFF4, 0x151400D0, 0x1515D480, 0x1515D440
LIMIT, DEFAULT = 0x80082FA0, 0x800A4AA0
OWNER_AFTER = '914f001c486928dec6b98dc840d66a3708d9e2c176f009fcc6eafdf5da268fb7'


def fixture(flags, table, resources, limit, alias, ordinal):
    memory = {machine.STACK + i: 0xA5 for i in range(-0x600, 0x180)}
    for base in (CREATED, DESCRIPTOR, PAYLOAD, TABLE, DEFAULT):
        memory.update({base + i: (i * 13 + ordinal + 0xA5) & 255 for i in range(-16, 0x180)})
    put(memory, DESCRIPTOR, flags)
    put(memory, LIMIT, limit)
    payload = (0, PAYLOAD, CREATED + 0xA4, CREATED + 0xA0, CREATED + 0xA8)[alias]
    args = (DESCRIPTOR, TABLE if table else 0, 0xABCDEF80, 0x876543FF,
        0xDEAD00F3, resources, 0x87654321, payload, 0x7FFFFFFF,
        0x112233C5, 0xFEDCBA98)
    return memory, args


def effects(memory, target, mode, resources=0):
    if target == ALLOC and mode == 1:
        put(memory, DESCRIPTOR + 6, 0xE7, 1)
    if target == ATTR and mode == 2:
        put(memory, LIMIT, 2)
    if target == VIEW:
        put(memory, CREATED + 0x40, 0x1234, 2)
    if target == ATTR:
        put(memory, CREATED + 0x42, 0x5678, 2)
    if target == RESOURCE and resources == 1:
        if mode == 1:
            put(memory, LIMIT, 0)
        if mode == 2:
            put(memory, LIMIT, 3)


def reference(memory, args, created, mode):
    result, calls = dict(memory), []
    descriptor, table, tag80, tag81, variant, count, value, payload, extra, channel, context = args
    category = 0x4A if read(result, descriptor) & 0x40000 else 0x1B
    calls.append((ALLOC, (category, context, (extra + 0xB0) & 0xFFFFFFFF, 1, channel & 255, 1), None))
    effects(result, ALLOC, mode)
    if not created:
        return result, calls, 0
    data = bytes(result[descriptor + i] for i in range(40))
    calls.append((COPY, (CREATED + 0x18, descriptor, 40), data))
    for i, byte in enumerate(data):
        result[CREATED + 0x18 + i] = byte
    calls.append((VIEW, (CREATED + 0x40, read(result, CREATED + 0x1E, 1), variant & 255), None))
    effects(result, VIEW, mode)
    calls.append((ATTR, (CREATED + 0x40, table or DEFAULT), None))
    effects(result, ATTR, mode)
    for offset, word, size in ((0x80, tag80, 1), (0x81, tag81, 1), (0x84, count, 4),
            (0x10, 1, 4), (0x14, 0, 4), (0xA0, value, 4)):
        put(result, CREATED + offset, word, size)
    for offset in range(0x8C, 0x9C, 4):
        put(result, CREATED + offset, 0)
    put(result, CREATED + 0x9C, 0)
    if count:
        index = 0
        while index <= signed(read(result, LIMIT)):
            assert index < 8, 'outside bounded helper fixture'
            calls.append((RESOURCE, (count,), None))
            effects(result, RESOURCE, mode, index + 1)
            put(result, CREATED + 0x8C + index * 4, 0 if mode == 1 and index == 0 else 0x35000 + index * 0x100)
            index += 1
        calls.append((FOOTER, (), None))
        put(result, CREATED + 0x9C, 0 if mode == 2 else 0x39000)
    if payload:
        # Qualify emitted sequential accesses even for guest-only partial aliases.
        for offset in (0, 4, 8):
            put(result, CREATED + 0xA4 + offset, read(result, payload + offset))
    return result, calls, CREATED


class ConstructorOracle(machine.BurstOracle):
    def __init__(self, words, memory, args, created=CREATED, mode=0, phase=0, fault=None):
        super().__init__(words, memory, actor=DESCRIPTOR, phase=phase, mode=mode,
            entry=source.ENTRY, arguments=args, symbols={'unused': 0})
        self.created, self.resource_calls = created, 0
        self.current_pc, self.delay_of, self.root_fault = None, None, fault
        self.code = faults.TrackedCode(self.code, self)

    def access(self):
        if self.own_instruction and source.ENTRY <= self.current_pc < source.ENTRY + 412:
            if self.accesses == self.root_fault:
                raise faults.AccessBoundary
            self.accesses += 1

    def record_call(self, target):
        counts = {ALLOC: 6, COPY: 3, VIEW: 3, ATTR: 2, RESOURCE: 1, FOOTER: 0}
        assert target in counts, hex(target)
        args = tuple(self.arguments(counts[target]))
        data = bytes(self.get(args[1] + i, 1) for i in range(args[2])) if target == COPY else None
        self.calls.append((target, args, data))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        args = self.calls[-1][1]
        returned = 0x11223344
        if target == ALLOC:
            returned = self.created
        if target == COPY:
            for i, byte in enumerate(self.calls[-1][2]):
                self.put(args[0] + i, byte, 1)
            returned = args[0]
        if target == RESOURCE:
            returned = 0 if self.mode == 1 and self.resource_calls == 0 else 0x35000 + self.resource_calls * 0x100
            self.resource_calls += 1
        if target == FOOTER:
            returned = 0 if self.mode == 2 else 0x39000
        effects(self.memory, target, self.mode, self.resource_calls)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = returned & 0xFFFFFFFF


class RecordPayloadConstructorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.out.mkdir(exist_ok=True)
        source.freeze(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>103I', cls.rom, source.ROM))
        cls.original = cls.root / source.PATHS['original']

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def assemble(self, text, label):
        path = self.out / (label + '.s')
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], capture_output=True, text=True, check=True)
        return obj

    def test_01_complete_owner_neighbors_pools_and_both_padders(self):
        before = (self.out / 'before-owner').read_text()
        old, w0 = build.compile_owner(self.root, self.out, before, 'owner-before')
        new, w1 = build.compile_owner(self.root, self.out, source.recover(before), 'owner-after')
        t0, f0, r0 = parse_object(old)
        t1, f1, r1 = parse_object(new)
        self.assertEqual(set(f0), set(f1))
        self.assertEqual(w1.count('cfe: Warning'), w0.count('cfe: Warning'))
        for name in set(f0) - {source.FUNCTION}:
            a, b = f0[name], f1[name]
            self.assertEqual(a['size'], b['size'], name)
            self.assertEqual(t0[a['value']:a['value'] + a['size']], t1[b['value']:b['value'] + b['size']], name)
            relative = lambda table, info: {at - info['value']: value for at, value in table.items() if info['value'] <= at < info['value'] + info['size']}
            self.assertEqual(relative(r0, a), relative(r1, b), name)
        self.assertEqual(normalized_pools(old), normalized_pools(new))
        raw, functions = build.link_owner(self.root, self.out, new, source.OWNER)
        info = functions[source.FUNCTION]
        self.assertEqual(info['size'], 412)
        self.assertEqual(list(struct.unpack_from('>103I', raw, info['value'])), self.retail)
        self.assertEqual(self.retail[0], 0x27BDFFC8)
        self.assertEqual(self.retail[88:94], [0x8C410000, 0xAE8100A4, 0x8C4E0004, 0xAE8E00A8, 0x8C410008, 0xAE8100AC])
        with (self.root / source.PATHS['guards']).open() as stream:
            self.assertFalse(any(row['function'] == source.FUNCTION for row in csv.DictReader(stream)))
        primary = pad_c_object.emit_padded_assembly(new, self.root / 'conker/retail_layout.us.txt', source.OWNER,
            word_patches_path=self.root / source.PATHS['guards'])
        primary_obj = self.assemble(primary, 'primary-padded')
        extracted, unresolved = emit_function(t1, f1[source.FUNCTION], r1, source.FUNCTION,
            nm_anchors(self.root / source.PATHS['elf']))
        self.assertFalse(unresolved)
        compact = self.assemble(extracted, 'selected-compact')
        generated_obj = self.assemble(emit_padded_assembly(compact, self.original, filename=source.OWNER), 'generated-padded')
        for artifact in (primary_obj, generated_obj):
            data, f = build.link_owner(self.root, self.out, artifact, source.OWNER)
            self.assertEqual(data[f[source.FUNCTION]['value']:f[source.FUNCTION]['value'] + 412],
                self.rom[source.ROM:source.ROM + 412])
        self.receipt('owners', neighbors=len(f0) - 1, warnings_before=w0.count('cfe: Warning'),
            warnings_after=w1.count('cfe: Warning'), words=103, frame=0x38, guards=0,
            retained_words_sizes_relative_relocations_and_pools=True, both_actual_padders=True,
            original_shared_prototype_and_all_caller_words_retained=True)

    def words(self):
        data, functions = build.link_owner(self.root, self.out, self.out / 'generated-padded.o', source.OWNER)
        return list(struct.unpack_from('>103I', data, functions[source.FUNCTION]['value']))

    def test_02_original_and_rebased_independent_links(self):
        original = self.assemble(self.original.read_text() + '\n.type ' + source.FUNCTION + ',@function\n.size ' + source.FUNCTION + ',412\n', 'original-retail')
        anchors = nm_anchors(self.root / source.PATHS['elf'])
        anchors.update(build.load_symbol_addrs(str(self.root / 'conker/symbol_addrs.us.txt')))
        for phase, base in enumerate((source.ENTRY, 0x16108000)):
            spans = []
            for index, artifact in enumerate((original, self.out / 'primary-padded.o', self.out / 'generated-padded.o')):
                text, f, relocations = parse_object(artifact)
                info = f[source.FUNCTION]
                asm, unresolved = emit_function(text, info, relocations, source.FUNCTION, anchors)
                self.assertFalse(unresolved)
                single = self.assemble(asm, 'rebase-input-%d-%d' % (phase, index))
                symbols = {symbol for at, entries in relocations.items() if info['value'] <= at < info['value'] + 412 for _, symbol in entries}
                values = {symbol: (0x17008000 + i * 4 if symbol.startswith('func_') or symbol == 'memcpy' else
                    0x90007FFC + (i % 4) * 4 + (i // 4) * 0x10000) for i, symbol in enumerate(sorted(symbols))} if phase else {symbol: anchors[symbol] for symbol in symbols}
                script = single.with_suffix('.ld')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % base)
                elf = single.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in values.items()], '-o', str(elf), str(single)], capture_output=True, text=True, check=True)
                spans.append(sections(elf)['.text'][1][:412])
            self.assertEqual(spans[0], spans[1])
            self.assertEqual(spans[0], spans[2])

    def test_03_mips_o32_widths_live_limits_payload_aliases_and_helpers(self):
        words, cases, seen = self.words(), 0, set()
        for ordinal, (flags, table, count, limit, alias, created, mode, phase) in enumerate(itertools.product(
                (0, 0x40000, 0x80000000), (0, 1), (0, 1, 0xFFFFFFFF), (0xFFFFFFFF, 0, 3, 4),
                range(5), (0, CREATED), range(3), (0, 8))):
            memory, args = fixture(flags, table, count, limit, alias, ordinal)
            expected, calls, returned = reference(memory, args, created, mode)
            models = [ConstructorOracle(body, memory, args, created, mode, phase).run() for body in (self.retail, words)]
            for model in models:
                self.assertEqual(model.calls, calls)
                self.assertEqual(model.r[2], returned)
                self.assertEqual({a: v for a, v in model.memory.items() if not machine.STACK - 0x600 <= a < machine.STACK + 0x180},
                    {a: v for a, v in expected.items() if not machine.STACK - 0x600 <= a < machine.STACK + 0x180})
            self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
            seen.update(models[0].visits)
            cases += 1
        self.assertEqual(seen, set(range(source.ENTRY, source.ENTRY + 412, 4)))
        self.receipt('mips', cases=cases, reached_words=len(seen), eleven_argument_o32_ABI=True,
            byte_truncations_full_word_inputs_and_signed_wrap=True, five_payload_alias_layouts=True,
            live_global_loop_limit_and_helper_mutations=True, full_instruction_state_equal=True,
            partial_aggregate_aliases_and_fifth_handle_guest_only=True, helpers_are_bounded_atomic_contracts=True)

    def test_04_every_fired_root_memory_prefix(self):
        words, cuts = self.words(), 0
        for flags, count, limit, alias, created, mode in ((0, 0, 0, 0, 0, 0),
                (0x40000, 0, 0, 1, CREATED, 1), (0, 1, 0xFFFFFFFF, 2, CREATED, 0),
                (0x80000000, 1, 4, 3, CREATED, 2), (0, 0xFFFFFFFF, 3, 4, CREATED, 1)):
            memory, args = fixture(flags, 0, count, limit, alias, 7)
            finished = ConstructorOracle(self.retail, memory, args, created, mode).run()
            for cut in range(finished.accesses):
                models = [ConstructorOracle(body, memory, args, created, mode, fault=cut) for body in (self.retail, words)]
                for model in models:
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
                self.assertEqual((models[0].current_pc, models[0].delay_of), (models[1].current_pc, models[1].delay_of))
                cuts += 1
        self.receipt('faults', fired_prefixes=cuts, actual_root_memory_instructions=True,
            helpers_atomic_and_bounded=True, no_portable_C_or_arbitrary_helper_fault_claim=True)

    def test_05_effective_compiled_semantic_and_raw_allocation_controls(self):
        before = (self.out / 'before-owner').read_text()
        for label, body in (('category', source.BODY.replace('0x40000', '0x20000')),
                ('copy-length', source.BODY.replace('descriptor, 0x28', 'descriptor, 0x24')),
                ('clear-range', source.BODY.replace('i < 4', 'i < 3')),
                ('scalar-fields', dict(source.variants())['scalar-fields'])):
            self.assertNotEqual(body, source.BODY)
            obj, _ = build.compile_owner(self.root, self.out, source.recover(before, body), 'negative-' + label)
            raw, f = build.link_owner(self.root, self.out, obj, source.OWNER)
            info = f[source.FUNCTION]
            words = list(struct.unpack_from('>%dI' % (info['size'] // 4), raw, info['value']))
            self.assertNotEqual(words, self.retail)
            memory, args = fixture(0x40000, 0, 0, 0, 1, 1)
            expected, calls, _ = reference(memory, args, CREATED, 0)
            model = ConstructorOracle(words, memory, args).run()
            if label == 'scalar-fields':
                retail = ConstructorOracle(self.retail, memory, args).run()
                self.assertEqual(model.calls, retail.calls)
                self.assertEqual(model.memory, retail.memory)
                self.assertNotEqual(model.r, retail.r)
            else:
                self.assertTrue(model.calls != calls or any(model.memory[a] != value for a, value in expected.items()
                    if not machine.STACK - 0x600 <= a < machine.STACK + 0x180))

    def test_06_native32_contract_cases_and_controls(self):
        prelude = r'''#include <stddef.h>
typedef unsigned char u8;typedef short s16;typedef unsigned int u32;typedef int s32;
typedef struct {s32 unk0,unk4,unk8;} struct167;
typedef struct {s32 unk0;u8 p4[12];s32 unk10,unk14;struct {struct {s32 unk0;} i;} unk18;
 u8 p1c[2],unk1E,unk1F,p20[32];s16 unk40;u8 p42[62],unk80,unk81,p82[2];s32 unk84;
 u8 p88[4];s32 unk8C[4],unk9C,unkA0,unkA4[4];u8 tail[164];} struct210;
#define OFF(n) __builtin_offsetof(struct210,n)
_Static_assert(sizeof(void *)==4 && sizeof(struct210)==0x158 && sizeof(struct167)==12,"32-bit SDK layout");
_Static_assert(OFF(unk18)==0x18 && OFF(unk1E)==0x1E && OFF(unk40)==0x40 && OFF(unk80)==0x80 &&
 OFF(unk84)==0x84 && OFF(unk8C)==0x8C && OFF(unk9C)==0x9C && OFF(unkA0)==0xA0 && OFF(unkA4)==0xA4,"field offsets");
static union {u32 align;u8 bytes[0x180];} rs,ds,ps,er,ed,ep;
static u8 *record,*descriptor;static u32 tableData[8];s32 D_800A4AA0,D_80082FA0;
static s32 expectedLimit,mode,created,error,events,total,resourceCalls;
static u32 wanted[24][7];
static u32 get(u8 *p,int off){return *(u32 *)(p+off);}
static void set(u8 *p,int off,u32 value){*(u32 *)(p+off)=value;}
static void effect(u8 *r,u8 *d,s32 *limit,int role,int calls){
 if(role==0&&mode==1)d[6]=0xE7;if(role==2)set(r,0x40,(get(r,0x40)&0xFFFF)|0x12340000);
 if(role==3){set(r,0x40,(get(r,0x40)&0xFFFF0000)|0x5678);if(mode==2)*limit=2;}
 if(role==4&&calls==1){if(mode==1)*limit=0;if(mode==2)*limit=3;}}
static void want(u32 role,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f){u32 v[7]={role,a,b,c,d,e,f};int i;
 for(i=0;i<7;i++)wanted[total][i]=v[i];total++;}
static void event(u32 role,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f){u32 v[7]={role,a,b,c,d,e,f};int i;
 if(events>=total){error=1;return;}for(i=0;i<7;i++)if(wanted[events][i]!=v[i])error=1;events++;}
void *func_15167A68(s32 a,s32 b,s32 c,s32 d,u8 e,u8 f){event(0,(u32)a,(u32)b,(u32)c,(u32)d,e,f);
 effect(record,descriptor,&D_80082FA0,0,0);return created?record:0;}
void *memcpy(void *out,const void *in,u32 size){u8 snapshot[40];u32 i;
 event(1,(u32)out,(u32)in,size,0,0,0);if(size>40){error=1;return out;}
 for(i=0;i<size;i++)snapshot[i]=((const u8 *)in)[i];for(i=0;i<size;i++)((u8 *)out)[i]=snapshot[i];return out;}
void func_1513FFF4(u8 *out,u8 index,u8 variant){event(2,(u32)out,index,variant,0,0,0);
 effect(record,descriptor,&D_80082FA0,2,0);}
void func_151400D0(u8 *out,u8 *table){event(3,(u32)out,(u32)table,0,0,0,0);
 effect(record,descriptor,&D_80082FA0,3,0);}
u8 *func_1515D480(s32 count){u32 value=0x35000+(u32)resourceCalls*0x100;
 if(mode==1&&resourceCalls==0)value=0;
 event(4,(u32)count,0,0,0,0,0);resourceCalls++;effect(record,descriptor,&D_80082FA0,4,resourceCalls);return (u8 *)value;}
u8 *func_1515D440(void){event(5,0,0,0,0,0,0);return mode==2?0:(u8 *)0x39000;}
'''
        suffix = r'''
static u32 ref(u32 flags,u32 table,u32 count,u32 user,int alias,u32 extra,u8 tag80,u8 tag81,u8 variant,u8 channel,u32 context){
 u8 *r=er.bytes,*d=ed.bytes,*payload;int i;u32 value;
 want(0,flags&0x40000?0x4A:0x1B,context,extra+0xB0,1,channel,1);effect(r,d,&expectedLimit,0,0);
 if(!created)return 0;want(1,(u32)record+0x18,(u32)descriptor,40,0,0,0);
 for(i=0;i<40;i++)r[0x18+i]=d[i];want(2,(u32)record+0x40,r[0x1E],variant,0,0,0);effect(r,d,&expectedLimit,2,0);
 want(3,(u32)record+0x40,table?table:(u32)&D_800A4AA0,0,0,0,0);effect(r,d,&expectedLimit,3,0);
 r[0x80]=tag80;r[0x81]=tag81;set(r,0x84,count);set(r,0x10,1);set(r,0x14,0);set(r,0xA0,user);
 for(i=0;i<4;i++)set(r,0x8C+i*4,0);set(r,0x9C,0);
 if(count){i=0;while(i<=expectedLimit){want(4,count,0,0,0,0,0);effect(r,d,&expectedLimit,4,i+1);
  set(r,0x8C+i*4,mode==1&&i==0?0:0x35000+(u32)i*0x100);i++;}want(5,0,0,0,0,0,0);set(r,0x9C,mode==2?0:0x39000);}
 payload=alias==1?ep.bytes:alias==2?r+0xA4:0;if(payload)for(i=0;i<3;i++){value=get(payload,i*4);set(r,0xA4+i*4,value);}
 return (u32)record;}
static int run(void){u32 flags[3]={0,0x40000,0x80000000},counts[3]={0,1,0xFFFFFFFF};s32 limits[3]={-1,0,3};
 int fi,ti,ci,li,alias,phase,i,ordinal=0,cases=0;u32 table,wantedReturn,returned;struct167 *payload;
 record=rs.bytes;descriptor=ds.bytes;
 for(fi=0;fi<3;fi++)for(ti=0;ti<2;ti++)for(ci=0;ci<3;ci++)for(li=0;li<3;li++)for(alias=0;alias<3;alias++)
 for(created=0;created<2;created++)for(mode=0;mode<3;mode++)for(phase=0;phase<2;phase++,ordinal++,cases++){
  for(i=0;i<0x180;i++){rs.bytes[i]=er.bytes[i]=(u8)(i*13+ordinal+0xA5);
   ds.bytes[i]=ed.bytes[i]=(u8)(i*13+ordinal+0xA5);ps.bytes[i]=ep.bytes[i]=(u8)(i*13+ordinal+0xA5);}
  set(descriptor,0,flags[fi]);set(ed.bytes,0,flags[fi]);D_80082FA0=expectedLimit=limits[li];
  table=ti?(u32)tableData:0;error=events=total=resourceCalls=0;
  wantedReturn=ref(flags[fi],table,counts[ci],0x87654321,alias,0x7FFFFFFF,0x80,0xFF,0xF3,0xC5,0xFEDCBA98);
  payload=alias==1?(struct167 *)ps.bytes:alias==2?(struct167 *)(record+0xA4):0;
  returned=(u32)func_1513C350((struct210 *)descriptor,(s32)table,0x80,0xFF,0xF3,(s32)counts[ci],
   (s32)0x87654321,payload,0x7FFFFFFF,0xC5,(s32)0xFEDCBA98);
  if(error||events!=total||returned!=wantedReturn||D_80082FA0!=expectedLimit)return 1;
  for(i=0;i<0x180;i++)if(rs.bytes[i]!=er.bytes[i]||ds.bytes[i]!=ed.bytes[i]||ps.bytes[i]!=ep.bytes[i])return 2;
 }return cases==1944?0:81;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        for label, profile, body, status in (('O2', '-O2', source.BODY, 0), ('O0', '-O0', source.BODY, 0),
                ('negative-category', '-O2', source.BODY.replace('0x40000', '0x20000'), 1),
                ('negative-copy', '-O2', source.BODY.replace('descriptor, 0x28', 'descriptor, 0x24'), 1),
                ('negative-clear', '-O2', source.BODY.replace('i < 4', 'i < 3'), 2)):
            path = self.out / ('native-' + label + '.c')
            path.write_text(prelude + body + suffix)
            binary = path.with_suffix('')
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-fwrapv', '-fno-builtin',
                '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([str(binary)], capture_output=True).returncode, status, label)
        self.receipt('native', cases_per_profile=1944, profiles=['O2', 'O0'], native32_required=True,
            SDK_field_offsets_and_size_asserted=True, full_record_descriptor_and_payload_memory_compared=True,
            live_limit_helper_args_return_null_allocations_and_widths=True, three_valid_payload_alias_layouts=True,
            partial_aggregate_aliases_and_fifth_handle_excluded=True, effective_compiled_controls=True,
            no_guest_endian_arbitrary_helper_or_gameplay_claim=True)

    def test_07_installed_source_and_identical_complete_image(self):
        source.freeze(self.root, self.out)
        self.assertEqual((self.root / source.PATHS['owner']).read_text(), source.recover((self.out / 'before-owner').read_text()))
        self.assertEqual(hashlib.sha256((self.root / source.PATHS['owner']).read_bytes()).hexdigest(), OWNER_AFTER)
        self.assertEqual((self.root / source.PATHS['elf']).read_bytes(), (self.out / 'before-elf').read_bytes())
        self.assertEqual((self.root / source.PATHS['progress']).read_bytes(), source.expected_progress((self.out / 'before-progress').read_bytes()))
        for key in ('guards', 'makefile', 'functions', 'structs', 'variables', 'original'):
            self.assertEqual((self.root / source.PATHS[key]).read_bytes(), (self.out / ('before-' + key)).read_bytes(), key)
        data = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('image', ELF_sha256=source.BASELINE['elf'], identical_entire_ELF=True,
            every_symbol_extent_address_and_serialized_byte_fixed=True, new_guards=0, unchanged_Makefile_and_shared_headers=True,
            only_one_progress_language_field_changed=True, protected_data=data)

    def test_08_effective_installed_and_immutable_input_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for key in ('elf', 'owner', 'progress', 'guards', 'makefile', 'functions', 'structs', 'variables', 'original'):
            path = self.root / source.PATHS[key]
            bad = rb(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p, value=bad: value if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_07_installed_source_and_identical_complete_image()
        path = self.root / source.PATHS['owner']
        with patch.object(Path, 'read_text', lambda p, *a, **k: rt(p, *a, **k) + '\n' if p == path else rt(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_installed_source_and_identical_complete_image()
        path = self.out / 'before-owner'
        with patch.object(Path, 'read_bytes', lambda p: b'changed baseline' if p == path else rb(p)):
            with self.assertRaisesRegex(ValueError, 'immutable constructor input'):
                self.test_07_installed_source_and_identical_complete_image()

    def test_09_pinned_progress_inverse_and_unknown_input_controls(self):
        self.test_07_installed_source_and_identical_complete_image()
        checkpoint.freeze_after(self.root)
        current = (self.root / checkpoint.PROGRESS).read_bytes()
        self.assertEqual(checkpoint.previous_input(current, checkpoint.PROGRESS, self.root),
            (self.out / 'before-progress').read_bytes())
        self.assertEqual(checkpoint.previous_input(current, self.root / checkpoint.PROGRESS, self.root),
            (self.out / 'before-progress').read_bytes())
        self.assertEqual(checkpoint.previous_input(current + b'\n', checkpoint.PROGRESS, self.root), current + b'\n')
        self.assertEqual(checkpoint.previous_input(current, 'unrelated.csv', self.root), current)
        path = self.out / 'after-progress'
        rb = Path.read_bytes
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
            with self.assertRaisesRegex(AssertionError, 'after-progress fixture'):
                checkpoint.freeze_after(self.root)

        from tools.tests.test_game_codec_frame_dispatch import CodecFrameDispatchTests
        CodecFrameDispatchTests.setUpClass()
        historical = CodecFrameDispatchTests('test_07_installed_source_profile_guards_and_closed_image')
        historical.test_07_installed_source_profile_guards_and_closed_image()
        path = self.root / checkpoint.PROGRESS
        with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
            with self.assertRaises(AssertionError):
                historical.test_07_installed_source_profile_guards_and_closed_image()


if __name__ == '__main__':
    unittest.main()
