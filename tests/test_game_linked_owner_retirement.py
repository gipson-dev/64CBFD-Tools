"""Linked-owner retirement: Boolean spill guards, real callback and bounded factory."""
from dataclasses import dataclass
from pathlib import Path
import csv
import io
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_linked_owner_retirement as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
OWNER,ACTOR,OTHER,ALT,EFFECT,PAYLOAD=0x30000,0x28000,0x34000,0x40000,0x48000,0x50000
COPY,POSITION,CREATE,RELEASE,TICKS=0x10022EC0,0x151A4E34,0x15147A80,0x1516972C,0x800BE9E4
TABLE_ROM,EXIT_TABLE,EXIT_ROM=0x22EFA8,0x8008A4C0,0x22EF80
VECTOR=(0x3F800000,0xBF800000,0x40000000)


@dataclass(frozen=True)
class Case:
    live:int=1
    same:bool=True
    capable:int=1
    state:int=0
    byte:int=255
    mode:int=0
    alias:int=0
    allocated:bool=True
    positioned:bool=True


def fixture(c,phase=0):
    actor=(ACTOR,OWNER,OWNER+0x10,OWNER-0x28)[c.alias]
    m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    for base,size in((OWNER-32,0x300),(actor-32,0x250),(OTHER-32,0x100),(ALT-32,0x250),(EFFECT-16,0xC0),(PAYLOAD-16,112)):
        m.update({base+i:(i*13+c.byte)&255 for i in range(size)})
    put(m,OWNER+0x28,actor);put(m,actor,c.live);m[actor+0x3B]=c.byte if c.same else c.byte^128
    m[actor+0x74]=c.state;put(m,actor+0x1D4,c.capable);m[OWNER+0x2C]=c.byte
    m[OWNER+12]=c.byte;m[OWNER+13]=0xA4;put(m,OWNER+14,0x1234,2)
    return m


def active(m):
    actor=read(m,OWNER+0x28)
    failed=read(m,actor)==0
    if m[OWNER+0x2C]!=m[actor+0x3B]:failed=True
    call=not failed and read(m,actor+0x1D4)!=0 and m[actor+0x74]&15!=15
    return failed,call


def effects(m,c,entered):
    if c.mode&1:m[OWNER+13]=0x58;put(m,OWNER+14,0x2468,2)
    if c.mode&2:put(m,OWNER+0x28,ALT)
    if c.mode&4:put(m,entered,OTHER)
    if c.mode&24:
        for i,value in enumerate((0xA5,0xB6,0xC7)):m[entered-8+i]=value
        m[entered-5]=0 if c.mode&8 else 1


def reference(m,c,entered):
    m=dict(m);failed,call=active(m);calls=[];owner=OWNER
    if call:
        calls.append((source.HELPER,(OWNER+0x28,m[OWNER+12])))
        put(m,entered,OWNER);effects(m,c,entered);failed=not bool(c.mode&8);owner=read(m,entered)
    if failed:put(m,owner+14,0xFFFF,2);m[owner+13]|=1
    return m,calls


def public(m):
    return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}


class GateOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=source.ENTRY,connected=None,helper=source.HELPER,arguments=None,callbacks=()):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=arguments or(OWNER,),connected=connected)
        self.case=c;self.entered=STACK+phase;self.helper_entered=STACK+phase;self.gate_helper=helper
        self.callbacks=set(callbacks);self.chain_mode=False;self.copied_payload=None;self.factory_vector=None

    def record_call(self,target):
        if target==source.ENTRY:self.entered=self.r[29];n=1
        elif target==self.gate_helper:self.helper_entered=self.r[29];n=2
        elif target==COPY:n=3
        elif target==POSITION:n=2
        elif target==CREATE:n=11
        elif target==RELEASE or target in self.callbacks:n=1
        else:raise AssertionError(('unbounded owner-retirement call',hex(target)))
        args=self.arguments(n);self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==self.gate_helper:assert args==(OWNER+0x28,self.case.byte),args
        if target==COPY and args[2]==80:self.copied_payload=bytes(self.memory[args[1]+i]for i in range(80))
        if target==CREATE:self.factory_vector=bytes(self.memory[args[0]+i]for i in range(12))

    def hook(self,target):
        if target==self.gate_helper:
            effects(self.memory,self.case,self.entered);value=(0,ALT,0xFFFFFFFF)[self.case.byte%3]
        elif target==COPY:
            dst,src,n=self.arguments(3)
            for i in range(n):self.put(dst+i,self.get(src+i,1),1)
            value=dst
        elif target==POSITION:
            dst,out=self.arguments(2)
            assert dst==self.helper_entered-168+0x3C and out==self.helper_entered-168+0x8C
            if self.case.positioned:
                for i,v in enumerate(VECTOR):self.put(out+i*4,v,4)
            value=int(self.case.positioned)
        elif target==CREATE:
            args=self.arguments(11)
            assert args==(self.helper_entered-168+0x8C,80,24,6,6,6,0,0,0,self.case.byte,0),args
            value=EFFECT if self.case.allocated else 0
            if value:self.put(EFFECT+0x98,PAYLOAD,4)
        else:
            assert target==RELEASE or target in self.callbacks;value=0xB5000002
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True;self.r[2]=value


def controls():
    b=source.SELECTED
    snapshot='    u8 flags = ((u8 *)owner)[0xD];\n'
    return dict(selected=b,
        wrong_live=b.replace('link->owner == 0','link->owner != 0'),
        wrong_identity=b.replace('link->identity !=','link->identity =='),
        wrong_capability=b.replace('0x1D4) != 0','0x1D4) == 0'),
        wrong_mask=b.replace('0xF','0x7'),
        wrong_slot=b.replace('link, ((u8 *)owner)[0xC]','link, 0'),
        missing_helper=b.replace('        func_151A3504(link, ((u8 *)owner)[0xC]);',''),
        missing_latch=b.replace('failed = 1','failed = 0'),
        wrong_lifetime=b.replace('= -1','= 0'),
        wrong_flag=b.replace('|= 1','|= 2'),
        early_flags=b.replace('    PayloadOwnerLink *link',snapshot+'    PayloadOwnerLink *link').replace('((u8 *)owner)[0xD] |= 1','((u8 *)owner)[0xD] = flags | 1'),
        early_dead_return=b.replace('if (*(s32 *)link->owner == 0) {\n        failed = 1;','if (*(s32 *)link->owner == 0) {\n        return;'))


def native_harness():
    text=source.HEADERS+source.DECLARATIONS+'''
typedef struct {s32 live;u8 opaque4[0x37];u8 identity;u8 opaque3C[0x38];u8 state;u8 opaque75[0x15F];s32 capable;} NativeActor;
typedef struct {u8 header[14];s16 lifetime;u8 opaque10[24];PayloadOwnerLink link;u8 tail[40];} NativeOwner;
typedef char link_offset[__builtin_offsetof(NativeOwner,link)==0x28?1:-1];
typedef char identity_offset[__builtin_offsetof(NativeActor,identity)==0x3B?1:-1];
typedef char capability_offset[__builtin_offsetof(NativeActor,capable)==0x1D4?1:-1];
static NativeActor actor,other;static NativeOwner actual,expected;
static u32 calls,error,mode,slot;
__attribute__((noinline,noclone)) void *func_151A3504(void *descriptor,u8 byte){
 calls++;if(descriptor!=&actual.link||byte!=slot)error=1;
 if(mode&1){actual.header[13]=0x58;actual.lifetime=0x2468;}
 if(mode&2)actual.link.owner=(u8*)&other;
 return byte%3?(void*)&other:0;
}
'''
    for n,b in controls().items():text+=b.replace(source.FUNCTION,n)+'\n'
    text+='''typedef void(*Update)(struct260*);
static int variant(Update fn){
 u32 p,state,live,same,cap,m,i,shouldCall,failed;
 for(p=0;p<8;p++)for(state=0;state<256;state++)for(live=0;live<2;live++)for(same=0;same<2;same++)for(cap=0;cap<2;cap++)for(m=0;m<4;m++){
  slot=(state*37+p*17)&255;mode=m;
  for(i=0;i<sizeof(actual);i++)((u8*)&actual)[i]=(u8)(i*13+p+state);
  actor.live=live?(s32)(p&1?0x80000000u:0xFFFFFFFFu):0;
  actor.capable=cap?(s32)(p&1?0x80000000u:1):0;actor.identity=(u8)(same?slot:slot^128);actor.state=(u8)state;
  actual.header[12]=(u8)slot;actual.header[13]=(u8)(state^p*17);actual.lifetime=(s16)(p&1?-1:32767);
  actual.link.owner=(u8*)&actor;actual.link.identity=(u8)slot;expected=actual;
  failed=!live||!same;shouldCall=!failed&&cap&&(state&15)!=15;
  if(shouldCall){if(m&1){expected.header[13]=0x58;expected.lifetime=0x2468;}if(m&2)expected.link.owner=(u8*)&other;failed=1;}
  if(failed){expected.lifetime=-1;expected.header[13]|=1;}
  calls=error=0;fn((struct260*)(void*)&actual);
  if(error||calls!=shouldCall)return 23;
  for(i=0;i<sizeof(actual);i++)if(((u8*)&actual)[i]!=((u8*)&expected)[i])return 23;
 }
 return 0;
}
int run(void){
'''
    for i,n in enumerate(controls()):text+=' if(variant(%s)!=%d)return %d;\n'%(n,0 if n=='selected'else 23,i+1)
    return text+' return 0;\n}\n'+START


def parent_harness(body):
    text=source.HEADERS+'''
static struct260 owner;static u32 calls,trace[3],updateMode,exitMode;
s32 D_800BE9E4;void(*D_8008A4E8[98])(struct260*);void(*D_8008A4C0[10])(struct260*);
static void capture(struct260*p,u32 id){
 if(p!=&owner||calls>=3){calls=99;return;}trace[calls++]=id;
 if(id<98&&updateMode){p->unkE=-1;p->unkD|=1;}
 if(id>=100&&id<110&&exitMode)p->unkE=2;
}
void func_1516972C(struct260*p){capture(p,200);}
'''
    for i in range(98):text+='static void slot%d(struct260*p){capture(p,%d);}\n'%(i,i)
    for i in range(10):text+='static void exit%d(struct260*p){capture(p,%d);}\n'%(i,100+i)
    variants=dict(selected_parent=body,wrong_tick=body.replace('D_800BE9E4','0'),
        wrong_index=body.replace('D_8008A4E8[arg0->unk11]','D_8008A4E8[0]'),missing_release=body.replace('func_1516972C(arg0);',';'))
    for n,b in variants.items():text+=b.replace('func_15149264',n)+'\n'
    text+='''typedef void(*Parent)(struct260*);
static int variant(Parent fn){
 u32 s,g,l,u,d,e,t,i,n,w[3];s16 life;u8 flags;
 static const s16 lives[]={-1,0,32767};static const s32 ticks[]={0,1,30};
 for(s=0;s<99;s++)for(g=0;g<2;g++)for(l=0;l<3;l++)for(u=0;u<2;u++)for(d=0;d<3;d++)for(e=0;e<2;e++)for(t=0;t<3;t++){
  owner.unk11=s==98?-1:(s8)s;owner.unk10=d==0?-1:d==1?0:9;
  owner.unkD=flags=(u8)(0xA4|g);owner.unkE=life=lives[l];D_800BE9E4=ticks[t];updateMode=u;exitMode=e;n=0;
  if(g)life=(s16)((s32)life-ticks[t]);
  if(s!=98){w[n++]=s;if(u){life=-1;flags|=1;}}
  if(life<0&&owner.unk10!=-1){w[n++]=100+(u8)owner.unk10;if(e)life=2;}
  if(life<0)w[n++]=200;calls=0;fn(&owner);
  if(calls!=n||owner.unkE!=life||owner.unkD!=flags)return 23;
  for(i=0;i<n;i++)if(trace[i]!=w[i])return 23;
 }
 return 0;
}
int run(void){
'''
    for i in range(98):text+=' D_8008A4E8[%d]=slot%d;\n'%(i,i)
    for i in range(10):text+=' D_8008A4C0[%d]=exit%d;\n'%(i,i)
    for i,n in enumerate(variants):text+=' if(variant(%s)!=%d)return %d;\n'%(n,0 if n=='selected_parent'else 23,i+1)
    return text+' return 0;\n}\n'+START


class LinkedOwnerRetirementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.obj,diag=source.compile_owner(ROOT,cls.out,source.HEADERS+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        data,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER);cls.raw=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']))
        cls.fit=list(cls.raw)
        for at,word in source.REPLACEMENT.items():cls.fit[at//4]=word
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>44I',cls.rom,source.ROM))
        cls.parent=list(struct.unpack_from('>45I',cls.rom,0x176714))
        cls.table=list(struct.unpack_from('>98I',cls.rom,TABLE_ROM));cls.exit_table=list(struct.unpack_from('>10I',cls.rom,EXIT_ROM))
        cls.helper=list(struct.unpack_from('>70I',cls.rom,0x1D09B4));cls.receipt={}

    def compare(self,c,phase=0,images=None,entry=source.ENTRY,helper=source.HELPER):
        initial=fixture(c,phase);expected,calls=reference(initial,c,STACK+phase)
        calls=[(helper,args)for _,args in calls]
        models=[GateOracle(w,initial,c,phase,entry,helper=helper).run()for w in(images or(self.truth,self.fit))]
        for m in models:
            self.assertEqual(public(m.memory),public(expected),c);self.assertEqual(m.calls,calls)
            self.assertEqual(m.r[29],STACK+phase);self.assertEqual(m.r[31],0xDEAD0000)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]

    def test_01_complete_C_two_spill_guards_and_fail_closed_normalizer(self):
        self.assertEqual(self.truth,self.fit);self.assertEqual({i for i in range(44)if self.truth[i]!=self.raw[i]},{28,31})
        raw,rs=source.payload(self.obj);self.assertEqual(rs,source.BINDINGS)
        self.assertEqual(source.normalized(raw,rs),source.payload(source.original(ROOT,self.out)))
        for i in(0,28,29,31,43):
            bad=bytearray(raw);bad[i*4]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),rs)
        with self.assertRaises(ValueError):source.normalized(raw,{})
        with self.assertRaises(ValueError):source.normalized(raw[:-4],rs)
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual(q['preserved_neighbors'],22)
        self.receipt.update(words=44,frame=32,bindings=1,new_guards=2,compiler_only=False,preserved_neighbors=22,
            raw_normalizer_negatives=7,helper_stub_unchanged=True)

    def test_02_gates_byte_widths_aliases_helper_mutations_and_private_limit(self):
        phases=raw_phases=0;visits=set()
        for live,same,cap,state,mode,phase in itertools.product((0,0x80000000),(False,True),(0,0xFFFFFFFF),range(256),(0,3),(0,8)):
            c=Case(live,same,cap,state,state,mode);model=self.compare(c,phase);visits.update(model.visits);phases+=1
            raw=GateOracle(self.raw,fixture(c,phase),c,phase).run()
            self.assertEqual(public(raw.memory),public(model.memory));self.assertEqual(raw.calls,model.calls);raw_phases+=1
        for alias,mode,live,same,phase in itertools.product(range(4),(0,1,2,4,8,16),(0,1),(False,True),(0,8)):
            self.compare(Case(live,same,1,0,255,mode,alias),phase);phases+=1
        c=Case(mode=8);initial=fixture(c);a=self.compare(c)
        raw=GateOracle(self.raw,initial,c).run();self.assertNotEqual(public(raw.memory),public(a.memory))
        c=Case();a=self.compare(c);raw=GateOracle(self.raw,fixture(c),c).run()
        self.assertNotEqual(raw.memory,a.memory);self.assertEqual(public(raw.memory),public(a.memory))
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+176,4)))
        self.receipt.update(guest_phases=phases,raw_public_comparisons=raw_phases,all_root_words_visited=True,
            raw_private_memory_and_fault_equality_claimed=False,raw_guest_private_alias_counterexample_observed=True)

    def test_03_native32_defined_typed_storage_and_eleven_controls(self):
        unit=self.out/'native32.c';unit.write_text(native_harness())
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native32'+opt);p=subprocess.run([*native_command(opt),str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            p=subprocess.run([str(exe)],capture_output=True,timeout=90);self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_selected_calls_per_optimization=65536,native_optimizations=['O0','O2','O3'],
            effective_wrong_C_controls=11,trap_UBSan=True,typed_full_root_link_and_actor_storage=True,
            helper_return_ignored=True,helper_boundary_not_unrecovered_stub_C=True)

    def test_04_registration_complete_original_parent_and_real_update_path(self):
        ptr=struct.pack('>I',source.ENTRY);jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[TABLE_ROM+40])
        self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
        self.assertEqual(self.table[10],source.ENTRY);old=self.values['conker/build/conker.us.elf']
        at=source.elf_slot_offset(old,source.PARENT,180);self.assertEqual(list(struct.unpack_from('>45I',old,at)),self.parent)
        at=source.elf_slot_offset(old,source.TABLE,392);self.assertEqual(old[at:at+392],self.rom[TABLE_ROM:TABLE_ROM+392])
        count=0;visits=set()
        for selector,destructor,flags,life,ticks in itertools.product((-1,0,10,97),(-1,0,9),(0xA4,0xA5),(0xFFFF,0,32767),(0,1,30)):
            c=Case(byte=255);m=fixture(c);m[OWNER+17]=selector&255;m[OWNER+16]=destructor&255;m[OWNER+13]=flags;put(m,OWNER+14,life,2);put(m,TICKS,ticks)
            for i,v in enumerate(self.table):put(m,source.TABLE+i*4,v)
            for i,v in enumerate(self.exit_table):put(m,EXIT_TABLE+i*4,v)
            expected=dict(m);calls=[]
            if flags&1:put(expected,OWNER+14,(life-ticks)&65535,2)
            if selector!=-1:
                callback=self.table[selector];calls.append((callback,(OWNER,)))
                if selector==10:expected,more=reference(expected,c,STACK-24);calls+=more
            value=read(expected,OWNER+14,2)
            if value&0x8000 and destructor!=-1:calls.append((self.exit_table[destructor],(OWNER,)))
            if value&0x8000:calls.append((RELEASE,(OWNER,)))
            models=[]
            for words in(self.truth,self.fit):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                model=GateOracle(self.parent,m,c,entry=source.PARENT,connected=connected,callbacks=self.table+self.exit_table).run()
                self.assertEqual(public(model.memory),public(expected));self.assertEqual(model.calls,calls);visits.update(model.visits);models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(source.PARENT,source.PARENT+180,4))<=visits)
        self.receipt.update(actual_parent_words=45,actual_parent_phases=count,registration_index=10,update_table_entries=98,
            selected_path_and_disable_sentinel_qualified=True,other_callbacks_and_release_bounded=True,
            all_parent_words_visited=True,parent_destructor_non_sentinel_path_qualified=True)

    def test_05_actual_C_parent_native_boundary_and_effective_controls(self):
        text=self.values['conker/src/game/done/game_1765E0.c'].decode();lo,hi=source.function_span(text,'func_15149264')
        unit=self.out/'native-parent.c';unit.write_text(parent_harness(text[lo:hi]))
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native-parent'+opt);p=subprocess.run([*native_command(opt),str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=90).returncode,0,opt)
        self.receipt.update(native_parent_cases_per_optimization=21384,native_parent_effective_controls=3,
            actual_C_parent_with_typed_callback_and_release_boundaries=True,full_native_parent_callee_closure_claimed=False)

    def test_06_complete_original_factory_helper_and_explicit_live_stub_boundary(self):
        phases=0;visits=set()
        for byte,allocated,positioned,phase in itertools.product((0,127,128,255),(False,True),(False,True),(0,8)):
            c=Case(byte=byte,allocated=allocated,positioned=positioned);initial=fixture(c,phase);expected,_=reference(initial,c,STACK+phase)
            helper_sp=STACK+phase-32-168;buffer=helper_sp+0x3C
            payload={i:initial[buffer+i]for i in range(80)}
            for i in range(48):payload[i]=initial[OWNER+0x28+i]
            for offset in(0x40,0x48):
                for i in range(4):payload[offset+i]=0
            for offset,value in((0x30,6),(0x44,0),(0x4C,0)):payload[offset]=value
            if positioned:
                for i,w in enumerate(VECTOR):
                    for j,b in enumerate(w.to_bytes(4,'big')):payload[0x34+i*4+j]=b
            if allocated:
                put(expected,EFFECT+0x98,PAYLOAD)
                for i,b in payload.items():expected[PAYLOAD+i]=b
            models=[]
            for words in(self.truth,self.fit):
                connected={source.HELPER+i*4:w for i,w in enumerate(self.helper)}
                model=GateOracle(words,initial,c,phase,connected=connected).run();models.append(model);visits.update(model.visits)
                self.assertEqual(public(model.memory),public(expected))
                self.assertEqual(model.calls[0],(source.HELPER,(OWNER+0x28,byte)))
                self.assertEqual([p for p,_ in model.calls],[source.HELPER,COPY,POSITION,CREATE]+([COPY]if allocated else[]))
                if allocated:self.assertEqual(model.copied_payload,bytes(payload[i]for i in range(80)))
            self.assertEqual(complete(models[0]),complete(models[1]));phases+=1
        initial=fixture(Case());put(initial,OWNER+0x28,0)
        model=GateOracle(self.helper,initial,entry=source.HELPER,arguments=(OWNER+0x28,255)).run()
        self.assertEqual(model.r[2],0);self.assertFalse(model.calls);visits.update(model.visits)
        self.assertTrue(set(range(source.HELPER,source.HELPER+280,4))<=visits)
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.HELPER,280)
        self.assertNotEqual(old[at:at+280],self.rom[0x1D09B4:0x1D09B4+280])
        self.receipt.update(original_helper_words=70,original_helper_phases=phases+1,all_original_helper_words_visited=True,
            helper_live_C_stub_unrecovered_and_unchanged=True,copy_position_and_create_providers_bounded=True,
            descriptor_holes_preserved=True,full_asset_factory_or_live_helper_acceptance_claimed=False)

    def linked(self,obj,entry,helper,label):
        data,fs,rs=source.parse_object(obj);asm,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,{'func_151A3504':helper})
        self.assertFalse(unknown);p=self.out/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
            '--defsym=func_151A3504=0x%X'%helper,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack_from('>44I',sections(p.with_suffix('.elf'))['.text'][1]))

    def test_07_independent_GNU_rebases_and_literal_fault_prefixes(self):
        phases=cuts=0
        for i,(entry,helper)in enumerate(((source.ENTRY,source.HELPER),(0x18017FFC,0x18207FFC),(0x1A028000,0x1B047FF0))):
            objects=(source.original(ROOT,self.out),self.out/'qualified-padded.o',self.out/'make-shadow/src/game/generated_1D0840.c.o')
            images=[self.linked(obj,entry,helper,'rebased-%d-%d'%(i,j))for j,obj in enumerate(objects)]
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for live,same,cap,mode,phase in itertools.product((0,1),(False,True),(0,1),(0,3,4,8,16),(0,8)):
                self.compare(Case(live,same,cap,0,255,mode),phase,images[:2],entry,helper);phases+=1
        for live,same,cap,state,mode,phase in itertools.product((0,1),(False,True),(0,1),(0,15),(0,8),(0,8)):
            c=Case(live,same,cap,state,255,mode);initial=fixture(c,phase);done=GateOracle(self.truth,initial,c,phase).run()
            for cut in range(done.root_accesses):
                models=[GateOracle(w,initial,c,phase)for w in(self.truth,self.fit)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=9,rebase_phases=phases,fired_literal_root_prefixes=cuts,
            raw_private_or_fault_equality_claimed=False)

    def test_08_guard_history_actual_Make_strict_image_and_frozen_inputs(self):
        old=self.values['conker/retail_word_patches.us.csv'];new=source.guard_bytes(old);self.assertTrue(new.startswith(old))
        rows=list(csv.DictReader(io.StringIO(new.decode())));added=[r for r in rows if r['function']==source.FUNCTION]
        self.assertEqual(len(added),2);self.assertEqual({int(r['offset'],0)for r in added},{0x70,0x7C})
        with self.assertRaises(ValueError):source.guard_bytes(old[:-1])
        bad=bytearray(old);bad[-8]^=1
        with self.assertRaises(ValueError):source.guard_bytes(bytes(bad))
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+176]
        expected=source.predicted_image(before,truth);source.check_image(before,expected,truth)
        at=source.elf_slot_offset(before,source.ENTRY,176);sym=[o for o,n,_,_ in source.symbol_rows(before)if n==source.FUNCTION][0]
        for pos in(0,at-1,at,at+172,at+176,sym+4,sym+8,len(before)-1):
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
        source.check_inputs(ROOT,self.out,self.installed)
        self.receipt.update(strict_image_negatives=9,guard_prefix_byte_identical=True,guard_append_only_rows=2,
            metadata_exclusions=0,actual_Make_commands=5,normal_O2_g3=True)
