"""Private integration through original bzero and target-randomization helper."""
import itertools,json,struct
from tools.experiments import game_table_initializer_1500fe30_match as p
from tools.tests import game_table_initializer_1500fe30_oracle as g
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();target=struct.unpack_from('>91I',rom,p.ROM)
 helpers=((g.ZERO,0x226f0,39),(g.FINISH,0xf59cc,57));code={}
 for addr,off,size in helpers:code.update(zip(range(addr,addr+4*size,4),struct.unpack_from('>'+str(size)+'I',rom,off)))
 NESTED=0x150cdb6c
 class Connected(g.Oracle):
  def record_call(self,t):
   if t==NESTED:self.calls.append((t,tuple(self.arguments(1))))
   else:super().record_call(t)
  def hook(self,t):
   if t!=NESTED:return super().hook(t)
   if self.c.mutation:g.put(self.memory,g.GLOBAL,g.B)
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=0
 visits=set();count=0
 for mutation,seed,phase in itertools.product((0,1),range(4),(0,8)):
  c=g.Case(mutation,seed,phase);m=Connected(target,c,connected=code);m.run();want,outer=g.reference(c,m.initial)
  calls=[]
  for call in outer:
   calls.append(call)
   if call[0]==g.FINISH:calls.extend([(NESTED,(100,))]+[(g.RAND,())]*10)
  base=g.read(want,g.GLOBAL)
  for i in range(10):
   value=117+g.rand(c,10+i)%69;g.put(want,base+10*i+8,value,2);g.put(want,base+10*i+6,value,2)
  assert g.public(m.memory)==g.public(want),(c,'memory');assert m.calls==calls,(c,m.calls,calls)
  visits.update(m.visits);count+=1
 result=dict(cases=count,original_helpers={hex(addr):sum(addr+4*i in visits for i in range(size)) for addr,off,size in helpers},allocation_random_and_nested_effect_modeled=True,source_installed=False)
 (p.out/'deeper-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
