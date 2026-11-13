from tools.tests import game_trajectory_actor_150e1570_oracle as o
from itertools import product

def run():
 rom=(o.root/'conker/conker.us.bin').read_bytes();retail=o.struct.unpack_from('>161I',rom,0x10ea20);programs=[retail,o.program(o.out/'after.o'),o.program(o.out/'generated.o'),o.program(o.out/'generic.o')];SOURCE2=0x44000
 class Mutation(o.Machine):
  def __init__(self,w,c,mode):
   super().__init__(w,c);self.mode=mode;self.memory.update({SOURCE2+i:0 for i in range(0x32c)});self.memory[SOURCE2+0x124]=4;o.put(self.memory,SOURCE2+0x76,0xcafe,2)
  def hook(self,t):
   if t==o.LOOK and self.mode&1:
    o.put(self.memory,self.r[29]+0xe0,SOURCE2);o.put(self.memory,self.r[29]+0xe8,o.bits(-10.0));o.put(self.memory,self.r[29]+0xf4,o.bits(7.0))
   if t==o.EMIT and self.mode&2:
    o.put(self.memory,self.r[29]+0xe0,SOURCE2)
   return super().hook(t)
 count=0
 for phase,flags,pattern,mode in product((0,8),(0,7),range(5),range(4)):
  c=o.Case(phase,1,-1,flags,pattern);ms=[Mutation(w,c,mode).run() for w in programs];a=ms[0]
  assert all((o.external(m.memory),m.calls,m.r[2])==(o.external(a.memory),a.calls,a.r[2]) for m in ms[1:]),(c,mode)
  count+=1
 print('incoming-home and argument mutation cases',count,'agree through four streams')
