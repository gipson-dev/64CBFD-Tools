"""Impact response: six-word callback ABI, ordered captures and bounded original helpers."""
from dataclasses import dataclass,replace
import itertools,struct,math
from tools.experiments import game_record_impact_response_match as source
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import test_game_actor_burst_consumer_match as faults
ACTOR,PAYLOAD,OTHER,RECORDS,MARK=0x22000,0x24000,0x25000,0x30000,0x38000
QUERY,RANDOM,CREATE_A,CREATE_B=0x150A29C8,0x150ADA20,0x1513C73C,0x1513C5B0
STATE,BYTE,COLORS=0x800BE9F0,0x800E0A10,0x800AB414
WINDOW,END,WINDOW_ROM=0x15148D30,0x15148DCC,0x1761E0
FLOATS=(0,0x80000000,0x3F800000,0xC0200000,0x3FA00000,0xBF400000,0x0DA24260,0x60AD78EC)
COPY_BITS=FLOATS+(0x7F800000,0xFF800000,0x7FC12345)
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
sbyte=lambda v:((v&255)^128)-128
@dataclass(frozen=True)
class Case:
 cursor:int=0
 byte:int=37
 pattern:int=2
 height:int=0x3FC00000
 result:int=0x12345678
 mode:int=0
 phase:int=0
 actor_layout:int=0
 payload_layout:int=0
 seed:int=0
 selector:int=17
 state:int=1
 query:int=1

def actor_address(c):return ACTOR if not c.actor_layout else STACK+c.phase-64
def payload_address(c):return(PAYLOAD,actor_address(c)+0x78,RECORDS+c.cursor*20)[c.payload_layout]
def args(c):return(actor_address(c),FLOATS[(c.pattern+3)%8],FLOATS[(c.pattern+4)%8],FLOATS[(c.pattern+5)%8],c.height,u32(c.result))
def fixture(c=Case()):
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,2048)}
 for base,length in((ACTOR-32,1024),(PAYLOAD-32,256),(OTHER-32,256),(MARK,32),(RECORDS-130*20,260*20)):
  m.update({base+i:(i*13+c.seed+0x59)&255 for i in range(length)})
 actor=actor_address(c);payload=payload_address(c)
 for i in range(-129,129):
  for axis in range(5):put(m,RECORDS+i*20+4*axis,COPY_BITS[(i+axis+c.pattern)%len(COPY_BITS)])
 put(m,actor+0x94,RECORDS);put(m,actor+0x98,payload);put(m,payload,FLOATS[c.pattern%8]);m[payload+0x1B]=c.byte;m[actor+0x2D]=c.cursor&255;m[actor+12]=c.byte;m[actor+1]=255-c.byte
 put(m,OTHER,FLOATS[(c.pattern+1)%8]);m[OTHER+27]=c.byte^0x55
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def selector_effect(m,c,home,payload):
 actor=actor_address(c)
 if c.mode&1:put(m,payload,bits(3.25));m[payload+27]^=0x55;m[actor+12]^=0xAA;m[actor+1]^=0x55
 if c.mode&2:put(m,actor+0x98,OTHER);put(m,actor+0x94,RECORDS+20);m[actor+45]=(c.cursor+1)&255
 if c.mode&4:put(m,home+16,bits(-19));put(m,home+20,0xABCDEF01)
 if c.mode&8:
  for i,v in enumerate((bits(9),bits(-10),bits(11))):put(m,home-20+4*i,v)

def effect_effect(m,c,home,payload):
 put(m,MARK,read(m,payload+32,1))
 if c.mode&16:put(m,home-4,OTHER)
 if c.mode&32:put(m,actor_address(c)+0x98,OTHER);m[payload+32]=0x77

def clobber(m,home):
 for i in range(4):put(m,home-72+4*i,0xB5000000+i)

def reference(initial,c=Case(),selected=None,home=None):
 m=dict(initial);home=STACK+c.phase if home is None else home;actor=actor_address(c)
 for i,v in enumerate(args(c)[4:],4):put(m,home+4*i,v)
 for i,v in enumerate(args(c)[1:4],1):put(m,home+4*i,v)
 payload=read(m,actor+0x98);put(m,home-4,payload);records=read(m,actor+0x94)
 x=read(m,records+sbyte(m[actor+45])*20);put(m,home-16,c.height);put(m,home-20,x);put(m,home-12,read(m,records+sbyte(m[actor+45])*20+8))
 calls=[(source.SELECTOR,())];selector_effect(m,c,home,payload);clobber(m,home)
 selected=c.selector&255 if selected is None else selected
 payload=read(m,home-4);scale=bits(floating(read(m,payload))*7.0);packet=tuple(read(m,home-20+4*i)for i in range(3));calls.append((source.EFFECT,(selected,scale,m[payload+27],read(m,home+20),home-20,m[actor+12],m[actor+1])))
 effect_effect(m,c,home,payload);clobber(m,home);m[read(m,home-4)+32]=4
 return m,calls,packet

class ImpactOracle(RayOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,selector=source.SELECTOR,effect=source.EFFECT,connected=None,arguments=None):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=args(c)if arguments is None else arguments,connected=connected)
  self.case,self.selector,self.effect=c,selector,effect;self.home=STACK+c.phase;self.payload=read(memory,actor_address(c)+152);self.trace=[];self.packets=[];self.descriptors=[];self.random_calls=0
 def execute(self,word):
  if word>>26==0 and word&63==3:self.r[word>>11&31]=u32(signed(self.r[word>>16&31])>>(word>>6&31));self.r[0]=0
  else:super().execute(word)
 def get(self,address,size):
  v=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,v))
  return v
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  counts={source.ENTRY:6,self.selector:0,self.effect:7,QUERY:2,RANDOM:0,CREATE_A:14,CREATE_B:14};assert target in counts,hex(target);a=tuple(self.arguments(counts[target]));self.calls.append((target,a));self.events.append(('CALL',target,a))
  if target==source.ENTRY:self.home=self.r[29]
  if target==self.effect:self.packets.append(tuple(read(self.memory,a[4]+4*i)for i in range(3)))
  if target in(CREATE_A,CREATE_B):self.descriptors.append(bytes(self.memory[a[0]+i]for i in range(40)))
 def hook(self,target):
  c=self.case;value=0x76543210
  if target==self.selector:selector_effect(self.memory,c,self.home,self.payload);value=c.selector&255
  elif target==self.effect:effect_effect(self.memory,c,self.home,read(self.memory,self.home-4))
  elif target==QUERY:assert self.calls[-1][1]==(0,28);selector_effect(self.memory,c,self.home,self.payload);value=c.query
  elif target==RANDOM:self.random_calls+=1;value=(0xABCDEF00+c.byte+17*self.random_calls)&0xFFFFFFFF
  elif target in(CREATE_A,CREATE_B):effect_effect(self.memory,c,self.home,read(self.memory,self.home-4))
  else:raise AssertionError(hex(target))
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def caller_machine(rom,words,c=Case(),enabled=True):
 c=replace(c,actor_layout=0,payload_layout=0);initial=fixture(c);home=STACK+c.phase;actor=actor_address(c);payload=payload_address(c)
 initial[payload+36]=2 if enabled else 0
 for i,v in enumerate(args(c)[1:4]):put(initial,home+64+4*i,v)
 put(initial,actor+96,c.height)
 for i,v in enumerate(struct.unpack_from('>8I',rom,0x22EF10)):put(initial,source.TABLE+4*i,v)
 connected=dict(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));connected[END]=0;connected[0x15148DC8]=0x24020001
 body=list(struct.unpack_from('>19I',rom,WINDOW_ROM));m=ImpactOracle(body,initial,c,entry=WINDOW,connected=connected,arguments=());m.r[16]=actor;m.r[8]=payload;m.code=WindowCode(m.code,m);m.code.ends=(END,)
 expected_case=replace(c,result=actor+100);want,calls,packet=reference(initial,expected_case,home=home)if enabled else(dict(initial),[],None)
 return m,(want,([(source.ENTRY,args(expected_case))]if enabled else[])+calls,[]if packet is None else[packet],1)

def corpus():
 for cursor in range(-128,128):yield Case(cursor=cursor,byte=cursor&255,pattern=cursor%8,phase=(cursor&1)*8)
 for byte,mode,phase in itertools.product(range(256),(0,1,2,3),(0,8)):yield Case(byte=byte,selector=byte,mode=mode,phase=phase)
 for actor,payload,mode,pattern in itertools.product(range(2),range(3),range(64),(2,3)):yield Case(actor_layout=actor,payload_layout=payload,mode=mode,pattern=pattern)
 for height in COPY_BITS:yield Case(height=height)
