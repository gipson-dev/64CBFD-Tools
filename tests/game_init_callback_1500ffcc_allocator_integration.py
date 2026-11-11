"""Connect both original allocation wrappers; model their allocator and zeroer."""
import itertools,json,struct
from tools.experiments import game_init_callback_1500ffcc_match as p
from tools.experiments import game_init_callback_1500ffcc_match as n
from tools.tests import game_init_callback_1500ffcc_oracle as g
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes()
 helpers=((g.FIRST,0x1766a4,28),(g.SECOND,0x1765e0,49))
 code={}
 for addr,off,size in helpers:code.update(zip(range(addr,addr+size*4,4),struct.unpack_from('>'+str(size)+'I',rom,off)))
 ALLOC=0x15167a68;ZERO=0x100226f0
 class Connected(g.Oracle):
  def __init__(self,*args,**kwargs):self.alloc_index=0;super().__init__(*args,**kwargs)
  def record_call(self,t):
   if t in (ALLOC,ZERO):self.calls.append((t,tuple(self.arguments(6 if t==ALLOC else 2))))
   else:super().record_call(t)
  def hook(self,t):
   if t not in (ALLOC,ZERO):return super().hook(t)
   a=self.calls[-1][1]
   if t==ALLOC:
    value=(g.RECORD1 if self.c.alloc1 else 0) if self.alloc_index==0 else (g.RECORD2 if self.c.alloc2 else 0)
    self.alloc_index+=1
   else:
    assert a[1]==16
    for i in range(a[1]):self.memory[a[0]+i]=0
    value=0
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
 def header(memory,record,kind,mode):
  memory[record+0xd]=0;g.put(memory,record+0xe,300,2)
  memory[record+0x10]=255;memory[record+0x11]=kind;memory[record+0x12]=255;memory[record+0x13]=mode
  for i in range(16):memory[record+0x14+i]=0
 def reference(c,initial):
  memory,outer=g.reference(c,initial);calls=[]
  for target,args in outer:
   calls.append((target,args))
   if target==g.FIRST:
    calls.append((g.SECOND,(300,0xffffffff,18,0xffffffff,0,14,4,255,0)))
    calls.append((ALLOC,(35,0,44,1,255,1)))
    if c.alloc1:calls.append((ZERO,(g.RECORD1+0x14,16)));header(memory,g.RECORD1,18,14)
   elif target==g.SECOND:
    calls.append((ALLOC,(35,1,48,1,255,1)))
    if c.alloc2:calls.append((ZERO,(g.RECORD2+0x14,16)));header(memory,g.RECORD2,23,20)
  return memory,calls
 raw,refs=p.payload(p.out/'independent-selected.o');normal,nrefs=n.normalize(raw,refs)
 elf=p.out/'frozen/conker/build/conker.us.elf';lookup={v[1]:v[2][1] for v in p.symbol_rows(elf.read_bytes())};syms={name:lookup[name] for entries in refs.values() for _,name in entries}
 programs=(struct.unpack_from('>79I',rom,p.ROM),p.bound_blob(raw,refs,syms),p.bound_blob(normal,nrefs,syms));visits=set();cases=0
 for first,second,mutation,phase in itertools.product((0,1),(0,1),(0,1),(0,8)):
  c=g.Case(first,second,mutation,phase,cases%3);memory=g.fixture(c);want,calls=reference(c,memory)
  for words in programs:
   m=Connected(words,c,connected=code,memory=memory);m.run()
   assert g.public(m.memory)==g.public(want),(c,'memory');assert m.calls==calls,(c,m.calls,calls);visits.update(m.visits)
  cases+=1
 result=dict(cases=cases,executions=3*cases,original_helpers={hex(addr):sum(addr+4*i in visits for i in range(size)) for addr,off,size in helpers},inner_allocator_zeroer_and_other_helpers_modeled=True,source_installed=False)
 (p.out/'connected-alloc-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result

if __name__=="__main__":main()
