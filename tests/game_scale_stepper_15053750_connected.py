"""Private original scale-helper screen, with nested helpers modeled."""
import json,struct
from tools.experiments import game_scale_stepper_15053750_match as p
from tools.tests import game_scale_stepper_15053750_oracle as g
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes()
 retail=struct.unpack_from('>81I',rom,p.ROM)
 addr=g.HELPER;off=addr-0x15000000+0x2d4b0;helper=struct.unpack_from('>77I',rom,off)
 code=dict(zip(range(addr,addr+len(helper)*4,4),helper));visits=set();cases=0
 NESTED=(0x15062ac4,0x15062b84);TABLE=0x800d1c90;MODEL=0x38000
 class Connected(g.Oracle):
  def record_call(self,t):
   if t in NESTED:self.calls.append((t,tuple(self.arguments(1))))
   else:super().record_call(t)
  def hook(self,t):
   if t not in NESTED:return super().hook(t)
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
 samples=[(0,0,0,0,1),(0,0,.5,.5,1),(0,0,2,-2,1),(1,1,-2,2,.5),(0,0,1,-1,1),(2,-1,2,1,.5),(1,1,-1,1,2),(0,1,0,-1,0),(0,0,2,-2,-1)]
 for actor_id in (255,3):
  for vals in samples:
   c=g.Case(*(g.b(v) for v in vals),0,0,cases%3);memory=g.fixture(c);memory[g.ACTOR+4]=actor_id
   if actor_id!=255:
    g.put(memory,TABLE+4*actor_id,MODEL)
    for i,n in enumerate((-20,15,30,50,-8,4)):g.put(memory,MODEL+0x1a+2*i,n&0xffff,2)
   m=Connected(retail,c,connected=code,memory=memory);m.run();want,outer=g.reference(c,m.initial);calls=[]
   for call in outer:
    calls.append(call)
    if actor_id!=255:calls.extend((n,(g.ACTOR,)) for n in NESTED)
   if actor_id!=255 and outer:
    x=g.read(want,g.ACTOR+0x14c);y=g.read(want,g.ACTOR+0x150)
    for dst,src,scale in ((0xd2,0x20,x),(0xd4,0x22,y),(0xd6,0x24,y),(0xe4,0x1a,x),(0xe6,0x1c,y),(0xe8,0x1e,y)):
     value=(g.read(want,MODEL+src,2)^0x8000)-0x8000
     g.put(want,g.ACTOR+dst,int(g.f(g.mul(g.b(value),scale)))&0xffff,2)
   assert g.public(m.memory)==g.public(want),(c,actor_id,'memory');assert m.calls==calls,(c,m.calls,calls)
   visits.update(m.visits);cases+=1
 result=dict(cases=cases,original_helper_words_visited=sum(addr+4*i in visits for i in range(77)),original_helper_words=77,actor_ids=[255,3],nested_helpers_modeled=True,source_installed=False)
 (p.out/'connected-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
