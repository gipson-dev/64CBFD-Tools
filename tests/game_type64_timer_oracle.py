import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_type64_timer_match as match
root=match.ROOT;out=match.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x151041E4;REC=0x30000;OWNER=0x31000;OTHER=0x32000;ACTOR=0x33000;POS=0x34000;ALT=0x35000;ALT_ACTOR=0x36000;TICKS=0x800BEA08;DELTA=0x800BE9E4;FLAG=0x800BEA0C
START=0x100176C4;AUDIO=0x10010F30;END=0x1000E2F4;ADJUST=0x151254F4;FADE=0x151D66F0;RELEASE=0x1516972C
SIGNATURE={START:0,AUDIO:5,END:1,ADJUST:2,FADE:2,RELEASE:1}
@dataclass(frozen=True)
class Case:
 state:int;selector:int;timer:int;fade:int;ticks:int;delta:int;height:int;mutation:int;phase:int;seed:int=0

def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-2048,512)}
 for base,n in ((REC,0x30),(OWNER,0x400),(OTHER,0x200),(ACTOR,0x800),(POS,0x20),(ALT,0x400),(ALT_ACTOR,0x800)):
  m.update({base+i:(i*13+0x21)&255 for i in range(n)})
 for a in (TICKS,DELTA,FLAG):m.update({a+i:0 for i in range(4)})
 put(m,REC+0x10,OWNER);put(m,REC+0x14,OTHER);put(m,REC+0x18,c.timer,2);m[REC+0x1a]=c.state;m[REC+0x1b]=c.fade;m[REC+0x1c]=c.selector
 put(m,OWNER+0x2d0,POS);put(m,OWNER+0x318,ACTOR);put(m,ALT+0x318,ALT_ACTOR);m[OWNER+0x13f]=0x37;m[OTHER+0x13f]=0x71;put(m,POS+8,c.height);put(m,TICKS,c.ticks);put(m,DELTA,c.delta)
 return m

def public(m):return {a:v for a,v in m.items() if not STACK-2048<=a<STACK+512}
def signed32(x):
 x &= 0xFFFFFFFF
 return x if x < 0x80000000 else x-0x100000000
def reference(c):
 m=fixture(c);events=[]
 def call(t,*a):
  events.append((t,a))
  if c.mutation and t==START:put(m,REC+0x10,ALT);put(m,REC+0x14,ALT)
  if c.mutation and t==ADJUST:put(m,OWNER+0x318,ALT_ACTOR)
 state=c.state;owner=OWNER
 if state==0:
  h=struct.unpack('>f',struct.pack('>I',c.height))[0];trigger=False
  if c.selector==0:trigger=h>=19.0
  elif c.selector==1:
   if c.delta<c.timer:put(m,REC+0x18,c.timer-c.delta,2)
   else:trigger=True
  if trigger:
   m[REC+0x1a]=1;m[FLAG]=1;call(START)
   for a in ((0x5b2,0x7fff,0,0,0),(0x5b2,0x7fff,127,0xffffff9c,0))*2:call(AUDIO,*a)
   call(FADE,210,2);call(ADJUST,read(m,owner+0x318),m[OTHER+0x13f]);put(m,read(m,owner+0x318)+0x674,0)
 elif state==1:
  value=signed32(c.fade+c.ticks*10)
  if value>=255:m[REC+0x1b]=255;m[REC+0x1a]=2;put(m,REC+0x18,180,2)
  else:m[REC+0x1b]=value&255
 elif state==2:
  if c.ticks<c.timer:put(m,REC+0x18,c.timer-c.ticks,2)
  else:
   m[FLAG]=0;call(END,0);call(ADJUST,read(m,owner+0x318),m[owner+0x13f]);put(m,read(m,owner+0x318)+0x674,0);m[REC+0x1a]=3
 elif state==3:
  value=signed32(c.fade-c.ticks*10)
  if value<=0:call(RELEASE,REC);call(FADE,0,0)
  else:call(FADE,(signed32(value*210)>>8)&0xFFFFFFFF,2);m[REC+0x1b]=value&255
 return public(m),events
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(REC,));self.initialregs=self.r[:];self.initialf=self.f[:];self.calls2=[]
 def record_call(self,t):
  assert t in SIGNATURE,hex(t);a=tuple(self.arguments(SIGNATURE[t]));self.calls2.append((t,a));self.calls.append((t,a))
 def hook(self,t):
  if self.case.mutation and t==START:put(self.memory,REC+0x10,ALT);put(self.memory,REC+0x14,ALT)
  if self.case.mutation and t==ADJUST:put(self.memory,OWNER+0x318,ALT_ACTOR)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000

def load(path):
 data,fs,rs=parse_object(path);a,n=fs['func_151041E4']['value'],fs['func_151041E4']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};syms={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};return tuple(bound_blob(data[a:a+n],refs,{nm:syms[nm] if nm in syms else int(nm.split('_',1)[1],16) for es in refs.values() for _,nm in es}))
