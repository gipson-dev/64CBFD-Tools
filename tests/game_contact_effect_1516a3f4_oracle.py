from pathlib import Path
import sys, struct, itertools, math
from dataclasses import dataclass
from tools.experiments import game_contact_effect_1516a3f4_match as packet
root=packet.ROOT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
out=packet.OUT
ENTRY=0x1516A3F4;MODE=0x1510F800;FLOOR=0x1510F8D8;EMIT=0x15167AD8
OWNER=0x30000;TAG=0x8008CADC;FACTOR=0x800A6CC8
S=dict(D_8008CADC=TAG,D_800A6CC8=FACTOR,func_1510F800=MODE,func_1510F8D8=FLOOR,func_15167AD8=EMIT)
u32=lambda x:x&0xffffffff
s16=lambda x:((x&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 phase:int;initial:int;floor:int;alpha:int;factor:int;mutation:int
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-512,128)}
 m.update({OWNER+i:(i*29+0x51)&255 for i in range(0x80)})
 for off,val,size in ((0x14,c.initial,4),(0x20,0x80,2),(0x22,0x60,2),(0x24,0x7ff0,2),(0x26,-71,2),(0x28,177,2),(0x2a,0x20,2),(0x38,0x8833,2),(0x3b,c.alpha,1),(0xc,0xa2,1),(1,0xc3,1)):
  put(m,OWNER+off,u32(val),size)
 put(m,TAG,0x1234fedc);put(m,FACTOR,c.factor)
 return m
def public(m):return {a:b for a,b in m.items() if not STACK-1024<=a<STACK+512}
def mutate(m,c,target):
 if c.mutation and target==MODE:
  put(m,OWNER+0x20,-0x32,2);put(m,OWNER+0x22,0x110,2);m[OWNER+0x3b]=0xb7
 if c.mutation and target==FLOOR:
  put(m,OWNER+0x24,-0x40,2);m[OWNER+0x0c]=0x44
def packet(m,ptr):return bytes(m[ptr+i] for i in range(24))
def reference(c):
 m=fixture(c);calls=[];observations=[];home=STACK+c.phase;p=home-0x24
 threshold=s16(read(m,OWNER+0x22,2))+s16(read(m,OWNER+0x2a,2));height=signed(read(m,OWNER+0x14))
 if height>=threshold:
  calls.append((MODE,(0,)));mutate(m,c,MODE)
  calls.append((FLOOR,tuple(u32(s16(read(m,OWNER+i,2))) for i in (0x20,0x22,0x24))+(0,)))
  mutate(m,c,FLOOR);height=signed(c.floor);put(m,OWNER+0x14,u32(height))
 if height>=threshold:
  put(m,OWNER+0x38,0,2)
  if signed(u32(threshold-height))<50:
   put(m,p+4,0,2);put(m,p+6,256,2);put(m,p,read(m,TAG))
   put(m,p+8,read(m,OWNER+0x20,2),2);put(m,p+10,u32(read(m,OWNER+0x14)+10),2);put(m,p+12,read(m,OWNER+0x24,2),2)
   alpha=m[OWNER+0x3b];m[p+18]=0;m[p+20]=3;scale=(alpha<<12)//5100+204
   put(m,p+14,scale,2);put(m,p+16,scale,2);m[p+21]=alpha
   args=(p,m[OWNER+0x0c],m[OWNER+1]);calls.append((EMIT,args));observations.append(packet(m,p))
 else:
  factor=floating(read(m,FACTOR));a=s16(read(m,OWNER+0x26,2));b=s16(read(m,OWNER+0x28,2))
  put(m,OWNER+0x26,u32(math.trunc(floating(bits(a*factor)))),2);put(m,OWNER+0x28,u32(math.trunc(floating(bits(b*factor)))),2)
 return public(m),calls,observations
class Machine(FactoryOracle):
 def __init__(self,w,c):super().__init__(w,fixture(c),c,entry=ENTRY,s=S,arguments=(OWNER,));self.observations=[]
 def record_call(self,t):
  assert t in (MODE,FLOOR,EMIT),hex(t);n={MODE:1,FLOOR:4,EMIT:3}[t];a=tuple(self.r[4:4+n]);self.calls.append((t,a))
  if t==EMIT:self.observations.append(packet(self.memory,a[0]))
 def hook(self,t):
  mutate(self.memory,self.case,t)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
  self.r[2]=u32(self.case.floor if t==FLOOR else 0xdeadbeef)
def program(path):
 d,r=payload(path,'func_1516A3F4');return bound_blob(d,r,S)
def run():
 rom=(root/'conker/conker.us.bin').read_bytes();programs=[struct.unpack_from('>81I',rom,0x1978a4)]+[program(out/(x+'.o')) for x in ('after','generated','generic')]
 count=0
 for phase,initial,floor,alpha,factor,mutation in itertools.product((0,8),(-0x80000000,0,0x7f,0x80,0x7fffffff),(-0x80000000,0x7f,0x80,0x7fffffff),(0,1,127,255),(0x3f000000,0xbf000000),(0,1)):
  c=Case(phase,initial,floor,alpha,factor,mutation);want=reference(c)
  for words in programs:
   m=Machine(words,c).run();actual=(public(m.memory),m.calls,m.observations)
   assert actual==want,(c,actual[1:],want[1:])
  count+=1
 print('independent model:',count,'cases per stream, complete 24-byte effect payload and helper mutations',flush=True)
