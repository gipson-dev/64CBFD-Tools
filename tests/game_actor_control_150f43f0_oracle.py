"""Actor-control callback model with live helper mutations and input gates."""
import itertools,json,struct
from dataclasses import dataclass
from tools.experiments import game_actor_control_150f43f0_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits
from tools.experiments.game_actor_state_tick_integration import symbol_rows
ACTOR=0x30000;AUDIO=0x1509BFB0;INPUT=0x1509BE40;GATE=0x15123934;EXIT=0x151239CC;START=0x15124B18
@dataclass(frozen=True)
class Case:
 kind:int=0x3B
 state:int=0
 held:int=0
 gate:int=1
 first:int=1
 second:int=0
 mutation:int=0
 phase:int=0
 seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-512,512)};m.update({ACTOR+i:(i*29+c.seed*11+90)&255 for i in range(0x700)});m[ACTOR+0x23E]=c.kind;put(m,ACTOR+0x2C,c.state);put(m,ACTOR+0x6C8,c.held);put(m,ACTOR+0x84,0x1234567F);return m
def effect(m,c,t,ordinal):
 if c.mutation&1 and t==AUDIO and ordinal==0:put(m,ACTOR+0x2C,0);put(m,ACTOR+0x6C8,0)
 if c.mutation&2 and t==GATE:put(m,ACTOR+0x84,0xA0000005)
 if c.mutation&4 and t==START:put(m,ACTOR+0x134,0xDEADBEEF);put(m,ACTOR+0x190,bits(99.))
 if c.mutation&8 and t==INPUT and ordinal==0:put(m,ACTOR+0x84,0x12340005)
 if c.mutation&16 and t==INPUT and ordinal==1:put(m,ACTOR+0x84,0x90000007)
def reference(initial,c):
 m=dict(initial);calls=[];counts={AUDIO:0,INPUT:0}
 def call(t,a):
  ordinal=counts.get(t,0);counts[t]=ordinal+1;calls.append((t,a));effect(m,c,t,ordinal)
  if t==GATE:return c.gate
  if t==INPUT:return (c.first,c.second)[ordinal]
  return 0x87654321
 if m[ACTOR+0x23E]==0x3B:
  call(AUDIO,(0,0x405C,1))
  if read(m,ACTOR+0x2C)!=0x100 and read(m,ACTOR+0x6C8)==0:
   if call(GATE,(ACTOR,8,0,0,0)):
    f=read(m,ACTOR+0x84)|0x300000;put(m,ACTOR+0x84,f);put(m,ACTOR+0x84,f&0xFFFFFFFB);put(m,ACTOR+0x1B4,1,2);put(m,ACTOR+0x1E0,3,2);call(START,(ACTOR,))
   for off,val in ((0x134,0),(0x348,bits(125.)),(0x34C,bits(125.)),(0x374,bits(220.)),(0x190,bits(30.))):put(m,ACTOR+off,val)
  else:put(m,ACTOR+0x190,0)
 elif read(m,ACTOR+0x2C)==8 and read(m,ACTOR+0x6C8)==0:
  call(EXIT,(ACTOR,0));call(AUDIO,(0,0x405C,0))
 if call(INPUT,(1,0x4054,6,0x9000)) and not call(INPUT,(1,0x405E,6,0x9000)):put(m,ACTOR+0x84,read(m,ACTOR+0x84)|0x80000000)
 else:put(m,ACTOR+0x84,read(m,ACTOR+0x84)&0x7FFFFFFF)
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=p.ENTRY,connected=None):
  self.c=c;self.counts={};super().__init__(words,fixture(c),c,entry=entry,arguments=(ACTOR,),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  sizes={AUDIO:3,INPUT:4,GATE:5,EXIT:2,START:1};assert t in sizes,hex(t);self.calls.append((t,tuple(self.arguments(sizes[t]))))
 def hook(self,t):
  ordinal=self.counts.get(t,0);self.counts[t]=ordinal+1;effect(self.memory,self.c,t,ordinal);value=self.c.gate if t==GATE else (self.c.first,self.c.second)[ordinal]if t==INPUT else 0x87654321
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True;self.r[2]=value&0xFFFFFFFF
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');lookup={r[1]:r[2][1]for r in symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});truth=struct.unpack_from('>96I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM);assert tuple(words)==truth[:94] and truth[94:]==(0,0)
 cases=[]
 for i,(kind,state,held,gate,first,second,mutation)in enumerate(itertools.product((0,0x3B),(0,8,0x100),(0,1),(0,1),(0,1),(0,1),(0,1,2,4,8,16,31))):cases.append(Case(kind,state,held,gate,first,second,mutation,(i&1)*8,i%5))
 visits=set()
 for c in cases:
  m=Oracle(words,c);m.run();want,calls=reference(m.initial,c);public=lambda x:{a:v for a,v in x.items()if not STACK-512<=a<STACK+512};assert public(m.memory)==public(want),(c,'memory');assert m.calls==calls,(c,m.calls,calls);assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];visits.update(m.visits)
 r=dict(cases=len(cases),raw_equals_retail=True,visited_words=len(visits),missing=[i for i in range(94)if p.ENTRY+i*4 not in visits],helper_mutations_and_short_circuit_checked=True,return_value_not_claimed=True,hardware_and_full_helpers_not_qualified=True,source_installed=False);(p.out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
