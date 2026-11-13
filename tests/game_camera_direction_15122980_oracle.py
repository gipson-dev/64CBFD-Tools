from pathlib import Path
import sys,struct,itertools
from dataclasses import dataclass
from tools.experiments import game_camera_direction_15122980_match as packet
root=packet.ROOT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
out=packet.OUT
ENTRY=0x15122980;CAMERA=0x60000;FACTOR=0x800a34a0
DIFF=0x15048f90;HEADING=0x15048fc8;SMOOTH=0x150495b0;ANGLE=0x15048a70;FINAL=(0x15123a54,0x1512e140,0x1512a390)
S=dict(D_800A34A0=FACTOR,func_15048F90=DIFF,func_15048FC8=HEADING,func_150495B0=SMOOTH,func_15048A70=ANGLE,func_15123A54=FINAL[0],func_1512E140=FINAL[1],func_1512A390=FINAL[2])
@dataclass(frozen=True)
class Case:
 phase:int;mode:int;gate:int;flags:int;angle:int;mutation:int
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-512,256)}
 m.update({CAMERA+i:(i*29+0x51)&255 for i in range(0x900)})
 for off,value in ((0xdc,c.mode),(0x84,c.flags),(0x390,c.angle),(0x37c,bits(10.0)),(0x39c,bits(-3.0)),(0x8d4,bits(9.0)),(0x8d8,bits(7.0)),(0x8dc,bits(4.0)),(0x7b4,bits(0.25))):put(m,CAMERA+off,value)
 put(m,CAMERA+0x298,c.gate,2);put(m,FACTOR,bits(0.5))
 for off,values in ((0x2f8,(1.,2.,3.)),(0x2c8,(4.,6.,8.)),(0x2bc,(7.,9.,11.))):
  for i,value in enumerate(values):put(m,CAMERA+off+4*i,bits(value))
 return m
def public(m):return {a:b for a,b in m.items() if not STACK-1024<=a<STACK+512}
def vec(m,origin,target):return tuple(bits(floating(read(m,target+4*i))-floating(read(m,origin+4*i))) for i in range(3))
def reference(c):
 m=fixture(c);events=[]
 if c.mode!=4:
  for dest in (0x2c8,0x2bc):events.append(('diff',dest,vec(m,CAMERA+0x2f8,CAMERA+dest)))
  events += [('heading',tuple(map(bits,(3.,4.,5.)))),('heading',tuple(map(bits,(6.,7.,8.))))]
  angle=floating(c.angle)
  value=0.0 if not c.gate else 0.75 if c.flags&0x100000 or (angle>180.0 and angle<270.0) else 0.5
  put(m,CAMERA+0x8d4,bits(value))
  events.append(('smooth',bits(value),read(m,CAMERA+0x8d8),read(m,CAMERA+0x7b4)))
  put(m,CAMERA+0x8dc,bits(2.0));put(m,CAMERA+0x8d8,bits(-2.0))
  events.append(('angle',bits(30.0),bits(90.0)))
  if c.mutation&1:put(m,CAMERA+0x37c,bits(50.0));put(m,CAMERA+0x8dc,bits(3.0))
  if c.mutation&2:put(m,FACTOR,bits(0.25))
  delta=bits(8.0);prod=bits(floating(delta)*floating(read(m,CAMERA+0x8dc)))
  updated=bits(floating(read(m,CAMERA+0x37c))+floating(prod));put(m,CAMERA+0x37c,updated)
  put(m,CAMERA+0x39c,bits(floating(updated)*floating(read(m,FACTOR))))
 for i,t in enumerate(FINAL):events.append(('final',t));m[CAMERA+0x100+i]=0x71+i
 return public(m),events
class Machine(FactoryOracle):
 def __init__(self,w,c):
  super().__init__(w,fixture(c),c,entry=ENTRY,s=S,arguments=(CAMERA,))
  self.log=[];self.heading_count=0
 def record_call(self,t):
  a=self.arguments(6)
  if t==DIFF:
   assert a[0]==CAMERA+0x2f8 and a[1] in (CAMERA+0x2c8,CAMERA+0x2bc)
   self.log.append(('diff',a[1]-CAMERA,vec(self.memory,a[0],a[1])))
  elif t==HEADING:
   self.log.append(('heading',tuple(read(self.memory,a[0]+4*i) for i in range(3))))
  elif t==SMOOTH:
   assert a[0]==CAMERA+0x8dc and a[2]==CAMERA+0x8d8 and a[3]==bits(1.) and a[4]==bits(2.)
   self.log.append(('smooth',a[1],read(self.memory,a[2]),a[5]))
  elif t==ANGLE:self.log.append(('angle',self.f[12],self.f[14]))
  else:
   assert t in FINAL and a[0]==CAMERA;self.log.append(('final',t))
  self.calls.append((t,tuple(a)))
 def hook(self,t):
  a=self.calls[-1][1];value=None
  if t==DIFF:
   for i,v in enumerate(vec(self.memory,a[0],a[1])):put(self.memory,a[2]+4*i,v)
  elif t==HEADING:
   value=bits((30.0,90.0)[self.heading_count]);self.heading_count+=1
  elif t==SMOOTH:put(self.memory,CAMERA+0x8dc,bits(2.0));put(self.memory,CAMERA+0x8d8,bits(-2.0))
  elif t==ANGLE:
   value=bits(8.0)
   if self.case.mutation&1:put(self.memory,CAMERA+0x37c,bits(50.0));put(self.memory,CAMERA+0x8dc,bits(3.0))
   if self.case.mutation&2:put(self.memory,FACTOR,bits(0.25))
  else:self.memory[CAMERA+0x100+FINAL.index(t)]=0x71+FINAL.index(t)
  for i in range(6 if t==SMOOTH else 4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)]
  if value is not None:self.f[0]=value
def program(path):
 d,r=payload(path,'func_15122980');return bound_blob(d,r,S)
def run():
 rom=(root/'conker/conker.us.bin').read_bytes()
 programs=[struct.unpack_from('>87I',rom,0x14fe30)]+[program(out/(n+'.o')) for n in ('after','generated','generic')]
 count=0
 for phase,mode,gate,flags,angle,mutation in itertools.product((0,8),(0,4),(0,1),(0,0x100000),(bits(179.),bits(180.),bits(181.),bits(269.),bits(270.),bits(271.),0x7fc00000),range(4)):
  c=Case(phase,mode,gate,flags,angle,mutation);want,events=reference(c)
  for words in programs:
   m=Machine(words,c).run();assert (public(m.memory),m.log)==(want,events),(c,m.log,events)
  count+=1
 print('independent camera heading model',count,'cases across four streams, with helper mutations and NaN gate',flush=True)
