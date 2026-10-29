"""Owner command: ordered link/event alias reference and bounded original pair helpers."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_payload_owner_command_match as source
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
OWNER,EVENT,ALT=0x20000,0x24000,0x26000
WORDS=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678)
@dataclass(frozen=True)
class Case:
 command:int=60
 relation:int=0
 byte:int=37
 flags:int=255
 alias:int=0
 mode:int=0
 phase:int=0
 pattern:int=0

def event_address(c):return(EVENT,OWNER+40,OWNER+44,OWNER+36,OWNER+8,STACK+c.phase+8,STACK+c.phase-4)[c.alias]
def fixture(c=Case()):
 home=STACK+c.phase;event=event_address(c);m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,1024)}
 for base,length in((OWNER-32,256),(EVENT-32,128),(ALT-16,64)):
  m.update({base+i:(i*13+c.byte+0x59)&255 for i in range(length)})
 first=WORDS[c.pattern%6];second=first^0x87654321
 if c.relation==4:second=first
 put(m,event,first);put(m,event+4,second);m[event+8]=0x12;m[event+9]=0xE7
 first,second=read(m,event),read(m,event+4);put(m,OWNER+40,first if c.relation in(0,4)else second if c.relation==1 else first^0x01000000);m[OWNER+44]=m[event+4]if c.relation==3 else m[event+4]^1;m[OWNER+56]=c.flags
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def free_effect(m,c):
 if c.mode&1:m[OWNER+49]^=0x55
 if c.mode&2:put(m,OWNER+40,ALT)

def pair_effect(m,c,event,calls,connected=False):
 command=c.command&255
 if connected:calls.append((source.PAIR,(event,command,OWNER+40,OWNER+44,OWNER)))
 if command==0:
  if read(m,event)==read(m,OWNER+40)or m[event+4]==m[OWNER+44]:
   if connected:calls.append((source.FREE,(OWNER,)))
   free_effect(m,c)
 elif command==45:
  first,current=read(m,event),read(m,OWNER+40)
  if first==current:put(m,OWNER+40,read(m,event+4));m[OWNER+44]=m[event+9]
  elif read(m,event+4)==current:put(m,OWNER+40,first);m[OWNER+44]=m[event+8]

def reference(initial,c=Case(),connected=False):
 m=dict(initial);event=event_address(c);home=STACK+c.phase;put(m,home+8,c.command);put(m,home-4,0xDEAD0000);calls=[];command=c.command&255
 if command in(60,4):
  if read(m,OWNER+40)==read(m,event)or m[OWNER+44]==m[event+4]:
   if command==60:calls.append((source.FREE,(OWNER,)));free_effect(m,c)
   else:m[OWNER+56]&=254
 else:
  calls.append((source.WRAPPER,(event,command,OWNER+40,OWNER+44,OWNER)));pair_effect(m,c,event,calls,connected)
 return m,calls

class CommandOracle(RayOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,free=source.FREE,wrapper=source.WRAPPER,connected=None,arguments=None,callbacks=()):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(OWNER,event_address(c),c.command)if arguments is None else arguments,connected=connected)
  self.case,self.free,self.wrapper,self.trace=c,free,wrapper,[];self.callback_set=set(callbacks)
 def get(self,address,size):
  v=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,v))
  return v
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  counts={source.ENTRY:3,self.free:1,self.wrapper:5,source.PAIR:5,**{t:3 for t in self.callback_set}};assert target in counts,hex(target);a=tuple(self.arguments(counts[target]));self.calls.append((target,a));self.events.append(('CALL',target,a))
 def hook(self,target):
  if target==self.free:free_effect(self.memory,self.case)
  elif target==self.wrapper:pair_effect(self.memory,self.case,self.r[4],[],False)
  else:assert target in self.callback_set
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0x76543210

def corpus():
 for command,relation,byte,phase in itertools.product(range(256),range(5),(0,255),(0,8)):yield Case(command,relation,byte,mode=byte&3,phase=phase)
 for alias,command,relation,phase in itertools.product(range(7),(0,4,45,60,255,0xAB000004,0xAB00003C),range(5),(0,8)):yield Case(command,relation,alias=alias,phase=phase)
 for flags,relation in itertools.product(range(256),range(5)):yield Case(command=4,relation=relation,flags=flags)
