"""Ordered RNG, live scalar homes and a closed private prologue permutation."""
from dataclasses import dataclass
import struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngOracle
from tools.tests.game_seeded_sprite_oracle import Oracle as SignedAddOracle
from tools.tests.game_table_payload_spawn_oracle import Oracle as PartialOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
ENTRY,RI,RF,CREATE=0x151B4EA4,0x150ADA20,0x150ADA68,0x151D9014
POSITION,OTHER,ACTOR,OUTPUT=0x30000,0x31000,0x32000,0x50000
SCALE,SIZE,SPREAD,SEED,FACTOR=0x800AA3D4,0x800AA3D8,0x800AA3DC,0x800885B0,0x8009F740
REGISTRY,CALLBACK,FACTORY,COPY=0x8008FCD0,0x18010000,0x15130280,0x10022EC0
u32=lambda n:n&0xFFFFFFFF
data=lambda m,p,n:bytes(m[u32(p+i)]for i in range(n))
COORDS=((0x3FA00000,0xC1900000,0x3F000000),(0,0x80000000,0x3E800000),(0x7FC12345,0x7F800000,0xFF800000),(0x46FFFF80,0xC7000080,1))

@dataclass(frozen=True)
class Case:
 selector:int=3
 mode:int=7
 integers:tuple=(0,0x80000000,0xFFFFFFFF)
 floats:tuple=(0x3E800000,0x3F400000)
 coordinates:int=0
 mutation:int=0
 phase:int=0
 seed:int=0x123456789ABCDEF0
 connected:int=0
 outcome:int=1
 alias:int=0

def symbols():return dict(func_150ADA20=RI,func_150ADA68=RF,func_151D9014=CREATE,D_800AA3D4=SCALE,D_800AA3D8=SIZE,D_800AA3DC=SPREAD)
def packet(c,home=None):return(STACK+c.phase if home is None else home)-112+96
def position(c,s=None):return(POSITION,OTHER,SCALE)[c.alias]if s is None else(POSITION,OTHER,s['D_800AA3D4'])[c.alias]
def args(c,s=None):return(position(c,s),*COORDS[c.coordinates],c.selector,c.mode)

def fixture(c=Case(),s=None,globals=None):
 s=symbols()if s is None else s;m={STACK+i:(i*17+165)&255 for i in range(-2048,1024)}
 for p,n in((POSITION,32),(OTHER,32),(ACTOR,128),(OUTPUT,512)):
  m.update({p+i:(i*13+89)&255 for i in range(n)})
 for name,v in(('D_800AA3D4',0x3DCCCCCD),('D_800AA3D8',0x3E800000),('D_800AA3DC',0x40000000)):put(m,s[name],v)
 put(m,s['D_800AA3D4']+4,0x3E800000);put(m,s['D_800AA3D4']+8,0x40000000)
 put(m,SEED,c.seed,8);put(m,FACTOR,0x37800000)
 for i,v in enumerate(COORDS[c.coordinates]):put(m,POSITION+i*4,v);put(m,OTHER+i*4,v^0x80000000)
 for i in range(256):put(m,REGISTRY+i*4,CALLBACK+i*4)
 if globals:m.update(globals)
 # Actual binding values can be overridden independently by test mutations.
 for i,v in enumerate(args(c,s)[4:]):put(m,STACK+c.phase+16+i*4,v)
 m[ACTOR+0x58]=c.selector;m[ACTOR+0xC]=c.mode
 return m

def effect(m,c,s,ordinal,home):
 if ordinal==1 and c.mutation&1:
  put(m,s['D_800AA3D4'],0x40800000);put(m,s['D_800AA3D8'],0x3F000000);put(m,s['D_800AA3DC'],0x40400000)
  for i in range(3):put(m,POSITION+i*4,0x3F800000+i*0x800000)
 if ordinal==5 and c.mutation&2:
  put(m,s['D_800AA3D8'],0x3F400000);put(m,s['D_800AA3DC'],0x40800000)
 if ordinal==5 and c.mutation&4:
  put(m,home,OTHER);put(m,home+16,c.selector^255);put(m,home+20,c.mode^255)

def reference(initial,c=Case(),s=None,home=None,coordinates=None):
 s=symbols()if s is None else s;home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];draws=[]
 v=COORDS[c.coordinates]if coordinates is None else coordinates;scale=read(m,s['D_800AA3D4']);vector=tuple(bits(floating(n^0x80000000)*floating(scale))for n in v)
 put(m,home,position(c,s));put(m,home+12,v[2])
 for ordinal,key in enumerate(('func_150ADA68','func_150ADA20','func_150ADA20','func_150ADA68','func_150ADA20'),1):
  target=s[key];calls.append((target,()));effect(m,c,s,ordinal,home)
  if c.connected:
   seed=next_seed(read(m,SEED,8));put(m,SEED,seed,8);value=bits(float(seed&65535)*floating(read(m,FACTOR)))if target==s['func_150ADA68']else u32(seed)
  else:value=c.floats[(ordinal==4)]if target==s['func_150ADA68']else c.integers[{2:0,3:1,5:2}[ordinal]]
  draws.append(value)
 size=read(m,s['D_800AA3D8']);spread=read(m,s['D_800AA3DC']);first=bits(floating(bits(floating(draws[0])*floating(spread)))+-1.0);second=bits(floating(bits(floating(draws[3])*152.0))+109.0)
 a=(read(m,home),packet(c,home),read(m,home+19,1),first,draws[1]%31+20,draws[2]%101+155,second,draws[4]&1,size,size,0,0,1,0,read(m,home+23,1),1);calls.append((s['func_151D9014'],a))
 return m,calls,vector,draws

class Oracle(RngOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None,arguments=None,home=None):
  self.c=c;self.s=symbols()if s is None else s;self.ordinal=0;self.submissions=[];self.factories=[];self.copies=[];self.home=STACK+c.phase if home is None else home
  FactoryOracle.__init__(self,words,memory,c,entry=entry,arguments=args(c,self.s)if arguments is None else arguments,connected=connected)
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000;return
  if w>>26 in(34,38,42,46):return PartialOracle.execute(self,w)
  if w>>26==0 and w&63==32:return SignedAddOracle.execute(self,w)
  return super().execute(w)
 def record_call(self,t):
  if CALLBACK<=t<CALLBACK+1024:n=0
  else:n={self.s['func_150ADA20']:0,self.s['func_150ADA68']:0,self.s['func_151D9014']:16,FACTORY:6,COPY:3,ENTRY:6}[t]
  a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==ENTRY:self.home=self.r[29]
  if t in(self.s['func_150ADA20'],self.s['func_150ADA68']):self.ordinal+=1;effect(self.memory,self.c,self.s,self.ordinal,self.home)
  if t==self.s['func_151D9014']:self.submissions.append((a,tuple(read(self.memory,a[1]+i*4)for i in range(3)),data(self.memory,a[0],12)))
  if t==FACTORY:self.factories.append((a,data(self.memory,a[0],0x6C)))
  if t==COPY:self.copies.append((a,data(self.memory,a[1],a[2])))
 def hook(self,t):
  value=0x81234560
  if t==self.s['func_150ADA20']:value=self.c.integers[{2:0,3:1,5:2}[self.ordinal]]
  elif t==self.s['func_150ADA68']:value=self.c.floats[self.ordinal==4]
  elif t==self.s['func_151D9014']:pass
  elif CALLBACK<=t<CALLBACK+1024:value=(t-CALLBACK)//4
  elif t==FACTORY:value=OUTPUT if self.c.outcome else 0
  elif t==COPY:
   a=self.calls[-1][1]
   for i,b in enumerate(data(self.memory,a[1],a[2])):self.memory[a[0]+i]=b
   value=a[0]
  else:raise AssertionError(('Unbounded effect provider',hex(t)))
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  if t==self.s['func_150ADA68']:self.f[0]=value
  else:self.r[2]=u32(value)

def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.submissions,m.factories,m.copies,m.current_pc,m.delay_of,m.all_accesses)
def canonical_state(m):
 stores=[m.home-112+68,m.home,m.home+12]
 def reorder(events):
  events=events.copy()
  for i in range(len(events)-3):
   if [v[:3]for v in events[i:i+4]]==[('W',a,4)for a in stores]+[('R',m.s['D_800AA3D4'],4)]:events[i:i+4]=[events[i+3],*events[i:i+3]];break
  else:raise AssertionError('Raw prologue permutation did not fire')
  return events
 values=list(state(m));values[7]=reorder(m.events);values[8]=reorder(m.trace);return tuple(values)
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def helpers(rom,consumer=False):
 code={}
 for e,p,n in((RI,0xDAED0,18),(RF,0xDAF18,25),*(((CREATE,0x2064C4,248),(COPY,0x22EC0,11))if consumer else())):code.update(zip(range(e,e+4*n,4),struct.unpack_from('>%dI'%n,rom,p)))
 return code
