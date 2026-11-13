"""Guest contracts for two random effect wrappers and connected RNGs."""
import itertools
from dataclasses import dataclass
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_actor_intensity_byte_oracle import float32
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
F=0x150ada68;I=0x150ada20;A=0x151541b8;B=0x15154884;AB0=0x800a0ab0;AB4=0x800a0ab4;SEED=0x800885b0;UNIT=0x8009f740;POSITION=0x30000;OTHER=0x60000;MARK=0x50000
ENTRIES={'func_150D6388':0x150d6388,'func_150D6434':0x150d6434};MASK=0xffffffff
@dataclass(frozen=True)
class Case:
 phase:int=0;selector:int=0;context:int=0x81234567;floats:tuple=(0x3e800000,0x3f000000,0x3f400000);integer:int=0xffffffff;mutation:int=0;seed:int=0x123456789abcdef0;connected:int=0;position:int=POSITION

def symbols():return {'func_150ADA68':F,'func_150ADA20':I,'func_151541B8':A,'func_15154884':B,'D_800A0AB0':AB0,'D_800A0AB4':AB4}
def words(obj,name):
 t,f,r=parse_object(obj);a=f[name]['value'];n=f[name]['size'];return bound_blob(t[a:a+n],{i-a:v for i,v in r.items()if a<=i<a+n},symbols())
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-1024,1024)}
 for base,n in ((POSITION,64),(OTHER,64),(MARK,4)):m.update({base+i:(i*29+0x59)&255 for i in range(n)})
 put(m,AB0,0x40000000);put(m,AB4,0xbf800000);put(m,SEED,c.seed,8);put(m,UNIT,0x37800000);return m
def public(mem):return {a:b for a,b in mem.items()if not STACK-1024<=a<STACK+1024}
def single(value):return bits(float32(value))
def mul(a,b):return single(floating(a)*floating(b))
def add(a,b):return single(floating(a)+floating(b))
def mutation(mem,c,n,home):
 if c.mutation&1:put(mem,AB0,bits(n*.25));put(mem,AB4,bits(float(n)))
 if c.mutation&2:put(mem,home,OTHER);put(mem,home+4,0x12345600|(0x80+n));put(mem,home+8,0xa0000000+n)
 if c.mutation&4:put(mem,POSITION,n)
def reference(initial,name,c,home=None):
 m=dict(initial);home=STACK+c.phase if home is None else home;put(m,home,c.position);put(m,home+4,c.selector);put(m,home+8,c.context);calls=[];draws=[];n=0;fi=0
 def draw(kind):
  nonlocal n,fi
  n+=1;calls.append((kind,()));mutation(m,c,n,home)
  if c.connected:
   seed=next_seed(read(m,SEED,8));put(m,SEED,seed,8);v=mul(bits(float(seed&65535)),read(m,UNIT))if kind==F else seed&MASK
  elif kind==F:v=c.floats[fi];fi+=1
  else:v=c.integer
  draws.append(v);return v
 first=draw(F)
 if name=='func_150D6388':
  value=draw(I);args=(read(m,home),add(mul(first,bits(4.)),bits(15.)),0x3faff1e9,bits(float((value%56)+200)),bits(0.),read(m,home+7,1),read(m,home+8));calls.append((A,args))
 else:
  second=draw(F);third=draw(F);args=(read(m,home),add(mul(first,bits(3.)),bits(8.)),add(mul(second,read(m,AB0)),read(m,AB4)),add(mul(third,bits(50.)),bits(100.)),read(m,home+7,1),read(m,home+8));calls.append((B,args))
 put(m,MARK,0xabcdef12);return public(m),calls,draws
class Machine(RngInstructions):
 def __init__(self,ws,name,c,mem,connected=None):
  self.case=c;self.name=name;self.draws=[];self.n=self.fi=0;self.home=STACK+c.phase;self.syms=symbols();FactoryOracle.__init__(self,ws,mem,c,entry=ENTRIES[name],s=self.syms,connected=connected,arguments=(c.position,c.selector,c.context));self.before=self.r[:]
 def execute(self,w):
  # The inherited 64-bit RNG oracle restores wide registers after generic
  # instructions; MFC1 writes its destination and must not be undone.
  super().execute(w)
  if w>>26==17 and (w>>21&31)==0:
   self.r[w>>16&31]=self.f[w>>11&31]&MASK
   self.r[0]=0
 def record_call(self,t):
  counts={F:0,I:0,A:7,B:6};assert t in counts,hex(t);args=tuple(x&MASK for x in self.arguments(counts[t]));self.calls.append((t,args))
  if t in (F,I):self.n+=1;mutation(self.memory,self.case,self.n,self.home)
 def hook(self,t):
  c=self.case;float_value=None
  if t==F:float_value=c.floats[self.fi];self.fi+=1;self.draws.append(float_value);value=0xa5000002
  elif t==I:value=c.integer;self.draws.append(value)
  else:assert t in(A,B);put(self.memory,MARK,0xabcdef12);value=0x87654321
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value&MASK
  if float_value is not None:self.f[0]=float_value
def run(state):
    names=tuple(ENTRIES);n=0
    for name in names:
     bodies=[words(state['after'],name),words(state['retail'][name],name),words(state['generated'],name)];assert bodies[0]==bodies[1]==bodies[2]
     for selector,integer,phase,mut in itertools.product(range(256),(0,55,56,0x7fffffff,0x80000000,0xffffffff),(0,8),(0,1,2,3,4,7)):
      c=Case(phase,0x12340000|selector,0x87654321,(0x3e800000,0x3f000000,0x3f400000),integer,mut);initial=fixture(c);expect,calls,draws=reference(initial,name,c)
      for ws in bodies:
       m=Machine(ws,name,c,initial.copy()).run();assert (public(m.memory),m.calls,m.draws)==(expect,calls,draws),(name,c,m.calls,calls)
      n+=1
    return {'cases':n,'bodies':3,'selectors':'all 256','helper_mutations':True}
