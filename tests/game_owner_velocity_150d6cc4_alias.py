"""Check overlapping owner and target memory with modeled helpers."""
import itertools
from tools.tests import game_owner_velocity_150d6cc4_oracle as g
from tools.tests.game_actor_intensity_byte_oracle import float32
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import read
class Alias(g.Machine):
 def __init__(self,ws,c,mem,target):self.target=target;super().__init__(ws,c,mem)
 def record_call(self,t):
  assert t in(g.COPY,g.SCALE);args=tuple(self.arguments(2));assert args[0]==(self.target if t==g.COPY else g.OWNER+0x58),args
  if t==g.COPY:assert args[1]==g.OWNER+0x40,args
  else:assert args[1]==read(self.memory,g.OWNER+0xb0),args
  self.calls.append((t,args))
 def hook(self,t):
  c=self.case
  if t==g.COPY:
   for i in range(3):
    value=read(self.memory,self.target+0x14+4*i)
    if i==1:value=bits(float32(floating(value)+60.0))
    g.put(self.memory,g.OWNER+0x40+4*i,value)
   if c.mutation&1:g.put(self.memory,g.OWNER+0xb0,0x3f000000);g.put(self.memory,g.OWNER+0x58,0x40400000);g.put(self.memory,g.DT,0x3f000000)
  else:
   factor=floating(self.r[5]);count=read(self.memory,g.COUNT);assert 0<=count<=2
   for _ in range(count):
    values=[bits(float32(floating(read(self.memory,g.OWNER+0x58+4*i))*factor))for i in range(3)]
    for i,v in enumerate(values):g.put(self.memory,g.OWNER+0x58+4*i,v)
   if c.mutation&2:g.put(self.memory,g.DT,0x3f800000);g.put(self.memory,g.ACCEL,0x3f800000);g.put(self.memory,g.OWNER+0x4c,0x42480000)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)]

def run(state):
    bodies=[g.words(state[x])for x in ('after','retail','generated')];n=0
    for delta,word,identity,count,mutation in itertools.product((0,-0x14,0x2c,0xa0),(0,1),(0,1),(0,1,2),(0,1,2,3)):
     target=g.OWNER+delta;c=g.Case(0,word,identity,0x3f000000,count,0x3e800000,mutation,0);mem={g.STACK+i:(i*17+0xa5)&255 for i in range(-512,512)};mem.update({g.OWNER+i:(i*29+0x59)&255 for i in range(-256,1024)});g.put(mem,target,word)
     for off,v in ((0x14,0x3f800000),(0x18,0x40000000),(0x1c,0x40400000)):g.put(mem,target+off,v)
     g.put(mem,g.OWNER+0xa8,target);mem[g.OWNER+0xac]=0x41;g.put(mem,g.OWNER+0xb0,c.factor)
     for off,v in ((0x4c,0x41200000),(0x50,0x41a00000),(0x54,0x41f00000),(0x58,0x3f800000),(0x5c,0x40000000),(0x60,0x40400000),(0x64,0x40000000)):g.put(mem,g.OWNER+off,v)
     mem[target+0x3b]=0x41 if identity else 0x42;g.put(mem,g.DT,c.dt);g.put(mem,g.ACCEL,0x3f000000);g.put(mem,g.COUNT,count)
     machines=[Alias(ws,c,mem.copy(),target).run()for ws in bodies];states=[(g.public(m.memory),m.calls,m.r[2],m.fcsr,[e for e in m.trace if not g.STACK-512<=e[1]<g.STACK+512])for m in machines];assert states[0]==states[1]==states[2],(delta,c);n+=1
    return {'cases':n,'overlap_offsets':[0,-0x14,0x2c,0xa0]}
