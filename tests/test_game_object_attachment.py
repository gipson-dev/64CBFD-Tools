"""Attachment lists: signed keys, late inputs, callers and bounded allocation closure."""
from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_object_attachment as source
from tools.experiments import game_character_effect_pair as pairs
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
OWNER,ALT_OWNER,OBJECT,ALT_OBJECT,NODE,HEAD,ALT_HEAD=0x30000,0x32000,0x60000,0x61000,0x70000,0x80000,0x82000
ROWS,DESCRIPTORS,CALLBACKS=0x90000,0x8008ABE8,0x8008AB58
NODE_ALLOC,ALLOCATE,HEAP,REGISTER,RELEASE=0x1514EBA4,0x15167A68,0x10003C6C,0x15168A4C,0x1516972C
PROVIDERS=(0x16100000,0x16101000,0x16102000)
KEYS=(0,1,13,14,24,26,27,32767,32768,65535,65536,0x7FFFFFFF,0x80000000,0xABCD001A,0xFFFFFFFF)
SITES=(0x1506CDC8,0x1506CE4C,0x15073404,0x1509D2E8,0x15141F54,0x1514D634,0x1514D7A4,0x1514D8F0,0x1514D9DC,0x1514DA20,
       0x1514DA8C,0x1514DB00,0x1514DB40,0x1514DFB8,0x1514E160,0x1514E2E8,
       0x1514E474,0x1514E54C,0x1514E5A0,0x1514E5FC,0x1514E650,0x1514E6AC,
       0x1514E700,0x1514E75C,0x1514E7B0,0x1514E80C,0x1514EEB4,0x1514EF44,
       0x1514F2EC,0x1514F490,0x1519D618,0x1519E534)
SYMBOLS={'func_1514EBA4':NODE_ALLOC,'func_1516972C':RELEASE,'D_8008ABE8':DESCRIPTORS,'D_8008AB58':CALLBACKS}


def short(value):
    return ((value&65535)^32768)-32768


@dataclass(frozen=True)
class Case:
    object:int=OBJECT
    key:int=13
    allocated:bool=True
    head:bool=True
    callback:int=-1
    alias:int=0
    mode:int=0


def node_address(case):
    return (NODE,OWNER+0x2E0,OWNER+0x2DC,OWNER+0x2F4)[case.alias]


def fixture(case,phase=0,symbols=None):
    s=SYMBOLS if symbols is None else symbols
    m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
    for base in(OWNER,ALT_OWNER,NODE,HEAD,ALT_HEAD):m.update({base+i:0xA5 for i in range(-16,0x340)})
    for i in range(3):put(m,s['D_8008AB58']+4*i,PROVIDERS[i])
    for i,key in enumerate(dict.fromkeys((short(case.key),26))):
        row=ROWS+0x20*i;put(m,s['D_8008ABE8']+4*key,row);put(m,row+2,case.callback,2)
    put(m,OWNER+0x2F4,HEAD if case.head else 0);put(m,ALT_OWNER+0x2F4,HEAD if case.head else 0)
    return m


def effect(memory,case,entered,symbols):
    if case.mode&1:put(memory,OWNER+0x2F4,ALT_HEAD)
    if case.mode&2:
        put(memory,entered,ALT_OBJECT);put(memory,entered+4,ALT_OWNER);put(memory,entered+8,0xABCD001A)
    if case.mode&4:
        for key in dict.fromkeys((short(case.key),26)):
            put(memory,symbols['D_8008ABE8']+4*key,ROWS+0x80);put(memory,ROWS+0x82,2,2)


def reference(initial,case,entered=STACK,symbols=None,chain=False):
    s=SYMBOLS if symbols is None else symbols;m=dict(initial);calls=[]
    if not case.object:return m,calls,0
    calls.append((s['func_1514EBA4'],(case.object,short(case.key)&0xFFFFFFFF,0)))
    put(m,entered,case.object);put(m,entered+4,OWNER);put(m,entered+8,case.key)
    effect(m,case,entered,s)
    node=node_address(case)if case.allocated else 0
    if chain:
        calls.extend(((ALLOCATE,(36,1,32,1,255,1)),(HEAP,(32,1,1,0,1))))
        if node:
            calls.append((REGISTER,(node,36)));m[node+1]=1;m[node+12]=255
            put(m,node+20,0);put(m,node+24,0);put(m,node+16,case.object);put(m,node+28,case.key,2)
    owner=read(m,entered+4);object_word=read(m,entered)
    if node:
        put(m,node+20,read(m,owner+0x2F4));put(m,owner+0x2F4,node)
        following=read(m,node+20);put(m,node+24,0)
        if following:put(m,following+24,node)
    else:
        callback=short(read(m,read(m,s['D_8008ABE8']+4*short(read(m,entered+8)))+2,2))
        calls.append((s['func_1516972C']if callback==-1 else read(m,s['D_8008AB58']+4*callback),(object_word,)))
    return m,calls,node


class AttachmentOracle(TimingOracle):
    def __init__(self,words,memory,case=Case(),phase=0,entry=source.ENTRY,connected=None,symbols=None):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(case.object,OWNER,case.key),connected=connected)
        self.case=case;self.entered=STACK+phase;self.symbols=SYMBOLS if symbols is None else symbols

    def record_call(self,target):
        counts={self.symbols['func_1514EBA4']:3,self.symbols['func_1516972C']:1,ALLOCATE:6,HEAP:5,REGISTER:2,
                **{p:1 for p in PROVIDERS}}
        if target==source.ENTRY:self.entered=self.r[29];args=self.arguments(3)
        elif target in counts:args=self.arguments(counts[target])
        else:raise AssertionError(('Unbounded attachment service',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target in(self.symbols['func_1514EBA4'],HEAP):
            effect(self.memory,self.case,self.entered,self.symbols)
            value=node_address(self.case)if self.case.allocated else 0
        else:
            if self.case.mode&8:put(self.memory,self.entered,0x87654321)
            value=0x87654321
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True;self.r[2]=value


class WindowBoundary(Exception):
    pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==self.end:raise WindowBoundary
        return super().__getitem__(pc)


def controls():
    b=source.SELECTED
    return dict(selected=b,
        wrong_key=b.replace('object, key, 0','object, (u8)key, 0'),
        wrong_extra=b.replace('object, key, 0','object, key, 1'),
        wrong_head=b.replace('owner + 0x2F4','owner + 0x2F0'),
        missing_publish=b.replace('*(GameListNode **)(owner + 0x2F4) = node','*(GameListNode **)(owner + 0x2F4) = NULL'),
        wrong_prev=b.replace('node->prev = NULL','node->prev = node->next'),
        missing_backlink=b.replace('node->next->prev = node;',''),
        wrong_destructor=b.replace('D_8008ABE8[key][1]','D_8008ABE8[key][0]'),
        only_first_callback=b.replace('callback != -1','callback == 0'),
        missing_release=b.replace('func_1516972C(object);',''),
        missing_callback=b.replace('D_8008AB58[callback](object);',''),
        wrong_return=b.replace('return (s32)node;','return object;'))


def native_harness(values):
    owner=values[source.SOURCE].decode();lib=values['conker/src/game_1944C0.c'].decode()
    def extract(text,name):
        scan=text;prefix='GameListNode *'+name
        if prefix in text:
            # Preserve offsets while the shared brace lexer scans a named pointer return.
            replacement='void'+' '*(len(prefix)-len('void*'+name))+'*'+name
            if text.count(prefix)!=1 or len(replacement)!=len(prefix):raise ValueError('Ambiguous node definition')
            scan=text.replace(prefix,replacement,1)
        return text[slice(*source.function_span(scan,name))]
    text=source.HEADERS+'#include "structs.h"\n'+source.DECLARATIONS+'''
void *func_15167A68(s32,s32,s32,s32,u8,u8);
void *func_10003C6C(s32,s32,s32,s32,u8);
void func_15168A4C(void *,s32);
s32 func_1514EC1C(s32,s32,s16);
typedef union {GameListNode node;u8 bytes[36];} NodeStorage;
typedef char node_next[__builtin_offsetof(GameListNode,next)==20?1:-1];
typedef char node_prev[__builtin_offsetof(GameListNode,prev)==24?1:-1];
static NodeStorage pool[2],old;
static u8 *owner;
static s16 rows[30][4],alternate[4];
s16 *D_8008ABE8[30];
static u32 error,heapCalls,registrations,cleanups,failed,mutation,poolIndex;
static s32 objectWord;static s16 keyWord;static s32 cleanupKind;
static void setHead(GameListNode *p){*(GameListNode **)(owner+0x2F4)=p;}
static GameListNode *head(void){return *(GameListNode **)(owner+0x2F4);}
__attribute__((noinline,noclone)) void *func_10003C6C(s32 n,s32 a,s32 b,s32 c,u8 d){
 heapCalls++;if(n!=32||a!=1||b!=1||c||d!=1)error=1;
 if(mutation){setHead(&old.node);if(failed){D_8008ABE8[keyWord]=alternate;alternate[1]=2;cleanupKind=2;}}
 return failed?0:&pool[poolIndex++].node;
}
__attribute__((noinline,noclone)) void func_15168A4C(void *p,s32 kind){
 registrations++;if(p!=&pool[poolIndex-1].node||kind!=36||((u8*)p)[1]!=1)error=1;
}
static void dispose(s32 value,s32 kind){cleanups++;if(value!=objectWord||kind!=cleanupKind)error=1;}
void func_1516972C(s32 value){dispose(value,-1);}
static void destroy0(s32 value){dispose(value,0);}
static void destroy1(s32 value){dispose(value,1);}
static void destroy2(s32 value){dispose(value,2);}
void (*D_8008AB58[])()={destroy0,destroy1,destroy2};
static void initialize(s32 object,s16 key,u32 fail,u32 mutate,u32 existing,s32 callback){
 u32 i,j;objectWord=object;keyWord=key;failed=fail;mutation=mutate;cleanupKind=callback;
 error=heapCalls=registrations=cleanups=poolIndex=0;
 for(i=0;i<0x340;i++)owner[i]=0;
 for(i=0;i<30;i++){D_8008ABE8[i]=rows[i];for(j=0;j<4;j++)rows[i][j]=0;rows[i][0]=1;rows[i][1]=(s16)callback;}
 for(i=0;i<sizeof(pool);i++)((u8*)pool)[i]=0xA5;
 for(i=0;i<sizeof(old);i++)((u8*)&old)[i]=0xA5;
 old.node.next=0;old.node.prev=0;setHead(existing?&old.node:0);
}
typedef s32 (*Attach)(s32,s32,s16);
static int one(Attach f,s32 object,s16 key,u32 fail,u32 mutate,u32 existing,s32 callback){
 s32 result;u32 i;GameListNode *previous;
 initialize(object,key,fail,mutate,existing,callback);previous=head();
 result=f(object,object?(s32)owner:0,key);
 if(!object)return result||heapCalls||registrations||cleanups||head()!=previous?23:0;
 if(mutate)previous=&old.node;
 if(error||heapCalls!=1)return 23;
 if(fail)return result||registrations||cleanups!=1||head()!=previous?23:0;
 if(result!=(s32)&pool[0].node||registrations!=1||cleanups||head()!=&pool[0].node)return 23;
 if(pool[0].node.next!=previous||pool[0].node.prev||pool[0].node.unk10!=object||pool[0].node.unk1C!=key)return 23;
 if(previous&&previous->prev!=&pool[0].node)return 23;
 for(i=0;i<36;i++){
  if(i==1||i==12||(i>=16&&i<30))continue;
  if(pool[0].bytes[i]!=0xA5)return 23;
 }return 0;
}
'''+extract(lib,'func_15167A68')+'\n'+extract(owner,'func_1514EBA4')+'\n'
    for label,body in controls().items():
        if label!='selected'and body==source.SELECTED:raise ValueError('Ineffective native control '+label)
        text+=body.replace(source.FUNCTION,source.FUNCTION+'_'+label)+'\n'
    text+='s32 func_1514EC1C(s32 a,s32 b,s16 c){return func_1514EC1C_selected(a,b,c);}\n'
    text+=pairs.DECLARATIONS+r'''
static u32 pairMode;static u8 *created;static u8 *wantedDescriptor;
u8 D_800A58D0[20],D_800A58E4[20],D_800A58F8[20],D_800A590C[20];
s32 func_1518D1C0(void *p,s32 type,s32 a,s32 b,u8 c,u8 d,void *label){
 if(p!=owner||type!=5||a||b!=1||c!=255||d!=1||label!=wantedDescriptor)error=1;
 return pairMode&1?0:0x60000;
}
s32 func_1515D5F8(s32 a,s32 high,s32 low,s32 type,u8 r,u8 g,u8 b,u8 alpha,s32 x,s32 y){
 u32 address=(u32)(owner+20);if(a!=-32768||high!=(s32)address>>16||low!=(s32)(address&65535)||type!=5||r!=255||g!=255||b!=255||alpha!=255||x||y)error=1;
 return pairMode&2?0:0x61000;
}
typedef struct {s32 index;u8 *actor;u8 identity;} GameEffectRefreshRequest;
struct32 D_8008A0B4[21];
s32 func_1514ECE0(u8 *node,s16 key,u8 **out){if(node||key!=26)error=1;*out=0;return 0;}
u8 *func_15149130(s16 a,s8 b,s8 c,s8 d,u8 e,u8 f,struct37 *g,u8 h,s32 i){
 if(a!=123||b!=-1||c!=-1||d!=-1||e!=1||f!=50||g!=(struct37*)12||h!=255||i!=1)error=1;
 return pairMode?0:created;
}
__attribute__((noinline,noclone)) void *memcpy(void *a,const void *b,u32 n){u32 i;for(i=0;i<n;i++)((u8*)a)[i]=((const u8*)b)[i];return a;}
static void *allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");
 end=p+n;__asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
'''
    for body in pairs.SELECTED.values():text+=body+'\n'
    external=source.recovered_caller(values[source.CALLER_SOURCE].decode())
    text+=extract(external,'func_15141E38')+'\n'
    text+='''int run(void){u32 key,headFlag,mutate,fail,cb,o;static const s32 objects[]={0,1,(s32)0x80000000u,(s32)0x87654321u,-1};
 owner=allocate(0x400);created=allocate(0x100);if(!owner||!created)return 97;
 for(key=0;key<65536;key++)for(headFlag=0;headFlag<2;headFlag++)for(mutate=0;mutate<2;mutate++){
  if(one(func_1514EC1C_selected,0x60000,(s16)key,0,mutate,headFlag,-1))return 10;
  if(one(func_1514EC1C_selected,0,(s16)key,1,mutate,headFlag,-1))return 11;
 }
 for(key=0;key<28;key++)for(o=0;o<5;o++)for(fail=0;fail<2;fail++)for(cb=0;cb<4;cb++)for(mutate=0;mutate<2;mutate++)for(headFlag=0;headFlag<2;headFlag++)
  if(one(func_1514EC1C_selected,objects[o],(s16)key,fail,mutate,headFlag,(s32)cb-1))return 12;
'''
    for label in controls():
        if label=='selected':continue
        text+='''{u32 bad=0;static const u16 keys[]={0,13,26,32767,32768,65535};
 for(key=0;key<6;key++)for(fail=0;fail<2;fail++)for(cb=0;cb<4;cb++)for(headFlag=0;headFlag<2;headFlag++){
  if(fail&&keys[key]>=28)continue;
  if(one(func_1514EC1C_LABEL,0x60000,(s16)keys[key],fail,0,headFlag,(s32)cb-1))bad=1;
 }if(!bad)return 30;}
'''.replace('LABEL',label)
    for name,t in pairs.TARGETS.items():
        text+='''for(pairMode=0;pairMode<4;pairMode++){
 initialize(0x60000,13,0,0,0,-1);wantedDescriptor=D_DESCRIPTOR;NAME(owner);
 if(error||heapCalls!=((pairMode&1?0u:1u)+(pairMode&2?0u:1u))||cleanups)return 41;
 if(poolIndex){GameListNode *last=&pool[poolIndex-1].node;if(head()!=last||last->prev)return 42;
  if(!(pairMode&2)&&last->unk1C!=24)return 43;if(pairMode&2&&last->unk1C!=KEY)return 44;}
}
'''.replace('D_DESCRIPTOR','D_%08X'%t['descriptor']).replace('NAME',name).replace('KEY',str(t['key']))
    text+='''for(pairMode=0;pairMode<2;pairMode++){
 owner=allocate(0x400);if(!owner)return 98;for(key=0;key<0x340;key++)owner[key]=0;
 error=heapCalls=registrations=cleanups=poolIndex=failed=mutation=0;objectWord=(s32)created;keyWord=26;cleanupKind=-1;
 owner[0x3B]=0xE7;D_8008A0B4[3].unk4=123;
 func_15141E38(owner,3);if(error||heapCalls!=(pairMode?0u:1u))return 51;
 if(!pairMode){if(head()!=&pool[0].node||pool[0].node.unk10!=(s32)created||pool[0].node.unk1C!=26)return 52;
 if(*(s32*)(created+0x28)!=3||*(u8**)(created+0x2C)!=owner||created[0x30]!=0xE7)return 53;}
}return 0;}
'''
    return text+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')


class ObjectAttachmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.truth=list(struct.unpack_from('>49I',cls.rom,source.ROM));data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.words=list(struct.unpack_from('>49I',data,fs[source.FUNCTION]['value']));cls.receipt={}

    def compare(self,case,phase=0,chain=False,images=None,entry=source.ENTRY,symbols=None):
        s=SYMBOLS if symbols is None else symbols;memory=fixture(case,phase,s);connected={}
        if chain:
            for at,n in((NODE_ALLOC,30),(ALLOCATE,28)):
                connected.update(zip(range(at,at+4*n,4),struct.unpack_from('>%dI'%n,self.rom,at-0x15000000+0x2D4B0)))
        expected,calls,answer=reference(memory,case,STACK+phase,s,chain)
        models=[AttachmentOracle(w,memory,case,phase,entry,connected,s).run()for w in(images or(self.truth,self.words))]
        public=lambda m:{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
        for model in models:self.assertEqual(public(model.memory),public(expected));self.assertEqual(model.calls,calls);self.assertEqual(model.r[2],answer)
        for model in models[1:]:self.assertEqual(complete(models[0]),complete(model))
        return models[0]

    def test_01_words_callers_owner_actual_Make_and_stub_rejection(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFE0)
        self.assertEqual(source.payload(self.out/'after-owner.o',source.FUNCTION),source.payload(source.original(ROOT,self.out,source.FUNCTION),source.FUNCTION))
        self.assertEqual(sum(map(len,source.payload(self.out/'after-owner.o',source.FUNCTION)[1].values())),6)
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['preserved_neighbors'],q['caller_functions_preserved']),(77,89))
        m=json.loads((self.out/'make-shadow.json').read_text());self.assertEqual([x['actual_Make_commands']for x in m],[3,5]);self.assertTrue(all(x['complete_padded_object_equal']for x in m))
        old,fs=source.link_owner(ROOT,self.out,self.out/'before-owner.o',source.OWNER);self.assertNotEqual(list(struct.unpack_from('>49I',old,fs[source.FUNCTION]['value'])),self.truth)
        self.receipt.update(words=49,frame=32,bindings=6,new_guards=0,compiler_only=True,preserved_neighbors=77,caller_functions_preserved=89,actual_Make_commands=8)

    def test_02_guest_signed_keys_aliases_late_homes_and_all_root_words(self):
        count=0;visits=set()
        for object_word,key,allocated,head,callback,alias,mode,phase in itertools.product((0,OBJECT),KEYS,(False,True),(False,True),(-1,0,1,2),range(4),(0,1,2,4,8,15),(0,8)):
            c=Case(object_word,key,allocated,head,callback,alias,mode);m=self.compare(c,phase);visits.update(m.visits);count+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+196,4))<=visits)
        self.receipt.update(guest_phases=count,all_49_words_visited=True,signed_key_and_callback=True,ordered_aliases_and_late_homes=True,portable_native_alias_or_invalid_table_claimed=False)

    def test_03_native_actual_C_helpers_callers_and_eleven_defined_controls(self):
        c=self.out/'native.c';c.write_text(native_harness(self.values))
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native-'+opt[1:]);p=subprocess.run(native_command(opt)+[str(c),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''),p.stdout+p.stderr)
            p=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''),opt)
        self.receipt.update(native_selected_cases_per_optimization=65536*2*2*2+28*5*2*4*2*2,
            native_optimizations=3,trap_UBSan=True,defined_wrong_C_controls=11,actual_node_and_allocator_C=True,
            actual_C_pair_callers=4,actual_external_C_allocation_path=True,native_complete_allocated_storage=True)

    def test_04_all_original_JAL_argument_windows(self):
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        refs=[0x15000000+i-0x2D4B0 for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal]
        self.assertEqual(refs,list(SITES));self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',source.ENTRY)for i in range(0,len(self.rom),4)))
        phases=0
        for site in SITES:
            start=site-(12 if site==0x1519E534 else 8);code=list(struct.unpack_from('>%dI'%((site+8-start)//4),self.rom,start-0x15000000+0x2D4B0));key=code[-1]&65535
            self.assertEqual(code[-1]>>16,0x2406)
            for object_word,allocated,callback,phase in itertools.product((0,OBJECT),(False,True),(-1,2),(0,8)):
                case=Case(object_word,key,allocated,True,callback);models=[]
                for words in(self.truth,self.words):
                    memory=fixture(case,phase);connected=dict(zip(range(source.ENTRY,source.ENTRY+196,4),words))
                    m=AttachmentOracle(code,memory,case,phase,start,connected)
                    for word in code[:-2]:
                        op,rs,rt,rd=word>>26,word>>21&31,word>>16&31,word>>11&31
                        if op==35 and rt in(4,5):
                            if rs!=29:m.r[rs]=0xA0000
                            put(m.memory,m.r[rs]+(word&65535),object_word if rt==4 else OWNER)
                        elif op==0 and word&63==37 and rd in(4,5)and rt==0:m.r[rs]=object_word if rd==4 else OWNER
                        elif op==40 and rs==29 and word&65535==0x33:m.r[rt]=0xE7
                        else:self.fail(('Unknown original caller argument instruction',hex(site),hex(word)))
                    m.code[site+8]=0;m.code=WindowCode(m.code,m);m.code.end=site+8
                    with self.assertRaises(WindowBoundary):m.run()
                    self.assertEqual(m.calls[0],(source.ENTRY,(object_word,OWNER,key)));models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));phases+=1
        self.receipt.update(original_JAL_sites=32,original_argument_window_phases=phases,full_all_parent_execution_claimed=False)

    def test_05_retained_original_node_and_allocator_chain(self):
        old=self.values['conker/build/conker.us.elf'];visits=set();count=0
        for entry,n in((NODE_ALLOC,30),(ALLOCATE,28)):
            at=source.elf_slot_offset(old,entry,n*4);rom=entry-0x15000000+0x2D4B0;self.assertEqual(old[at:at+4*n],self.rom[rom:rom+4*n])
        for key,allocated,head,callback,mode,phase in itertools.product((13,26,0xFFFF),(False,True),(False,True),(-1,0,2),(0,1,2,4),(0,8)):
            m=self.compare(Case(OBJECT,key,allocated,head,callback,0,mode),phase,True);visits.update(m.visits);count+=1
        for entry,n in((NODE_ALLOC,30),(ALLOCATE,28)):self.assertTrue(set(range(entry,entry+4*n,4))<=visits)
        self.receipt.update(retained_helper_words=58,helper_phases=count,all_58_helper_words_visited=True,heap_registration_and_cleanup_providers_bounded=True)

    def linked(self,obj,entry,symbols,label):
        text,functions,bindings=source.parse_object(obj);asm,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown)
        p=self.out/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
            *['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack_from('>49I',sections(p.with_suffix('.elf'))['.text'][1]))

    def test_06_rebased_real_objects_and_fired_root_fault_prefixes(self):
        links=phases=cuts=0
        objects=(source.original(ROOT,self.out,source.FUNCTION),self.out/'qualified-padded.o',self.out/'make-shadow-target/src/game/generated_179F30.c.o')
        for i,(entry,symbols)in enumerate(((source.ENTRY,SYMBOLS),(0x18017FFC,dict(zip(SYMBOLS,(0x18207FFC,0x18308000,0x81017FF0,0x8200FFF0)))),(0x1A028000,dict(zip(SYMBOLS,(0x1B047FFC,0x1B05FFFC,0x83008000,0x84017FFC)))))):
            images=[self.linked(obj,entry,symbols,'rebase-%d-%d'%(i,j))for j,obj in enumerate(objects)];links+=3
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for key,allocated,alias,mode,phase in itertools.product((13,0xFFFF),(False,True),range(4),(0,15),(0,8)):
                self.compare(Case(OBJECT,key,allocated,True,2,alias,mode),phase,images=images,entry=entry,symbols=symbols);phases+=1
        for allocated,alias,mode,phase in itertools.product((False,True),range(4),(0,15),(0,8)):
            case=Case(OBJECT,13,allocated,True,2,alias,mode);memory=fixture(case,phase);done=AttachmentOracle(self.truth,memory,case,phase).run()
            for cut in range(done.root_accesses):
                models=[AttachmentOracle(w,memory,case,phase)for w in(self.truth,self.words)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=phases,fired_root_fault_prefixes=cuts,portable_C_fault_claimed=False)

    def test_07_strict_image_and_corruption_controls(self):
        old=self.values['conker/build/conker.us.elf'];truths=source.truths(self.values);wanted=source.predicted_image(old,truths)
        positions=[0,len(wanted)-1,source.elf_slot_offset(old,source.ENTRY,196),source.elf_slot_offset(old,0x15141E38,4),source.elf_slot_offset(old,0x80082B20,4)]
        positions.extend(at+8 for at,name,_,_ in source.symbol_rows(old)if name in(source.FUNCTION,'func_1514E508'))
        for pos in positions:
            wrong=bytearray(wanted);wrong[pos]^=1
            with self.assertRaises(ValueError):source.check_image(old,bytes(wrong),truths)
        with self.assertRaises(ValueError):source.check_image(old,wanted[:-1],truths)
        bad=dict(truths);bad[source.FUNCTION]=bytes(196)
        with self.assertRaises(ValueError):source.predicted_image(old,bad)
        self.receipt.update(strict_image_negatives=len(positions)+2,metadata_exclusions=0)

    def test_08_frozen_current_inputs_and_installed_identity(self):
        source.check_inputs(ROOT,self.out,self.installed)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
        self.receipt.update(focused_inputs=30,guard_manifest_byte_identical=True,installed=self.installed)


if __name__=='__main__':unittest.main()
