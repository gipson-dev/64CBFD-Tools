"""Independent sampled-position model and opaque heading/trig providers."""
from pathlib import Path
from dataclasses import dataclass,asdict,replace
import itertools,json,struct
from tools.tests import game_strip_update_151ad174_private_oracle as o
from tools.tests.game_strip_update_151ad174_ordered_trace import Trace
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_strip_follow_151ae3a8_recovery as source
p=source.OUT;ENTRY=source.ENTRY
ACTOR,OTHER_ACTOR,RECORD,OTHER_RECORD,POINTS,OTHER_POINTS,CHILD,OTHER_CHILD,INPUT=0x30000,0x32000,0x40000,0x41000,0x50000,0x54000,0x60000,0x61000,0x70000
elf=(source.FROZEN/'conker/build/conker.us.elf').read_bytes();SYMS={row[1]:row[2][1]for row in symbol_rows(elf)}
HEADING,TRIG=[SYMS[n]for n in('func_15143E08','func_151423D8')]
put,read=o.put,o.read
selected=lambda c:OTHER_RECORD if c.seed&1 else RECORD
@dataclass(frozen=True)
class Case:
 seed:int=0
 count:int=20
 spacing:float=140.
 progress:float=.5
 heading:int=0
 mutation:int=0
 phase:int=0
 pattern:int=0

def fixture(c):
 m={o.STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-1024,128)}
 for base,size in((ACTOR,1024),(OTHER_ACTOR,1024),(RECORD,88),(OTHER_RECORD,88),(CHILD,192),(OTHER_CHILD,192),(INPUT,64),(POINTS-40*24,320*24),(OTHER_POINTS-40*24,320*24)):
  m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(size)})
 put(m,INPUT+0x1C,ACTOR);put(m,INPUT+0x28,o.bits((0.,1.5,-2.,100.)[c.seed%4]))
 for actor in(ACTOR,OTHER_ACTOR):
  put(m,actor+0x31C,CHILD)
  for j,value in enumerate((1.25,-2.5,4.)):put(m,actor+0x14+4*j,o.bits(value+c.seed))
 for child in(CHILD,OTHER_CHILD):put(m,child+0x9C,selected(c));put(m,child+0xA0,o.bits(c.progress));m[child+0xAE]=0xA5
 for rec in(RECORD,OTHER_RECORD):put(m,rec+0x38,POINTS);put(m,rec+0x3C,o.bits(c.spacing));m[rec+0x42]=c.count
 for base in(POINTS,OTHER_POINTS):
  for i in range(-40,280):
   for j,value in enumerate((i*1.5,i*.25,-i*.5)):
    word=o.bits(value+(3 if base==OTHER_POINTS else 0))
    if c.pattern and (i+j+c.seed)%7==0:word=(0x7FC12345,0x80000000,0x7F800000,0xFF800000)[c.pattern-1]
    put(m,base+i*24+j*4,word)
 return m

class Service:
 def __init__(self,m,c):self.m,self.c,self.calls=m,c,[]
 def invoke(self,target,args):
  m,c=self.m,self.c;ordinal=len(self.calls);self.calls.append((target,tuple(args)))
  if target==HEADING:
   assert ordinal==0 and args==(ACTOR,)
   if c.mutation&1:
    put(m,INPUT+0x1C,OTHER_ACTOR);put(m,ACTOR+0x31C,OTHER_CHILD);put(m,OTHER_CHILD+0x9C,OTHER_RECORD if selected(c)==RECORD else RECORD)
   return c.heading&0xFFFFFFFF
  assert target==TRIG and ordinal in(1,2)and 0<=args[0]<256
  if ordinal==1 and c.mutation&2:
   rec=selected(c);m[rec+0x42]=(c.count+1)&255;put(m,rec+0x3C,o.bits(280.));put(m,rec+0x38,OTHER_POINTS)
  if ordinal==2 and c.mutation&4:
   for j in range(3):put(m,ACTOR+0x14+j*4,o.add(read(m,ACTOR+0x14+j*4),o.bits(.5+j*.25)))
   put(m,INPUT+0x28,o.bits(3.25));put(m,read(m,ACTOR+0x31C)+0xA0,o.bits(1.-c.progress))
  if c.mutation&8:put(m,read(m,ACTOR+0x31C)+0x9C,OTHER_RECORD if selected(c)==RECORD else RECORD)
  return o.bits(-.875+args[0]/128.)

def reference(initial,c):
 m=dict(initial);service=Service(m,c);actor=read(m,INPUT+0x1C);record=read(m,read(m,actor+0x31C)+0x9C)
 angle=(service.invoke(HEADING,(actor,))-128)&255
 side=service.invoke(TRIG,((angle-64)&255,));forward=service.invoke(TRIG,(angle,))
 child=read(m,actor+0x31C);old=[read(m,actor+0x14+j*4)for j in range(3)];scale=read(m,INPUT+0x28);progress=read(m,child+0xA0)
 steps=o.signed(o.narrow(o.div(o.bits(140.),read(m,record+0x3C))))
 span=m[record+0x42]-steps-1;product=o.mul(o.bits(float(span)),progress);index=o.signed(o.narrow(product));assert -40<=index and index+1<280
 m[child+0xAE]=index&255
 along=o.sub(o.mul(o.bits(float(m[record+0x42]-steps-1)),progress),o.bits(float(index)))
 base=read(m,record+0x38);first=[read(m,base+index*24+j*4)for j in range(3)];nxt=[read(m,base+(index+1)*24+j*4)for j in range(3)]
 result=[o.add(o.mul(o.sub(y,x),along),x)for x,y in zip(first,nxt)]
 result[0]=o.add(result[0],o.mul(scale,side));result[2]=o.add(result[2],o.mul(scale,forward))
 for j,value in enumerate(result):put(m,actor+0x14+j*4,o.add(o.sub(value,old[j]),old[j]))
 return m,service.calls

class Oracle(Trace):
 def __init__(self,words,m,c,entry=ENTRY,arguments=None,connected=None):
  self.fp=[];self.loads={};self.boundaries=[]
  FactoryOracle.__init__(self,words,m,c,entry=entry,s={},arguments=arguments or(INPUT,),connected=connected)
  self.service=Service(self.memory,c);self.saved_g=tuple(self.r[16:24])+(self.r[28],self.r[29],self.r[30]);self.saved_fp=tuple(self.f[20:])
 def get(self,at,n):return FactoryOracle.get(self,at,n)
 def record_call(self,target):assert target in(HEADING,TRIG),hex(target);self.pending=tuple(self.arguments(1))
 def hook(self,target):
  self.boundaries.append((target,self.pending,tuple(self.get(self.r[29]+i,1)for i in range(136))))
  value=self.service.invoke(target,self.pending)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF
  if target==HEADING:self.r[2]=value
  else:self.f[0]=value

def verify(words,c):
 initial=fixture(c);expected,calls=reference(initial,c);m=Oracle(words,initial,c).run()
 assert o.public(m.memory)==o.public(expected),('public',asdict(c),next(((hex(at),v,expected.get(at))for at,v in o.public(m.memory).items()if v!=expected.get(at)),None))
 assert m.service.calls==calls,('calls',asdict(c),m.service.calls,calls)
 assert tuple(m.r[16:24])+(m.r[28],m.r[29],m.r[30])==m.saved_g
 assert tuple(m.f[20:])==m.saved_fp
 return m

def cases():
 for i,(count,spacing,progress,mutation,heading)in enumerate(itertools.product((0,1,4,20,128,255),(5.,140.),(0.,.5,1.),range(16),(0,127,128,255))):
  yield Case(seed=i%8,count=count,spacing=spacing,progress=progress,heading=heading,mutation=mutation,phase=(i&1)*8,pattern=(i//7)%5)
 for heading in range(256):yield Case(seed=heading%8,heading=0x12340000+heading,mutation=heading%16,phase=(heading&1)*8)
