"""Actor status effect: ordered packet/alias reference and original helper/caller."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_actor_status_effect_match as source
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import test_game_actor_burst_consumer_match as faults
RECORD,ACTOR,TIMER,EFFECT,ALT,RULE=0x22000,0x24000,0x26000,0x28000,0x01F42000,0x2C000
PREP,ALLOC,COPY,ZERO,RANDOM=0x15191B8C,0x15167A68,0x10022EC0,0x100226F0,0x151D8E20
WINDOW,END,WINDOW_ROM=0x15158F40,0x15158F6C,0x1863F0
@dataclass(frozen=True)
class Case:
 kind:int=150
 selector:int=0
 byte:int=37
 phase:int=0
 actor_layout:int=0
 timer_layout:int=0
 mode:int=0
 allocated:bool=True
 seed:int=0

def actor_address(c):return(ACTOR,RECORD,RECORD-24,STACK+c.phase-20)[c.actor_layout]
def timer_address(c):return(TIMER+102,RECORD+1,RECORD+12,STACK+c.phase,STACK+c.phase-6,ACTOR+4)[c.timer_layout]
def fixture(c=Case()):
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,2048)}
 for base in(RECORD,ACTOR,TIMER,EFFECT,ALT,RULE):
  m.update({base+i:(i*13+c.seed+0x59)&255 for i in range(-64,0x380)})
 actor=actor_address(c)
 for i in range(-16,0x340):m.setdefault(actor+i,(i*13+c.seed+0x59)&255)
 m[actor+4]=c.kind;m[actor+0x3B]=c.byte;m[actor+0x127]=c.selector;put(m,actor+0x31C,timer_address(c)-0x66)
 put(m,RECORD+0x18,actor);m[RECORD+12]=c.byte;m[RECORD+1]=255-c.byte;m[ALT+12]=0xA1;m[ALT+1]=0xB2
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def provider_effect(m,c,packet):
 if c.mode&1:m[packet+8]^=128
 if c.mode&2:m[RECORD+1]^=0x55;m[actor_address(c)+0x3B]^=0xAA

def reference(initial,c=Case(),real=False):
 m=dict(initial);home=STACK+c.phase;packet=home-16;actor=read(m,RECORD+24);calls=[];packets=[]
 # Retail saves the record in its incoming home; timer alias probes can rewrite it.
 put(m,home,RECORD)
 if m[actor+4]not in(0,1,2,3,4,150):return m,calls,packets
 put(m,packet,actor);identity=m[actor+0x3B];put(m,packet+6,300,2);m[packet+8]=m[packet+9]=0;m[packet+4]=identity
 m[packet+10]=3 if m[actor+4]==150 else 0
 if m[actor+0x127]!=255:put(m,read(m,actor+0x31C)+0x66,500,2)
 record=read(m,home);group=m[record+12];context=m[record+1];calls.append((source.HELPER,(packet,0,group,context)));packets.append(bytes(m[packet+i]for i in range(12)))
 provider_effect(m,c,packet)
 if real and c.allocated:
  for i in range(12):m[EFFECT+16+i]=m[packet+i]
  for off,value in((28,0),(32,0),(36,EFFECT+48),(40,EFFECT+768)):put(m,EFFECT+off,value)
  for i in range(720):m[EFFECT+48+i]=0
  m[EFFECT+44]=c.byte
 return m,calls,packets

class StatusOracle(RayOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,helper=source.HELPER,connected=None):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(RECORD,),connected=connected)
  self.case,self.helper,self.trace=c,helper,[];self.packets=[];self.prep_records=[];self.packet=None
 def get(self,address,size):
  v=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,v))
  return v
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  counts={source.ENTRY:1,self.helper:4,PREP:2,ALLOC:6,COPY:3,ZERO:2,RANDOM:0};assert target in counts,hex(target);a=tuple(self.arguments(counts[target]));self.calls.append((target,a));self.events.append(('CALL',target,a))
  if target==self.helper:self.packet=a[0];self.packets.append(bytes(self.memory[a[0]+i]for i in range(12)))
  if target==PREP:self.prep_records.append(bytes(self.memory[a[0]+i]for i in range(5)))
 def hook(self,target):
  a=self.calls[-1][1];c=self.case;value=0x76543210
  if target==self.helper:provider_effect(self.memory,c,self.packet)
  elif target==PREP:assert a[1]==14;provider_effect(self.memory,c,self.packet)
  elif target==ALLOC:assert a[0]==32 and a[2:4]==(768,1)and a[5]==1;value=EFFECT if c.allocated else 0
  elif target==COPY:
   assert a[2]==12
   for i in range(a[2]):self.put(a[0]+i,self.get(a[1]+i,1),1)
   value=a[0]
  elif target==ZERO:
   assert a[1]==720
   for i in range(a[1]):self.put(a[0]+i,0,1)
  elif target==RANDOM:value=0x12340000|c.byte
  else:raise AssertionError(hex(target))
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def caller_machine(rom,words,c=Case(),mask=0,allowed=0,index=0):
 initial=fixture(c);put(initial,RULE+4,allowed);table=rom[0x22FA90:0x22FAEC]
 for i,value in enumerate(struct.unpack('>23I',table)):put(initial,source.TABLE+4*i,value)
 connected=dict(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words));connected[END]=0
 m=StatusOracle(struct.unpack_from('>11I',rom,WINDOW_ROM),initial,c,entry=WINDOW,connected=connected);m.r[4]=RULE;m.r[3]=21;m.r[16]=index;m.r[17]=RECORD;m.r[18]=mask;m.r[22]=source.TABLE;m.code=WindowCode(m.code,m);m.code.ends=(END,)
 enabled=(mask|allowed)==allowed;wanted,calls,packets=reference(initial,c)if enabled else(dict(initial),[],[])
 return m,(wanted,([(source.ENTRY,(RECORD,))]if enabled else[])+calls,packets,index+1)

def corpus():
 for kind,selector,byte,phase in itertools.product(range(256),(0,1,254,255),(0,255),(0,8)):yield Case(kind,selector,byte,phase)
 for byte,kind in itertools.product(range(256),(4,150)):yield Case(kind=kind,byte=byte,mode=byte&3,seed=byte)
 for layout,timer,kind,mode,phase in itertools.product(range(4),range(6),(0,1,4,5,150,255),(0,1,2),(0,8)):yield Case(kind=kind,actor_layout=layout,timer_layout=timer,mode=mode,phase=phase)
