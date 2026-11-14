from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,STOP,RANDOM,GROUND,ATTACHED,FREE=0x151a8cec,0x151464b8,0x150ada68,0x15046c80,0x151a8f1c,0x151a8f6c
OWNER,OTHER,SPATIAL,MARK=0x30000,0x31000,0x32000,0x33000
GATES,EMITTERS,GATE,EMIT,TIME=0x8008f980,0x8008f970,0x20000000,0x21000000,0x800be9a4
u32=lambda v:v&0xffffffff
signed=lambda v:((v&255)^128)-128
fb=lambda v:bits(rounded(v))
@dataclass(frozen=True)
class Case:
 flags:int=15
 mode:int=255
 selector:int=0
 attached:int=1
 spatial:int=1
 gate:int=1
 stop:int=0
 ground:int=0
 accumulator:float=1.25
 mutation:int=0
 phase:int=0
 seed:int=0
def gate(mode):return GATE+(signed(mode)+128)*4
def emit(selector):return EMIT+(signed(selector)+128)*4
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,512)}
 for p in (OWNER,OTHER,SPATIAL,MARK):m.update({p+i:(i*19+c.seed*7)&255 for i in range(256)})
 state=OWNER+40;m[state]=c.flags;m[state+37]=c.mode;m[state+38]=c.selector;put(m,state+4,OTHER if c.attached else 0);put(m,state+80,SPATIAL if c.spatial else 0)
 for at,v in ((state+8,.25),(state+12,.5),(state+40,c.accumulator),(state+44,-2.),(state+84,.5),(TIME,.5)):put(m,at,fb(v))
 # Seed selected entries at the original neighboring table bases.
 put(m,GATES+4*signed(c.mode),gate(c.mode));put(m,EMITTERS+4*signed(c.selector),emit(c.selector));put(m,MARK,0)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def effect(m,c,stage,index):
 state=OWNER+40
 if not c.mutation:return
 if stage=='gate':m[state]^=2;put(m,state+4,OTHER)
 elif stage=='stop':m[state]^=1
 elif stage=='random':
  for at,v in ((state+8,.75),(state+12,.25),(state+84,.75),(TIME,.25)):put(m,at,fb(v))
 elif stage=='position':
  m[state]^=2
  if index==0:m[state+38]=255 if c.selector==255 else c.selector
 elif stage=='ground':put(m,state+44,fb(-7.-index))
 elif stage=='emit' and index==0:put(m,state+40,fb(3.25))
def position(m,c,args,index):
 _,vec,out0,out1=args
 for at,v in ((vec,10.+index),(vec+4,20.+index),(vec+8,30.+index),(out0,40.+index),(out1,50.+index)):put(m,at,fb(v))
 effect(m,c,'position',index)
def reference(initial,c):
 m=dict(initial);calls=[];observed=[];state=OWNER+40;home=STACK+c.phase;vec,out0,out1=home-20,home-28,home-24
 def call(t,a,stage,index=0):calls.append((t,tuple(map(u32,a))));effect(m,c,stage,index)
 mode=signed(m[state+37])
 if mode!=-1:
  call(read(m,GATES+4*mode),(OWNER,),'gate')
  if not c.gate:put(m,OWNER+14,65535,2);return m,calls,observed
 if m[state]&4 and read(m,state+80):
  call(STOP,(read(m,state+80),),'stop')
  if c.stop:return m,calls,observed
 if not m[state]&1:return m,calls,observed
 call(RANDOM,(),'random')
 increment=rounded(rounded(rounded(floating(read(m,state+8))+rounded(.5*floating(read(m,state+12))))*floating(read(m,TIME)))*floating(read(m,state+84)))
 put(m,state+40,fb(floating(read(m,state+40))+increment))
 if not floating(read(m,state+40))>1:return m,calls,observed
 retained=m[home-29];which=ATTACHED if m[state]&2 and read(m,state+4) else FREE;index=0
 while True:
  a=(OWNER,vec,out0,out1);calls.append((which,a));position(m,c,a,index)
  if m[state]&8:put(m,vec+4,read(m,out1));retained=1
  else:
   call(GROUND,(vec,0,read(m,out1),state+44),'ground',index)
   if (c.ground+index)&1:put(m,vec+4,read(m,state+44))
   else:put(m,vec+4,read(m,out1));retained=1
  selector=signed(m[state+38])
  if selector!=-1:
   t=read(m,EMITTERS+4*selector);a=(OWNER,vec,read(m,out0),retained);calls.append((t,a));observed.append((tuple(read(m,vec+4*i) for i in range(3)),a[2],a[3]));effect(m,c,'emit',index)
  put(m,state+40,fb(floating(read(m,state+40))-1.));index+=1;assert index<10
  if not floating(read(m,state+40))>1:break
 return m,calls,observed
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None):
  self.observed=[];self.positions=0;self.grounds=0;self.emits=0
  super().__init__(words,initial,c,entry=entry,arguments=(OWNER,),connected=connected);self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in (0,1,2,60):
   a,b=floating(self.f[fs]),floating(self.f[ft])
   if fn==60:self.condition=a<b
   else:self.f[fd]=fb(a+b if fn==0 else a-b if fn==1 else a*b)
   self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  n=4 if t in (GROUND,ATTACHED,FREE) or EMIT<=t<EMIT+1024 else 0 if t==RANDOM else 1
  a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if EMIT<=t<EMIT+1024:self.observed.append((tuple(read(self.memory,a[1]+4*i) for i in range(3)),a[2],a[3]))
 def hook(self,t):
  a=self.calls[-1][1];c=self.case;m=self.memory
  if GATE<=t<GATE+1024:effect(m,c,'gate',0);answer=c.gate
  elif t==STOP:effect(m,c,'stop',0);answer=c.stop
  elif t==RANDOM:effect(m,c,'random',0);answer=fb(.5)
  elif t in (ATTACHED,FREE):position(m,c,a,self.positions);self.positions+=1;answer=0
  elif t==GROUND:effect(m,c,'ground',self.grounds);answer=(c.ground+self.grounds)&1;self.grounds+=1
  else:assert EMIT<=t<EMIT+1024,hex(t);effect(m,c,'emit',self.emits);self.emits+=1;answer=0
  for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=answer;self.hi,self.lo=0xa5000010,0xa5000011
  if t==RANDOM:self.f[0]=answer
def cases():
 for i,(flags,mode,attached,accumulator,mutation,phase,seed) in enumerate(itertools.product((0,1,3,5,9,15),(255,0,1),(0,1),(-1.,1.,3.5),(0,1),(0,8),(0,1))):
  yield Case(flags=flags,mode=mode,attached=attached,accumulator=accumulator,mutation=mutation,phase=phase,seed=seed,selector=(255,0,1,128,127)[i%5],spatial=(i//2)%2,gate=(i//3)%2,stop=(i//5)%2,ground=(i//7)%2)
def machine_state(m):return m.memory,m.r,m.f,m.trace,m.calls,m.events,m.observed,m.hi,m.lo,m.condition
def verify(m,initial,c):
 expected,calls,obs=reference(initial,c);assert (public(m.memory),m.calls,m.observed)==(public(expected),calls,obs),c
 assert m.r[29]==m.before[29] and all(m.r[i]==m.before[i] for i in (*range(16,24),28,30,31)) and m.f[20:]==m.before_f[20:]
def run():
 r=Path.cwd();o=r/'conker/build/game-effect-update-151a8cec-screen';sy={a[1]:a[2][1] for a in symbol_rows((r/'conker/build/conker.us.elf').read_bytes())};programs=[bound_blob(*payload(o/f,'func_151A8CEC'),sy) for f in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[1]==programs[2]
 seen=set();count=0
 for c in cases():
  initial=fixture(c);states=[]
  for p in programs:
   m=Oracle(p,initial,c);m.run();verify(m,initial,c);states.append(machine_state(m));seen.update(m.visits)
  assert states[0]==states[1]==states[2];count+=1
 missing=set(range(ENTRY,ENTRY+560,4))-seen;assert missing=={0x151a8d60},[hex(a) for a in sorted(missing)]
 prefixes=0
 for c in (Case(),Case(flags=1,mutation=1),Case(mode=0,gate=0),Case(flags=5,stop=1)):
  initial=fixture(c);whole=Oracle(programs[0],initial,c);whole.run()
  for cut in range(whole.all_accesses):
   states=[]
   for p in programs:
    m=Oracle(p,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('missing fired boundary')
    states.append(machine_state(m))
   assert states[0]==states[1]==states[2];prefixes+=1
 caller_cases=0;rom=(r/'conker/conker.us.bin').read_bytes();window_start,end=0x15149294,0x151492b8;window=struct.unpack_from('>9I',rom,window_start-0x15000000+0x2d4b0)
 assert struct.unpack_from('>I',rom,0x22f03c)[0]==ENTRY
 for flags,mode,mutation,phase in itertools.product((1,15),(255,0),(0,1),(0,8)):
  c=Case(flags=flags,mode=mode,mutation=mutation,phase=phase);initial=fixture(c);put(initial,0x8008a57c,ENTRY);expected,calls,obs=reference(initial,c)
  for p in programs:
   code=dict(zip(range(ENTRY,ENTRY+560,4),p));code[end]=0;m=Oracle(window,initial,c,entry=window_start,connected=code);m.r[2]=0x25;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary missing')
   assert (public(m.memory),m.calls,m.observed)==(public(expected),[(ENTRY,(OWNER,))]+calls,obs),c
  caller_cases+=1
 report=dict(cases=count,executions=(count+caller_cases)*3,caller_window_cases=caller_cases,dispatch_table_slot='D_8008A4E8[0x25]',observed_words=len(seen),unreachable_retail_word='0x151A8D60',access_prefixes=prefixes,helpers_modeled=True,retained_flag_guest_only=True)
 (o/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':run()
