"""Private bounded guest screen for the ten-entry table initializer."""
import itertools,json,struct
from dataclasses import dataclass
from tools.experiments import game_table_initializer_1500fe30_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
GLOBAL=0x800be4e0;A=0x50000;B=0x51000;ALLOC=0x10003c40;ZERO=0x100226f0;RAND=0x150ada20;FINISH=0x150c851c
@dataclass(frozen=True)
class Case:
 mutation:int;seed:int;phase:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 for base in (A,B):m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(128)})
 put(m,GLOBAL,0x12345678);return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+1024}
def rand(c,ordinal):return (0xffffffff-7*ordinal-c.seed*29)&0xffffffff
def effects(m,c,t,ordinal):
 if t==RAND and c.mutation:
  if ordinal==2:put(m,GLOBAL,B)
  if ordinal==6:put(m,GLOBAL,A)
 if t==FINISH:
  if c.mutation:put(m,GLOBAL,B)
  base=read(m,GLOBAL)
  for i in range(10):put(m,base+10*i+8,(i*101+c.seed*13-200)&0xffff,2)
def reference(c,initial):
 m=dict(initial);calls=[(ALLOC,(100,1,0,0)),(ZERO,(A,100))];put(m,GLOBAL,A)
 for i in range(100):m[A+i]=0
 for i in range(10):
  m[read(m,GLOBAL)+10*i]=i//5;m[read(m,GLOBAL)+10*i+2]=255;calls.append((RAND,()))
  effects(m,c,RAND,i);put(m,read(m,GLOBAL)+10*i+4,rand(c,i)%5,2)
 calls.append((FINISH,(100,)));effects(m,c,FINISH,0)
 for i in range(10):
  base=read(m,GLOBAL)+10*i;put(m,base+6,read(m,base+8,2),2)
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,c,connected=None,memory=None):
  self.c=c;self.ordinal=0;super().__init__(words,fixture(c) if memory is None else memory,c,entry=p.ENTRY,arguments=(),connected=connected)
  self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  counts={ALLOC:4,ZERO:2,RAND:0,FINISH:1};assert t in counts,hex(t);self.calls.append((t,tuple(self.arguments(counts[t]))))
 def hook(self,t):
  a=self.calls[-1][1];c=self.c
  if t==ZERO:
   assert a==(A,100)
   for i in range(100):self.memory[A+i]=0
  effects(self.memory,c,t,self.ordinal)
  value=A if t==ALLOC else rand(c,self.ordinal) if t==RAND else 0
  if t==RAND:self.ordinal+=1
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');elf=p.out/'frozen/conker/build/conker.us.elf';lookup={v[1]:v[2][1] for v in p.symbol_rows(elf.read_bytes())}
 words=p.bound_blob(raw,refs,{n:lookup[n] for es in refs.values() for _,n in es});truth=struct.unpack_from('>91I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM);assert tuple(words)==truth
 cases=[Case(m,seed,phase) for m,seed,phase in itertools.product((0,1),range(4),(0,8))];visits=set()
 for c in cases:
  m=Oracle(words,c);m.run();want,calls=reference(c,m.initial)
  assert public(m.memory)==public(want),(c,'memory');assert m.calls==calls,(c,m.calls,calls)
  assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];visits.update(m.visits)
 result=dict(cases=len(cases),retail_words_visited=sum(p.ENTRY+4*i in visits for i in range(91)),unvisited=[hex(p.ENTRY+4*i) for i in range(91) if p.ENTRY+4*i not in visits],retail_equals_compiled=True,global_pointer_mutations=True,helpers_modeled=True,null_allocation_not_qualified=True,source_installed=False)
 (p.out/'guest-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
