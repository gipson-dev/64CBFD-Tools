from pathlib import Path
import sys,struct,itertools
from dataclasses import dataclass
from tools.experiments import game_fade_graphic_151ed09c_match as packet
root=packet.ROOT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import signed
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
out=packet.OUT
ENTRY=0x151ed09c;DRAW=0x151ed430;FINISH=0x15096934;MODE=0x800e0a90;LEVEL=0x800e0b97;STATE=0x800d2dab
BASE=0x30000;LAYER=0x31000;END=0x32000
S=dict(D_80090028=0x80090028,D_8009181C=0x8009181c,D_80091828=0x80091828,D_800E0A90=MODE,D_800E0B97=LEVEL,func_151ED430=DRAW,func_15096934=FINISH)
u32=lambda x:x&0xffffffff
@dataclass(frozen=True)
class Case:
 phase:int;timer:int;level:int;mutation:int;alias:int
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-512,128)}
 for base in (BASE,LAYER,END):m.update({base+i:(i*29+0x51)&255 for i in range(256)})
 put(m,MODE,c.timer);m[LEVEL]=c.level;m[STATE]=0x5a
 return m
def public(m):return {a:b for a,b in m.items() if not STACK-1024<=a<STACK+512}
def result(c,n):return (LAYER if n==1 else END) if not c.alias else (BASE if n==1 else BASE+32)
def mutate(m,c,n):
 if c.mutation and n==1:m[LEVEL]=255-c.level;put(m,MODE,0x12345678)
def reference(c):
 m=fixture(c);calls=[];p=BASE
 put(m,p,0xde000000);put(m,p+4,S['D_80090028']);p+=8
 alpha=signed(u32(c.timer<<2));alpha=255 if alpha>=256 else alpha
 put(m,p,0xfb000000);put(m,p+4,0xffffff00|(alpha&255));p+=8
 calls.append((DRAW,(p,S['D_8009181C'],146,108,8,3,0x3f800000,0)));mutate(m,c,1);p=result(c,1)
 put(m,p,0xe7000000);put(m,p+4,0);put(m,p+8,0xfcffd3ff);put(m,p+12,0xffa6ff7f);put(m,p+16,0xfb000000)
 a=(signed(u32(m[LEVEL]*u32(alpha+1)))>>8)&255;put(m,p+20,0xff802000|a);p+=24
 calls.append((DRAW,(p,S['D_80091828'],146,108,8,3,0x3f800000,0)));mutate(m,c,2);p=result(c,2)
 calls.append((FINISH,(p,)));put(m,p,0xde000000);put(m,p+4,0x80087408);m[STATE]=0
 return public(m),calls,u32(p+8)
class Machine(FactoryOracle):
 def __init__(self,w,c):super().__init__(w,fixture(c),c,entry=ENTRY,s=S,arguments=(BASE,));self.draws=0
 def record_call(self,t):
  assert t in (DRAW,FINISH),hex(t);a=tuple(self.arguments(8 if t==DRAW else 1));self.calls.append((t,a))
 def hook(self,t):
  if t==DRAW:self.draws+=1;mutate(self.memory,self.case,self.draws);value=result(self.case,self.draws)
  else:
   p=self.calls[-1][1][0];self.put(p,0xde000000,4);self.put(p+4,0x80087408,4);self.put(STATE,0,1);value=p+8
  for i in range(8):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000;self.r[2]=u32(value)
def program(path):
 d,r=payload(path,'func_151ED09C');return bound_blob(d,r,S)
def run():
 rom=(root/'conker/conker.us.bin').read_bytes();programs=[struct.unpack_from('>81I',rom,0x21a54c)]+[program(out/(x+'.o')) for x in ('after','generated','generic')];count=0
 for phase,timer,level,mutation,alias in itertools.product((0,8),(0,1,63,64,255,0x1fffffff,0x20000000,0x7fffffff,0x80000000,0xffffffff),(0,1,127,255),(0,1),(0,1)):
  c=Case(phase,timer,level,mutation,alias);want=reference(c)
  for words in programs:
   m=Machine(words,c).run();actual=(public(m.memory),m.calls,m.r[2]);assert actual==want,(c,actual[1:],want[1:])
  count+=1
 print('independent fade renderer model:',count,'cases per stream with draw mutation and buffer aliases',flush=True)
