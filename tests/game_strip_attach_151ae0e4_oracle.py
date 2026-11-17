"""Independent attachment model, opaque providers and complete MIPS execution."""
from pathlib import Path
from dataclasses import dataclass,asdict,replace
import itertools,json,struct
from tools.tests import game_strip_update_151ad174_private_oracle as o
from tools.tests.game_strip_update_151ad174_ordered_trace import Trace
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_strip_attach_151ae0e4_recovery as source
p=source.OUT;r=source.ROOT;ENTRY=source.ENTRY
ACTOR,RECORD,OTHER_RECORD,POINTS,OTHER_POINTS,CHILD,OTHER_CHILD,REQUEST=0x30000,0x40000,0x41000,0x50000,0x54000,0x60000,0x61000,0x70000
elf=(source.FROZEN/'conker/build/conker.us.elf').read_bytes();SYMS={row[1]:row[2][1]for row in symbol_rows(elf)}
QUERY,PROJECT,CUTOFF=[SYMS[n]for n in('func_151AE590','func_151AE2BC','D_800A9290')]
raw_cutoff=struct.unpack_from('>I',elf,elf_slot_offset(elf,CUTOFF,4))[0]
put,read=o.put,o.read
selected=lambda c:OTHER_RECORD if c.seed&1 else RECORD

@dataclass(frozen=True)
class Case:
 seed:int=0
 key:int=0xA5
 count:int=20
 spacing:float=140.0
 fraction:float=.5
 gate:int=0
 mutation:int=0
 phase:int=0
 threshold:int=0
 nan_point:bool=False

def fixture(c):
 m={o.STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-1024,128)}
 for base,size in((ACTOR,0x400),(RECORD,88),(OTHER_RECORD,88),(CHILD,192),(OTHER_CHILD,192),(REQUEST,64),(POINTS-32*24,288*24),(OTHER_POINTS-32*24,288*24)):
  m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(size)})
 for rec in(RECORD,OTHER_RECORD):
  put(m,rec+0x38,POINTS);put(m,rec+0x3C,o.bits(c.spacing));m[rec+0x42]=c.count
  put(m,rec+0x52,{2:1,3:256,4:0xFFFF}.get(c.gate,0),2)
 put(m,ACTOR+0x31C,CHILD);m[ACTOR+0x1CA]=0 if c.gate==5 else 1;m[ACTOR+0x104]=1 if c.gate==6 else 0
 for child in(CHILD,OTHER_CHILD):put(m,child+0xA0,o.bits(c.fraction));m[child+0x98]=0;put(m,child+0x9C,OTHER_RECORD)
 m[REQUEST+0x1B]=c.key&255
 for base in(POINTS,OTHER_POINTS):
  for i in range(-32,256):
   for j,value in enumerate((i*1.5,i*.25,-i*.5)):put(m,base+i*24+j*4,o.bits(value))
 quotient=o.signed(o.narrow(o.div(o.bits(140.),o.bits(c.spacing))))
 idx=o.signed(o.narrow(o.mul(o.bits(float(c.count-quotient-1)),o.bits(c.fraction))))
 assert -32<=idx<256
 for j,value in enumerate((idx*1.5+(1 if c.seed&2 else 0),idx*.25,-idx*.5)):put(m,ACTOR+0x14+j*4,o.bits(value))
 put(m,CUTOFF,(o.bits(0.),o.bits(1.),o.bits(100.),0x7FC00000)[c.threshold])
 if c.nan_point:put(m,POINTS+idx*24,0x7FC12345)
 return m

class Service:
 def __init__(self,m,c):self.m,self.c,self.calls=m,c,[]
 def invoke(self,target,args):
  m,c=self.m,self.c;self.calls.append((target,tuple(args)))
  if target==QUERY:
   if c.mutation&1:
    put(m,ACTOR+0x31C,OTHER_CHILD);put(m,ACTOR+0x14,o.add(read(m,ACTOR+0x14),o.bits(.25)))
   return 0 if c.gate==1 else selected(c)
  assert target==PROJECT
  put(m,args[0],o.bits(c.fraction))
  if c.mutation&2:
   m[args[1]+0x42]=(c.count+1)&255;put(m,args[1]+0x3C,o.bits(280.));put(m,args[1]+0x38,OTHER_POINTS)
  if c.mutation&4:
   child=CHILD if read(m,ACTOR+0x31C)==OTHER_CHILD else OTHER_CHILD
   put(m,ACTOR+0x31C,child);put(m,child+0xA0,o.bits(1.-c.fraction))
  if c.mutation&8:
   m[ACTOR+0x1CA]=0;m[ACTOR+0x104]=0xA5;put(m,args[1]+0x52,1,2)
   put(m,ACTOR+0x18,o.add(read(m,ACTOR+0x18),o.bits(.5)));put(m,CUTOFF,o.bits(9.))
  return 0xABCD1234

def reference(initial,c):
 m=dict(initial);service=Service(m,c);record=service.invoke(QUERY,(c.key&255,))
 if not record:return m,service.calls,True
 if read(m,record+0x52,2)!=0 or not m[ACTOR+0x1CA] or m[ACTOR+0x104]:return m,service.calls,False
 service.invoke(PROJECT,(read(m,ACTOR+0x31C)+0xA0,record,read(m,ACTOR+0x14),read(m,ACTOR+0x18),read(m,ACTOR+0x1C)))
 limit=m[record+0x42]-o.signed(o.narrow(o.div(o.bits(140.),read(m,record+0x3C))))-1
 idx=o.signed(o.narrow(o.mul(o.bits(float(limit)),read(m,read(m,ACTOR+0x31C)+0xA0))))
 assert -32<=idx<256,(asdict(c),idx)
 points=read(m,record+0x38);x,y,z=[read(m,points+idx*24+4*i)for i in range(3)]
 dx,dy,dz=[o.sub(v,read(m,ACTOR+0x14+4*i))for i,v in enumerate((x,y,z))]
 distance=o.add(o.mul(dz,dz),o.add(o.mul(dx,dx),o.mul(dy,dy)))
 if not o.floating(read(m,CUTOFF))<o.floating(distance):
  m[read(m,ACTOR+0x31C)+0x98]=c.key&255;m[ACTOR+0x8A]=0x12
  put(m,read(m,ACTOR+0x31C)+0x9C,record);put(m,record+0x44,ACTOR)
 return m,service.calls,False

class SpinBoundary(Exception):pass
class SpinCode(dict):
 def __init__(self,values,owner):super().__init__(values);self.owner=owner
 def __getitem__(self,at):
  word=super().__getitem__(at)
  if at==ENTRY+0x24:
   assert word==0x1000FFFF and dict.__getitem__(self,at+4)==0,'non-stationary lookup failure'
   assert self.owner.r[2]==0,'false lookup spin'
   raise SpinBoundary
  self.owner.current_pc=at
  return word

class Oracle(Trace):
 def __init__(self,words,m,c,entry=ENTRY,arguments=None,connected=None):
  self.fp=[];self.loads={};self.boundaries=[];self.spins=False
  FactoryOracle.__init__(self,words,m,c,entry=entry,s={},arguments=arguments or(ACTOR,c.key),connected=connected)
  self.code=SpinCode(self.code,self);self.service=Service(self.memory,c)
  self.saved_g=tuple(self.r[16:24])+(self.r[28],self.r[29],self.r[30]);self.saved_fp=tuple(self.f[20:])
 def get(self,address,size):return FactoryOracle.get(self,address,size)
 def record_call(self,target):
  assert target in(QUERY,PROJECT),hex(target)
  self.pending=tuple(self.arguments(1 if target==QUERY else 5))
 def hook(self,target):
  self.boundaries.append((target,self.pending,tuple(self.get(self.r[29]+i,1)for i in range(72))))
  value=self.service.invoke(target,self.pending)
  for i in range(4 if target==QUERY else 5):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=value
 def run(self):
  try:return super().run()
  except SpinBoundary:self.spins=True;return self

def verify(words,c):
 initial=fixture(c);expected,calls,spin=reference(initial,c);m=Oracle(words,initial,c).run()
 assert o.public(m.memory)==o.public(expected),('public',asdict(c),next(((hex(at),v,expected.get(at))for at,v in o.public(m.memory).items()if v!=expected.get(at)),None))
 assert m.service.calls==calls,('calls',asdict(c),m.service.calls,calls)
 assert m.spins==spin
 if not spin:
  assert tuple(m.r[16:24])+(m.r[28],m.r[29],m.r[30])==m.saved_g
  assert tuple(m.f[20:])==m.saved_fp
 return m

def cases():
 for i,(count,spacing,fraction,mutation)in enumerate(itertools.product((0,1,4,20,128,255),(5.,140.),(0.,.5,1.),range(16))):
  yield Case(seed=i%4,key=(0,0xABCD0080,0xFFFF00FF,0x12340001)[i%4],count=count,spacing=spacing,fraction=fraction,mutation=mutation,phase=(i&1)*8,threshold=i%4,nan_point=i%19==0)
 for gate,seed in itertools.product(range(1,7),range(8)):yield Case(seed=seed,key=0xABCD0081,gate=gate,mutation=seed&1,phase=(seed&1)*8)
