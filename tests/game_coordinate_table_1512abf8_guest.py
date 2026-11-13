from dataclasses import dataclass
from pathlib import Path
import itertools,math,sys
from tools.experiments import game_coordinate_table_1512abf8_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
NAME='func_1512ABF8';ENTRY=0x1512ABF8;PRESET=0x80089590;TARGET=0x800DC200;CLEAR=0x800DC0C0;PLAYERS=0x80082FA0;MODE=0x800BE9F0;BZERO=0x100226F0
SYMS={'D_80089590':PRESET,'D_800DC200':TARGET,'D_800DC0C0':CLEAR,'D_80082FA0':PLAYERS,'D_800BE9F0':MODE,'bzero':BZERO}
@dataclass(frozen=True)
class Case: players:int;mode:int;pattern:int;phase:int=0
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
 for base,n in ((PRESET,32),(TARGET,128),(CLEAR,304)):m.update({base+i:(i*29+0x35)&255 for i in range(n)})
 put(m,PLAYERS,c.players&0xffffffff);put(m,MODE,c.mode&0xffffffff)
 rows=((35,45,400,300),(-32768,32767,1,2),(-3,-1,11,12),(0,1,17,18)) if c.pattern else ((35,45,400,300),(35,45,300,300),(35,45,250,300),(35,45,530,300))
 for i,row in enumerate(rows):
  for j,value in enumerate(row):put(m,PRESET+i*8+j*2,value&65535,2)
 return m
class Machine(FactoryOracle):
 def __init__(self,words,c,m):self.c=c;super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=())
 def execute(self,word):
  op,rs,rt=word>>26,word>>21&31,word>>16&31
  if op==17 and rs==16 and word&63==13:
   self.f[word>>6&31]=math.trunc(floating(self.f[word>>11&31]))&0xffffffff;return
  if op not in (34,38,42,46):return super().execute(word)
  self.own_instruction=True;self.dispatched_word=word
  try:
   at=(self.r[rs]+(((word&65535)^32768)-32768))&0xffffffff;k=at&3;n=4-k if op in (34,42) else k+1
   if op==34:self.r[rt]=(self.get(at,n)<<((4-n)*8))|(self.r[rt]&((1<<((4-n)*8))-1))
   elif op==38:self.r[rt]=(self.r[rt]&~((1<<(n*8))-1))|self.get(at-n+1,n)
   elif op==42:self.put(at,self.r[rt]>>((4-n)*8),n)
   else:self.put(at-n+1,self.r[rt]&((1<<(n*8))-1),n)
   self.r[0]=0
  finally:self.own_instruction=False
 def record_call(self,t):assert t==BZERO;self.calls.append((t,tuple(self.arguments(2))))
 def hook(self,t):
  assert self.calls[-1][1]==(CLEAR,304)
  for i in range(304):self.memory[CLEAR+i]=0
  for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010
def reference(initial,c):
 m=initial.copy()
 def signed16(v):return v-65536 if v&32768 else v
 for group in range(4):
  for index in range(4):
   src=PRESET+index*8;dst=TARGET+group*32+index*8
   for j in range(8):m[dst+j]=m[src+j]
   for factor in ((0.5,) if 0<c.players<4 else ())+((0.75,) if c.mode in (27,30) else ()):
    for off in (0,2):put(m,dst+off,math.trunc(signed16(read(m,dst+off,2))*factor)&65535,2)
 for i in range(304):m[CLEAR+i]=0
 return {a:b for a,b in m.items() if not STACK-512<=a<STACK+512},[(BZERO,(CLEAR,304))]
def words():
 programs=[bound_blob(*payload(out/x,NAME),SYMS) for x in ('retail.o','after.o','generated.o','generic.o')]
 return programs

def run():
 programs=words();assert programs[0]==programs[2]==programs[3]
 count=0;visits=set()
 for vals in itertools.product((-1,0,1,2,3,4,0x7fffffff),(0,27,30,31),(0,1)):
  c=Case(*vals);initial=fixture(c);expected=reference(initial,c)
  for p in programs:
   m=Machine(p,c,initial.copy()).run();actual=({a:b for a,b in m.memory.items() if not STACK-512<=a<STACK+512},m.calls);assert actual==expected,c;visits.update(m.visits)
  count+=1
 print(count,'guest cases per stream passed independent state/call model; bzero modeled')
