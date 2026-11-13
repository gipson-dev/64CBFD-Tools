"""Connected retail RNG and effect-wrapper paths with bounded services."""
import itertools,struct
from tools.experiments import game_paired_ground_constructor_match as packet
from tools.tests import game_paired_ground_constructor_oracle as g
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
SEED=0x800885b0;SCALE=0x8009f740;CORE=0x1513c350;SETUP=0x1513e2ac;RELEASE=0x1516972c
class Connected(g.Machine,RngInstructions):pass
class Full(Connected):
 def record_call(self,target):
  counts={CORE:11,SETUP:9,RELEASE:1}
  if target in counts:
   a=tuple(self.arguments(counts[target]));snap=bytes(self.memory[a[0]+i]for i in range(40))if target==CORE else b'';self.calls.append((target,a,snap))
  else:super().record_call(target)
 def hook(self,target):
  if target in (CORE,SETUP,RELEASE):
   if target==CORE and self.c.success:
    for i,b in enumerate(self.calls[-1][2]):self.memory[g.OUT+0x18+i]=b
   value=(g.OUT if self.c.success else 0)if target==CORE else 1 if target==SETUP else 0
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
  else:super().hook(target)
def helper_code(rom,full=False):
 chunks=[(g.RNG,0xdaed0,18),(g.RF,0xdaf18,25)]
 if full:chunks.extend(((g.FACTORY,0x169bec,50),(g.COPY,0x22ec0,11)))
 code={}
 for entry,off,n in chunks:code.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,off)))
 return code

def run(state,full=False):
 rom=(packet.ROOT/'conker/conker.us.bin').read_bytes();code=helper_code(rom,full);report={}
 for name in state:
  ws=g.programs(state,name);count=0;visited=set()
  for seed,matrix,hit,success in itertools.product(SEEDS,(0,1),(0,1),(0,1)):
   c=g.Case(matrix=matrix,hit=hit,success=success);states=[];expected=seed
   for _ in range(4 if hit else 0):expected=next_seed(expected)
   for w in ws:
    memory=g.fixture(c,name);put(memory,SEED,seed,8);put(memory,SCALE,bits(1.0/65535.0))
    m=(Full if full else Connected)(w,c,memory,name);m.code.update(code);m.run();home=g.STACK
    assert read(m.memory,SEED,8)==expected
    public={a:v for a,v in m.memory.items()if not home-2048<=a<home+2048};states.append((public,m.calls,m.r[2]));visited.update(m.visits&set(code))
    if full and hit:
     paths=[x[0]for x in m.calls];assert CORE in paths and (SETUP in paths)==bool(success)
   assert states.count(states[0])==4,(name,seed,c);count+=1
  if not full:assert visited==set(code),(name,len(visited),len(code))
  report[name]={'cases':count,'visited':len(visited),'total':len(code)}
 return report


class Caller(Full):
 def __init__(self,words,c,memory,name,code):
  self.c=c;self.rng=0;self.first=name.endswith('6460');self.target=int(name[5:],16)
  entry=0x150c5dc0 if self.first else 0x150c66f0
  FactoryOracle.__init__(self,words,memory,c,entry=entry,s={},arguments=(c.ctx,),connected=code)
 def record_call(self,target):
  if target==self.target:self.calls.append((target,(self.r[4],),b''))
  else:super().record_call(target)

def callers(state):
 rom=(packet.ROOT/'conker/conker.us.bin').read_bytes();basecode=helper_code(rom,True);report={}
 for name in state:
  first=name.endswith('6460');caller_off,slot=(0xf3270,0x58)if first else(0xf3ba0,0x6c)
  words=struct.unpack_from('>19I',rom,caller_off);target=int(name[5:],16);ws=g.programs(state,name);count=0
  for existing,matrix,hit,success in itertools.product((0,1),repeat=4):
   c=g.Case(matrix=matrix,hit=hit,success=success);states=[]
   for w in ws:
    memory=g.fixture(c,name);put(memory,SEED,0x123456789abcdef0,8);put(memory,SCALE,bits(1.0/65535.0));put(memory,c.ctx+slot,g.OUT if existing else 0)
    code=dict(basecode);code.update(zip(range(target,target+len(w)*4,4),w))
    m=Caller(words,c,memory,name,code).run();public={a:v for a,v in m.memory.items()if not g.STACK-2048<=a<g.STACK+2048};states.append((public,m.calls))
   assert states.count(states[0])==4,(name,c,existing)
   memory,calls=states[0];actual=read(memory,c.ctx+slot)
   if existing:assert actual==g.OUT and memory[g.OUT+0xb4]==1 and not calls
   else:
    assert calls[0]==(target,(c.ctx,),b'')
    assert actual==(g.OUT if hit and success else 0),(name,c,actual)
   count+=1
  report[name]=count
 return report


def faults(state):
 report={}
 for name in state:
  ws=g.programs(state,name);cuts=0;private=0
  for matrix,hit,success,seed in itertools.product((0,1),repeat=4):
   c=g.Case(matrix=matrix,hit=hit,success=success,seed=seed);initial=g.fixture(c,name);full=g.Machine(ws[1],c,initial.copy(),name).run()
   for cut in range(full.all_accesses):
    machines=[]
    for w in ws:
     m=g.Machine(w,c,initial.copy(),name);m.cut=cut
     try:m.run();raise AssertionError(('missing cut',cut))
     except AccessBoundary:pass
     machines.append(m)
    retail=machines[1];assert all((m.memory,m.calls,m.trace)==(retail.memory,retail.calls,retail.trace)for m in machines[2:]),(name,c,cut,'padded')
    public=lambda m:{a:v for a,v in m.memory.items()if not g.STACK-2048<=a<g.STACK+2048}
    assert (public(machines[0]),machines[0].calls)==(public(retail),retail.calls),(name,c,cut,'raw public')
    private+=machines[0].memory!=retail.memory;cuts+=1
  report[name]={'cases':16,'cuts':cuts,'private_differences':private}
 return report
