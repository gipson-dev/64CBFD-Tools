"""Private bounded initialization callback screen with modeled helpers."""
import itertools,json,struct
from dataclasses import dataclass
from tools.experiments import game_init_callback_1500ffcc_match as p
from tools.experiments import game_init_callback_1500ffcc_match as n
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
G0=0x800b0e00;G1=0x800b0e04;CTX=0x800902dc;OUTPUT=0x80088870
SETUP=0x15195aa8;START=0x1500fe30;SOUND=0x1500ff9c;FIRST=0x151491f4;SECOND=0x15149130;COPY=0x10022ec0
RECORD1=0x50000;RECORD2=0x51000
u32=lambda x:x&0xffffffff
@dataclass(frozen=True)
class Case:
 alloc1:int;alloc2:int;mutation:int;phase:int=0;seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 for base in (RECORD1,RECORD2):m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(128)})
 for a,v in ((G0,0x12345678),(G1,0x87654321),(CTX,0x11223344),(OUTPUT,0x77889900)):put(m,a,v)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+1024}
def effects(m,c,t,ordinal):
 if c.mutation and t==SETUP and ordinal==0:put(m,G1,0x12344321);put(m,CTX,0xfedcba98)
def reference(c,initial):
 m=dict(initial);calls=[];sp=STACK+c.phase-0x48
 calls.append((SETUP,(read(m,G0),read(m,CTX),1,0xffffffff,0,0,0,0xfffffffc)));effects(m,c,SETUP,0)
 calls.append((SETUP,(read(m,G1),read(m,CTX),1,0xffffffff,0,1,0,0xfffffffc)));calls.extend(((START,()),(SOUND,()),(FIRST,(300,0xffffffff,18,0,14,4,255,0))))
 if c.alloc1:
  calls.append((COPY,(RECORD1+0x28,sp+0x44,4)))
  for i in range(4):m[RECORD1+0x28+i]=0
 calls.append((SECOND,(300,0xffffffff,23,0xffffffff,0,20,8,255,1)));put(m,OUTPUT,RECORD2 if c.alloc2 else 0)
 if c.alloc2:
  calls.append((COPY,(RECORD2+0x28,sp+0x38,8)))
  for i in range(8):m[RECORD2+0x28+i]=0
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,c,connected=None,memory=None):
  self.c=c;self.setup_count=0;super().__init__(words,fixture(c) if memory is None else memory,c,entry=p.ENTRY,arguments=(),connected=connected)
  self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  counts={SETUP:8,START:0,SOUND:0,FIRST:8,SECOND:9,COPY:3};assert t in counts,hex(t)
  self.calls.append((t,tuple(self.arguments(counts[t]))))
 def hook(self,t):
  a=self.calls[-1][1];c=self.c
  if t==SETUP:effects(self.memory,c,t,self.setup_count);self.setup_count+=1
  if t==COPY:
   chunk=bytes(self.memory[a[1]+i] for i in range(a[2]))
   for i,v in enumerate(chunk):self.memory[a[0]+i]=v
  value=RECORD1 if t==FIRST and c.alloc1 else RECORD2 if t==SECOND and c.alloc2 else a[0] if t==COPY else 0
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');normal,nrefs=n.normalize(raw,refs)
 elf=p.out/'frozen/conker/build/conker.us.elf';lookup={v[1]:v[2][1] for v in p.symbol_rows(elf.read_bytes())}
 syms={name:lookup[name] for es in refs.values() for _,name in es};candidate=p.bound_blob(raw,refs,syms);fixed=p.bound_blob(normal,nrefs,syms);retail=struct.unpack_from('>79I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM)
 assert tuple(fixed)==retail
 cases=[Case(a,b,m,phase,i%3) for i,(a,b,m,phase) in enumerate(itertools.product((0,1),(0,1),(0,1),(0,8)))]
 visits=[set(),set(),set()]
 for c in cases:
  models=[]
  for idx,ws in enumerate((retail,candidate,fixed)):
   machine=Oracle(ws,c);machine.run();want,calls=reference(c,machine.initial)
   assert public(machine.memory)==public(want),(c,'public');assert machine.calls==calls,(c,machine.calls,calls)
   assert machine.r[16:24]==machine.before[16:24] and machine.r[28:]==machine.before[28:] and machine.f[20:]==machine.before_f[20:]
   visits[idx].update(machine.visits);models.append(machine)
  a,b,d=models;assert (a.memory,a.r,a.f,a.calls,a.trace)==(d.memory,d.r,d.f,d.calls,d.trace),(c,'normalized')
 result=dict(cases=len(cases),executions=3*len(cases),retail_words_visited=sum(p.ENTRY+4*i in visits[0] for i in range(79)),normalized_complete_state=True,helpers_modeled=True,source_installed=False,byte_exact=False)
 (p.out/'guest-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
