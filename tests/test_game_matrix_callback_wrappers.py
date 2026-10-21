"""SDK command order, opaque callbacks, actual callers and strict wrapper images."""

from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_matrix_callback_wrappers as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command

ROOT=Path(__file__).resolve().parents[2]
BUFFER,OTHER,ROWS=0x30000,0x34000,(0x28000,0x28100)
PROVIDER,LAYER,OUT,INDEX,DISABLED=0x152F0000,0x151674F8,0x1517D7B0,0x800BE9F0,0x800BE616
SYMBOLS=dict(D_80089470=0x80089470,D_800B0DF0=0x800B0DF0,D_8008CD74=0x8008CD74,D_8008CD7C=0x8008CD7C)
VIEWS=(0,1,0xFFFFFFFF,0xFFFF8000,0x7FFF,0x80000000,0x7FFFFFFF,0xABCD8001)


@dataclass(frozen=True)
class Case:
    bank:int=0
    selector:int=1
    mode:int=0
    view:int=0xFFFFFFFF
    unused:int=0x12345678
    delta:int=8
    caller:int=0
    disabled:int=0
    alias:int=0


def name_of(case):
    return source.FUNCTIONS[case.bank]


def symbols(values=None):
    return dict(values or SYMBOLS)


def target_of(case, selector):
    return PROVIDER+case.bank*0x1000+selector*4


def fixture(case,phase=0,anchors=None):
    s=symbols(anchors);m={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
    for base,length in ((BUFFER,512),(OTHER,256),(ROWS[0],256),(ROWS[1],256),
                        (s['D_80089470'],64),(s['D_800B0DF0']-8,20),
                        (s[source.TARGETS[name_of(case)]['table']],1024),(INDEX,4),(DISABLED,1)):
        for i in range(length):m.setdefault(base+i,0xA5)
    for row in ROWS:m[row+12]=m[row+13]=case.selector
    row=ROWS[0]
    if case.alias==2:row=STACK+phase+4-source.TARGETS[name_of(case)]['byte']
    put(m,s['D_800B0DF0'],row)
    table=s[source.TARGETS[name_of(case)]['table']]
    for i in range(256):put(m,table+i*4,target_of(case,i))
    put(m,INDEX,case.unused);m[DISABLED]=case.disabled
    return m


def buffer_of(case):
    return ROWS[0] if case.alias==1 else BUFFER+16


def public(memory):
    return {a:v for a,v in memory.items()if not STACK-0x400<=a<STACK+0x100}


def signed16(value):
    return ((value&65535)^32768)-32768


def emit(memory, address, first, second):
    put(memory,address,first);put(memory,address+4,second)
    return address+8


def log_event(kind,args,memory):
    if kind>=0x1000:
        cursor,view=args
        return [kind,cursor,view,0,read(memory,cursor-16),read(memory,cursor-12),
                read(memory,cursor-8),read(memory,cursor-4)]
    if kind==2:
        cursor,mode,view,ordinal=args
        return [2,cursor,mode,view,ordinal,0,0,0]
    pointer,mode=args
    return [3,read(memory,pointer),mode,0,0,0,0,0]


def effect(case,memory,kind,args,sp,anchors):
    s=symbols(anchors);byte=source.TARGETS[name_of(case)]['byte']
    if kind>=0x1000:
        cursor,view=args;slot=kind-0x1000-case.bank*256
        base=OTHER+32 if case.mode&4 else cursor
        for i in range(2 if case.mode&2 else 1):
            emit(memory,base+i*8,0xD0000000|case.bank<<16|slot<<8|i,view)
        if case.mode&1:
            put(memory,s['D_800B0DF0'],ROWS[1]);memory[ROWS[1]+byte]=0
            put(memory,INDEX,read(memory,INDEX)^0x55000055)
        if case.mode&8:put(memory,sp+24,0x81001234)
        result=base+case.delta
    elif kind==2:
        cursor,mode,view,ordinal=args
        result=emit(memory,cursor,0xD2000000|mode<<16|ordinal,view)
        if case.mode&1:
            put(memory,INDEX,0xA0000055|mode<<16|ordinal<<8)
            put(memory,s['D_800B0DF0'],ROWS[1]);memory[ROWS[1]+12]=memory[ROWS[1]+13]=1
    else:
        pointer,mode=args;cursor=OTHER+16 if case.mode&4 else read(memory,pointer)
        result=emit(memory,cursor,0xD3000000|mode,0)
        put(memory,pointer,result)
        if case.mode&1:
            put(memory,INDEX,0xB0000000|mode)
            put(memory,s['D_800B0DF0'],ROWS[1]);memory[ROWS[1]+12]=memory[ROWS[1]+13]=1
        if case.mode&8:put(memory,pointer+4,0x1234FFF9)
    for i in range(4):put(memory,sp+i*4,0xB5000000+i)
    return result


def reference(case,phase=0,anchors=None,memory=None):
    s=symbols(anchors);m=dict(fixture(case,phase,s)if memory is None else memory)
    calls=[];logs=[];entry_sp=STACK+phase
    def external(kind,args,sp):
        logs.append(log_event(kind,args,m))
        return effect(case,m,kind,args,sp,s)
    def leaf(cursor,unused,view,sp):
        put(m,sp+4,unused);frame=sp-40;put(m,frame+20,0xDEAD0000)
        cursor=emit(m,cursor,0xE7000000,0)
        cursor=emit(m,cursor,0xDA380003,s['D_80089470'])
        matrix=s['D_80089470'];index=m[read(m,s['D_800B0DF0'])+source.TARGETS[name_of(case)]['byte']]
        if index:
            target=read(m,s[source.TARGETS[name_of(case)]['table']]+index*4)
            calls.append((target,(cursor,view)));put(m,frame+24,matrix)
            cursor=external(0x1000+case.bank*256+index,(cursor,view),frame)
            matrix=read(m,frame+24)
        return emit(m,cursor,0xDA380003,matrix)
    cursor=buffer_of(case)
    if not case.caller:
        result=leaf(cursor,case.unused,case.view,entry_sp)
    else:
        frame=entry_sp-24;put(m,entry_sp,cursor);put(m,entry_sp+4,case.view)
        def view():return signed16(read(m,entry_sp+4))&0xFFFFFFFF
        def layer(mode,ordinal):
            nonlocal cursor
            args=(cursor,mode,view(),ordinal);calls.append((LAYER,args));cursor=external(2,args,frame)
            put(m,entry_sp,cursor)
        def output(mode):
            nonlocal cursor
            args=(entry_sp,mode);calls.append((OUT,args));external(3,args,frame);cursor=read(m,entry_sp)
        def call_leaf():
            nonlocal cursor
            args=(cursor,read(m,INDEX),view())
            calls.append((source.TARGETS[name_of(case)]['entry'],args))
            cursor=leaf(*args,frame);put(m,entry_sp,cursor)
        if case.bank==0:
            if not m[DISABLED]:output(1)
            layer(0,0);layer(0,1);call_leaf()
        else:
            call_leaf();layer(1,0);layer(1,1);output(2)
        result=cursor
    return m,result,calls,logs


class ProviderBoundary(Exception):
    pass


class MatrixOracle(TimingOracle):
    def __init__(self,words,case,phase=0,anchors=None,entry=None,connected=None,memory=None):
        self.case,self.anchors=case,symbols(anchors);self.logs=[];self.trace=[]
        row=source.TARGETS[name_of(case)]
        args=(buffer_of(case),case.unused,case.view)if not case.caller else (buffer_of(case),case.view)
        super().__init__(words,fixture(case,phase,self.anchors)if memory is None else memory,
            phase=phase,entry=entry or row['entry'],arguments=args,connected=connected)

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        if self.recording and self.own_instruction:
            assert all(address+i in self.memory for i in range(size)),('unmapped matrix wrapper store',address,size)
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self,target):
        row=source.TARGETS[name_of(self.case)]
        if target==row['entry']:args=tuple(self.r[4:7]);kind=0
        elif target==LAYER:args=tuple(self.r[4:8]);kind=2
        elif target==OUT:args=tuple(self.r[4:6]);kind=3
        else:
            args=tuple(self.r[4:6]);kind=0x1000+self.case.bank*256+(target-PROVIDER-self.case.bank*0x1000)//4
        self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==0:raise ProviderBoundary
        if kind:self.logs.append(log_event(kind,args,self.memory))

    def hook(self,target):
        args=self.calls[-1][1]
        kind=2 if target==LAYER else 3 if target==OUT else 0x1000+self.case.bank*256+(target-PROVIDER-self.case.bank*0x1000)//4
        result=effect(self.case,self.memory,kind,args,self.r[29],self.anchors)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678
        self.r[2]=result


def corpus():
    for bank in range(2):
        for selector,mode,view,delta in itertools.product((0,1,4,255),range(8),VIEWS,(-8,0,8,16)):
            yield Case(bank,selector,mode,view,delta=delta)
    for bank,mode,phase_alias in itertools.product(range(2),(0,1,8),(1,2)):
        yield Case(bank,1,mode,unused=0x01000000,alias=phase_alias)


@lru_cache(maxsize=1)
def native_records(cases):
    records=[]
    for case in cases:
        m,result,calls,logs=reference(case)
        words=[read(m,base+i*4)for base,n in ((BUFFER,128),(OTHER,64))for i in range(n)]
        patches=[(i,w)for i,w in enumerate(words)if w!=0xA5A5A5A5]
        restored=[0xA5A5A5A5]*192
        for i,w in patches:restored[i]=w
        assert restored==words and len(patches)<=20
        state=[m[base+i]for base in ROWS for i in (12,13)]
        for r,base in enumerate(ROWS):
            assert all(m[base+i]==(state[r*2+i-12]if i in (12,13)else 0xA5)for i in range(0x4C))
        assert len(logs)<=4
        compact=[0]*(32-len(logs)*8)+sum(logs,[])
        assert [0]*96+compact==[0]*(128-len(logs)*8)+sum(logs,[])
        row=lambda xs:'{'+','.join('0x%08Xu'%(x&0xFFFFFFFF)for x in xs)+'}'
        patch='{'+','.join('{%d,0x%Xu}'%p for p in patches)+'}'
        records.append('{%d,%d,%d,0x%Xu,0x%Xu,%d,%d,%d,0x%Xu,0x%Xu,%d,%d,%s,%s,%s,%d,%s}'%(
            case.bank,case.selector,case.mode,case.view,case.unused,case.delta,case.caller,case.disabled,
            result,read(m,INDEX),ROWS.index(read(m,SYMBOLS['D_800B0DF0'])),len(patches),patch,row(state),
            row(compact),len(logs),row([0])))
    return ',\\n'.join(records).replace('\\n','\n')


def native_harness(bodies,parents,cases):
    records=native_records(tuple(cases))
    return '#include <ultra64.h>\n'+source.DECLARATIONS+r"""
typedef struct{u32 before[4];Gfx commands[64],other[32];struct104 rows[2];u32 after[4];}State;
typedef struct{u32 bank,selector,mode,view,unused;s32 delta;u32 caller,disabled,result,index,row;
 u32 patch_count,patch[20][2],bytes[4],logs[32],count,pad[1];}Case;
typedef char Width[(sizeof(void*)==4&&sizeof(Gfx)==8&&sizeof(struct104)==0x4C)?1:-1];
static const Case cases[]={""" + records + r"""};
static State state;static const Case *item;static u32 seen[128],number;
struct104 *D_800B0DF0;Mtx D_80089470;
s32 D_800BE9F0;u8 D_800BE616;
static u32 location(u32 p){if(p>=0x30000&&p<0x30200)return (u32)state.commands+p-0x30000;
 if(p>=0x34000&&p<0x34100)return (u32)state.other+p-0x34000;
 if(p==0x80089470u)return (u32)&D_80089470;return p;}
static void log(u32 tag,Gfx *p,u32 a,u32 b,u32 c){
 u32 *o=seen+number*8;number++;o[0]=tag;o[1]=(u32)p;o[2]=a;o[3]=b;o[4]=c;o[5]=o[6]=o[7]=0;}
static void homes(void){}
static Gfx *provider(Gfx *p,s32 view,u32 bank,u32 slot){u32 i;Gfx *base;
 log(0x1000+bank*256+slot,p,(u32)view,0,0);
 seen[(number-1)*8+4]=p[-2].words.w0;seen[(number-1)*8+5]=p[-2].words.w1;
 seen[(number-1)*8+6]=p[-1].words.w0;seen[(number-1)*8+7]=p[-1].words.w1;
 base=item->mode&4?state.other+4:p;
 for(i=0;i<(item->mode&2?2u:1u);i++){base[i].words.w0=0xD0000000u|bank<<16|slot<<8|i;base[i].words.w1=(u32)view;}
 if(item->mode&1){D_800B0DF0=&state.rows[1];((u8*)&state.rows[1])[12+item->bank]=0;D_800BE9F0=(s32)((u32)D_800BE9F0^0x55000055u);}
 homes();return base+item->delta/8;}
#define P(B,I) static Gfx *p##B##_##I(Gfx *p,s32 v){return provider(p,v,B,I);}
P(0,1) P(1,1) P(1,2) P(1,3) P(1,4)
MatrixWrapperCallback D_8008CD74[2]={0,p0_1};
MatrixWrapperCallback D_8008CD7C[5]={0,p1_1,p1_2,p1_3,p1_4};
Gfx *func_151674F8(Gfx *p,s32 mode,s32 view,s32 ordinal){
 log(2,p,(u32)mode,(u32)view,(u32)ordinal);
 p->words.w0=0xD2000000u|(u32)mode<<16|(u32)ordinal;p->words.w1=(u32)view;
 if(item->mode&1){D_800BE9F0=(s32)(0xA0000055u|(u32)mode<<16|(u32)ordinal<<8);
 D_800B0DF0=&state.rows[1];((u8*)&state.rows[1])[12]=((u8*)&state.rows[1])[13]=1;}
 return p+1;}
void func_1517D7B0(void **out,s32 mode){Gfx *p=(Gfx*)*out;
 log(3,p,(u32)mode,0,0);if(item->mode&4)p=state.other+2;
 p->words.w0=0xD3000000u|(u32)mode;p->words.w1=0;*out=p+1;
 if(item->mode&1){D_800BE9F0=(s32)(0xB0000000u|(u32)mode);
 D_800B0DF0=&state.rows[1];((u8*)&state.rows[1])[12]=((u8*)&state.rows[1])[13]=1;}}
""" + '\n\n'.join(bodies.values())+'\n'+parents+r"""
static u32 expected_word(const Case *c,u32 k){u32 i;for(i=0;i<c->patch_count;i++)if(c->patch[i][0]==k)return c->patch[i][1];return 0xA5A5A5A5u;}
static int run(void){u32 n,i,j,b,w;u8 *p=(u8*)&state;Gfx *result;u32 unused;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){item=&cases[n];
  for(i=0;i<sizeof(state);i++)p[i]=0xA5;
  for(i=0;i<64;i++)((u8*)&D_80089470)[i]=0xA5;
  for(i=0;i<2;i++){((u8*)&state.rows[i])[12]=(u8)item->selector;((u8*)&state.rows[i])[13]=(u8)item->selector;}
  D_800B0DF0=&state.rows[0];D_800BE9F0=(s32)item->unused;D_800BE616=(u8)item->disabled;number=0;
  for(i=0;i<128;i++)seen[i]=0;
  if(item->caller){if(item->bank==0)result=(Gfx*)func_15018E88(state.commands+2,(s16)item->view);
   else result=(Gfx*)func_15018F08(state.commands+2,(s16)item->view);}
  else result=item->bank?func_15174B48(state.commands+2,(s32)item->unused,(s32)item->view):
                         func_15174AA4(state.commands+2,(s32)item->unused,(s32)item->view);
  if((u32)result!=location(item->result)||number!=item->count||(u32)D_800BE9F0!=item->index||D_800B0DF0!=&state.rows[item->row])return 23;
  for(b=0;b<2;b++)for(i=0;i<(b?64u:128u);i++){
   Gfx *g=b?state.other:state.commands;u32 k=b?128+i:i;
   w=expected_word(item,k);if((i&1)&&expected_word(item,k-1)==0xDA380003u)w=location(w);
   if((i&1?g[i/2].words.w1:g[i/2].words.w0)!=w)return 23;}
  for(i=0;i<152;i++){j=i%76;w=(j==12||j==13)?item->bytes[(i/76)*2+j-12]:0xA5u;if(((u8*)state.rows)[i]!=(u8)w)return 23;}
  for(i=0;i<4;i++)if(state.before[i]!=0xA5A5A5A5u||state.after[i]!=0xA5A5A5A5u)return 23;
  for(i=0;i<number;i++)for(j=0;j<8;j++){w=item->logs[(4-number+i)*8+j];
   if(j==1||(j==7&&item->logs[(4-number+i)*8]>=0x1000))w=location(w);
   if(seen[i*8+j]!=w)return 23;}
 }return 0;}
void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
"""


class MatrixCallbackWrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin'];cls.words={};cls.truth={};cls.objects={}
        for name,row in source.TARGETS.items():
            obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED[name],'fresh-'+name)
            if diag:raise ValueError(diag)
            data,fs=source.link_owner(ROOT,cls.out,obj,source.OWNER)
            cls.objects[name]=obj;cls.words[name]=list(struct.unpack_from('>41I',data,fs[name]['value']))
            cls.truth[name]=list(struct.unpack_from('>41I',cls.rom,row['rom']))
        caller=source.recovered_caller(cls.values[source.CALLER_SOURCE].decode());parents=[]
        for name in ('func_15018E88','func_15018F08'):
            lo,hi=source.function_span(caller,name);parents.append(caller[lo:hi])
        cls.parents='\n'.join(parents);cls.cases=list(corpus());cls.receipt=dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('matrix callback wrapper qualification:',cls.receipt)

    def compare(self,case,phase=0,anchors=None,images=None,entry=None):
        expected,result,calls,logs=reference(case,phase,anchors)
        models=[MatrixOracle(code,case,phase,anchors,entry).run()for code in images or (self.truth[name_of(case)],self.words[name_of(case)])]
        for m in models:
            self.assertEqual(public(m.memory),public(expected),(case,phase))
            self.assertEqual((m.r[2],m.calls,m.logs),(result,calls,logs),(case,phase))
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
        return models

    def test_01_direct_SDK_bodies_bindings_two_owners_and_old_stubs(self):
        for name,row in source.TARGETS.items():
            raw,bindings=source.payload(self.objects[name],name)
            self.assertEqual(self.words[name],self.truth[name]);self.assertEqual(self.words[name][0],0x27BDFFD8)
            self.assertEqual((len(raw),source.digest(raw)),(164,row['SHA256']))
            self.assertEqual(bindings,{44:[('R_MIPS_HI16','D_80089470')],48:[('R_MIPS_LO16','D_80089470')],
                68:[('R_MIPS_HI16','D_800B0DF0')],72:[('R_MIPS_LO16','D_800B0DF0')],
                76:[('R_MIPS_HI16',row['table'])],96:[('R_MIPS_LO16',row['table'])]})
            self.assertEqual(source.payload(source.original(ROOT,self.out,name),name),(raw,bindings))
            before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,row['entry'],164)
            case=Case(bank=source.FUNCTIONS.index(name),selector=0)
            old=MatrixOracle(struct.unpack_from('>41I',before,at),case).run()
            self.assertNotEqual(public(old.memory),public(reference(case)[0]))
        q=json.loads((self.out/'qualification.json').read_text());m=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual((q['total_words'],q['preserved_neighbors'],q['preserved_caller_functions']),(82,2,16))
        self.assertEqual(q['caller_diagnostics'],dict(before_warnings=4,after_warnings=3,corrected_pointer_warning=1))
        self.assertEqual(m['actual_Make_commands'],6);self.assertTrue(m['entire_caller_object_identical'])
        self.receipt.update(targets=2,body_words=[41,41],frames=[40,40],bindings=12,new_guards=0,
            neighbors=2,unchanged_caller_functions=16,actual_Make_commands=6,one_pointer_warning_fixed=True)

    def test_02_full_command_order_callbacks_results_late_reads_and_guest_aliases(self):
        visits=[set(),set()];count=0
        for case,phase in itertools.product(self.cases,(0,8)):
            models=self.compare(case,phase);visits[case.bank].update(models[0].visits);count+=1
        for bank,name in enumerate(source.FUNCTIONS):
            row=source.TARGETS[name];self.assertTrue(set(range(row['entry'],row['entry']+164,4))<=visits[bank])
        self.receipt.update(guest_cases=len(self.cases),guest_phases=count,all82_words_visited=True,
            callback_GPR_FPR_clobbers=True,prefix_store_and_late_selector_order=True,
            pointer_return_redirection_and_overlap=True,guest_home_and_saved_matrix_aliases_not_native_claim=True)

    def native(self,bodies,label,opt='-O2'):
        cases=[]
        for bank in range(2):
            for selector,mode,view,delta,caller,disabled in itertools.product(
                    range(source.TARGETS[source.FUNCTIONS[bank]]['count']),range(8),VIEWS,(-8,0,8,16),(0,1),(0,1)):
                cases.append(Case(bank,selector,mode,view,delta=delta,caller=caller,disabled=disabled))
        path=self.out/(label+opt+'.c');exe=path.with_suffix('.elf');path.write_text(native_harness(bodies,self.parents,cases))
        cmd=native_command(opt)+['-Wno-unused-variable',str(path),'-o',str(exe)]
        q=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);self.assertEqual(q.returncode,0,q.stderr)
        return subprocess.run([str(exe)],capture_output=True).returncode,len(cases)

    def test_03_actual_SDK_native32_typed_arrays_callers_and_effective_wrong_C(self):
        for opt in ('-O0','-O2','-O3'):
            result,count=self.native(source.SELECTED,'native',opt);self.assertEqual(result,0)
        transforms={
            'missing-pipe':lambda b:b.replace('    gDPPipeSync(commands++);\n',''),
            'multiply-matrix':lambda b:b.replace('G_MTX_LOAD','G_MTX_MUL'),
            'wrong-matrix':lambda b:b.replace('&D_80089470,','&D_80089470 + 1,'),
            'ignored-return':lambda b:b.replace('commands = D_','D_'),
            'wrong-view':lambda b:b.replace('(commands, view);','(commands, (s32)((u32)view ^ 1));'),
            'missing-tail':lambda b:b[:b.rfind('    gSPMatrix')]+'    return commands;\n}',
            'extra-command':lambda b:b.replace('    return commands;','    gDPPipeSync(commands++);\n    return commands;'),
        }
        for label,transform in transforms.items():
            bodies={name:transform(body)for name,body in source.SELECTED.items()}
            self.assertNotEqual(bodies,source.SELECTED);result,_=self.native(bodies,label);self.assertEqual(result,23,label)
        wrong=dict(source.SELECTED);wrong[source.FUNCTIONS[0]]=wrong[source.FUNCTIONS[0]].replace('D_8008CD74','D_8008CD7C')
        result,_=self.native(wrong,'wrong-table');self.assertEqual(result,23)
        self.receipt.update(native_cases_per_optimization=count,native_optimizations=3,trap_UBSan=True,
            actual_SDK_macros_and_both_C_callers=True,effective_wrong_C_controls=8,
            native_only_legal_table_indices_and_typed_arrays=True,guest_stack_or_MMIO_claimed=False)

    def test_04_complete32_and30_word_callers_current_and_original_ABI(self):
        count=0;visits=[set(),set()]
        for bank in range(2):
            entry,rom,size=(0x15018E88,0x46338,128)if bank==0 else (0x15018F08,0x463B8,120)
            parent=list(struct.unpack_from('>%dI'%(size//4),self.rom,rom))
            before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,entry,size)
            self.assertEqual(list(struct.unpack_from('>%dI'%(size//4),before,at)),parent)
            for selector,mode,view,disabled,phase in itertools.product((0,1),range(9),VIEWS,(0,1),(0,8)):
                case=Case(bank,selector,mode,view,caller=1,disabled=disabled)
                expected,result,calls,logs=reference(case,phase);models=[]
                for images in (self.truth,self.words):
                    connected={}
                    for name,code in images.items():
                        e=source.TARGETS[name]['entry'];connected.update(zip(range(e,e+164,4),code))
                    model=MatrixOracle(parent,case,phase,entry=entry,connected=connected).run()
                    self.assertEqual(public(model.memory),public(expected),(case,phase))
                    self.assertEqual((model.r[2],model.calls,model.logs),(result,calls,logs),(case,phase))
                    models.append(model);visits[bank].update(model.visits)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
            self.assertTrue(set(range(entry,entry+size,4))<=visits[bank])
        self.receipt.update(complete_caller_words=[32,30],caller_phases=count,all62_caller_words_visited=True,
            signed16_view_and_late_unused_word_read=True,opaque_layer_and_out_pointer_helpers_only=True)

    def test_05_independent_GNU_relocations_matrix_pointer_table_signed_carries(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        links=phases=0
        for bank,name in enumerate(source.FUNCTIONS):
            original=source.original(ROOT,self.out,name);row=source.TARGETS[name]
            for i in range(3):
                anchors=dict(SYMBOLS);anchors.update(D_80089470=0x80208000+i*0x10000,D_800B0DF0=0x80107FFC+i*0x10000)
                anchors[row['table']]=0x8030FFFC+i*0x10000;entry=0x17007FFC+i*0x10000;images=[]
                for label,obj in (('original',original),('C',self.objects[name])):
                    text,fs,rs=source.parse_object(obj);assembly,unknown=emit_function(text,fs[name],rs,name,anchors)
                    self.assertEqual(unknown,[]);stem=self.out/('rebase-%s-%d-%s'%(name,i,label))
                    asm=stem.with_suffix('.s');out=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                    asm.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(out),str(asm)],capture_output=True,check=True)
                    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',name,
                        *['--defsym=%s=0x%X'%p for p in anchors.items()],'-o',str(elf),str(out)],capture_output=True,check=True)
                    images.append(list(struct.unpack_from('>41I',sections(elf)['.text'][1])));links+=1
                self.assertEqual(images[0],images[1])
                for selector,mode,phase in itertools.product((0,1,255),(0,1,4,8),(0,8)):
                    self.compare(Case(bank,selector,mode),phase,anchors,images,entry);phases+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=phases,all12_bindings_rebased=True,
            global_anchors_independent=True)

    def test_06_early_selector_and_invented_NULL_check_are_effectively_rejected(self):
        for bank,name in enumerate(source.FUNCTIONS):
            body=source.SELECTED[name];byte='0xC'if bank==0 else '0xD';expr='((u8 *)D_800B0DF0)['+byte+']'
            early=body.replace('    gDPPipeSync','    u8 saved = '+expr+';\n    gDPPipeSync',1).replace('if ('+expr,'if (saved').replace('['+expr+']','[saved]')
            obj,diag=source.compile_owner(ROOT,self.out,'#include <ultra64.h>\n'+source.DECLARATIONS+early,'early-'+name)
            self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER)
            raw,_=source.payload(obj,name);words=struct.unpack_from('>%dI'%(len(raw)//4),data,fs[name]['value'])
            case=Case(bank,1,alias=1);model=MatrixOracle(words,case).run()
            self.assertNotEqual(public(model.memory),public(reference(case)[0]))
            table=source.TARGETS[name]['table']
            guarded=body.replace('if ('+expr+' != 0)','if ('+expr+' != 0 && '+table+'['+expr+'] != 0)')
            obj,diag=source.compile_owner(ROOT,self.out,'#include <ultra64.h>\n'+source.DECLARATIONS+guarded,'null-guard-'+name)
            self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER)
            raw,_=source.payload(obj,name);words=struct.unpack_from('>%dI'%(len(raw)//4),data,fs[name]['value'])
            case=Case(bank,1);m=fixture(case);put(m,SYMBOLS[table]+4,0)
            for code in (self.truth[name],self.words[name]):
                model=MatrixOracle(code,case,memory=m)
                with self.assertRaises(ProviderBoundary):model.run()
                self.assertEqual(model.calls[-1],(0,(BUFFER+32,case.view)))
            self.assertFalse(MatrixOracle(words,case,memory=m).run().calls)
        self.receipt.update(guest_early_read_controls=2,guest_NULL_policy_controls=2,
            target0_call_packet_not_native_C_fault_or_hardware_claim=True)

    def test_07_fired_root_fault_prefixes_full_private_state_and_delay_slots(self):
        count=0
        for bank,selector,mode,phase in itertools.product(range(2),(0,1),(0,1,4,8),(0,8)):
            case=Case(bank,selector,mode);good=MatrixOracle(self.truth[name_of(case)],case,phase).run()
            for cut in range(good.root_accesses):
                models=[MatrixOracle(code,case,phase)for code in (self.truth[name_of(case)],self.words[name_of(case)])]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].trace,models[0].current_pc,models[0].delay_of),
                                 (models[1].trace,models[1].current_pc,models[1].delay_of));count+=1
        self.receipt.update(fired_root_fault_prefixes=count,connected_hook_accesses_excluded=True,
            portable_fault_FCSR_or_hardware_claimed=False)

    def test_08_strict_image24_inputs_caller_object_warning_and_alignment(self):
        before=self.values['conker/build/conker.us.elf'];expected=source.predicted_image(before,self.rom)
        self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes())
        offsets=[0,len(expected)-1]
        for row in source.TARGETS.values():
            at=source.elf_slot_offset(before,row['entry'],row['slot_size']);offsets.extend((at,at+160))
        tail=source.elf_slot_offset(before,0x15174BEC,4);self.assertEqual(expected[tail:tail+4],bytes(4));offsets.append(tail)
        for at in offsets:
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),self.rom)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],self.rom)
        for name,wanted in source.INPUTS.items():
            old=self.values[name];self.assertEqual(source.digest(old),wanted)
            current=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.recovered_caller(old.decode()).encode()if self.installed and name==source.CALLER_SOURCE else expected if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),current)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.assertEqual(source.digest((self.out/'before-caller-padded.o').read_bytes()),source.BEFORE_CALLER_OBJECT_SHA)
        self.receipt.update(strict_image_corruptions_rejected=len(offsets)+1,live_and_historical_inputs=len(source.INPUTS),
            both_old_objects_pinned=True,second_alignment_bytes_preserved=4,complete_guard_manifest_unchanged=True)


if __name__=='__main__':
    unittest.main()
