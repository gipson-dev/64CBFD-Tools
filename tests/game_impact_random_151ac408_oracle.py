from pathlib import Path
import sys,struct,itertools
from dataclasses import dataclass
from tools.experiments import game_impact_random_151ac408_match as packet_module
root=packet_module.ROOT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
out=packet_module.OUT
ENTRY=0x151ac408;SELECT=0x151d8e20;RAND=0x150ada20;EFFECTA=0x151d9b8c;EFFECTB=0x151dab58
ACTOR=0x22000;PAYLOAD=0x24000;OTHER=0x25000;RECORDS=0x30000;RESULT=0x38000
S=dict(func_151D8E20=SELECT,func_150ADA20=RAND,func_151D9B8C=EFFECTA,func_151DAB58=EFFECTB)
u32=lambda x:x&0xffffffff
@dataclass(frozen=True)
class Case:
 phase:int;index:int;selector:int;first:int;second:int;mode:int;pattern:int;result:int=RESULT;height:int=0x3fc00000
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-512,256)}
 for base,length in ((ACTOR,0x120),(PAYLOAD,0x80),(OTHER,0x80),(RECORDS-100,200),(RESULT,0x20)):m.update({base+i:(i*13+0x59)&255 for i in range(length)})
 for i in range(-4,5):
  put(m,RECORDS+20*i,bits(float(i)+0.25));put(m,RECORDS+20*i+8,bits(float(i)-0.5))
 put(m,ACTOR+0x94,RECORDS);put(m,ACTOR+0x98,PAYLOAD);put(m,ACTOR+0x60,c.height);m[ACTOR+0x2d]=c.index&255;m[ACTOR+0xc]=0x92;m[ACTOR+1]=0x63
 put(m,PAYLOAD,(0,0x80000000,0x3f800000,0xc0200000,0x3fa00000)[c.pattern]);m[PAYLOAD+0x1b]=0x84
 return m
def args(c):return (ACTOR,0x3f000000,0x40000000,0xbf800000,c.height,c.result)
def public(m):return {a:b for a,b in m.items() if not STACK-1024<=a<STACK+512}
def mutate(m,c,target,ordinal,home):
 if target==SELECT and c.mode&1:
  put(m,PAYLOAD,bits(3.25));m[PAYLOAD+0x1b]^=0x55;m[ACTOR+0xc]^=0xaa;m[ACTOR+1]^=0x55;put(m,ACTOR+0x98,OTHER);put(m,ACTOR+0x94,RECORDS+20);m[ACTOR+0x2d]=0
 if target==RAND and c.mode&2:
  for i,v in enumerate((bits(9),bits(-10),bits(11))):put(m,home-20+i*4,v)
 if target in (EFFECTA,EFFECTB) and c.mode&4:
  put(m,ACTOR+0x98,OTHER);m[PAYLOAD+0x20]=0x77
def reference(c):
 m=fixture(c);home=STACK+c.phase;payloadptr=read(m,ACTOR+0x98);records=read(m,ACTOR+0x94);index=c.index
 for i,v in enumerate((read(m,records+index*20),c.height,read(m,records+index*20+8))):put(m,home-20+4*i,v)
 calls=[(SELECT,())];mutate(m,c,SELECT,0,home);calls.append((RAND,()));mutate(m,c,RAND,1,home)
 if c.first&1:
  calls.append((RAND,()));mutate(m,c,RAND,2,home);scale=bits(floating(read(m,payloadptr))*6.0)
  event=(c.selector&255,scale,m[payloadptr+0x1b],c.result,home-20,(c.second%41)+80,1,1,0,m[ACTOR+0xc],m[ACTOR+1]);target=EFFECTA
 else:
  scale=bits(floating(read(m,payloadptr))*1.5);event=(c.selector&255,scale,m[payloadptr+0x1b],home-20,1,m[ACTOR+0xc],m[ACTOR+1]);target=EFFECTB
 calls.append((target,event));position=tuple(read(m,home-20+4*i) for i in range(3));mutate(m,c,target,0,home);m[payloadptr+0x20]=4
 return public(m),calls,position,1
class Machine(FactoryOracle):
 def __init__(self,w,c):super().__init__(w,fixture(c),c,entry=ENTRY,s=S,arguments=args(c));self.randoms=0;self.position=[];self.home=STACK+c.phase
 def record_call(self,t):
  counts={SELECT:0,RAND:0,EFFECTA:11,EFFECTB:7};assert t in counts,hex(t);a=tuple(self.arguments(counts[t]));self.calls.append((t,a))
  if t in (EFFECTA,EFFECTB):
   p=a[4 if t==EFFECTA else 3];self.position.append(tuple(read(self.memory,p+4*i)for i in range(3)))
 def hook(self,t):
  if t==RAND:self.randoms+=1;v=self.case.first if self.randoms==1 else self.case.second
  else:v=self.case.selector if t==SELECT else 0x76543210
  mutate(self.memory,self.case,t,self.randoms,self.home)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000;self.r[2]=u32(v)
def program(path):
 d,r=payload(path,'func_151AC408');return bound_blob(d,r,S)
def programs():
 rom=(root/'conker/conker.us.bin').read_bytes();return [struct.unpack_from('>82I',rom,0x1d98b8)]+[program(out/(x+'.o')) for x in ('after','generated','generic')]
def run():
 count=0;streams=programs()
 for phase,index,selector,first,second,mode,pattern in itertools.product((0,8),(-2,2),(0,255),(0,1),(0,40,0xffffffff),(0,1,2,4,7),range(5)):
  c=Case(phase,index,selector,first,second,mode,pattern);want,calls,position,value=reference(c)
  for words in streams:
   m=Machine(words,c).run();assert (public(m.memory),m.calls,m.position,m.r[2])==(want,calls,[position],value),(c,m.calls,calls)
  count+=1
 print('independent randomized impact model:',count,'cases per stream, both branches and helper mutations',flush=True)
