from pathlib import Path
import itertools,struct,sys
from tools.experiments.game_point_descriptor_151382e0_match import ROOT as root, OUT as out
from tools.tests.game_actor_point_effects_oracle import Case,fixture,reference,public,EffectsOracle,FIRST,STACK,put
from tools.experiments.game_actor_point_effects_match import ENTRY
SUBMIT=0x15153F18;rom=(root/'conker/conker.us.bin').read_bytes();target=list(struct.unpack_from('>81I',rom,0x165790))
# The exact original caller begins at 0x15138BC0, translated by the Game ROM base.
assert ENTRY==0x15138BC0
caller=list(struct.unpack_from('>48I',rom,ENTRY-0x15000000+0x2d4b0))
connected={FIRST+4*i:w for i,w in enumerate(target)}
class Connected(EffectsOracle):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.packets=[]
 def record_call(self,t):
  if t!=SUBMIT:return super().record_call(t)
  a=self.arguments(5);self.calls.append((t,a));self.packets.append((a,bytes(self.get(a[0]+i,1) for i in range(76))))
 def hook(self,t):
  if t!=SUBMIT:return super().hook(t)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xA5000010

count=0
for kind,query,mode,phase,category in itertools.product((0,1,19,99),(0,1,256,257),(0,1,2,3),(0,8),(0,1,2,255)):
 c=Case(kind=kind,query=query,mode=mode,phase=phase);mem=fixture(c)
 if kind!=99:mem[0x800A3FE6+kind*16]=category
 for i,v in enumerate((0x3F800000,0x40000000,0x40400000,0x40800000,0x40a00000)):put(mem,0x800A4830+i*4,v)
 wanted,calls,observations=reference(mem,c);m=Connected(caller,mem,c,connected=connected).run()
 assert public(m.memory)==public(wanted)
 assert [x for x in m.calls if x[0]!=SUBMIT]==calls,(c,m.calls,calls)
 assert m.observations==observations
 active=kind!=99 and bool(query&255);assert len(m.packets)==int(active and category!=2)
 if m.packets:
  args,packet=m.packets[0];first=next(a for t,a in calls if t==FIRST);obs=next(o for t,o in observations if t==FIRST)
  assert args[1]==args[0]+8 and args[2:]==(first[2],first[3],first[4]);assert packet[8:20]==obs[0] and packet[60]==int(category==1)
 count+=1
print('connected original caller and retail point target:',count,'cases; disabled gate, stack inputs, forwarded surface/group/context verified')
