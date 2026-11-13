"""Connect both original RNG implementations to the candidate programs."""
import itertools,struct
from tools.experiments import game_random_paired_constructor_match as packet
from tools.tests import game_random_paired_constructor_match_oracle as model
from tools.tests import game_random_paired_constructor_oracle as g
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
SEED=0x800885b0;SCALE=0x8009f740
class Connected(g.Machine,RngInstructions):
 pass

def run(state):
 rom=(packet.ROOT/'conker/conker.us.bin').read_bytes();code={}
 for entry,offset,n in ((g.RNG,0xdaed0,18),(g.RF,0xdaf18,25)):
  code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
 report={}
 for name in state:
  ws=model.programs(state,name);visited=set();count=0
  for seed,phase,success in itertools.product(SEEDS,(0,8),(0,1)):
   c=g.Case(phase=phase,success=success);states=[];expected_seed=seed
   for _ in range(14):expected_seed=next_seed(expected_seed)
   for w in ws:
    memory=g.fixture(c,name);put(memory,SEED,seed,8);put(memory,SCALE,bits(1.0/65535.0))
    m=Connected(w,c,memory,name);m.code.update(code);m.run();home=g.STACK+phase
    public={a:v for a,v in m.memory.items()if not home-2048<=a<home+2048}
    assert read(m.memory,SEED,8)==expected_seed,(name,seed,read(m.memory,SEED,8),expected_seed)
    states.append((public,m.calls));visited.update(m.visits&set(code))
   assert states.count(states[0])==4,(name,seed,phase,success);count+=1
  assert visited==set(code),(name,len(visited),len(code))
  report[name]={'cases':count,'rng_words_visited':len(visited)}
 return report


WRAPPER=0x15130374;FACTORY_CORE=0x15130280;ALLOC=0x15167a68
class Full(Connected):
 def record_call(self,target):
  counts={WRAPPER:5,FACTORY_CORE:6,ALLOC:6}
  if target in counts:self.calls.append((target,tuple(self.arguments(counts[target])),()))
  else:super().record_call(target)
 def hook(self,target):
  if target==ALLOC:
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
   self.r[2]=g.OUT if self.c.success else 0
  else:super().hook(target)

def full_helpers(state):
 rom=(packet.ROOT/'conker/conker.us.bin').read_bytes();code={}
 for entry,offset,n in ((g.RNG,0xdaed0,18),(g.RF,0xdaf18,25),(g.FACTORY,0x15d86c,12),(WRAPPER,0x15d824,18),(FACTORY_CORE,0x15d730,61),(g.COPY,0x22ec0,11)):
  code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
 report={}
 for name in state:
  ws=model.programs(state,name);visited=set();count=0
  for seed,phase,success in itertools.product(SEEDS,(0,8),(0,1)):
   c=g.Case(phase=phase,success=success);states=[];expected_seed=seed
   for _ in range(14):expected_seed=next_seed(expected_seed)
   for w in ws:
    memory=g.fixture(c,name);put(memory,SEED,seed,8);put(memory,SCALE,bits(1.0/65535.0))
    m=Full(w,c,memory,name);m.code.update(code);m.run();home=g.STACK+phase
    public={a:v for a,v in m.memory.items()if not home-2048<=a<home+2048}
    assert read(m.memory,SEED,8)==expected_seed
    paths=[x[0] for x in m.calls];assert WRAPPER in paths and FACTORY_CORE in paths and ALLOC in paths
    copies=[x for x in m.calls if x[0]==g.COPY];assert [x[1][2] for x in copies]==([112,40] if success else [])
    states.append((public,m.calls));visited.update(m.visits&set(code))
   assert states.count(states[0])==4,(name,seed,phase,success);count+=1
  report[name]={'cases':count,'helper_words_visited':len(visited),'helper_words_total':len(code)}
 return report


WINDOW=0x15134584;WINDOW_END=0x15134604;TABLE=0x80089a70
class Caller(Full):
 def __init__(self,window,c,memory,code,target,variant):
  self.c=c;self.rng=0;self.frng=0;self.target=target
  FactoryOracle.__init__(self,window,memory,c,entry=WINDOW,s={},arguments=(0,0,0,0),connected=code)
  self.r[16]=c.owner;self.r[17]=TABLE
  for index,value in ((0,.25),(20,.5),(22,2.0),(24,.25),(26,.75),(30,1.5)):
   self.f[index]=bits(value)
  self.code=WindowCode(self.code,self);self.code.ends=(WINDOW_END,)
 def record_call(self,target):
  if target==self.target:
   self.calls.append((target,(self.f[12],self.f[14],self.r[6],self.r[7],read(self.memory,self.r[29]+16),read(self.memory,self.r[29]+20),read(self.memory,self.r[29]+24)),()))
  else:super().record_call(target)

def callers(state):
 rom=(packet.ROOT/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>32I',rom,0x161a34);report={}
 assert 0x161a34+len(window)*4==0x161ab4
 basecode={}
 for entry,offset,n in ((g.RNG,0xdaed0,18),(g.RF,0xdaf18,25),(g.FACTORY,0x15d86c,12),(WRAPPER,0x15d824,18),(FACTORY_CORE,0x15d730,61),(g.COPY,0x22ec0,11)):
  basecode.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
 for name in state:
  target=int(name[5:],16);variant=4 if name.endswith('60D8') else 5;ws=model.programs(state,name);count=0
  for seed,phase,success in itertools.product(SEEDS,(0,8),(0,1)):
   c=g.Case(phase=phase,success=success);states=[]
   for w in ws:
    memory=g.fixture(c,name);home=g.STACK+phase;put(memory,SEED,seed,8);put(memory,SCALE,bits(1.0/65535.0))
    put(memory,TABLE+4*variant,target);memory[c.owner+0x3b]=variant;put(memory,c.owner+0x30,bits(3.0))
    for off,val in ((0x94,1.25),(0x98,-0.75),(0xa4,10.0),(0xa8,20.0),(0xac,30.0)):put(memory,home+off,bits(val))
    code=dict(basecode);code.update(zip(range(target,target+4*len(w),4),w));code[WINDOW_END]=0
    m=Caller(window,c,memory,code,target,variant)
    try:m.run();raise AssertionError('caller window did not stop')
    except WindowBoundary:pass
    assert m.calls[0][0]==target and m.calls[0][1][-1]==c.owner,(name,m.calls[0])
    public={a:v for a,v in m.memory.items()if not home-2048<=a<home+2048};states.append((public,m.calls))
   assert states.count(states[0])==4,(name,seed,phase,success);count+=1
  report[name]=count
 return report


def fault_prefixes(state):
 report={}
 for name in state:
  ws=model.programs(state,name);cuts=0;private_differences=0
  for phase,success,seed in itertools.product((0,8),(0,1),(0,1,2)):
   c=g.Case(phase=phase,success=success,seed=seed);initial=g.fixture(c,name)
   full=g.Machine(ws[1],c,initial.copy(),name).run()
   for cut in range(full.all_accesses):
    machines=[]
    for w in ws:
     m=g.Machine(w,c,initial.copy(),name);m.cut=cut
     try:m.run();raise AssertionError(('missing cut',cut))
     except AccessBoundary:pass
     machines.append(m)
    retail=machines[1]
    assert all((m.memory,m.calls,m.trace)==(retail.memory,retail.calls,retail.trace)for m in machines[2:]),(name,c,cut)
    home=g.STACK+phase;public=lambda m:{a:v for a,v in m.memory.items()if not home-2048<=a<home+2048}
    assert (public(machines[0]),machines[0].calls)==(public(retail),retail.calls),(name,c,cut)
    private_differences+=machines[0].memory!=retail.memory;cuts+=1
  report[name]={'cases':12,'access_cuts':cuts,'private_frame_differences':private_differences}
 return report
