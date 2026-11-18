"""Independent descriptor inheritance, provider-mutation and ABI model."""
from pathlib import Path
from dataclasses import dataclass,asdict
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_menu_layers_150b77a8_match as source
p=source.OUT;f=source.FROZEN;ENTRY=0x150B77A8
BASE,STATE,MARK=0x800D9898,0x800D9890,0x70000
FREE,CREATE=0x1516972C,0x15169968
FIRST_ASSET,SECONDARY_ASSET,SECOND_ASSET=0x800918F4,0x80091900,0x800918E8
data=lambda m,a,n:bytes(m[a+i]for i in range(n))
public=lambda m:{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
@dataclass(frozen=True)
class Case:
 presence:int=7;failure:int=0;mutation:int=0;phase:int=0;seed:int=0
def cases():
 for presence,failure,mutation,phase in itertools.product(range(8),range(4),(0,1,3,7),(0,8)):
  yield Case(presence,failure,mutation,phase,(presence*31+failure*11+mutation*3)&255)
def packet(c,home=None):return(STACK+c.phase if home is None else home)-60
def fields():
 return [(0,FIRST_ASSET,4),(4,SECONDARY_ASSET,4),*( (off,0,2)for off in(0x14,0x16,0x18)),(0x1C,0x42700000,4),(0x20,0x432A0000,4),
  (0x24,0xF800,2),(0x26,9,2),(0x28,4096,2),(0x2A,4096,2),(0x2C,64,2),(0x2E,64,2),
  *((0x30+i,v,1)for i,v in enumerate((4,0,255,0,0,255,13,18,2,3)))]
DEFINED=tuple(sorted({at+i for at,v,n in fields()for i in range(n)}));assert len(DEFINED)==44
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for a,n in((BASE-16,80),(MARK,4)):m.update({a+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for i,off in enumerate((4,16,32)):put(m,BASE+off,0x50000+i*0x1000 if c.presence&(1<<i)else 0)
 m[STATE]=c.seed;return m
class Service:
 def __init__(self,m,c):self.m,self.c=m,c;self.calls=[];self.retained=None;self.creates=0
 def invoke(self,target,arg):
  m,c=self.m,self.c;ordinal=len(self.calls);observed=b''
  if target==CREATE:
   self.retained=arg;observed=data(m,arg,60);normalized='descriptor'
  else:assert target==FREE and arg;normalized=arg
  self.calls.append((target,normalized,observed));put(m,MARK,(0x13579BDF+ordinal*0x10203+target)&0xFFFFFFFF)
  if target==FREE:
   if c.mutation&1:
    put(m,BASE+4,0x990000);put(m,BASE+16,0x60000+ordinal*0x1000);put(m,BASE+32,0 if c.seed&1 else 0x70000+ordinal*0x1000);m[STATE]=(c.seed+3)&255
   if c.mutation&2 and self.retained is not None:
    for i in range(60):m[self.retained+i]=(c.seed+i*7+ordinal*11)&255
   return 0xDEADBEEF
  if c.mutation&4:
   for i in range(60):m[arg+i]=(c.seed+i*13+ordinal*17)&255
   put(m,BASE+32,0 if c.seed&2 else 0xA0000+ordinal*0x1000);m[STATE]=0xA7
  index=self.creates;self.creates+=1
  return 0 if c.failure&(1<<index)else 0x80000+c.seed*0x100+index*0x10000
def reference(initial,c,home=None):
 m=dict(initial);s=Service(m,c);at=packet(c,home)
 old=read(m,BASE+4)
 if old:s.invoke(FREE,old);put(m,BASE+4,0)
 for off,v,n in fields():put(m,at+off,v,n)
 old=read(m,BASE+16)
 if old:s.invoke(FREE,old)
 put(m,BASE+16,s.invoke(CREATE,at))
 for off,v,n in((0,SECOND_ASSET,4),(0x24,0,2),(0x26,0,2),(0x2C,88,2),(0x2E,64,2),(0x30,0,1),(0x36,7,1),(0x37,17,1),(0x38,1,1)):put(m,at+off,v,n)
 old=read(m,BASE+32)
 if old:s.invoke(FREE,old)
 put(m,BASE+32,s.invoke(CREATE,at));m[STATE]=3
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
 from tools.tests.game_menu_layers_150b77a8_proof import derive
 syms={v[1]:v[2][1]for v in symbol_rows((f/'conker/build/conker.us.elf').read_bytes())}
 raw=bound_blob(*payload(p/'owner.o','func_150B77A8'),syms)
 return [('original',list(struct.unpack('>93I',(p/'retail.bin').read_bytes()))),('raw',raw),('normalized',derive(raw))]
def verify(words,c):
 initial=fixture(c);expected,s=reference(initial,c);machine=Oracle(words,initial,c).run()
 assert machine.service.calls==s.calls,('calls',asdict(c),machine.service.calls,s.calls)
 assert public(machine.memory)==public(expected),('public',asdict(c))
 assert data(machine.memory,packet(c),60)==data(expected,packet(c),60),('descriptor',asdict(c))
 assert tuple(machine.r[16:24])+tuple(machine.r[28:])==machine.saved and tuple(machine.f[20:])==machine.saved_fp
 return machine
def state(m):return(m.r,m.f,m.memory,m.trace,m.service.calls,m.hi,m.lo,getattr(m,'pc',None),getattr(m,'dispatched_word',None))
def main(programs=None):
 reports=[];programs=streams()if programs is None else programs
 for label,words in programs:
  seen=set();count=0
  for c in cases():
   m=verify(words,c);seen.update(m.visits&set(range(ENTRY,ENTRY+372,4)));count+=1
  row=dict(stream=label,cases=count,coverage=len(seen),words=93,public_bytes_and_all_60_descriptor_bytes=True,saved_GPR_FPR_SP_RA=True);reports.append(row);print(json.dumps(row),flush=True)
 prefixes=0
 for c in(Case(),Case(presence=0),Case(failure=3,mutation=7,phase=8),Case(presence=1,mutation=3)):
  initial=fixture(c);full=Oracle(programs[0][1],initial,c).run()
  for cut in range(full.all_accesses):
   machines=[]
   for label,words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('missing access cut',label,cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]),('access cut',c,cut);prefixes+=1
 report=dict(passes=True,streams=reports,exact_access_prefixes=prefixes,c_match_credit=0)
 (p/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
