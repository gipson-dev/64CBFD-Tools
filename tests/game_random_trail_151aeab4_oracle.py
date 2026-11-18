"""Independent randomized-trail model, full call homes and exposed packet."""
from pathlib import Path
from dataclasses import dataclass,asdict,replace
import itertools,json,struct
from tools.tests import game_strip_update_151ad174_private_oracle as o
from tools.tests.game_strip_update_151ad174_ordered_trace import Trace
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_random_trail_151aeab4_recovery as source
p=source.OUT;ENTRY=source.ENTRY;FRAME=152
POSITION,OUTPUT,ACTOR=0x30000,0x60000,0x50000
elf=(source.FROZEN/'conker/build/conker.us.elf').read_bytes();SYMS={row[1]:row[2][1]for row in symbol_rows(elf)}
RNG,REAL,TRIG,SUBMIT=[SYMS[n]for n in('func_150ADA20','func_150ADA68','func_151423D8','func_151DA6F8')]
GLOBALS=[SYMS[n]for n in('D_800A9D98','D_800A9D9C','D_800A9DA0','D_800A9DA4')]
CONSTANTS=[struct.unpack_from('>I',elf,elf_slot_offset(elf,at,4))[0]for at in GLOBALS]
COUNTS={RNG:0,REAL:0,TRIG:1,SUBMIT:18};put,read=o.put,o.read
@dataclass(frozen=True)
class Case:
 seed:int=0
 azimuth:int=0
 pitch:int=0
 first:int=0
 second:int=0
 last:int=0
 mode:int=0xABCD0080
 channel:int=0x123400FF
 mutation:int=0
 pattern:int=0
 phase:int=0

def fixture(c):
 m={o.STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,512)}
 for base,size in((POSITION,64),(OUTPUT,128),(ACTOR,256)):
  assert base+size<=o.STACK-2048 or base>=o.STACK+512,'public fixture overlaps private stack'
  m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(size)})
 for j,value in enumerate((1.25,-2.5,4.)):put(m,POSITION+j*4,o.bits(value+c.seed))
 for at,value in zip(GLOBALS,CONSTANTS):put(m,at,value)
 m[ACTOR+0xC]=c.channel&255
 return m

class Service:
 def __init__(self,m,c):self.m,self.c,self.calls,self.counts=m,c,[],dict.fromkeys(COUNTS,0);self.packets=[];self.physical=[]
 def invoke(self,target,args):
  c,m=self.c,self.m;ordinal=len(self.calls);index=self.counts[target];self.counts[target]+=1
  self.physical.append((target,tuple(args)))
  if target==SUBMIT:
   assert len(args)==18 and index==0
   packet=tuple(read(m,args[1]+4*j)for j in range(3));position=tuple(read(m,args[0]+4*j)for j in range(3));self.packets.append(packet)
   a=list(args);a[1]='VELOCITY'
   for i in(4,7,10,11,16):a[i]&=255
   for i in(3,13,14):a[i]=(((a[i]&65535)^32768)-32768)&0xFFFFFFFF
   self.calls.append((target,tuple(a),packet))
   for j,value in enumerate((*position,*packet)):put(m,OUTPUT+j*4,value)
   put(m,OUTPUT+24,a[7]);put(m,OUTPUT+28,a[16]);put(m,OUTPUT+32,a[3]);put(m,OUTPUT+36,a[4])
   if c.mutation&8:
    m[args[0]+1]^=0x5A;m[args[1]+10]^=0xA7
   return OUTPUT
  assert len(args)==COUNTS[target]
  self.calls.append((target,tuple(args)))
  if c.mutation&1:
   put(m,GLOBALS[0],o.bits(.125+ordinal*.0625));put(m,GLOBALS[1],o.bits(2.+ordinal*.25));put(m,GLOBALS[2],o.bits(4.+ordinal*.5));put(m,GLOBALS[3],o.bits(1.+ordinal*.125))
  if c.mutation&2:m[POSITION+2]^=(ordinal+1)&255
  if target==RNG:
   assert index<5;return(c.azimuth,c.pitch,c.first,c.second,c.last)[index]&0xFFFFFFFF
  if target==REAL:
   assert index<3
   values=(o.bits((c.seed%5)*.25),o.bits(.125+c.seed*.0625),o.bits(.75-c.seed*.03125))
   return(0x7FC12345 if c.pattern==1 and index==0 else 0x80000000 if c.pattern==2 and index==0 else 0x7F800000 if c.pattern==3 and index==0 else values[index])
  assert target==TRIG and 0<=args[0]<256
  return o.bits(-1.+args[0]/128.)

def reference(initial,c,position=POSITION,mode=None,channel=None,target_home=None):
 m=dict(initial);s=Service(m,c);mode=c.mode if mode is None else mode;channel=c.channel if channel is None else channel;home=o.STACK+c.phase if target_home is None else target_home
 az=s.invoke(RNG,())&255;pitch=((s.invoke(RNG,())&127)-63)&255
 av=s.invoke(TRIG,(az,));aq=s.invoke(TRIG,((az-64)&255,));pv=s.invoke(TRIG,(pitch,));pq=s.invoke(TRIG,((pitch-64)&255,))
 speed=o.mul(o.add(o.mul(s.invoke(REAL,()),o.bits(80.)),o.bits(20.)),read(m,GLOBALS[0]))
 horizontal=o.mul(speed,pv);negative=speed^0x80000000
 velocity=(o.mul(horizontal,aq),o.mul(negative,pq),o.mul(horizontal,av))
 first_sample=s.invoke(REAL,());first=s.invoke(RNG,());second=s.invoke(RNG,());second_sample=s.invoke(REAL,());last=s.invoke(RNG,())
 vector=home-16
 for j,value in enumerate(velocity):put(m,vector+j*4,value)
 args=(position,vector,o.add(o.mul(first_sample,read(m,GLOBALS[1])),read(m,GLOBALS[2])),first%41+60,second%101+155,o.add(o.mul(second_sample,o.bits(4.)),read(m,GLOBALS[3])),last%5+3,mode&255,o.bits(1.),o.bits(1.),0,0,0,16,15,0,channel&255,1)
 s.invoke(SUBMIT,args)
 return m,s.calls,s.packets

class Oracle(Trace):
 def __init__(self,words,m,c,entry=ENTRY,arguments=None,connected=None):
  self.fp=[];self.loads={};self.boundaries=[]
  FactoryOracle.__init__(self,words,m,c,entry=entry,s={},arguments=arguments or(POSITION,c.mode,c.channel),connected=connected)
  self.service=Service(self.memory,c);self.saved_g=tuple(self.r[16:24])+(self.r[28],self.r[29],self.r[30]);self.saved_fp=tuple(self.f[20:])
 def get(self,at,n):return FactoryOracle.get(self,at,n)
 def record_call(self,target):assert target in COUNTS,hex(target);self.pending=tuple(self.arguments(COUNTS[target]))
 def hook(self,target):
  self.boundaries.append((target,self.pending,tuple(self.get(self.r[29]+i,1)for i in range(FRAME+16))))
  value=self.service.invoke(target,self.pending)
  for i in range(max(4,COUNTS[target])):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF
  if target in(REAL,TRIG):self.f[0]=value
  else:self.r[2]=value

def verify(words,c):
 initial=fixture(c);expected,calls,packets=reference(initial,c);m=Oracle(words,initial,c).run()
 assert o.public(m.memory)==o.public(expected),('public',asdict(c),next(((hex(at),v,expected.get(at))for at,v in o.public(m.memory).items()if v!=expected.get(at)),None))
 assert m.service.calls==calls and m.service.packets==packets,('calls',asdict(c),m.service.calls,calls)
 assert tuple(m.r[16:24])+(m.r[28],m.r[29],m.r[30])==m.saved_g
 assert tuple(m.f[20:])==m.saved_fp
 return m

def cases():
 for i,(az,pitch,mutation)in enumerate(itertools.product((0,1,127,128,255,0xABCD0080),(0,63,64,127,128,255,0xFFFF00FF),range(16))):
  yield Case(seed=i%8,azimuth=az,pitch=pitch,first=(0,40,41,0xFFFFFFFF)[i%4],second=(0,100,101,0x80000000)[i%4],last=(0,4,5,0xFFFFFFFF)[i%4],mode=(0,0xABCD0080,0x123400FF,0xFFFFFFFF)[i%4],channel=(0xFFFF0000,0xABCD0001,0x12340080,0xFFFFFFFF)[i%4],mutation=mutation,pattern=(i//7)%4,phase=(i&1)*8)
 for az in range(256):yield Case(seed=az%8,azimuth=0x12340000+az,pitch=az,first=az*41+40,second=az*101+100,last=az*5+4,mutation=az%16,phase=(az&1)*8)
