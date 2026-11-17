"""Independent attached-point emission model and finite instruction execution."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,math,struct,sys
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as base
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_attached_emission_151a4a38_recovery as source
O=source.OUT;R=source.ROOT;ENTRY=source.ENTRY;RNG=0x150ADA20;TRANSFORM=0x15143134;EMIT=0x15153634
E,A,ALT,M,MARK,DT,STACK=0x30000,0x50000,0x60000,0x70000,0x80000,0x800BE9A4,base.STACK
S={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())}
u32=lambda n:n&0xffffffff
half=lambda n:((n&65535)^32768)-32768
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
public=lambda m:{p:v for p,v in m.items()if not STACK-4096<=p<STACK+1024}
DEFINED=tuple(i for i in range(108)if i!=5 and not 0x65<=i<0x6C)
@dataclass(frozen=True)
class Case:
 seed:int=0;flips:int=0;route:int=0;mutation:int=0;phase:int=0;pattern:int=0;alias:int=0
def actor(c):return E if c.alias else A
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-4096,1024)}
 for at,n in((E,512),(A,512),(ALT,512),(MARK,4)):
  m.update({at+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for p in(A,ALT,E if c.alias else A):
  put(m,p,1);m[p+0x3B]=c.seed&255;m[p+0x74]=0x20;put(m,p+0x76,((c.seed&255)<<8)|0xA5,2);put(m,p+0x1D4,M)
 p=actor(c);put(m,E+0x28,p);m[E+0x2C]=m[p+0x3B];m[E+0x38]=c.seed&255
 put(m,E+0x30,bits((.25,0.,-1.,2.)[c.pattern%4]));put(m,E+0x34,bits((1.5,1.,0.,2.75,32767.5,-2.,.5,-0.)[c.pattern%8]))
 for i,v in enumerate((1.25,-2.5,3.75)):put(m,E+0x3C+4*i,bits(v+c.seed*.125))
 put(m,DT,bits((1.,0.,2.,-.5)[c.pattern%4]));m[E+12]=c.seed&255
 if not c.alias:m[E+1]=(c.seed*7)&255
 if c.route in(1,2):put(m,p,0 if c.route==1 else 8)
 elif c.route==3:m[E+0x2C]^=0x80
 elif c.route==4:put(m,p+0x1D4,0)
 elif c.route==5:m[p+0x74]=0xAF
 elif c.route==6:put(m,E+0x34,bits(1.0));put(m,E+0x30,0)
 return m
def integer(index,c):return(0xFFFFFFFE|((c.flips>>index)&1))
def transform(m,c,args):
 point,out,matrix=args
 for i in range(3):put(m,out+4*i,fp(read(m,point+4*i),bits((i+1)*.5+c.seed*.0625),'add','left'))
 if c.mutation&1:
  put(m,E+0x34,bits((-1.75,2.75,3.5,.25)[c.seed%4]));put(m,E+0x28,ALT);put(m,actor(c)+0x76,0xF4A5,2)
 if c.mutation&2:m[E+12]^=0xA7;m[E+1]^=0x56;put(m,DT,bits(-4.0))
def mutate(m,c,target,index,out=None,packet=None):
 if target==RNG:
  if c.mutation&(4 if index==0 else 8):
   m[E+12]^=0x37+index;m[E+1]^=0x65+index
   if out is not None:
    for i in range(12):m[out+i]^=0x5A+index
 if target==EMIT:
  put(m,MARK,0x13579BDF);m[E+0xD]^=0x40
  if c.mutation&16 and packet is not None:
   for i in range(108):m[packet+i]^=0x96
def reference(initial,c,home=None):
 m=dict(initial);calls=[];ops=[];home=STACK+c.phase if home is None else home;out=home-16;packet=bytearray(data(m,home-124,108))
 def store(off,v,n=4):packet[off:off+n]=int(v&((1<<(8*n))-1)).to_bytes(n,'big')
 def op(k,x,y=None):
  ops.append((k,x)if y is None else(k,x,y))
  if k=='lt':return floating(x)<floating(y)
  if k=='trunc':
   f=floating(x);return u32(math.trunc(f))if math.isfinite(f)and -2147483648<=f<2147483648 else 0x80000000
  if k=='cvt':return bits((x^0x80000000)-0x80000000)
  return fp(x,y,k,'left')
 p=read(m,E+0x28)
 if read(m,p)==0 or read(m,p)==8 or m[E+0x2C]!=m[p+0x3B]:
  put(m,E+0xE,-1,2);m[E+0xD]|=1;return m,calls,E+0x28,ops
 if not read(m,p+0x1D4)or m[p+0x74]&15==15:return m,calls,E+0x28,ops
 value=op('add',read(m,E+0x34),op('mul',read(m,E+0x30),read(m,DT)));put(m,E+0x34,value)
 if not op('lt',bits(1.0),value):return m,calls,E+0x28,ops
 p=read(m,E+0x28);angle=(read(m,p+0x76,2)>>8)-64;args=(E+0x3C,out,u32(read(m,p+0x1D4)+(m[E+0x38]<<6)))
 calls.append((TRANSFORM,('point','position',args[2]),data(m,args[0],12)));transform(m,c,args)
 count=half(op('trunc',read(m,E+0x34)));store(0,count,2);store(2,0,2)
 remainder=op('sub',read(m,E+0x34),op('cvt',u32(count)));put(m,E+0x34,remainder)
 for off,v in((4,40),(0x1C,0),(0x1D,0),(0x1E,0),(0x1F,255),(0x20,0),(0x21,0),(0x22,0),(0x62,1),(0x63,0),(0x64,0)):store(off,v,1)
 for off,v in((6,0xC01),(0x10,23),(0x12,13),(0x26,1),(0x28,0),(0x2A,1),(0x44,angle-25),(0x46,-44),(0x48,50),(0x4A,50)):store(off,v,2)
 for off,v in((8,0x200005),(12,0),(0x14,0),(0x18,0),(0x2C,bits(1.)),(0x30,bits(300.)),(0x34,bits(400.)),(0x4C,0),(0x50,bits(15.)),(0x54,bits(-.5)),(0x58,bits(-.5))):store(off,v)
 packet[0x38:0x44]=data(m,out,12);flags=7
 for i in range(2):
  calls.append((RNG,(),b''));flags|=(0x40<<i)if integer(i,c)&1 else 0;mutate(m,c,RNG,i,out=out)
 store(0x5C,flags)
 for off,v in((0x23,255),(0x24,0),(0x25,255),(0x60,255),(0x61,255)):store(off,v,1)
 calls.append((EMIT,('packet',255,m[E+12],m[E+1]),bytes(packet)));mutate(m,c,EMIT,0)
 return m,calls,0xE5000002,ops
class Machine(base.Machine):
 def __init__(self,words,m,c):
  super().__init__(words,m,c,entry=ENTRY,args=(E,0xBAD00005,0xBAD00006,0xBAD00007));self.ri=0;self.homes=[];self.output_home=None
 def execute(self,w):
  if w>>26==17 and w>>21&31==20 and w&63==32:
   fs,fd=w>>11&31,w>>6&31;value=self.f[fs];self.fp_ops.append(('cvt',value));self.f[fd]=bits((value^0x80000000)-0x80000000);return
  super().execute(w)
 def record_call(self,t):
  args=list(self.arguments({RNG:0,TRANSFORM:3,EMIT:4}[t]));raw=args[:];packet=b''
  if t==TRANSFORM:
   packet=data(self.memory,args[0],12);self.output_home=args[1];self.homes.append(('position',args[1]-self.target_home));args[:2]=['point','position']
  elif t==EMIT:packet=data(self.memory,args[0],108);self.homes.append(('packet',args[0]-self.target_home));args[0]='packet'
  self.calls.append((t,tuple(args),packet));self.raw_calls.append((t,tuple(raw)))
 def hook(self,t):
  args=self.raw_calls[-1][1];result=0xA5000002
  if t==TRANSFORM:transform(self.memory,self.c,args)
  elif t==RNG:result=integer(self.ri,self.c);mutate(self.memory,self.c,RNG,self.ri,out=self.output_home);self.ri+=1
  else:assert t==EMIT;mutate(self.memory,self.c,EMIT,0,packet=args[0]);result=0xE5000002
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=result
def cases():
 for seed,flips in itertools.product(range(256),range(4)):yield Case(seed=seed,flips=flips,mutation=seed%32,phase=8*(seed%2),pattern=seed%8)
 for route,seed,flips in itertools.product(range(1,7),range(8),range(4)):yield Case(seed=seed,flips=flips,route=route,mutation=31,phase=8*(seed%2),pattern=seed%8)
 for seed,flips in itertools.product(range(8),range(4)):yield Case(seed=seed,flips=flips,mutation=31,pattern=seed%8,alias=1)
def programs(label='raw'):return source.programs()

def main(label='v13'):
 streams=programs(label);seen={k:set()for k in streams};homes={k:set()for k in streams};disagreements={k:0 for k in streams};n=0
 for c in cases():
  initial=fixture(c);expected,calls,answer,ops=reference(initial,c)
  for name,words in streams.items():
   q=Machine(words,initial,c).run();assert(public(q.memory),q.calls,q.r[2])==(public(expected),calls,answer),(name,c,'public/calls/return',q.calls,calls)
   seen[name].update(q.visits);homes[name].update(q.homes);disagreements[name]+=q.fp_ops!=ops
  n+=1
 assert all(v==0 for v in disagreements.values()),disagreements
 report=dict(cases_per_stream=n,reachable_words={k:len(v)for k,v in seen.items()},private_homes={k:sorted(v)for k,v in homes.items()},FP_order_disagreements=disagreements,full_public_bytes_calls_and_return=True,descriptor_bytes=108,defined_descriptor_bytes=100,indeterminate_C_bytes=8,source_installed=False,c_match_credit=0)
 (O/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main(sys.argv[1]if len(sys.argv)>1 else'v13')
