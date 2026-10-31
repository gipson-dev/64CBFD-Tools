"""Phase-pair callback: float order, saved state and original caller/helpers."""
from dataclasses import dataclass,replace
import itertools,math,struct
from types import SimpleNamespace
source=SimpleNamespace(ENTRY=0x15108C38,CALLER=0x1513B798)
from pathlib import Path
r=Path.cwd();o=r/'conker/build/game-owner-phase-state-15108C38-match'
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_trig_match as trig
from tools.tests.test_game_sine_phase_update import wrap
from tools.tests import test_game_actor_burst_consumer_match as faults
OWNER,OTHER,THIRD,MARK,LOOKUP=0x30000,0x50000,0x60000,0x70000,0x71000
CLOCK,BOUND,TICKS,GATE,TABLEPTR,TABLE=0x800BE9A4,0x800A56A4,0x800BE9E4,0x800C35EA,0x800C3958,0x80089C18
SINE,WRAP,TIMER,VALUE,RELEASE=0x15047D60,0x15144B68,0x15108B80,0x15108BC0,0x1516972C
HELPERS=((SINE,0x75210,104),(WRAP,0x172018,24),(TIMER,0x136030,16),(VALUE,0x136070,30))
u32=lambda x:x&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 phases:tuple=(bits(1.25),bits(-2.5))
 clock:int=bits(1.)
 scales:tuple=(0x3DAF837B,0x3DA05BC0,0x40E35C2A,0x40E35C2A)
 results:tuple=(bits(.25),bits(-.5),bits(1.5),bits(-2.5))
 offset:int=0
 mode:int=0
 alias:object=None
 phase:int=0
 index:int=2
 timer:int=3
 ticks:int=1
 gate:int=1
 seed:int=0
 flag:int=0

def symbols():return dict(sinf=SINE,func_15144B68=WRAP,func_15108B80=TIMER,func_15108BC0=VALUE,D_800BE9A4=CLOCK,**{'D_%08X'%a:a for a in range(0x800A2480,0x800A2490,4)})
def owner(c,s):return OWNER if c.alias is None else u32(s['D_800BE9A4']-c.offset-0xF8-c.alias)
def state(m,p):return u32(p+signed(read(m,p+0x50))+0xF8)
def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;p=owner(c,s);m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for base,n in((p-16,0x800),(OTHER-16,0x800),(THIRD-16,0x800),(MARK,32),(LOOKUP-0x88,0x200)):
  for i in range(n):m.setdefault(u32(base+i),(i*29+c.seed+0x5A)&255)
 for at,value in trig.GLOBALS.items():put(m,at,value)
 put(m,BOUND,0x40C90FDB);put(m,TICKS,c.ticks);m[GATE]=c.gate;put(m,TABLEPTR,LOOKUP)
 for b in(p,OTHER,THIRD):
  put(m,b+0x50,c.offset);q=state(m,b)
  for off,val in((0,bits(99.)),(4,bits(-99.)),(8,c.phases[0]),(12,c.phases[1]),(16,bits(226.)),(20,c.index),(28,c.timer)):put(m,q+off,val)
 for i in range(-2,5):put(m,LOOKUP+i*0x44+4,bits(i*.25+10.))
 for name,value in zip(('D_800A2480','D_800A2484','D_800A2488','D_800A248C'),c.scales):put(m,s[name],value)
 put(m,s['D_800BE9A4'],c.clock)
 for b in(p,OTHER,THIRD):m[state(m,b)+32]=c.flag
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def add(a,b):return bits(floating(a)+floating(b))
def mul(a,b):return bits(floating(a)*floating(b))
def effects(m,c,p,q,s,n,home):
 if n==1 and c.mode&1:put(m,q+12,bits(2.));put(m,p+0x50,0x400);put(m,s['D_800A2488'],bits(3.))
 if n==2 and c.mode&2:put(m,q+8,bits(-.75));put(m,s['D_800A248C'],bits(-3.))
 if n==3 and c.mode&4:put(m,q+12,bits(3.25));put(m,s['D_800A2488'],bits(4.))
 if n==4 and c.mode&8:put(m,s['D_800A248C'],bits(.5))
 if n==1 and c.mode&16:put(m,home,OTHER)
 if n==5 and c.mode&32:put(m,home,THIRD)
 if n==5 and c.mode&64:m[q+32]^=255
 if n==6 and c.mode&128:m[q+32]=0 if m[q+32] else 128
def tail(m,arg,t):
 q=state(m,arg)
 if t==TIMER:
  if read(m,q+20)!=999:
   result=u32(read(m,q+28)-read(m,TICKS));put(m,q+28,result)
   if signed(result)<0:put(m,q+20,999)
 else:
  index=read(m,q+20);result=bits(226.)if index==999 or m[GATE]!=1 else read(m,u32(read(m,TABLEPTR)+signed(index)*0x44+4))
  put(m,q+16,result)
def reference(initial,c=Case(),s=None,real=False,home=None):
 s=symbols()if s is None else s;m=dict(initial);p=owner(c,s);q=state(m,p);home=STACK+c.phase if home is None else home;calls=[]
 def call(name,arg):
  t=s[name];calls.append((t,arg));n=len(calls)
  if n<=4:result=(trig.reference(arg)if name=='sinf'else wrap(arg))if real else c.results[n-1]
  elif real:tail(m,arg,TIMER if name=='func_15108B80'else VALUE);result=0
  else:put(m,arg+0x30+(n-5),0x80+n,1);result=0
  if not real:effects(m,c,p,q,s,n,home)
  return result
 first=add(read(m,q+8),mul(read(m,s['D_800A2480']),read(m,s['D_800BE9A4'])));second=read(m,q+12)
 put(m,q+8,first);put(m,q+12,add(second,mul(read(m,s['D_800A2484']),read(m,s['D_800BE9A4']))))
 put(m,q+8,call('func_15144B68',read(m,q+8)));put(m,q+12,call('func_15144B68',read(m,q+12)))
 x=call('sinf',read(m,q+8));put(m,q,mul(x,read(m,s['D_800A2488'])))
 y=call('sinf',read(m,q+12));put(m,q+4,mul(y,read(m,s['D_800A248C'])))
 call('func_15108B80',p)
 call('func_15108BC0',p)
 m[p+0x12]=4 if m[q+32] else 2
 return m,calls,1

def corpus():
 for i in range(512):
  yield Case(phases=(bits((i%17-8)*.25),bits((i%23-11)*.5)),clock=bits((0.,-0.,.125,-.25,1.,-1.,4.,2.)[i%8]),offset=(-128,0,256)[i%3],mode=i%256,phase=(i%2)*8,seed=i,flag=(0,1,128,255)[(i//8)%4])
 for alias,mode,clock,flag in itertools.product((0,4,8,12),(0,15,16,32,63,64,128,255),(0.,1.),(0,255)):yield Case(alias=alias,mode=mode,clock=bits(clock),flag=flag)
 for word,field in itertools.product((1,0x80000001,0x7F800000,0xFF800000,0x7FC12345),range(2)):
  v=list(Case().phases);v[field]=word;yield Case(phases=tuple(v),flag=128)
class PhaseOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None,real=False):
  self.targets=symbols()if s is None else s;self.real=real;self.owner_pointer=owner(c,self.targets);self.saved_state=state(memory,self.owner_pointer);self.home=STACK+c.phase;self.ordinal=0
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=self.targets,connected=connected,arguments=(self.owner_pointer,))
 def execute(self,word):
  op,rs,rt,rd,fd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
  if op==0 and fn==3:self.r[rd]=u32(signed(self.r[rt])>>fd)
  elif op==17 and rs==16 and fn==13:self.f[fd]=u32(math.trunc(floating(self.f[rd])))
  elif op==17 and rs==16 and fn==7:self.f[fd]=self.f[rd]^0x80000000
  else:super().execute(word)
  self.r[0]=0
 def record_call(self,t):
  if t==source.ENTRY:self.home=self.r[29];arg=self.r[4]
  elif t==RELEASE:arg=self.r[4]
  else:
   assert t in self.targets.values(),hex(t)
   arg=self.f[12]if t in(self.targets['sinf'],self.targets['func_15144B68'])else self.r[4];self.ordinal+=1
  self.calls.append((t,arg));self.events.append(('CALL',t,arg))
 def hook(self,t):
  if t==RELEASE:put(self.memory,MARK,self.r[4]);value=0
  else:
   assert t in(self.targets['sinf'],self.targets['func_15144B68'],self.targets['func_15108B80'],self.targets['func_15108BC0'])
   if self.ordinal<=4:value=self.case.results[self.ordinal-1]
   else:put(self.memory,self.r[4]+0x30+(self.ordinal-5),0x80+self.ordinal,1);value=0
   effects(self.memory,self.case,self.owner_pointer,self.saved_state,self.targets,self.ordinal,self.home)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=value;self.hi,self.lo=0xA5000010,0xA5000011

def helper_code(rom):
 result={}
 for entry,offset,n in HELPERS:result.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
 return result

def caller_machine(rom,words,c=Case(),flags=0,lifetime=10,index=1,real=False):
 m=fixture(c);p=owner(c,symbols());m[p+0x10]=flags;m[p+0x11]=index&255;put(m,p+0x14,lifetime,2);[put(m,TABLE+4*i,struct.unpack_from('>I',rom,0x22E6D8+4*i)[0])for i in range(4)]
 before=dict(m);expired=False
 if flags&1:
  remaining=(lifetime-c.ticks)&65535;put(before,p+0x14,remaining,2);expired=bool(remaining&0x8000)
 if expired:put(before,MARK,p);calls=[(RELEASE,p)]
 elif index==-1:calls=[]
 else:
  before,inner,_=reference(before,c,real=real,home=STACK+c.phase-32);calls=[(source.ENTRY,p)]+inner
 code=helper_code(rom)if real else{};code.update(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words))
 model=PhaseOracle(struct.unpack_from('>41I',rom,0x168C48),m,c,entry=source.CALLER,connected=code,real=real)
 return model,(public(before),calls)

def fullstate(m):return m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace

import subprocess
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_four_head_lookup_match import payload
def linked(obj,label,s=None,entry=None):
 from tools.experiments.alternative_source_draft_word_screen import emit_function
 from tools.pad_generated_object import parse_object
 s=symbols()if s is None else s;entry=source.ENTRY if entry is None else entry;F='func_15108C38';text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;n=len(payload(obj,F)[0]);p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(n//4),sections(p.with_suffix('.elf'))['.text'][1][:n]))
def verify(m,initial,c,s=None,real=False):
 want,calls,result=reference(initial,c,s,real);assert(public(m.memory),m.calls,m.r[2])==(public(want),calls,result),c
def run_suite():
 objects=(o/'original-func_15108C38.o',o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[2] and ps[0]!=ps[1];visited=set();count=0
 for c in corpus():
  initial=fixture(c);machines=[]
  for words in ps:m=PhaseOracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert fullstate(machines[0])==fullstate(machines[1])==fullstate(machines[2]);visited.update(machines[0].visits);count+=1
 assert set(range(source.ENTRY,source.ENTRY+236,4))<=visited;prefixes=delay=0
 for c,real in((Case(),False),(Case(mode=255,flag=128),False),(Case(alias=8,flag=255),False),(Case(flag=0),True)):
  initial=fixture(c);rom=(r/'conker/conker.us.bin').read_bytes();code=helper_code(rom)if real else None;full=PhaseOracle(ps[0],initial,c,connected=code,real=real);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in ps:
    m=PhaseOracle(words,initial,c,connected=code,real=real);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Missing access cut')
    machines.append(m)
   assert fullstate(machines[0])==fullstate(machines[1])==fullstate(machines[2]);assert(machines[0].current_pc,machines[0].delay_of)==(machines[1].current_pc,machines[1].delay_of)==(machines[2].current_pc,machines[2].delay_of);prefixes+=1;delay+=machines[0].delay_of is not None
 rebased=0
 for j,entry in enumerate((0x17007FFC,0x2500FFFC)):
  s={n:entry+0x10000*(i+1)if n in('sinf','func_15144B68','func_15108B80','func_15108BC0')else(0x80417FFC if j==0 else 0x80528004)+i*0x10000 for i,(n,a)in enumerate(symbols().items())};programs=[linked(p,'rebase-'+str(j)+'-'+str(k),s,entry)for k,p in enumerate(objects)]
  for c in(Case(),Case(mode=255,flag=128),Case(alias=8,mode=15,flag=255)):
   initial=fixture(c,s);machines=[]
   for words in programs:m=PhaseOracle(words,initial,c,entry=entry,s=s);m.run();verify(m,initial,c,s);machines.append(m)
   assert fullstate(machines[0])==fullstate(machines[1])==fullstate(machines[2]);rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();code=helper_code(rom);connected_count=0;helper_visited=set()
 for x,y,offset,index,timer,gate,flag in itertools.product((-20.,-7.,1.,7.,20.),(-14.,-1.,8.,20.),(-128,256),(0,999),(-1,3),(0,1),(0,255)):
  c=Case(phases=(bits(x),bits(y)),offset=offset,index=index,timer=timer,gate=gate,flag=flag);initial=fixture(c);machines=[]
  for words in ps:m=PhaseOracle(words,initial,c,connected=code,real=True);m.run();verify(m,initial,c,real=True);helper_visited.update(m.visits);machines.append(m)
  assert fullstate(machines[0])==fullstate(machines[1])==fullstate(machines[2]);connected_count+=1
 coverage=[sum(pc in helper_visited for pc in range(e,e+4*n,4))for e,_,n in HELPERS];assert coverage[1:]==[24,16,30],(coverage,[[hex(pc)for pc in range(e,e+4*n,4)if pc not in helper_visited]for e,_,n in HELPERS])
 assert struct.unpack_from('>I',rom,0x22E6DC)[0]==source.ENTRY;caller_count=0
 for flags,lifetime,index,mode,real,flag in itertools.product((0,1,128,255),(-32768,-1,0,1,32767),(-1,1),(0,207),(False,True),(0,255)):
  c=Case(mode=0 if real else mode,flag=flag);machines=[]
  for words in ps:m,want=caller_machine(rom,words,c,flags,lifetime,index,real);m.run();assert(public(m.memory),m.calls)==want;machines.append(m)
  assert fullstate(machines[0])==fullstate(machines[1])==fullstate(machines[2]);caller_count+=1
 return dict(cases=count,executions=count*3,covered_words=59,frame=32,guards=1,access_prefix_pairs=prefixes,delay_slot_cuts=delay,rebase_layouts=2,rebase_cases=rebased,connected_cases=connected_count,helper_words=174,helper_coverage=coverage,complete_original_timer_and_lookup_and_wrap=True,original_caller_words=41,caller_cases=caller_count,original_callback_table_index=1,callback_pointer_ROM='0x22E6DC',saved_owner_and_state_lifetimes=True,live_flag_after_both_helpers=True,return_value=1,literal_full_state_equal=True,scripted_nonfinite_and_guest_alias_cases=True,native_alias_FCSR_or_gameplay_claimed=False,private_only=True,installed=False,matching_credit=0)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_remaining_donor_candidates import compile_owner
import sys
oracle=sys.modules[__name__]

def controls(body):
 return dict(rate=body.replace('D_800A2484 * *delta','D_800A2480 * *delta'),skip_wrap=body.replace('state[3] = func_15144B68(state[3]);','state[3] = state[3];'),phase=body.replace('sinf(state[3])','sinf(state[2])'),amplitude=body.replace('sinf(state[3]) * D_800A248C','sinf(state[3]) * D_800A2488'),skip_timer=body.replace('    func_15108B80(owner);',''),skip_value=body.replace('    func_15108BC0(owner);',''),result=body.replace('return 1;','return 0;'),cached_clock=body.replace('    f32 *delta = &D_800BE9A4;','    f32 cached = D_800BE9A4;\n    f32 *delta = &cached;'),wrong_true_mode=body.replace('owner[0x12] = 4;','owner[0x12] = 3;'),wrong_false_mode=body.replace('owner[0x12] = 2;','owner[0x12] = 3;'),inverted_flag=body.replace('*((u8 *)state + 0x20) != 0','*((u8 *)state + 0x20) == 0'),cached_flag=body.replace('    state[2] +=','    u8 flag = *((u8 *)state + 0x20);\n    state[2] +=',1).replace('if (*((u8 *)state + 0x20) != 0)','if (flag != 0)'))

def native_harness(body,cases):
 rows=[]
 for c in cases:
  initial=fixture(c);expected,calls,_=reference(initial,c);q=oracle.state(initial,oracle.OWNER)
  statearrays=[','.join('0x%Xu'%read(m,q+4*i)for i in range(8))for m in(initial,expected)]
  arrays=[','.join('0x%Xu'%v for v in values)for values in(c.scales,c.results,[v for _,v in calls[:4]],[read(expected,oracle.symbols()[n])for n in('D_800A2480','D_800A2484','D_800A2488','D_800A248C')])]
  rows.append('{{%s},{%s},{%s},{%s},{%s},{%s},0x%Xu,0x%Xu,%d,%d,%d,%d,%d}'%(*statearrays,*arrays,c.clock,read(expected,oracle.OWNER+0x50),c.offset,c.mode,c.flag,expected[q+32],expected[oracle.OWNER+0x12]))
 return source.HEADERS+r"""
typedef char Pointer32[sizeof(void*)==4?1:-1];
typedef struct {u32 initial[8],expected[8],scales[4],results[4],args[4],afterScales[4],clock,afterOffset;s32 offset,mode;u8 initialFlag,afterFlag,afterMode;} Item;
static const Item cases[]={"""+',\n'.join(rows)+r"""};
static union {u8 bytes[0x820];u32 words[0x208];f32 floats[0x208];} storage;
static const Item *item;static u8 *owner;static f32 *saved;static u32 ordinal,error;
f32 D_800BE9A4,D_800A2480,D_800A2484,D_800A2488,D_800A248C;
static f32 fp(u32 v){union{u32 w;f32 f;}x;x.w=v;return x.f;}
static u32 word(f32 v){union{u32 w;f32 f;}x;x.f=v;return x.w;}
static f32 helper(f32 value,u32 sine){u32 n=ordinal++;
 if(n>=4){error=1;return 0;}if(word(value)!=item->args[n]||sine!=(n>=2))error=1;
 if(n==0&&(item->mode&1)){saved[3]=2;*(s32*)(owner+0x50)=0x400;D_800A2488=3;}
 if(n==1&&(item->mode&2)){saved[2]=-.75f;D_800A248C=-3;}
 if(n==2&&(item->mode&4)){saved[3]=3.25f;D_800A2488=4;}
 if(n==3&&(item->mode&8))D_800A248C=.5f;
 return fp(item->results[n]);}
__attribute__((noinline,noclone)) f32 func_15144B68(f32 x){return helper(x,0);}
__attribute__((noinline,noclone)) f32 sinf(f32 x){return helper(x,1);}
void func_15108B80(u8*p){if(ordinal++!=4||p!=owner)error=1;p[0x30]=0x85;if(item->mode&64)((u8*)saved)[32]^=255;}
void func_15108BC0(u8*p){if(ordinal++!=5||p!=owner)error=1;p[0x31]=0x86;if(item->mode&128)((u8*)saved)[32]=((u8*)saved)[32]?0:128;}
"""+body+r"""
static s32(*volatile callback)(u8*)=func_15108C38;
static int run(void){u32 n,i;u8*p;u32 start;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  item=&cases[n];ordinal=error=0;for(i=0;i<sizeof(storage);i++)storage.bytes[i]=0xA5;
  owner=storage.bytes+16;*(s32*)(owner+0x50)=item->offset;saved=(f32*)(owner+item->offset+0xF8);start=(u8*)saved-storage.bytes;
  for(i=0;i<8;i++)((u32*)saved)[i]=item->initial[i];
  ((u8*)saved)[32]=item->initialFlag;
  D_800BE9A4=fp(item->clock);D_800A2480=fp(item->scales[0]);D_800A2484=fp(item->scales[1]);D_800A2488=fp(item->scales[2]);D_800A248C=fp(item->scales[3]);
  if(callback(owner)!=1||error||ordinal!=6)return 1;
  if(owner[0x12]!=item->afterMode||((u8*)saved)[32]!=item->afterFlag)return 6;
  for(i=0;i<8;i++)if(((u32*)saved)[i]!=item->expected[i])return 2;
  if(*(u32*)(owner+0x50)!=item->afterOffset||owner[0x30]!=0x85||owner[0x31]!=0x86)return 3;
  if(word(D_800BE9A4)!=item->clock||word(D_800A2480)!=item->afterScales[0]||word(D_800A2484)!=item->afterScales[1]||word(D_800A2488)!=item->afterScales[2]||word(D_800A248C)!=item->afterScales[3])return 4;
  p=storage.bytes;for(i=0;i<sizeof(storage);i++)if(!(i>=start&&i<start+33)&&!(i>=0x60&&i<0x64)&&i!=0x40&&i!=0x41&&i!=0x22&&p[i]!=0xA5)return 5;
 }return 0;}
"""+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

def native_cases():
 return [Case(phases=(bits((i%17-8)*.25),bits((i%23-11)*.5)),clock=bits((0.,.125,-.25,1.)[i%4]),offset=(-128,0,256)[i%3],mode=(i%16)|high,flag=flag)for i in range(128)for high in(0,64,128,192)for flag in(0,1,128,255)]
def run_native(selected):
 source.HEADERS=selected[:selected.index('/* Advance')];body=selected[selected.index('/* Advance'):];cases=native_cases();reports={}
 def run(text,name,opt):
  path=o/(name+opt+'.c');exe=path.with_suffix('.elf');path.write_text(native_harness(text,cases));p=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(path),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert p.returncode==0 and not p.stdout and not p.stderr,p.stdout+p.stderr;return subprocess.run([str(exe)],capture_output=True).returncode
 for opt in('-O0','-O2','-O3'):
  code=run(body,'native',opt);assert code==0,(opt,code);reports[opt]=dict(exit=0,cases=len(cases),UBSan=True)
 witnesses={}
 for name,bad in controls(body).items():
  assert bad!=body
  if name=='cached_clock':continue
  code=run(bad,'negative-'+name,'-O2');assert code in range(1,7),(name,code);witnesses[name]=code
 return dict(cases_per_profile=len(cases),profiles=reports,native_controls=len(witnesses),effective_native_controls=witnesses,guest_only_controls=['cached_clock'],SDK32=True,finite_scripted_math=True,owner_and_state_canaries_checked=True,all_four_flag_representations=True,live_flag_after_both_helpers=True,guest_alias_or_FCSR_or_gameplay_claimed=False)
def compiled_controls(selected):
 headers=selected[:selected.index('/* Advance')];body=selected[selected.index('/* Advance'):];witnesses={}
 for name,bad in controls(body).items():
  assert bad!=body;obj,diag=compile_owner(r,o,headers+bad,'control-'+name);assert not diag,diag;words=oracle.linked(obj,'linked-control-'+name);witness=None
  for c in oracle.corpus():
   initial=oracle.fixture(c);m=oracle.PhaseOracle(words,initial,c);m.run()
   try:oracle.verify(m,initial,c)
   except AssertionError:witness=dict(mode=c.mode,alias=c.alias,flag=c.flag);break
  assert witness is not None,('ineffective compiled control',name);witnesses[name]=witness
 return dict(count=len(witnesses),semantic_witnesses=witnesses,guest_only_controls=['cached_clock'],compiler_or_oracle_errors_accepted=False)
