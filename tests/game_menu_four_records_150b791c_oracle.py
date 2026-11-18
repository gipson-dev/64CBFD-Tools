"""Independent four-record descriptor/release model, including mismatched retail gates."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_menu_four_records_150b791c_match as source
p=source.OUT;f=source.FROZEN;ENTRY=0x150B791C
BASE,STATE,MARK=0x800D9898,0x800D9890,0x70000
FREE,CREATE=0x1516972C,0x15169968
FIRST_ASSET,FINAL_ASSET=0x8009190C,0x800918E8
SLOTS=(2,5,6,7,9)
data=lambda m,a,n:bytes(m[a+i]for i in range(n))
public=lambda m:{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
@dataclass(frozen=True)
class Case:
 presence:int=31;failure:int=0;mutation:int=0;phase:int=0;seed:int=0
def cases():
 for presence,failure,mutation in itertools.product(range(32),(0,1,4,8,15),(0,1,2,4,7)):
  seed=(presence*31+failure*11+mutation*3)&255
  yield Case(presence,failure,mutation,8*(seed&1),seed)
def packet(c,home=None):return(STACK+c.phase if home is None else home)-60
def fields():
 return [(0,FIRST_ASSET,4),(4,0,4),(8,0,4),(12,150,4),(16,0,4),*((off,0,2)for off in(0x14,0x16,0x18)),(0x1C,0x43660000,4),(0x20,0x43160000,4),
  (0x24,0,2),(0x26,0,2),(0x28,4096,2),(0x2A,4096,2),(0x2C,64,2),(0x2E,16,2),
  *((0x30+i,v,1)for i,v in enumerate((5,3,255,0,0,128,7,17,1,0)))]
DEFINED=tuple(sorted({off+i for off,v,n in fields()for i in range(n)}));assert len(DEFINED)==56
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for a,n in((BASE-16,80),(MARK,4)):m.update({a+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for i,slot in enumerate(SLOTS):put(m,BASE+4*slot,0x50000+i*0x1000 if c.presence&(1<<i)else 0)
 m[STATE]=c.seed;return m
class Service:
 def __init__(self,m,c):self.m,self.c=m,c;self.calls=[];self.retained=None;self.creates=0
 def globals(self,ordinal,bias):
  for i,slot in enumerate(SLOTS):put(self.m,BASE+4*slot,0 if(self.c.seed+ordinal+i)&3==0 else bias+ordinal*0x1000+i*0x100)
  self.m[STATE]=(self.c.seed+ordinal+0x33)&255
 def invoke(self,target,arg):
  m,c=self.m,self.c;ordinal=len(self.calls);observed=b''
  if target==CREATE:self.retained=arg;observed=data(m,arg,60);normalized='descriptor'
  else:assert target==FREE;normalized=arg # Retail can release a null first result.
  self.calls.append((target,normalized,observed));put(m,MARK,(0x13579BDF+ordinal*0x10203+target)&0xFFFFFFFF)
  if target==FREE:
   if c.mutation&1:self.globals(ordinal,0x60000)
   if c.mutation&2 and self.retained is not None:
    for i in range(60):m[self.retained+i]=(c.seed+i*7+ordinal*11)&255
   return 0xDEADBEEF
  if c.mutation&4:
   for i in range(60):m[arg+i]=(c.seed+i*13+ordinal*17)&255
   self.globals(ordinal,0xA0000)
  index=self.creates;self.creates+=1
  return 0 if c.failure&(1<<index)else 0x80000+c.seed*0x100+index*0x10000
def reference(initial,c,home=None):
 m=dict(initial);s=Service(m,c);at=packet(c,home);old=read(m,BASE+8)
 if old:s.invoke(FREE,old);put(m,BASE+8,0)
 for off,v,n in fields():put(m,at+off,v,n)
 old=read(m,BASE+20)
 if old:s.invoke(FREE,old)
 first=s.invoke(CREATE,at);put(m,BASE+20,first)
 for off,v,n in((0x16,256,2),(8,256,4),(0x35,255,1),(0x20,0x432A0000,4),(12,170,4)):put(m,at+off,v,n)
 if read(m,BASE+24):s.invoke(FREE,first)
 put(m,BASE+24,s.invoke(CREATE,at))
 for off,v,n in((0x16,512,2),(8,512,4),(0x35,128,1),(0x20,0x433E0000,4),(12,190,4)):put(m,at+off,v,n)
 if read(m,BASE+28):s.invoke(FREE,read(m,BASE+20))
 put(m,BASE+28,s.invoke(CREATE,at))
 for off,v,n in((0x14,0,2),(0x16,0,2),(0x18,0,2),(0x31,0,1),(0x2C,88,2),(0x2E,64,2),(0x35,255,1),(0x30,0,1),(0,FINAL_ASSET,4),(0x1C,0x43660000,4),(0x20,0x432A0000,4)):put(m,at+off,v,n)
 old=read(m,BASE+36)
 if old:s.invoke(FREE,old)
 put(m,BASE+36,s.invoke(CREATE,at));m[STATE]=3
 return m,s
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None):
  super().__init__(words,initial,c,entry=entry,s={},arguments=(),connected=connected)
  self.service=Service(self.memory,c);self.saved=tuple(self.r[16:24])+tuple(self.r[28:]);self.saved_fp=tuple(self.f[20:])
 def record_call(self,target):
  assert target in(FREE,CREATE);self.pending=target,self.arguments(1)[0]
 def hook(self,target):
  assert self.pending[0]==target;answer=self.service.invoke(*self.pending)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=answer&0xFFFFFFFF
def streams():
 from tools.tests.game_menu_four_records_150b791c_proof import derive
 syms={v[1]:v[2][1]for v in symbol_rows((f/'conker/build/conker.us.elf').read_bytes())}
 raw=bound_blob(*payload(p/'owner.o','func_150B791C'),syms)
 return [('original',list(struct.unpack('>137I',(p/'retail.bin').read_bytes()))),('raw',raw),('normalized',derive(raw))]
def verify(words,c):
 initial=fixture(c);expected,s=reference(initial,c);m=Oracle(words,initial,c).run()
 assert m.service.calls==s.calls,('calls',c,m.service.calls,s.calls)
 assert public(m.memory)==public(expected),('public',c)
 assert data(m.memory,packet(c),60)==data(expected,packet(c),60),('descriptor',c)
 assert tuple(m.r[16:24])+tuple(m.r[28:])==m.saved and tuple(m.f[20:])==m.saved_fp
 return m
def main(programs=None):
 reports=[];programs=streams()if programs is None else programs
 for label,words in programs:
  seen=set();count=0;null_releases=0
  for c in cases():
   m=verify(words,c);seen.update(m.visits&set(range(ENTRY,ENTRY+548,4)));null_releases+=sum(t==FREE and arg==0 for t,arg,obs in m.service.calls);count+=1
  row=dict(stream=label,cases=count,coverage=len(seen),words=137,public_bytes_and_all_60_descriptor_bytes=True,saved_GPR_FPR_SP_RA=True,observed_null_release_arguments=null_releases);reports.append(row);print(json.dumps(row),flush=True)
 # Register allocation differs before the fit; do not claim raw full-register
 # fault-prefix equality. Literal normalized and retail words are identical.
 assert programs[0][1]==programs[2][1]
 report=dict(passes=True,streams=reports,raw_fault_prefix_equality_unclaimed=True,hardware_FCSR_unclaimed=True,c_match_credit=0)
 (p/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
