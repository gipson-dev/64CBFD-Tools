"""Original sound wrapper and memcpy with nested and other helpers modeled."""
import itertools,json,struct
from tools.experiments import game_init_callback_1500ffcc_match as p
from tools.experiments import game_init_callback_1500ffcc_match as n
from tools.tests import game_init_callback_1500ffcc_oracle as g
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes()
 helpers=((g.SOUND,0x3d44c,12),(g.COPY,0x22ec0,11));code={}
 for addr,off,size in helpers:code.update(zip(range(addr,addr+size*4,4),struct.unpack_from('>'+str(size)+'I',rom,off)))
 NESTED=0x1510c4ac;SOUND_CONTEXT=0x800917b8
 class Connected(g.Oracle):
  def record_call(self,t):
   if t==NESTED:self.calls.append((t,tuple(self.arguments(4))))
   else:super().record_call(t)
  def hook(self,t):
   if t!=NESTED:return super().hook(t)
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=0
 raw,refs=p.payload(p.out/'independent-selected.o');normal,nrefs=n.normalize(raw,refs)
 elf=p.out/'frozen/conker/build/conker.us.elf';lookup={v[1]:v[2][1] for v in p.symbol_rows(elf.read_bytes())};syms={name:lookup[name] for es in refs.values() for _,name in es}
 programs=(struct.unpack_from('>79I',rom,p.ROM),p.bound_blob(raw,refs,syms),p.bound_blob(normal,nrefs,syms));visits=set();cases=0
 for first,second,mutation,phase in itertools.product((0,1),(0,1),(0,1),(0,8)):
  c=g.Case(first,second,mutation,phase,cases%3);memory=g.fixture(c);g.put(memory,SOUND_CONTEXT,0x01234567)
  want,outer=g.reference(c,memory);calls=[]
  for call in outer:
   calls.append(call)
   if call[0]==g.SOUND:calls.append((NESTED,(0x01234567,0,0xad,0x75)))
  for words in programs:
   m=Connected(words,c,connected=code,memory=memory);m.run()
   assert g.public(m.memory)==g.public(want),(c,'memory');assert m.calls==calls,(c,m.calls,calls);visits.update(m.visits)
  cases+=1
 result=dict(cases=cases,executions=3*cases,original_helpers={hex(addr):sum(addr+4*i in visits for i in range(size)) for addr,off,size in helpers},nested_and_other_helpers_modeled=True,source_installed=False)
 (p.out/'connected-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
