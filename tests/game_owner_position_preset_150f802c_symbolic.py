"""Bounded proof of both result paths, complete frame, descriptor and tail."""
from pathlib import Path
from collections import Counter
from unittest.mock import patch
import json,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests import game_radial_angle_150c16c0_symbolic as core
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_owner_position_preset_150f802c_match as p
r,o=p.ROOT,p.OUT;ENTRY=0x150f802c;POINT=0x30000;OUTPUT=0x60000;FACTORY=0x1513264c;COPY=0x10022ec0;COEFF=0x800a1bdc;CONSTANT=0x800a5480
class Machine(core.Machine):
 def __init__(self,words,outcome):
  self.initializing=True;self.outcome=outcome;self.public_writes=[];self.fcsr=('entry-FCSR',);super().__init__(words);self.initializing=False;self.r[4]=POINT;self.mem={a:v for a,v in self.mem.items()if a<core.STACK+16}
 def store(self,a,n,v,record=True):
  assert isinstance(a,int)
  private=core.STACK-200<=a and a+n<=core.STACK+16
  assert private or self.initializing and not record and core.STACK+16<=a and a+n<=core.STACK+60 or OUTPUT<=a and a+n<=OUTPUT+0x200,(a,n)
  if record and not core.STACK-200<=a<core.STACK:self.public_writes.append((self.epoch,a,n,core.mask(v,(1<<(8*n))-1)))
  for i in range(n):self.mem[a+i]=core.byte(v,n-1-i)
 def load(self,a,n):
  assert isinstance(a,int)
  private=core.STACK-200<=a and a+n<=core.STACK+16
  assert private or POINT<=a and a+n<=POINT+68 or COEFF<=a and a+n<=COEFF+4 or CONSTANT<=a and a+n<=CONSTANT+12,(a,n)
  return core.join([self.mem.get(a+i,('entry-private-byte',a+i)if core.STACK-200<=a<core.STACK else('public-byte',self.epoch,a+i))for i in range(n)])
 def frame(self):return tuple(self.mem.get(core.STACK-200+i,('entry-private-byte',core.STACK-200+i))for i in range(200))
 def execute(self,pc):
  w=self.code[pc]
  if w>>26==33:
   self.visits.append(pc);rs,rt=w>>21&31,w>>16&31;a=core.add(self.r[rs],core.u(((w&65535)^32768)-32768));v=self.load(a,2);self.r[rt]=core.u((v^32768)-32768)if isinstance(v,int)else('sx16',v);self.r[0]=0
  else:super().execute(pc)
 def call(self,target):
  assert target in(FACTORY,COPY);n=7 if target==FACTORY else 3;args=tuple(self.r[4+i]if i<4 else self.load(self.r[29]+4*i,4)for i in range(n))
  source=args[0]if target==FACTORY else args[1];extent=124 if target==FACTORY else 20;passed=tuple(self.load(source+i,1)for i in range(extent));self.calls.append((target,args,passed,self.frame(),self.fcsr));self.epoch+=1
  if target==FACTORY:
   assert source==core.STACK-144
   for i in range(124):self.mem[source+i]=('provider-descriptor-write',self.epoch,i)
  else:
   assert args[0]==OUTPUT+0x170 and source==core.STACK-20 and args[2]==20
   for i,v in enumerate(passed):self.store(args[0]+i,1,v)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=('provider-GPR',self.epoch,reg)
  for reg in range(20):self.f[reg]=('provider-FPR',self.epoch,reg)
  self.r[2]=(OUTPUT if self.outcome else 0)if target==FACTORY else args[0];self.hi=self.lo=('provider-hi-lo',self.epoch);self.fcsr=('provider-FCSR',self.epoch)
  for i in range(4):self.store(self.r[29]+4*i,4,('provider-outgoing-home',self.epoch,i),False)
 def run(self):
  pc=ENTRY
  for _ in range(160):
   if pc==core.RETURN:break
   w=self.code[pc];op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
   if op==3:self.visits.append(pc);self.r[31]=pc+8;self.execute(pc+4);self.call(((pc+4)&0xf0000000)|((w&0x3ffffff)<<2));pc+=8
   elif op==4:
    a,b=self.r[rs],self.r[rt];assert isinstance(a,int)and isinstance(b,int);taken=a==b;self.visits.append(pc);self.branches.append(taken);self.execute(pc+4);pc=pc+4+(((w&65535)^32768)-32768)*4 if taken else pc+8
   elif op==0 and fn==8:target=self.r[rs];assert isinstance(target,int);self.visits.append(pc);self.execute(pc+4);pc=target
   else:self.execute(pc);pc+=4
  else:raise AssertionError('Unbounded execution')
  assert self.r[29]==core.STACK and all(self.r[i]==self.before[i]for i in(*range(16,24),28,30,31))and self.f[20:]==self.before_f[20:]
  return self
def observe(m):return m.calls,m.public_writes,m.frame(),m.r,m.f,m.hi,m.lo,m.fcsr,m.branches
def main():
 best=dict(differences=p.MANIFEST['guard_count']);raw,refs=payload(o/'selected-final/owner-candidate.o','func_150F802C');truth,tr=payload(o/'original-target.o','func_150F802C');assert len(raw)==len(truth)==400
 base=dict(func_1513264C=FACTORY,memcpy=COPY,D_800A1BDC=COEFF,D_800A5480=CONSTANT);seen=set();rebases=0;cases=0
 for entry,low in [(ENTRY,0),(0x250f802c,0x7ff8),(0x350f802c,0x8000),(0x450f802c,0xfff8)]:
  symbols=base if entry==ENTRY else dict(func_1513264C=(entry&0xf0000000)+0x213264c,memcpy=(entry&0xf0000000)+0x22ec0,D_800A1BDC=0x80100000+low,D_800A5480=0x80120000+low)
  a,b=bound_blob(raw,refs,symbols),bound_blob(truth,tr,symbols);assert Counter(a)==Counter(b),'Only independent scheduling is selected'
  with patch.multiple(sys.modules[__name__],ENTRY=entry,FACTORY=symbols['func_1513264C'],COPY=symbols['memcpy'],COEFF=symbols['D_800A1BDC'],CONSTANT=symbols['D_800A5480']),patch.object(core,'ENTRY',entry):
   for outcome in(0,1):
    x,y=Machine(a,outcome).run(),Machine(b,outcome).run();assert observe(x)==observe(y),(hex(entry),outcome);assert len(x.calls)==len(y.calls)==1+outcome;seen|={pc-entry for pc in x.visits};cases+=1
  rebases+=1
 assert seen==set(range(0,400,4))
 with patch.object(core,'ENTRY',ENTRY):
  controls=[];reference=Machine(bound_blob(truth,tr,base),1).run();words=bound_blob(raw,refs,base)
  for name,find,change in [('resource-id',lambda w:w>>26==9 and w&65535==47,lambda w:w-1),('payload-size',lambda w:w>>26==9 and w&65535==180,lambda w:w-4),('lifetime-byte',lambda w:w>>26==9 and w&65535==20 and w>>16&31!=6,lambda w:w+1),('parameter-half',lambda w:w>>26==33 and w&65535==0xce,lambda w:w-2),('first-position',lambda w:w>>26==49 and w>>21&31==16 and w&65535==0,lambda w:w+4)]:
   changed=list(words);at=next(i for i,w in enumerate(changed)if find(w));changed[at]=change(changed[at]);m=Machine(changed,1).run();assert len(m.calls)==2 and observe(m)!=observe(reference);controls.append(dict(name=name,supported_complete_execution=True,rejected=True))

 q=dict(words=100,frame=200,raw_word_differences=best['differences'],same_instruction_word_multiset=True,normalization_scope='independent instruction scheduling only; relocation positions move with instructions',full_private_frame_at_each_provider_and_return=True,main_descriptor_bytes=124,main_initialized_bytes=116,main_holes=8,trailing_record_bytes=20,all_return_registers_and_FCSR_equal=True,both_factory_null_and_success_paths=True,all100_words_visited=True,rebased_proofs=rebases,path_proofs=cases,effective_controls=controls,raw_private_store_and_fault_order_not_claimed=True,typed_void_ABI_supported_by_native_and_bounded_caller=True,source_installed=p.installed(),matching_credit=0)
 (o/'symbolic-controls.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
