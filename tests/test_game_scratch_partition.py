"""Scratch-array partition: wrapping words, cursor publications and legacy owner gates."""

from dataclasses import dataclass, replace
from pathlib import Path
import csv
import io
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_scratch_partition as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
WRAPPER,SELECTOR=0x1510F800,0x150A49F4
CALLER,CALLER_ROM=0x15003668,0x30B18
CURSOR,COUNT,INDEX=0x800B0DC0,0x800DBE38,0x800DBE50
A,B,C,D,F=0x800DBDD8,0x800DBDE8,0x800DBDF8,0x800DBE08,0x800DBE18
PUBLISH=(0x800DBE3C,0x800DBE40,0x800DBE44,0x800DBE48,0x800DBE4C)
SYMBOLS=dict(D_800B0DC0=CURSOR,D_800DBE38=COUNT,D_800DBE50=INDEX,
    D_800DBDD8=A,D_800DBDE8=B,D_800DBDF8=C,func_1510F800=WRAPPER)
CURSORS=(0,1,2,3,7,0x7FFFFFFE,0x7FFFFFFF,0x80000000,0xFFFFFFFC,0xFFFFFFFD,0xFFFFFFFE,0xFFFFFFFF,0x12345679)
COUNTS=(0,1,2,3,4,0x15555555,0x2AAAAAAA,0x7FFFFFFF,0x80000000,0xFFFFFFFE,0xFFFFFFFF)
ACTORS,STREAMS=0x30000,0x800B0E00
SCENE_COUNT,SCENE_BASE=0x800DBEF0,0x800DBEF4
INIT,START,SCAN,RENDER,END,PACK=0x15001970,0x150026C4,0x15002724,0x15001460,0x150026E8,0x15002878


@dataclass(frozen=True)
class Case:
    cursor:int=0x12345679
    count:int=3
    index:int=2
    mode:int=0
    alias:object=None
    seed:int=0xA5


def corpus():
    for cursor,count,index in itertools.product(CURSORS,COUNTS,range(4)):
        yield Case(cursor,count,index,(cursor+count+index)&3,seed=(cursor^count)&255)
    for i in range(256):
        yield Case((i*1664525+1013904223)&0xFFFFFFFF,(i*22695477+1)&0xFFFFFFFF,i&3,i&3,seed=i)
    for index,count,mode in itertools.product((4,5,8,12,16,20,24,0xFFFFFFFF,0x40000000,0x80000000),
            (2,0xFFFFFFFF),(0,3)):
        yield Case(index=index,count=count,mode=mode)


def anchors(case,base=None):
    s=dict(base or SYMBOLS)
    if case.alias=='cursor-count':s['D_800B0DC0']=s['D_800DBE38']
    elif case.alias=='cursor-index':s['D_800B0DC0']=s['D_800DBE50']
    elif case.alias=='count-index':s['D_800DBE38']=s['D_800DBE50']
    return s


def cell(base,index):return (base+((index<<2)&0xFFFFFFFF))&0xFFFFFFFF


def fixture(case,symbols=None):
    s=anchors(case,symbols)
    m={STACK+i:(i*17+0xA5)&255 for i in range(-0x800,0x400)}
    for base,size in ((A-64,0x300),(s['D_800DBDD8']-64,0x300),(s['D_800B0DC0']-16,36),
            (s['D_800DBE38']-16,64),(s['D_800DBE50']-16,32),(STREAMS-16,64),(ACTORS-16,0x300),
            (0x800D2C20,96),(0x800D3300,16),(0x800D3660,24),(0x80038090,24)):
        for i in range(size):m.setdefault(base+i,(i*13+case.seed)&255)
    for array in (s['D_800DBDD8'],s['D_800DBDE8'],s['D_800DBDF8'],D,F):
        for i in range(4):put(m,array+i*4,(case.seed*0x01010101+array+i*0x1234567)&0xFFFFFFFF)
    put(m,s['D_800B0DC0'],case.cursor);put(m,s['D_800DBE38'],case.count);put(m,s['D_800DBE50'],case.index)
    put(m,SCENE_COUNT,0);put(m,SCENE_BASE,ACTORS);put(m,0x8003809C,0x80401000)
    put(m,0x800B0DE4,0)
    put(m,STREAMS,0x1000);put(m,STREAMS+12,0x1100)
    for i in range(3):
        put(m,ACTORS+i*0xA0+0x1C,0x2000+i*0x100)
        m[ACTORS+i*0xA0+0x4F]=(0,0x20,0x40)[i]
    return m


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x800<=a<STACK+0x400}


def packet(memory,index,s):
    return (index,read(memory,s['D_800B0DC0']),read(memory,s['D_800DBE38']),
        read(memory,s['D_800DBE50']),*(read(memory,s[name]+i*4)
        for name in ('D_800DBDD8','D_800DBDE8','D_800DBDF8')for i in range(4)))


def select(memory,index,s):
    for base,out in zip((s['D_800DBDD8'],s['D_800DBDE8'],s['D_800DBDF8'],D,F),PUBLISH):
        put(memory,out,read(memory,cell(base,index)))
    put(memory,s['D_800DBE50'],index)


def effects(memory,index,mode,s):
    if mode&1:
        put(memory,s['D_800DBE38'],0xAABBCCDD);put(memory,s['D_800DBE50'],(index+1)&3)
    if mode&2:
        put(memory,s['D_800B0DC0'],read(memory,s['D_800B0DC0'])^0x5A5A5A5A)
        put(memory,s['D_800DBDE8']+((index+1)&3)*4,0x87654321)


def reference(case,symbols=None,real=False,memory=None):
    s=anchors(case,symbols);m=dict(fixture(case,s) if memory is None else memory)
    cursor=((read(m,s['D_800B0DC0'])+3)&0xFFFFFFFF)&~3
    put(m,s['D_800B0DC0'],cursor)
    count=read(m,s['D_800DBE38']);index=read(m,s['D_800DBE50'])
    put(m,cell(s['D_800DBDD8'],index),cursor)
    cursor=(cursor+count*12)&0xFFFFFFFF;put(m,s['D_800B0DC0'],cursor)
    put(m,cell(s['D_800DBDE8'],index),cursor)
    cursor=(cursor+count*8)&0xFFFFFFFF;put(m,s['D_800B0DC0'],cursor)
    put(m,cell(s['D_800DBDF8'],index),cursor)
    cursor=(cursor+count*4)&0xFFFFFFFF;put(m,s['D_800B0DC0'],cursor)
    observed=packet(m,index,s);calls=[(s['func_1510F800'],(index,))]
    select(m,index,s)
    if real:calls.append((SELECTOR,(index,)))
    else:effects(m,index,case.mode,s)
    put(m,s['D_800DBE38'],0)
    return m,calls,[observed]


def weight(stream):return {0x1000:3,0x1100:5,0x2000:7,0x2100:11,0x2200:13}[stream]


def boundary_effect(memory,target,args,s):
    if target==START:
        put(memory,COUNT,0);select(memory,args[0],s)
    elif target in (SCAN,RENDER):put(memory,COUNT,(read(memory,COUNT)+weight(args[0]))&0xFFFFFFFF)
    elif target==END:
        put(memory,cell(F,args[0]),read(memory,COUNT));put(memory,PUBLISH[4],read(memory,COUNT))
        put(memory,0x800B0DE4,(read(memory,0x800B0DE4)+read(memory,COUNT))&0xFFFFFFFF)
    elif target not in (INIT,PACK):raise AssertionError(('Unknown caller boundary',hex(target)))


def caller_reference(case,memory):
    s=SYMBOLS;m=dict(memory);calls=[];observations=[]
    def call(target,*args):
        calls.append((target,args))
        if target==WRAPPER:
            observations.append(packet(m,args[0],s));calls.append((SELECTOR,args));select(m,args[0],s)
        else:boundary_effect(m,target,args,s)
    def partition():
        nonlocal m
        calls.append((source.ENTRY,()))
        m,more,seen=reference(replace(case,mode=0),real=True,memory=m)
        calls.extend(more);observations.extend(seen)
    m[0x800DBE62]=0;call(INIT);m[0x800D2C68]=0
    call(START,0);call(SCAN,read(m,STREAMS));partition();call(RENDER,read(m,STREAMS));call(END,0)
    call(START,1);call(SCAN,read(m,STREAMS+12));partition();call(RENDER,read(m,STREAMS+12));call(END,1)
    call(START,2)
    count=read(m,SCENE_COUNT);base=read(m,SCENE_BASE)
    for i in range(count):
        if m[base+i*0xA0+0x4F]&0x60!=0x20:call(SCAN,read(m,base+i*0xA0+0x1C))
    partition();m[0x800D2C68]=1;put(m,0x800D2C2C,0)
    for i in range(count):
        obj=base+i*0xA0
        if m[obj+0x4F]&0x60!=0x20:
            old=read(m,COUNT);put(m,obj+0x58,old,2)
            call(RENDER,read(m,obj+0x1C));put(m,obj+0x56,read(m,COUNT)-old,2)
        else:put(m,obj+0x58,0,2);put(m,obj+0x56,0,2)
    call(END,2);m[0x800D2C68]=0;put(m,0x800D3300,0);put(m,0x800D3304,read(m,PUBLISH[0])<<8)
    call(WRAPPER,0);call(PACK)
    base=read(m,0x8003809C);put(m,0x800D3668,base);put(m,0x800D366C,base+((0x31+7)&~7))
    call(WRAPPER,2)
    return m,calls,observations


class PartitionOracle(TimingOracle):
    def __init__(self,words,case,phase=0,symbols=None,entry=source.ENTRY,connected=None,
            real=False,memory=None):
        self.case,self.targets,self.real=case,anchors(case,symbols),real
        self.visits=set();self.packets=[]
        super().__init__(words,fixture(case,self.targets)if memory is None else memory,
            phase=phase,entry=entry,arguments=(0x12345678,0xAABBCCDD,0x87654321),connected=connected)

    def execute(self,word):
        self.visits.add(self.current_pc);super().execute(word)

    def record_call(self,target):
        if target in (self.targets['func_1510F800'],SELECTOR,START,SCAN,RENDER,END):args=(self.r[4],)
        elif target in (source.ENTRY,INIT,PACK):args=()
        else:raise AssertionError(('Unbounded partition call',hex(target)))
        if target==self.targets['func_1510F800']:self.packets.append(packet(self.memory,self.r[4],self.targets))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        args=self.calls[-1][1]
        if target==self.targets['func_1510F800']:
            select(self.memory,args[0],self.targets);effects(self.memory,args[0],self.case.mode,self.targets)
        else:boundary_effect(self.memory,target,args,self.targets)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.hi,self.lo=0x87654321,0x12345678
        self.r[2]=0x31 if target==PACK else 0x87654321


def native_layout():
    return [None]*4+[CURSOR,COUNT,INDEX]+[None]*4+list(range(A,A+16,4))+[None]*4+list(range(B,B+16,4))+[
        None]*4+list(range(C,C+16,4))+[None]*4+list(PUBLISH)+list(range(D,D+16,4))+list(range(F,F+16,4))+[None]*4


def native_harness(body,cases):
    layout=native_layout();rows=[]
    for c in cases:
        initial=fixture(c);expected,_,seen=reference(c)
        def words(memory):return [read(memory,a)if a is not None else 0xCA000000+i for i,a in enumerate(layout)]
        rows.append('{{%s},{%s},{%s},%d}'%(','.join('0x%Xu'%v for v in words(initial)),
            ','.join('0x%Xu'%v for v in words(expected)),','.join('0x%Xu'%v for v in seen[0]),c.mode))
    return """typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef struct{u32 fence0[4];s32 cursor,count,index;u32 fence1[4];s32 a[4];u32 fence2[4];
 s32 b[4];u32 fence3[4];s32 c[4];u32 fence4[4];u32 pub[5],desc[4],fields[4],fence5[4];}State;
typedef char size_check[sizeof(State)==""" + str(len(layout)*4) + """?1:-1];
static State state;
#define D_800B0DC0 state.cursor
#define D_800DBE38 state.count
#define D_800DBE50 state.index
#define D_800DBDD8 state.a
#define D_800DBDE8 state.b
#define D_800DBDF8 state.c
typedef struct{u32 initial["""+str(len(layout))+"""],expected["""+str(len(layout))+"""],packet[16],mode;}Case;
static const Case cases[]={"""+',\n'.join(rows)+"""};
static const Case*c;static u32 error,calls;
__attribute__((noinline)) void func_1510F800(s32 context){u32 i,seen[16],index=(u32)context;
 if(calls++||index>3){error=23;return;}
 seen[0]=index;seen[1]=(u32)state.cursor;seen[2]=(u32)state.count;seen[3]=(u32)state.index;
 for(i=0;i<4;i++){seen[4+i]=(u32)state.a[i];seen[8+i]=(u32)state.b[i];seen[12+i]=(u32)state.c[i];}
 for(i=0;i<16;i++)if(seen[i]!=c->packet[i])error=23;
 state.pub[0]=(u32)state.a[index];state.pub[1]=(u32)state.b[index];state.pub[2]=(u32)state.c[index];
 state.pub[3]=state.desc[index];state.pub[4]=state.fields[index];state.index=context;
 if(c->mode&1){state.count=(s32)0xAABBCCDDu;state.index=(s32)((index+1)&3);}
 if(c->mode&2){state.cursor=(s32)((u32)state.cursor^0x5A5A5A5Au);state.b[(index+1)&3]=(s32)0x87654321u;}
}
"""+body+"""
static void(*volatile callback)(void)=func_15002754;
static int run(void){u32 n,i,j;u8*p=(u8*)&state;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];calls=error=0;
  for(i=0;i<sizeof(State)/4;i++)for(j=0;j<4;j++)p[4*i+j]=(u8)(c->initial[i]>>(8*j));
  callback();if(calls!=1||error)return 23;
  for(i=0;i<sizeof(State)/4;i++)for(j=0;j<4;j++)if(p[4*i+j]!=(u8)(c->expected[i]>>(8*j)))return 23;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class ScratchPartitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD
        cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.output)
        else:
            source.freeze(ROOT,cls.output)
            if not (cls.output/'first-link.json').exists():
                source.qualify(ROOT,cls.output);source.make_shadow(ROOT,cls.output);source.predict(ROOT,cls.output)
        cls.values=source.snapshot(cls.output);cls.rom=cls.values['conker/conker.us.bin']
        cls.obj,diag=source.compile_owner(ROOT,cls.output,
            '#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        data,fs=source.link_owner(ROOT,cls.output,cls.obj,source.OWNER)
        cls.raw=list(struct.unpack_from('>41I',data,fs[source.FUNCTION]['value']))
        data,fs=source.link_owner(ROOT,cls.output,cls.output/'qualified-padded.o',source.OWNER)
        cls.fitted=list(struct.unpack_from('>41I',data,fs[source.FUNCTION]['value']))
        cls.truth=list(struct.unpack_from('>41I',cls.rom,source.ROM))
        cls.cases=list(corpus());cls.native_cases=[c for c in cls.cases if c.alias is None and c.index<4]
        cls.connected={WRAPPER+i*4:w for i,w in enumerate(struct.unpack_from('>8I',cls.rom,0x13CCB0))}
        cls.connected.update({SELECTOR+i*4:w for i,w in enumerate(struct.unpack_from('>40I',cls.rom,0xD1EA4))})
        cls.receipt=dict(installed=cls.installed,cases=len(cls.cases),native_cases=len(cls.native_cases),guards=10)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('scratch partition qualification:',cls.receipt)

    def test_01_full_guarded_extent_bindings_legacy_owner_and_actual_old_C(self):
        raw,bindings=source.payload(self.obj);fitted,fit_bindings=source.normalized(raw,bindings)
        self.assertEqual((len(raw),self.raw[0]),(164,0x27BDFFE8));self.assertEqual(self.truth,self.fitted)
        self.assertEqual(sum(map(len,bindings.values())),15)
        self.assertEqual(source.payload(source.original(ROOT,self.output)),(fitted,fit_bindings))
        self.assertEqual(source.payload(self.output/'qualified-padded.o'),(fitted,fit_bindings))
        self.assertEqual([i*4 for i,(a,b)in enumerate(zip(self.raw,self.truth))if a!=b],[r[0]for r in source.GUARDS])
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.ENTRY,164)
        self.assertEqual(sum(a!=b for a,b in zip(struct.unpack_from('>41I',old,at),self.truth)),38)
        q=json.loads((self.output/'qualification.json').read_text());self.assertEqual(q['preserved_neighbors'],25)
        self.assertEqual(json.loads((self.output/'make-shadow.json').read_text())['actual_Make_commands'],5)
        self.receipt.update(words=41,frame=24,bindings=15,compiler_only=False,raw_differences=10,
            preserved_neighbors=25,old_compiled_size=152,new_size=164,actual_Make_commands=5)

    def compare(self,c,phase=0,real=False,symbols=None,images=None,entry=source.ENTRY):
        expected,calls,seen=reference(c,symbols,real);models=[]
        for words in images or (self.truth,self.raw,self.fitted):
            m=PartitionOracle(words,c,phase,symbols,entry,self.connected if real else None,real).run()
            self.assertEqual((public(m.memory),m.calls,m.packets),(public(expected),calls,seen))
            self.assertEqual(m.r[29],STACK+phase);models.append(m)
        self.assertEqual(complete(models[0]),complete(models[-1]))
        if real:
            actual=list(complete(models[1]));registers=list(actual[0]);registers[5],registers[6]=registers[6],registers[5];actual[0]=registers
            self.assertEqual(complete(models[0]),tuple(actual))
        else:self.assertEqual(complete(models[0]),complete(models[1]))
        return models[0]

    def test_02_full_model_modular_words_captured_values_and_guest_aliases(self):
        visits=set();aliases=0
        for c,phase in itertools.product(self.cases,(0,8)):
            m=self.compare(c,phase);visits.update(m.visits);aliases+=int(c.alias is not None or c.index>3)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+164,4))<=visits)
        self.receipt.update(model_phases=len(self.cases)*2,guest_only_phases=aliases,
            all41_target_words_executed=True,wrapping_word_math=True,portable_OOB_or_global_alias_claimed=False)

    def native(self,body,label,opt='-O2'):
        path=self.output/(label+opt+'.c');exe=path.with_suffix('.elf')
        path.write_text(native_harness(body,self.native_cases))
        subprocess.run(['gcc','-m32','-std=c99',opt,'-fno-pie','-no-pie','-nostdlib','-fno-stack-protector',
            '-fno-builtin','-mstackrealign','-fsanitize=undefined','-fsanitize-undefined-trap-on-error',
            '-Werror=implicit-function-declaration','-Wl,-e,_start',str(path),'-o',str(exe)],capture_output=True,check=True)
        return subprocess.run([str(exe)],capture_output=True).returncode

    def test_03_native32_defined_unsigned_wrap_and_effective_controls(self):
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(source.SELECTED,'native',opt),0)
        controls={
            'wrong-align-bias':source.SELECTED.replace('+ 3U','+ 2U'),
            'wrong-align-mask':source.SELECTED.replace('& ~3U','& ~7U'),
            'wrong-first-size':source.SELECTED.replace('count * 12U','count * 8U'),
            'wrong-second-size':source.SELECTED.replace('count * 8U','count * 4U'),
            'wrong-third-size':source.SELECTED.replace('count * 4U','count * 8U'),
            'wrong-first-base':source.SELECTED.replace('D_800DBDD8[index] = D_800B0DC0','D_800DBDD8[index] = 0'),
            'wrong-second-base':source.SELECTED.replace('D_800DBDE8[index] = D_800B0DC0','D_800DBDE8[index] = 0'),
            'wrong-third-base':source.SELECTED.replace('D_800DBDF8[index] = D_800B0DC0','D_800DBDF8[index] = 0'),
            'wrong-context':source.SELECTED.replace('func_1510F800(index)','func_1510F800(0)'),
            'early-count-clear':source.SELECTED.replace('    func_1510F800(index);','    D_800DBE38 = 0;\n    func_1510F800(index);'),
            'missing-post-clear':source.SELECTED.replace('    D_800DBE38 = 0;',''),
        }
        for name,body in controls.items():
            self.assertNotEqual(body,source.SELECTED);self.assertEqual(self.native(body,name),23,name)
        self.assertNotEqual(self.native(source.BEFORE_BODY,'old-signed-C'),0)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,compiled_semantic_negatives=len(controls),
            signed_overflow_predecessor_rejected=True,native_numeric_addresses_not_heap_claims=True,typed_fenced_arrays=True)

    def test_04_actual_eight_word_wrapper_and_forty_word_handwritten_entry(self):
        visits=set();count=0
        cases=[Case(cursor=cursor,count=n,index=i)for cursor,n,i in itertools.product(
            (0,3,0x7FFFFFFF,0xFFFFFFFE),(0,1,0xFFFFFFFF),range(4))]
        for c,phase in itertools.product(cases,(0,8)):
            m=self.compare(c,phase,real=True);visits.update(m.visits);count+=1
        self.assertTrue(set(self.connected)<=visits)
        self.receipt.update(real_chain_phases=count,all8_wrapper_and40_selector_words=True,
            selector_66_word_slot_not_claimed=True,following_handwritten_continuation_excluded=True,
            void_return_no_value_assumed=True,raw_private_a1_a2_swap_explicit=True)

    def test_05_complete_142_word_caller_all_three_sites_and_bounded_providers(self):
        rows=list(csv.DictReader((ROOT/'conker/progress.csv').open()))
        syms=load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'));add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],syms)
        found=[]
        for row in rows:
            if row['version']!='us':continue
            entry=function_vram(row,syms);va,off=DEFAULT_SEGMENTS['us'][row['section']]
            code=struct.unpack_from('>%dI'%row['_retail_nwords'],self.rom,entry-va+off)
            found.extend((row['function'],entry+i*4)for i,w in enumerate(code)if w==0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual(found,[('func_15003668',0x150036BC),('func_15003668',0x150036E4),('func_15003668',0x15003768)])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==struct.pack('>I',source.ENTRY)],[])
        caller=list(struct.unpack_from('>142I',self.rom,CALLER_ROM));count=0
        for number,flags,cursor,phase in itertools.product((0,1,3),(0,0x20,0x40,0x60),(0,0xFFFFFFFE),(0,8)):
            c=Case(cursor=cursor);memory=fixture(c)
            put(memory,SCENE_COUNT,number)
            for i in range(3):memory[ACTORS+i*0xA0+0x4F]=flags
            expected,calls,seen=caller_reference(c,memory);models=[]
            for words in (self.truth,self.raw,self.fitted):
                connected=dict(self.connected);connected.update({source.ENTRY+i*4:w for i,w in enumerate(words)})
                m=PartitionOracle(caller,c,phase,entry=CALLER,connected=connected,real=True,memory=memory).run()
                self.assertEqual((public(m.memory),m.calls,m.packets),(public(expected),calls,seen))
                self.assertEqual(m.r[29],STACK+phase);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        self.receipt.update(all_three_direct_sites=found,full_caller_words=142,full_caller_phases=count,
            original48_word_selector_chain=True,init_scan_render_end_pack_providers_bounded=True)

    def test_06_closed_register_cycle_guard_prefix_and_effective_controls(self):
        raw,bindings=source.payload(self.obj);fitted,_=source.normalized(raw,bindings)
        def swap(word):
            op,fn=word>>26,word&63
            fields=(21,16,11)if op==0 and fn in (0,33,35)else (21,16)if op in (9,15,35,43)else ()
            out=word
            for shift in fields:
                value=word>>shift&31
                if value in (5,6):out=(out&~(31<<shift))|((11-value)<<shift)
            return out
        self.assertEqual(b''.join(struct.pack('>I',swap(w))for w in struct.unpack('>41I',raw)),fitted)
        prefix=self.values['conker/retail_word_patches.us.csv'];guards=source.guard_bytes(self.values)
        self.assertTrue(guards.startswith(prefix));self.assertEqual(guards.count(b'\n')-prefix.count(b'\n'),10)
        suffix=list(csv.DictReader(io.StringIO(prefix.splitlines()[0].decode()+'\n'+guards[len(prefix):].decode())))
        controls=0
        for i,row in enumerate(suffix):
            changed=bytearray(raw);changed[int(row['offset'],0)]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(changed),bindings)
            for field in ('expected','expected_relocations'):
                rows=[dict(r)for r in suffix]
                rows[i][field]='0x%08X'%(int(rows[i][field],0)^1)if field=='expected'else 'R_MIPS_HI16:wrong_symbol'
                text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=list(rows[0]),lineterminator='\n')
                writer.writerows(rows);path=self.output/('bad-guard-%d-%s.csv'%(i,field));path.write_bytes(prefix+text.getvalue().encode())
                with self.assertRaises(ValueError):
                    source.pad_c_object.emit_padded_assembly(self.output/'after-owner.o',ROOT/'conker/retail_layout.us.txt',
                        source.OWNER,word_patches_path=path)
                controls+=1
            rows=[dict(r)for r in suffix];rows[i]['replacement']='0x%08X'%(int(rows[i]['replacement'],0)^1)
            text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=list(rows[0]),lineterminator='\n');writer.writerows(rows)
            manifest=self.output/('bad-replacement-%d.csv'%i);manifest.write_bytes(prefix+text.getvalue().encode())
            asm=self.output/('bad-replacement-%d.s'%i);obj=asm.with_suffix('.o')
            asm.write_text('.include "asm_processor_prelude.inc"\n'+source.pad_c_object.emit_padded_assembly(
                self.output/'after-owner.o',ROOT/'conker/retail_layout.us.txt',source.OWNER,word_patches_path=manifest))
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(ROOT/'conker/include'),
                '-o',str(obj),str(asm)],capture_output=True,check=True)
            data,fs=source.link_owner(ROOT,self.output,obj,source.OWNER)
            self.assertNotEqual(data[fs[source.FUNCTION]['value']:fs[source.FUNCTION]['value']+164],self.rom[source.ROM:source.ROM+164])
            controls+=1
        self.receipt.update(guard_controls=controls,raw_word_controls=10,closed_a1_a2_cycle=True,old_guard_prefix_preserved=True)

    def test_07_independent_GNU_rebases_and_all_target_fault_prefixes(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        original=source.original(ROOT,self.output);count=0
        for index,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000,0x18027FFC,0x1A038000,0x18037FFC)):
            symbols=dict(SYMBOLS) if index==0 else {name:(0x80348000+index*0x100000+{
                'D_800B0DC0':0,'D_800DBE38':0x300,'D_800DBE50':0x318,'D_800DBDD8':0x2A0,
                'D_800DBDE8':0x2B0,'D_800DBDF8':0x2C0}[name]) for name in SYMBOLS if name!='func_1510F800'}
            if index:symbols['func_1510F800']=0x15197FFC+index*0x10000
            if index==3:symbols['D_800B0DC0']=symbols['D_800DBE38']
            if index==4:symbols['D_800B0DC0']=symbols['D_800DBE50']
            if index==5:symbols['D_800DBE38']=symbols['D_800DBE50']
            images=[]
            for label,obj in (('original',original),('raw',self.obj),('fitted',self.output/'qualified-padded.o')):
                data,fs,rs=source.parse_object(obj);text,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,symbols)
                self.assertEqual(unknown,[]);stem=self.output/('rebase-%d-%s'%(index,label))
                asm=stem.with_suffix('.s');compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                asm.write_text(text);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>41I',sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[2]);self.assertEqual(sum(a!=b for a,b in zip(images[0],images[1])),10)
            for mode,cursor,phase in itertools.product(range(4),(0,0xFFFFFFFF),(0,8)):
                self.compare(Case(cursor=cursor,mode=mode),phase,symbols=symbols,images=images,entry=entry);count+=1
        prefixes=0
        for c,phase in itertools.product((Case(),Case(index=16),Case(index=24)),(0,8)):
            good=PartitionOracle(self.truth,c,phase).run()
            for cut in range(good.root_accesses):
                models=[PartitionOracle(w,c,phase)for w in (self.truth,self.fitted)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut)
                self.assertEqual(complete(models[0]),complete(models[1]));prefixes+=1
        self.assertGreater(prefixes,0)
        self.receipt.update(independent_GNU_links=18,rebase_phases=count,bindings_rebased=15,
            three_symbol_alias_rebase_sets=True,
            target_fault_prefixes=prefixes,portable_C_faults_or_hardware_parity_claimed=False)

    def test_08_strict_whole_image_and_frozen_input_history(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+164]
        predicted=source.predicted_image(before,truth);source.check_image(before,predicted,truth)
        at=source.elf_slot_offset(before,source.ENTRY,164)
        for offset in (0,at-1,at,at+160,at+164,len(before)-1):
            wrong=bytearray(predicted);wrong[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        with self.assertRaises(ValueError):source.check_image(before,predicted[:-1],truth)
        for name,wanted in source.INPUTS.items():
            old=(self.output/('before-'+name.replace('/','_'))).read_bytes();self.assertEqual(source.digest(old),wanted)
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else (
                predicted if self.installed and name=='conker/build/conker.us.elf'else (
                source.guard_bytes(self.values)if self.installed and name=='conker/retail_word_patches.us.csv'else old))
            self.assertEqual((ROOT/name).read_bytes(),expected)
        self.assertEqual(source.digest((self.output/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(strict_image_negatives=7,live_inputs=len(source.INPUTS),frozen_padded_object_pinned=True)
