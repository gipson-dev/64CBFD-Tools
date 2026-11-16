"""Independent complete descriptor/parameter model and finite MIPS execution."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,struct,sys
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as base
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_inverse_motion_151a4638_recovery as source
O=source.OUT;R=source.ROOT;ENTRY=source.ENTRY
RNG,REAL,FACTORY,COPY=0x150ADA20,0x150ADA68,0x15130374,0x10022EC0
E,OUT,MARK,DT,CONSTANT,STACK=0x30000,0x50000,0x70000,0x800BE9A8,0x800A8D60,base.STACK
S={row[1]:row[2][1]for row in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())}
data=lambda m,p,n:bytes(m[p+i]for i in range(n));public=lambda m:{p:v for p,v in m.items()if not STACK-4096<=p<STACK+1024}
u32=lambda n:n&0xffffffff
DEFINED=tuple(i for i in range(112)if not(0x3C<=i<0x48 or 0x5C<=i<0x60 or 0x64<=i<0x70))
PARAMETERS=struct.pack('>6h',16,15,13,19,17,-24)

@dataclass(frozen=True)
class Case:
 seed:int=0;flips:int=0;success:int=1;mutation:int=0;phase:int=0;pattern:int=0;alias:int=0
 sample:int=0x3E800000;dt:int=0x3F800000

def inputs(c):
 return tuple(bits(v)for v in((1.25,-2.5,3.75,4.25,-5.5,6.75),(0.,-0.,0.,-0.,0.,-0.),(-1000.25,2000.5,-3000.75,40.,-50.,60.),(.00001,-.000002,.000003,-.0004,.00005,-.00006))[c.pattern])

def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-4096,1024)}
 for at,n in((E,192),(OUT,192),(MARK,4)):
  m.update({at+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 m[E+12]=c.seed&255;put(m,DT,c.dt);put(m,CONSTANT,0x3DB22D0E)
 a=inputs(c);home=STACK+c.phase
 for off,value in((16,a[4]),(20,a[5]),(24,E)):put(m,home+off,value)
 return m

def integer(i,c):return(0,4,5,0xffffffff,0x80000000,253,0x7fffffff,17)[c.seed%8]if i==0 else(0xFFFFFFFE|((c.flips>>(i-1))&1))
def output(c):return E if c.alias else OUT

def mutate(m,c,target,index,packet=None):
 if target==RNG and index==0 and c.mutation&1:m[E+12]^=0x55;put(m,DT,bits(2.0))
 if target==REAL and c.mutation&2:m[E+12]^=0xA6;put(m,DT,bits(-.5))
 if target==RNG and index==1 and c.mutation&4:m[E+12]^=0x81;put(m,DT,bits(3.0))
 if target==FACTORY:
  put(m,MARK,0x13579BDF)
  if c.mutation&8 and packet is not None:
   for i in range(112):m[packet+i]^=0x5A
  if c.mutation&16:m[E+12]^=0x37;put(m,DT,bits(-4.0))

def reference(initial,c,values=None):
 m=dict(initial);a=inputs(c)if values is None else values;packet=bytearray(data(m,STACK+c.phase-112,112));calls=[];ops=[]
 def store(off,value,n=4):packet[off:off+n]=int(value&((1<<(8*n))-1)).to_bytes(n,'big')
 def rng(i):calls.append((RNG,(),b''));v=integer(i,c);mutate(m,c,RNG,i);return v
 def real():calls.append((REAL,(),b''));mutate(m,c,REAL,0);return c.sample
 def op(kind,x,y=None):
  ops.append((kind,x)if y is None else(kind,x,y))
  return x^0x80000000 if kind=='neg'else fp(x,y,kind,'left')
 store(0,0x200005);store(4,0);store(8,0x1401,2);store(0x1D,0x27,1)
 store(0xA,rng(0)%5+15,2)
 for off in(0xC,0x10):store(off,0)
 for off,value in((0x14,0x8A),(0x15,0),(0x16,0),(0x17,255),(0x18,0),(0x19,0),(0x1A,0)):store(off,value,1)
 for off,value in((0x1E,1),(0x20,255),(0x22,1)):store(off,value,2)
 store(0x24,bits(1.0));sample=real();width=op('add',op('mul',sample,bits(50.0)),bits(500.0));scale=op('mul',read(m,CONSTANT),read(m,DT))
 # Follow the original arithmetic order while deriving every output byte
 # independently from the public arguments and provider return values.
 nx=op('neg',a[3]);vx=op('mul',nx,scale);ny=op('neg',a[4]);nz=op('neg',a[5]);vy=op('mul',ny,scale);vz=op('mul',nz,scale)
 for off,value in((0x28,width),(0x2C,width),(0x30,a[0]),(0x34,a[1]),(0x38,a[2]),(0x48,vx),(0x4C,vy),(0x50,vz),(0x54,0),(0x58,13)):store(off,value)
 store(0x60,1,1);store(0x61,1,1)
 flags=13
 if rng(1)&1:flags|=0x40
 if rng(2)&1:flags|=0x80
 store(0x58,flags)
 for off,value in((0x1B,255),(0x1C,255),(0x62,0),(0x63,255)):store(off,value,1)
 calls.append((FACTORY,('packet',0,12,m[E+12],1),bytes(packet)));mutate(m,c,FACTORY,0)
 answer=output(c)if c.success else 0
 if answer:
  calls.append((COPY,(answer+0xA8,'parameters',12),PARAMETERS))
  for i,value in enumerate(PARAMETERS):m[answer+0xA8+i]=value
 return m,calls,answer+0xA8 if answer else 0,ops

class Machine(base.Machine):
 def __init__(self,words,m,c):
  a=inputs(c);super().__init__(words,m,c,entry=ENTRY,args=(0xBAD00004,0xBAD00005,a[2],a[3]));self.f[12],self.f[14]=a[:2];self.ri=0;self.homes=[]
 def record_call(self,t):
  counts={RNG:0,REAL:0,FACTORY:5,COPY:3};assert t in counts,hex(t);args=list(self.arguments(counts[t]));raw=args[:];packet=b''
  if t==FACTORY:self.homes.append(('packet',args[0]-self.target_home));packet=data(self.memory,args[0],112);args[0]='packet'
  if t==COPY:self.homes.append(('parameters',args[1]-self.target_home));packet=data(self.memory,args[1],args[2]);args[1]='parameters'
  self.calls.append((t,tuple(args),packet));self.raw_calls.append((t,tuple(raw)))
 def hook(self,t):
  args=self.raw_calls[-1][1];index=self.ri;value=0xDEADBEEF
  if t==RNG:value=integer(self.ri,self.c);self.ri+=1
  elif t==REAL:value=0xA5000002
  elif t==FACTORY:value=output(self.c)if self.c.success else 0
  elif t==COPY:
   packet=data(self.memory,args[1],args[2]);assert args[2]==12
   for i,v in enumerate(packet):self.memory[args[0]+i]=v
   value=args[0]
  mutate(self.memory,self.c,t,index,args[0]if t==FACTORY else None)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=u32(value)
  if t==REAL:self.f[0]=self.c.sample

def cases():
 for seed,flips,success in itertools.product(range(256),range(4),(0,1)):
  yield Case(seed=seed,flips=flips,success=success,mutation=seed%32,phase=(seed%2)*8,pattern=seed%4,sample=bits((0.,.25,.5,.75,-.5,1.25)[seed%6]),dt=bits((0.,1.,2.,-.5)[seed%4]))
 for seed,flips,success in itertools.product(range(8),range(4),(0,1)):yield Case(seed=seed,flips=flips,success=success,alias=1,mutation=31,pattern=seed%4)

def programs(labels=None):return source.programs()

def main(labels=None):
 streams=programs(labels);seen={k:set()for k in streams};homes={k:set()for k in streams};fp_differences={k:0 for k in streams if k!='retail'};n=0
 for c in cases():
  initial=fixture(c);expected,calls,answer,ops=reference(initial,c)
  for label,words in streams.items():
   q=Machine(words,initial,c).run();assert(public(q.memory),q.calls,q.r[2])==(public(expected),calls,answer),(label,c,'public state/calls/return')
   seen[label].update(q.visits);homes[label].update(q.homes)
   if label=='retail':assert q.fp_ops==ops,('model FP order',c,q.fp_ops,ops)
   else:fp_differences[label]+=q.fp_ops!=ops
  n+=1
 report=dict(cases_per_stream=n,words_visited={k:len(v)for k,v in seen.items()},private_homes={k:sorted(v)for k,v in homes.items()},FP_order_disagreements=fp_differences,complete_public_bytes_calls_and_return_agree=True,source_installed=False,c_match_credit=0)
 (O/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main(sys.argv[1:]or['v4'])
