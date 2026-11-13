"""Execute original factory and byte-copy bodies with bounded allocation hooks."""
import itertools,struct
from dataclasses import dataclass
from tools.tests import game_paired_height_descriptor_oracle as base
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
ALLOC,RELEASE,TRANSFORM=0x15167A68,0x1516972C,0x15143134
@dataclass(frozen=True)
class ConnectedCase(base.Case):
 owner_state:int=0
class Machine(base.Machine):
 def record_call(self,target):
  if target in (ALLOC,RELEASE,TRANSFORM):
   n={ALLOC:6,RELEASE:1,TRANSFORM:3}[target];self.calls.append((target,tuple(self.arguments(n)),()))
  else:super().record_call(target)
 def hook(self,target):
  if target in (ALLOC,RELEASE,TRANSFORM):
   if target==ALLOC and self.c.owner_state==2:self.memory[self.c.owner+0x3b]^=0x80
   if target==TRANSFORM:
    for i in range(12):self.memory[self.calls[-1][1][0]+i]=(0xd0+i)&255
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010,0xa5000011
   self.r[2]=base.OUT if target==ALLOC and self.c.allocated else 0
  else:super().hook(target)
def helper_code(rom):
 result={}
 for entry,offset,n in ((base.FACTORY,0x16163c,76),(base.COPY,0x22ec0,11)):
  result.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
 return result
def run(state,rom):
 code=helper_code(rom);result={}
 for name in state:
  constants,ws=base.programs(state,name);visited=set();count=0;paths=set()
  for hit,allocated,owner_state,mutation in itertools.product((0,1),(0,1),range(5),range(4)):
   c=ConnectedCase(hit=hit,allocated=allocated,owner_state=owner_state,mutation=mutation);out=[]
   for w in ws:
    memory=base.fixture(c,constants)
    for i in range(256,512):memory[base.OWNER+i]=(i*29+90)&255
    base.put(memory,base.OWNER,0 if owner_state==1 else 1)
    base.put(memory,base.OWNER+0x1d4,0x60000 if owner_state>=3 else 0)
    memory[base.OWNER+0x74]=0x0f if owner_state==3 else 0x00
    machine=Machine(w,c,memory,constants,int(name[5:],16),connected=code).run()
    public={a:v for a,v in machine.memory.items() if not base.STACK-2048<=a<base.STACK+2048}
    out.append((public,machine.calls,machine.r[2]));visited.update(machine.visits)
   assert all(x==out[0] for x in out),(name,c,[(x[1],x[2]) for x in out])
   calls=out[0][1];paths.update(t for t,_,_ in calls)
   assert (any(t==RELEASE for t,_,_ in calls))==(bool(allocated) and owner_state in (1,2))
   assert (any(t==TRANSFORM for t,_,_ in calls))==(bool(allocated) and owner_state==4)
   assert out[0][2]==(base.OUT if allocated and owner_state not in (1,2) else 0)
   count+=1
  assert {base.FACTORY,base.COPY,ALLOC,RELEASE,TRANSFORM}<=paths
  result[name]={'cases':count,'factory_words_visited':len(set(range(base.FACTORY,base.FACTORY+304,4))&visited),'copy_words_visited':len(set(range(base.COPY,base.COPY+44,4))&visited)}
 return result


class CallerMachine(Machine):
 def __init__(self,words,c,memory,constants,caller,code,target):
  self.c=c;self.const=constants;self.target=target
  base.FactoryOracle.__init__(self,words,memory,c,entry=caller,s={},arguments=(c.context,),connected=code)
 def record_call(self,target):
  if target==self.target:self.calls.append((target,tuple(self.r[4:6]),()))
  else:super().record_call(target)

def callers(state,rom):
 report={}
 for name in state:
  first=name.endswith('5F94');caller,offset,slot=(0x150c5f40,0xf33f0,0x5c) if first else (0x150c6870,0xf3d20,0x70)
  target=int(name[5:],16);body=struct.unpack_from('>21I',rom,offset);constants,ws=base.programs(state,name);count=0
  for existing,hit,allocated,owner_state,mutation in itertools.product((0,1),(0,1),(0,1),(0,1,2,3,4),(0,3)):
   c=ConnectedCase(hit=hit,allocated=allocated,owner_state=owner_state,mutation=mutation);out=[]
   for w in ws:
    memory=base.fixture(c,constants)
    for i in range(256,512):memory[base.OWNER+i]=(i*29+90)&255
    base.put(memory,base.OWNER,0 if owner_state==1 else 1)
    base.put(memory,base.OWNER+0x1d4,0x60000 if owner_state>=3 else 0)
    memory[base.OWNER+0x74]=0xf if owner_state==3 else 0
    base.put(memory,c.context+0x18,c.owner);base.put(memory,c.context+slot,base.OUT if existing else 0)
    code=helper_code(rom);code.update(zip(range(target,target+4*len(w),4),w))
    m=CallerMachine(body,c,memory,constants,caller,code,target).run()
    public={a:v for a,v in m.memory.items() if not base.STACK-2048<=a<base.STACK+2048}
    out.append((public,m.calls))
   assert all(x==out[0] for x in out),(name,c,existing)
   mem,calls=out[0];final=base.read(mem,c.context+slot)
   if existing:
    assert final==base.OUT and mem[base.OUT+0x5c]==1 and not calls
   else:
    assert calls[0]==(target,(c.owner,c.context),())
    expected=base.OUT if allocated and owner_state not in (1,2) else 0
    assert final==expected,(name,c,final,expected)
   count+=1
  report[name]=count
 return report


def fault_prefixes(state):
 report={}
 for name in state:
  cs,ws=base.programs(state,name);cuts=0;private_differences=0
  for hit,allocated,mutation in itertools.product((0,1),(0,1),(0,3)):
   c=base.Case(hit=hit,allocated=allocated,mutation=mutation);initial=base.fixture(c,cs)
   full=base.Machine(ws[1],c,initial.copy(),cs,int(name[5:],16)).run()
   for cut in range(full.all_accesses):
    machines=[]
    for w in ws:
     m=base.Machine(w,c,initial.copy(),cs,int(name[5:],16));m.cut=cut
     try:m.run();raise AssertionError(('missing cut',cut))
     except AccessBoundary:pass
     machines.append(m)
    retail=machines[1];assert all((m.memory,m.calls,m.trace)==(retail.memory,retail.calls,retail.trace) for m in machines[2:]),(name,c,cut)
    public=lambda m:{a:v for a,v in m.memory.items() if not base.STACK-2048<=a<base.STACK+2048}
    assert (public(machines[0]),machines[0].calls)==(public(retail),retail.calls),(name,c,cut)
    private_differences+=machines[0].memory!=retail.memory;cuts+=1
  report[name]={'cases':8,'access_cuts':cuts,'raw_private_frame_differences':private_differences}
 return report
