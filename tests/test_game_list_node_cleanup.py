"""Cached list successors, signed table lookups and closed saved-register setup."""

from dataclasses import dataclass, replace
from pathlib import Path
import csv
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_list_node_cleanup as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths,function_vram,load_symbol_addrs,DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_random_burst import ReturnBoundaryCode,CallerBoundary

ROOT=Path(__file__).resolve().parents[2]
OWNER,NODES,PAYLOADS=0x28000,0x30000,0x35000
CB=(0x1514E830,0x1514E850,0x1514E87C)
REGISTRY,RELEASE,ALLOC,HANDLER=0x151696DC,0x15169804,0x15168B10,0x16010000
SLOT_COUNT,SLOTS,DESTRUCTORS=0x800DD190,0x800DD198,0x8008B4D0
ACTIONS=(-1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,2,0,0,0)
HEADERS=(0,1,1,1,1,1,2,1,1,1,1,3,3,4,3,3,0,0,0,0,5,0,0,0,0,6,7,7)
DESC=(0x800A5FCC,0x800A5FC4,0x800A5FBC,0x800A5FAC,0x800A5FA4,0x800A5FB4,0x800A5F9C,
      0x800A5F94,0x800A5F2C,0x800A5F34,0x800A5F3C,0x800A5F4C,0x800A5F7C,0x800A5F84,
      0x800A5F8C,0x800A5F74,0x800A5F54,0x800A5F5C,0x800A5F44,0x800A5F64,0x800A5F6C,
      0x800A5F24,0x800A5F1C,0x800A5F14,0x800A5F0C,0x800A5F04,0x800A5EFC,0x800A5EF4)
WORDS=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0xAABBCCDD)
RAW_ORIGINS=tuple({11:12,12:13,13:11}.get(i,i)for i in range(40))


@dataclass(frozen=True)
class Case:
    keys:tuple=(1,11,24,0)
    mode:int=0
    seed:int=0
    overrides:tuple=()
    kind:int=2
    real_payload:bool=False


def corpus():
    for seed,n,mode in itertools.product(range(28),(1,3),(0,3,12,48,63)):
        yield Case(tuple((seed+i*5)%28 for i in range(n)),mode,seed)
    for n,mode in itertools.product((0,2,6),(0,1,2,4,8,16,32,63)):
        yield Case(tuple((mode+i*5)%28 for i in range(n)),mode,n+mode)
    yield Case((-32768,-1,32767),63,overrides=((-32768,-32768),(-1,-1),(32767,32767)))
    yield Case((-2,-3),3,overrides=((-2,-2),(-3,-1)))
    yield Case((0,),0,overrides=((0,-2),))


def node(i):
    return NODES+i*0x100


def payload(case,i):
    return PAYLOADS+i*0x100 if case.real_payload else WORDS[(case.seed+i)%len(WORDS)]


def callback_target(action,delta=0):
    return CB[action]+delta if 0<=action<3 else 0x16040000+(action&65535)*4+delta


def descriptor(key):
    return DESC[key] if 0<=key<28 else 0x60000+((key+32768)&65535)*8


def reference(case):
    actions=dict(enumerate(ACTIONS));actions.update(case.overrides)
    values=[payload(case,i)for i in range(len(case.keys))]
    trace=[];head=bool(case.keys)
    for i,key in enumerate(case.keys):
        action=actions[key]
        if action!=-1:
            trace.append((1,action,values[i]))
            if case.mode&4 and i+1<len(case.keys):
                actions[case.keys[i+1]]=2
            if case.mode&8:
                head=False
        trace.append((2,i,0))
        if case.mode&32 and i+1<len(case.keys):
            values[i+1]=0xCC000000+i+1
    return trace,head,actions


def fixture(case,callbacks=source.CALLBACKS,descriptors=source.DESCRIPTORS,delta=0,slot_count=0,handler=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x800,0x200)}
    memory.update({OWNER+i:0xA5 for i in range(-16,0x350)})
    for i in range(8):
        memory.update({node(i)+j:0xA5 for j in range(-16,0x50)})
        memory.update({PAYLOADS+i*0x100+j:0xA5 for j in range(-16,0x30)})
        put(memory,PAYLOADS+i*0x100,0,1)
    put(memory,OWNER+0x2F0,0);put(memory,OWNER+0x2F4,node(0)if case.keys else 0)
    actions=dict(enumerate(ACTIONS));actions.update(case.overrides)
    for key,action in actions.items():
        d=descriptor(key);put(memory,descriptors+key*4,d)
        put(memory,d,HEADERS[key]if 0<=key<28 else 0x55AA,2);put(memory,d+2,action&65535,2)
        if action!=-1:
            put(memory,callbacks+action*4,callback_target(action,delta))
    for i,key in enumerate(case.keys):
        p=node(i);put(memory,p,case.kind,1);put(memory,p+8,0x39000+i*4)
        put(memory,p+0x10,payload(case,i));put(memory,p+0x14,node(i+1)if i+1<len(case.keys)else 0)
        put(memory,p+0x18,node(i-1)if i else 0);put(memory,p+0x1C,key&65535,2)
    put(memory,SLOT_COUNT,slot_count&255,1)
    for i,p in enumerate((node(0),node(1),node(0))):
        put(memory,SLOTS+i*4,p)
    put(memory,DESTRUCTORS+case.kind*52,HANDLER if handler else 0)
    return memory


class CleanupOracle(TimingOracle):
    def __init__(self,words,case,phase=0,delta=0,callbacks=source.CALLBACKS,
                 descriptors=source.DESCRIPTORS,entry=source.ENTRY,connected=None,slot_count=0,handler=0):
        self.case,self.delta,self.descriptors=case,delta,descriptors
        self.trace,self.roles,self.low_packets=[],[],[]
        self.boundary_hit=None
        self.node_indices={node(i):i for i in range(len(case.keys))}
        actions=set(ACTIONS)|{a for _,a in case.overrides}|{2}
        self.callback_ids={callback_target(a,delta):a for a in actions if a!=-1}
        super().__init__(words,fixture(case,callbacks,descriptors,delta,slot_count,handler),phase=phase,
            entry=entry,arguments=(OWNER,0x87654321),connected=connected)
        if entry==source.CALLER:
            self.code=ReturnBoundaryCode(self.code,source.JOIN,self)

    def execute(self,word):
        op,rs,rt,rd=word>>26,word>>21&31,word>>16&31,word>>11&31
        if op==32:
            imm=(word&65535)-(65536 if word&0x8000 else 0)
            value=self.get((self.r[rs]+imm)&0xFFFFFFFF,1)
            self.r[rt]=((value^128)-128)&0xFFFFFFFF;self.r[0]=0
        elif op==0 and word&63==42:
            self.r[rd]=int(signed(self.r[rs])<signed(self.r[rt]));self.r[0]=0
        else:
            super().execute(word)

    def record_call(self,target):
        self.roles.append((target,self.r[18],self.r[19]))
        args=self.arguments(2 if target==ALLOC else 1)
        if target in self.callback_ids:
            action=self.callback_ids[target]
            self.trace.append((1,action,args[0]))
        elif target==source.REMOVE+self.delta:
            if args[0]in self.node_indices:
                self.trace.append((2,self.node_indices[args[0]],0))
            else:
                self.low_packets.append((target,args))
        elif target==source.ENTRY:
            assert args==(OWNER,)
        elif target in (REGISTRY,RELEASE,ALLOC,HANDLER,0x1518E308,0x1515F10C):
            self.low_packets.append((target,args))
        else:
            raise AssertionError(('Unbounded cleanup call',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def clobber(self):
        for i in range(4):
            self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):
            self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=0x87654321;self.hi,self.lo=0x87654321,0x12345678

    def remove_effects(self,p):
        if p not in self.node_indices:
            return
        i=self.node_indices[p]
        if self.case.mode&2:
            self.put(p+0x14,0,4);self.put(p+0x10,0,4);self.put(p+0x1C,65535,2)
        if self.case.mode&32 and i+1<len(self.case.keys):
            self.put(node(i+1)+0x10,0xCC000000+i+1,4)

    def hook(self,target):
        if target in self.callback_ids:
            i=sum(x[0]==2 for x in self.trace)
            assert i<len(self.case.keys)
            if self.case.mode&1:
                self.put(node(i)+0x14,0,4)
            if self.case.mode&4 and i+1<len(self.case.keys):
                self.put(descriptor(self.case.keys[i+1])+2,2,2)
            if self.case.mode&8:
                self.put(OWNER+0x2F4,0,4)
            if self.case.mode&16:
                self.put(node(i)+0x10,0xDD000000+i,4)
        elif target in (source.REMOVE+self.delta,ALLOC,HANDLER):
            self.remove_effects(self.r[4])
        elif target not in (REGISTRY,0x1518E308,0x1515F10C,RELEASE):
            raise AssertionError(('Unsupported cleanup provider',hex(target)))
        self.clobber()


def native_harness(body,cases):
    rows=[]
    for c in cases:
        trace,head,actions=reference(c)
        keys=list(c.keys)+[0]*(6-len(c.keys))
        events=trace+[(0,0,0)]*(12-len(trace))
        rows.append('{%du,%du,%du,%du,{%s},{%s}}'%(
            len(c.keys),c.mode,c.seed,len(trace),','.join(str(k)for k in keys),
            ','.join('{%s}'%','.join('0x%Xu'%(w&0xFFFFFFFF)for w in e)for e in events)))
    return '''typedef unsigned char u8;typedef short s16;typedef int s32;typedef unsigned int u32;
#define NULL ((void *)0)
''' + source.TYPES + source.DECLARATIONS + body + '''
typedef struct{u32 kind,a,b;}Event;
typedef struct{u32 count,mode,seed,eventCount;s16 keys[6];Event events[12];}Case;
static const Case cases[]={''' + ',\n'.join(rows) + '''};
static const s16 initialActions[28]={''' + ','.join(map(str,ACTIONS)) + '''};
static const s16 headers[28]={''' + ','.join(map(str,HEADERS)) + '''};
static s16 records[28][2];
s16 *D_8008ABE8[28];
static struct{u32 before[4];GameListNode values[6];u32 after[4];}storage;
static union{double align;u8 bytes[0x360];}ownerStorage;
static u8 *owner;
static const Case *item;
static int events,error,removed;
static const u32 words[]={0,1,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu,0xAABBCCDDu};
static void event(u32 kind,u32 a,u32 b){
    if(events>=(int)item->eventCount || kind!=item->events[events].kind ||
       a!=item->events[events].a || b!=item->events[events].b){error=1;return;}
    events++;
}
static void callback(s32 value,int action){
    int i=removed;
    event(1,(u32)action,(u32)value);
    if(i>=(int)item->count){error=1;return;}
    if(item->mode&1)storage.values[i].next=0;
    if(item->mode&4 && i+1<(int)item->count)records[item->keys[i+1]][1]=2;
    if(item->mode&8)*(GameListNode **)(owner+0x2F4)=0;
    if(item->mode&16)storage.values[i].unk10=(s32)(0xDD000000u+(u32)i);
}
static void cb0(s32 value){callback(value,0);}
static void cb1(s32 value){callback(value,1);}
static void cb2(s32 value){callback(value,2);}
void (*D_8008AB58[])()={cb0,cb1,cb2};
__attribute__((noinline))void func_1516972C(GameListNode *p){
    int i=(int)(p-storage.values);
    if(i<0 || i>=(int)item->count || i!=removed){error=1;return;}
    event(2,(u32)i,0);removed++;
    if(item->mode&2){p->next=0;p->unk10=0;p->unk1C=-1;}
    if(item->mode&32 && i+1<(int)item->count)storage.values[i+1].unk10=(s32)(0xCC000000u+(u32)i+1);
}
static int test_all(void){
    u32 n,i,result;int hadCallback;
    if(sizeof(void *)!=4 || sizeof(GameListNode)!=0x20 ||
       __builtin_offsetof(GameListNode,unk10)!=0x10 || __builtin_offsetof(GameListNode,next)!=0x14 ||
       __builtin_offsetof(GameListNode,prev)!=0x18 || __builtin_offsetof(GameListNode,unk1C)!=0x1C)return 90;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
        item=&cases[n];events=error=removed=0;hadCallback=0;owner=ownerStorage.bytes+16;
        for(i=0;i<sizeof(ownerStorage);i++)ownerStorage.bytes[i]=0xA5;
        for(i=0;i<sizeof(storage);i++)((u8 *)&storage)[i]=0xA5;
        for(i=0;i<28;i++){records[i][0]=headers[i];records[i][1]=initialActions[i];D_8008ABE8[i]=records[i];}
        *(GameListNode **)(owner+0x2F0)=0;
        *(GameListNode **)(owner+0x2F4)=item->count?&storage.values[0]:0;
        for(i=0;i<item->count;i++){
            storage.values[i].unk10=(s32)words[(item->seed+i)%6];
            storage.values[i].next=i+1<item->count?&storage.values[i+1]:0;
            storage.values[i].prev=i?&storage.values[i-1]:0;
            storage.values[i].unk1C=item->keys[i];
        }
        result=(u32)func_1514D310(owner);
        if(error || result!=1 || removed!=(int)item->count || events!=(int)item->eventCount)return 23;
        for(i=0;i<item->eventCount;i++)if(item->events[i].kind==1)hadCallback=1;
        if(*(GameListNode **)(owner+0x2F4)!=((item->mode&8 && hadCallback)?0:(item->count?&storage.values[0]:0)))return 24;
        for(i=0;i<4;i++)if(storage.before[i]!=0xA5A5A5A5u || storage.after[i]!=0xA5A5A5A5u)return 25;
        for(i=0;i<16;i++)if(ownerStorage.bytes[i]!=0xA5 || ownerStorage.bytes[0x350+i]!=0xA5)return 26;
        for(i=0;i<28;i++)if(records[i][0]!=headers[i] || D_8008ABE8[i]!=records[i])return 27;
    }
    return 0;
}
__attribute__((noreturn))void _start(void){int status=test_all();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class ListNodeCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD
        cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:
            source.audit(ROOT,cls.output)
        else:
            source.freeze(ROOT,cls.output)
            if not (cls.output/'first-link.json').exists():
                source.qualify(ROOT,cls.output);source.make_shadow(ROOT,cls.output);source.predict(ROOT,cls.output)
        cls.values=source.snapshot(cls.output)
        cls.obj,diag=source.compile_owner(ROOT,cls.output,'#include <ultra64.h>\n'+source.TYPES+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:
            raise ValueError(diag)
        data,functions=source.link_owner(ROOT,cls.output,cls.obj,source.OWNER)
        cls.raw=list(struct.unpack_from('>40I',data,functions[source.FUNCTION]['value']))
        cls.normal=source.normalized(*source.payload(cls.obj))
        if source.payload(cls.output/'qualified-padded.o')!=cls.normal:
            raise ValueError('List cleanup actual padder differs from isolated normalization')
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>40I',cls.rom,source.ROM))
        linked=(cls.output/'first-linked.elf').read_bytes()
        cls.fitted=list(struct.unpack_from('>40I',linked,source.elf_slot_offset(linked,source.ENTRY,160)))
        cls.cases=list(corpus());cls.native_cases=[c for c in cls.cases if not c.overrides]
        cls.receipt=dict(installed=cls.installed,cases=len(cls.cases),native_cases=len(cls.native_cases),guards=5)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('list cleanup qualification:',cls.receipt)

    def test_01_closed_origin_register_cycle_words_and_retail_tables(self):
        self.assertEqual(self.fitted,self.truth)
        raw,bindings=source.payload(self.obj)
        self.assertEqual(source.normalized(raw,bindings),source.payload(source.original(ROOT,self.output)))
        self.assertEqual([i for i,(a,b)in enumerate(zip(self.raw,self.truth))if a!=b],[11,12,13,17,20])
        self.assertEqual(set(RAW_ORIGINS),set(range(40)))
        self.assertEqual(self.raw[0],0x27BDFFD0)
        a=struct.unpack('>40I',raw);b=struct.unpack('>40I',source.payload(source.original(ROOT,self.output))[0])
        for target,origin in enumerate(RAW_ORIGINS):
            word=a[origin]
            if target in (11,12,13,17,20):
                shifts=(16,)if word>>26==15 else (21,16)
                for shift in shifts:
                    reg=word>>shift&31
                    if reg in (18,19):
                        word=(word&~(31<<shift))|((37-reg)<<shift)
                if target==20:
                    word=(word&~((31<<21)|(31<<16)))|((word>>21&31)<<16)|((word>>16&31)<<21)
            self.assertEqual(word,b[target],(target,origin))
        self.assertEqual(struct.unpack_from('>3I',self.rom,0x22F618),CB)
        self.assertEqual(struct.unpack_from('>28I',self.rom,0x22F6A8),DESC)
        self.assertEqual(tuple(struct.unpack_from('>2h',self.rom,p-0x800A5FCC+0x24AA8C)for p in DESC),
                         tuple(zip(HEADERS,ACTIONS)))
        self.receipt.update(raw_words=40,frame=48,raw_differences=5,normalized_differences=0,
            origin_bijection=True,pure_setup_origins=[12,13,11],saved_role_cycle=[18,19],
            table_entries=28,callback_entries=3,removal_return_declaration_corrected=True)

    def test_02_three_way_complete_returns_mutations_cached_next_and_call_roles(self):
        visits=set();raw_private_differences=0
        for case,phase in itertools.product(self.cases,(0,8)):
            models=[CleanupOracle(code,case,phase).run()for code in (self.truth,self.raw,self.fitted)]
            trace,head,actions=reference(case)
            for m in models:
                self.assertEqual(m.trace,trace);self.assertEqual(m.r[2],1)
                self.assertEqual(bool(read(m.memory,OWNER+0x2F4)),head)
                for key,action in actions.items():
                    self.assertEqual(read(m.memory,descriptor(key)+2,2),action&65535)
                for reg in (*range(16,24),28,29,30,31):
                    self.assertEqual(m.r[reg],m.before[reg])
                self.assertEqual(m.f[20:],m.saved_f);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]))
            self.assertEqual(complete(models[0]),complete(models[2]))
            self.assertEqual(models[0].roles,models[2].roles)
            raw_private_differences+=models[0].roles!=models[1].roles
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+160,4))<=visits)
        self.assertGreater(raw_private_differences,0)
        self.receipt.update(three_way_final_model_phases=len(self.cases)*2,all40_words_visited=True,
            fitted_call_roles_exact=True,raw_call_role_difference_phases=raw_private_differences,
            signed_guest_only_cases=sum(bool(c.overrides)for c in self.cases))
        for code in (self.truth,self.raw,self.fitted):
            m=CleanupOracle(code,Case(()))
            for base,size in ((source.CALLBACKS,12),(source.DESCRIPTORS,112),*( (p,4)for p in DESC)):
                for address in range(base,base+size):
                    m.memory.pop(address,None)
            m.run();self.assertEqual(m.trace,[]);self.assertEqual(m.r[2],1)
        self.receipt['empty_list_never_reads_callback_or_descriptor_tables']=True

    def native(self,body,label,opt='-O2'):
        unit=self.output/(label+'.c');unit.write_text(native_harness(body,self.native_cases))
        binary=self.output/(label+opt)
        args=['gcc','-m32',opt,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static',
            '-fno-pie','-no-pie','-fno-stack-protector','-fsanitize=undefined','-fsanitize-undefined-trap-on-error',
            '-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(unit),'-o',str(binary)]
        p=subprocess.run(args,capture_output=True,text=True)
        (self.output/(label+opt+'-compiler.log')).write_text(p.stdout+p.stderr)
        self.assertEqual(p.returncode,0,p.stderr[:3000])
        return subprocess.run([str(binary)],capture_output=True,timeout=30).returncode

    def test_03_native32_typed_nodes_and_effective_compiled_negatives(self):
        for opt in ('-O0','-O2','-O3'):
            self.assertEqual(self.native(source.SELECTED,'native',opt),0)
        late=source.SELECTED.replace('        next = node->next;\n','').replace(
            '        node = next;','        next = node->next;\n        node = next;')
        after_callback=source.SELECTED.replace('        next = node->next;\n','').replace(
            '        func_1516972C(node);','        next = node->next;\n        func_1516972C(node);')
        controls={
            'late-next-after-removal':late,
            'late-next-after-callback':after_callback,
            'missing-removal':source.SELECTED.replace('        func_1516972C(node);',''),
            'skipped-callback-one':source.SELECTED.replace('callback != -1','callback != -1 && callback != 1'),
            'wrong-payload':source.SELECTED.replace('](node->unk10)','](node->unk10 ^ 1)'),
            'wrong-descriptor':source.SELECTED.replace('callback = D_8008ABE8[node->unk1C][1];','callback = 0;'),
            'wrong-head':source.SELECTED.replace('owner + 0x2F4','owner + 0x2F0'),
            'wrong-return':source.SELECTED.replace('return 1;','return 0;'),
            'skipped-last':source.SELECTED.replace('while (node != NULL)','while (node != NULL && node->next != NULL)'),
        }
        for name,body in controls.items():
            self.assertNotEqual(body,source.SELECTED)
            self.assertEqual(self.native(body,name),23,name)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,compiled_semantic_negatives=len(controls),
            actual_native_node_layout=True,negative_native_table_index_claimed=False)

    def test_04_all_guard_words_bindings_prefix_and_omission_identity(self):
        raw,bindings=source.payload(self.obj);old=self.values['conker/retail_word_patches.us.csv']
        self.assertEqual(source.guard_bytes(self.values),old+source.GUARD_SUFFIX)
        rows=source.GUARD_SUFFIX.splitlines(keepends=True);count=0
        for i,(at,expected,_,expected_binding,_)in enumerate(source.GUARDS):
            bad=bytearray(raw);struct.pack_into('>I',bad,at,expected^1)
            with self.assertRaises(ValueError):
                source.normalized(bad,bindings)
            bad_bindings={a:list(r)for a,r in bindings.items()}
            bad_bindings[at]=[('R_MIPS_26','func_1516972C')]
            with self.assertRaises(ValueError):
                source.normalized(raw,bad_bindings)
            changed=rows.copy();fields=changed[i].decode().rstrip('\n').split(',')
            fields[3]='0x%08X'%(expected^1);changed[i]=(','.join(fields)+'\n').encode()
            path=self.output/('wrong-guard-%d.csv'%i);path.write_bytes(old+b''.join(changed))
            with self.assertRaises(ValueError):
                source.emit_padded_assembly(self.output/'after-owner.o',ROOT/source.ASM,
                    word_patches_path=path,filename=source.OWNER)
            fields=rows[i].decode().rstrip('\n').split(',')
            fields[5]='-' if expected_binding!='-' else 'R_MIPS_26:func_1516972C'
            changed=rows.copy();changed[i]=(','.join(fields)+'\n').encode()
            path=self.output/('wrong-binding-%d.csv'%i);path.write_bytes(old+b''.join(changed))
            with self.assertRaises(ValueError):
                source.emit_padded_assembly(self.output/'after-owner.o',ROOT/source.ASM,
                    word_patches_path=path,filename=source.OWNER)
            omitted=self.fitted.copy();omitted[at//4]=self.raw[at//4]
            self.assertNotEqual(omitted,self.truth)
            count+=5
        self.receipt.update(guard_controls=count,all_five_guard_sites_fired=True,prefix_byte_identical=True)

    def test_05_independent_GNU_signed_LO16_rebases(self):
        count=0
        for delta,callbacks,descriptors in ((0x10000,0x80087FFC,0x80097FFC),
                (0xCF20,0x80088000,0x80098000),(0x18000,0x8008FFF0,0x8009FFF0)):
            images=[]
            for i,path in enumerate((self.output/'qualified-padded.o',source.original(ROOT,self.output))):
                if i==0:
                    from tools.experiments.alternative_source_draft_word_screen import emit_function
                    anchors={'D_8008AB58':callbacks,'D_8008ABE8':descriptors,'func_1516972C':source.REMOVE+delta}
                    assembly,unresolved=emit_function(self.normal[0],dict(value=0,size=160),
                        self.normal[1],source.FUNCTION,anchors)
                    self.assertFalse(unresolved)
                    asm=self.output/'isolated-fitted.s';asm.write_text(assembly);path=asm.with_suffix('.o')
                    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(path),str(asm)],
                        capture_output=True,check=True)
                elf=self.output/('rebase-%d-%d.elf'%(delta,i));script=self.output/'rebase.ld'
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                defs=['--defsym=D_8008AB58=0x%X'%callbacks,'--defsym=D_8008ABE8=0x%X'%descriptors,
                      '--defsym=func_1516972C=0x%X'%(source.REMOVE+delta)]
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *defs,'-o',str(elf),str(path)],capture_output=True,check=True)
                section_base,data=sections(elf)['.text']
                _,functions,_=source.parse_object(path)
                images.append(list(struct.unpack_from('>40I',data,functions[source.FUNCTION]['value'])))
            self.assertEqual(images[0],images[1])
            for case in self.native_cases[::19]:
                m=CleanupOracle(images[0],case,delta=delta,callbacks=callbacks,descriptors=descriptors).run()
                self.assertEqual(m.trace,reference(case)[0]);count+=1
        self.receipt.update(rebase_sets=3,signed_LO16_carry_verified=True,independent_rebase_phases=count)

    def test_06_direct_caller_inventory_and_actual_opening_window(self):
        symbols=load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        rows=list(csv.DictReader((ROOT/'conker/progress.csv').open()))
        add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],symbols)
        opcode=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);found=[]
        for row in rows:
            if row['version']!='us' or row['section']not in DEFAULT_SEGMENTS['us']:
                continue
            base,start=DEFAULT_SEGMENTS['us'][row['section']];entry=function_vram(row,symbols)
            code=struct.unpack_from('>%dI'%row['_retail_nwords'],self.rom,entry-base+start)
            found.extend((row['function'],entry+i*4)for i,w in enumerate(code)if w==opcode)
        self.assertEqual(found,[('func_15060F28',0x15060F40)])
        self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',source.ENTRY)for i in range(0,len(self.rom),4)))
        window=list(struct.unpack_from('>8I',self.rom,source.CALLER_ROM))
        self.assertEqual(window[6:],[opcode,0x02202025])
        count=0
        for case,phase in itertools.product(self.native_cases[::23],(0,8)):
            models=[]
            for code in (self.truth,self.raw,self.fitted):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+160,4),code))
                m=CleanupOracle(window,case,phase,entry=source.CALLER,connected=connected)
                with self.assertRaises(CallerBoundary):
                    m.run()
                self.assertEqual(m.boundary_hit,source.JOIN)
                self.assertEqual(m.r[29],STACK+phase-0x20);self.assertEqual(m.r[16],0x87654321)
                self.assertEqual(m.r[17],OWNER);self.assertEqual(m.r[2],1)
                self.assertEqual(m.trace,reference(case)[0]);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        self.receipt.update(all_direct_sites=found,caller_window_phases=count,fired_join_boundaries=count*3,
            full176_word_parent_executed=False,original_window_words=8)

    def test_07_original_callbacks_and_removal_registry_chain(self):
        connected={}
        for address,offset,n in ((CB[0],0x17BCE0,8),(CB[1],0x17BD00,11),(CB[2],0x17BD2C,8)):
            connected.update(zip(range(address,address+n*4,4),struct.unpack_from('>%dI'%n,self.rom,offset)))
        visits=set();count=0
        for mode,phase in itertools.product((0,2),(0,8)):
            case=Case((1,11,24,0),mode,real_payload=True);models=[]
            for code in (self.truth,self.raw,self.fitted):
                m=CleanupOracle(code,case,phase,connected=connected).run()
                self.assertEqual(m.trace,reference(case)[0]);self.assertEqual(m.r[2],1)
                self.assertEqual(m.low_packets,[(source.REMOVE,(payload(case,0),)),
                    (0x1518E308,(payload(case,1),)),(source.REMOVE,(payload(case,1),)),
                    (0x1515F10C,(payload(case,2),))])
                models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        self.assertTrue(set(connected)<=visits)
        original={}
        for address,offset,n in ((source.REMOVE,0x196BDC,28),(REGISTRY,0x196B8C,20),(RELEASE,0x196CB4,8)):
            original.update(zip(range(address,address+n*4,4),struct.unpack_from('>%dI'%n,self.rom,offset)))
        visits=set();release_count=0
        for kind,slot_count,handler,n,phase in itertools.product((0,1,2,255),(0,3,128),(0,1),(1,3),(0,8)):
            case=Case((0,)*n,2,kind=kind);models=[]
            for code in (self.truth,self.raw,self.fitted):
                m=CleanupOracle(code,case,phase,connected=original,slot_count=slot_count,handler=handler).run()
                self.assertEqual(m.trace,[(2,i,0)for i in range(n)]);self.assertEqual(m.r[2],1)
                initial=(node(0),node(1),node(0))
                expected=tuple(0x39000+((p-NODES)//0x100)*4 if slot_count==3 and p in m.node_indices else p for p in initial)
                self.assertEqual(tuple(read(m.memory,SLOTS+i*4)for i in range(3)),expected)
                if kind>=2:
                    tail=[p for p in m.low_packets if p[0]in (HANDLER,ALLOC)]
                    self.assertEqual(tail,[(HANDLER,(node(i),))if handler else (ALLOC,(node(i),1))for i in range(n)])
                models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));release_count+=1
        self.assertTrue(set(original)<=visits)
        self.receipt.update(original_callback_phases=count,all27_callback_words=True,
            original_removal_chain_phases=release_count,all28_remove_words=True,all20_registry_words=True,
            all8_release_wrapper_words=True,lower_destructor_allocator_and_payload_calls_bounded=True)

    def test_08_strict_image_negative_controls(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+160]
        predicted=source.predicted_image(before,truth)
        self.assertEqual(predicted,(self.output/'first-linked.elf').read_bytes())
        offsets=(20,source.elf_slot_offset(predicted,source.ENTRY,160),
            source.elf_slot_offset(predicted,0x15001000,4),source.elf_slot_offset(predicted,0x80082B20,4),
            next(at+8 for at,name,_,_ in source.symbol_rows(predicted)if name==source.FUNCTION),
            next(at+4 for at,name,_,_ in source.symbol_rows(predicted)if name=='D_8008ABE8'),
            next(string for _,name,_,string in source.symbol_rows(predicted)if name=='func_1503DF48'))
        for at in offsets:
            bad=bytearray(predicted);bad[at]^=1
            with self.assertRaises(ValueError):
                source.check_image(before,bad,truth)
        for bad in (predicted[:-1],predicted+b'\0'):
            with self.assertRaises(ValueError):
                source.check_image(before,bad,truth)
        self.receipt['strict_image_negatives']=9
