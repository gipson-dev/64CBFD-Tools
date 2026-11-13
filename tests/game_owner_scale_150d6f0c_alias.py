"""Check overlapping owner and target memory with a modeled helper."""
import itertools
from tools.tests import game_owner_scale_150d6f0c_oracle as g
from tools.tests.game_actor_intensity_byte_oracle import float32
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import read
class Alias(g.Machine):
 def __init__(self,ws,c,mem,target):self.target=target;super().__init__(ws,c,mem)
 def record_call(self,t):
  assert t==g.HELPER;args=tuple(self.arguments(2));assert args==(self.target,g.OWNER+0x40),args;self.calls.append((t,args))
 def hook(self,t):
  c=self.case
  for i in range(3):
   value=read(self.memory,self.target+0x14+4*i)
   if i==1:value=bits(float32(floating(value)+60.0))
   g.put(self.memory,g.OWNER+0x40+4*i,value)
  if c.mutation&1:g.put(self.memory,g.OWNER+0xb0,0x40800000);g.put(self.memory,g.OWNER+0xbc,0x42a00000)
  if c.mutation&2:g.put(self.memory,g.OWNER+0xb8,0x3f000000);g.put(self.memory,g.OWNER+0xc0,0x3f800000)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)]

def run(state):
    bodies=[g.words(state[x])for x in ('after','retail','generated')];count=0
    for delta,word,match,elapsed,mutation in itertools.product((0,-0x14,0x2c,0xa0),(0,1),(0,1),(0,0x3f800000,0x40800000),(0,1,2,3)):
     target=g.OWNER+delta;c=g.Case(0,word,match,elapsed,0x42c80000,0x3f800000,mutation,0);mem={g.STACK+i:(i*17+0xa5)&255 for i in range(-512,512)};mem.update({g.OWNER+i:(i*29+0x59)&255 for i in range(-256,1024)});g.put(mem,target,word)
     for o,v in ((0x14,0x3f800000),(0x18,0x40000000),(0x1c,0x40400000)):g.put(mem,target+o,v)
     g.put(mem,g.OWNER+0xa8,target);mem[g.OWNER+0xac]=0x41
     for o,v in ((0xb0,elapsed),(0xb4,0x40800000),(0xb8,0x40000000),(0xbc,0x42c80000),(0xc0,0x3f800000)):g.put(mem,g.OWNER+o,v)
     mem[target+0x3b]=0x41 if match else 0x42;g.put(mem,g.DELTA,0x3e800000)
     machines=[Alias(ws,c,mem.copy(),target).run()for ws in bodies];states=[(g.public(m.memory),m.calls,m.r[2],m.fcsr)for m in machines];assert states[0]==states[1]==states[2],(delta,c);count+=1
    return {'cases':count,'overlap_offsets':[0,-0x14,0x2c,0xa0]}
