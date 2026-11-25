"""Bounded all-bit FP operation-order and public/private/provider-state proof.

FP operators and FCSR transitions are uninterpreted ordered operations, not
an IEEE emulator or SMT solver. No commutative floating rewrite is permitted.
"""
from pathlib import Path
from collections import Counter
from unittest.mock import patch
import hashlib,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests import game_radial_angle_150c16c0_symbolic as core
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_local_vector_transform_15117da4_match as p
o=p.OUT;ENTRY=0x15117da4;POINT=0x30000;ALT=0x32000;OUTPUT=0x50000;CATEGORY=0x800be9f0
SYMBOLS=dict(D_800BE9F0=CATEGORY,D_800A2FF4=0x800a2ff4,D_800A2FF8=0x800a2ff8,D_800A2FFC=0x800a2ffc,func_151149AC=0x151149ac,func_1511F31C=0x1511f31c,sinf=0x15047d60,cosf=0x15047c00)
class Machine(core.Machine):
 def __init__(self,words,kind,category,output):
  super().__init__(words);self.fcsr=('initial-FCSR',);self.fp=[];self.public_writes=[];self.reads=[];self.write_epoch=0;self.output=output;self.r[4]=POINT;self.before=self.r[:]
  self.public_addresses=set(range(POINT-16,POINT+128))|set(range(ALT-16,ALT+128))|set(range(OUTPUT-16,OUTPUT+32))|set(range(CATEGORY,CATEGORY+4))|set(range(0x800a2ff4,0x800a3000))
  for p in(POINT,ALT):
   for at,n,name in[(0,4,'angleX'),(4,4,'angleY'),(16,2,'x'),(18,2,'y'),(20,2,'z')]:self.store(p+at,n,('initial',p,name),False)
  self.store(POINT+0x54,2,kind,False);self.store(CATEGORY,4,category,False);self.store(core.STACK+16,4,output,False)
 def load(self,a,n):
  assert isinstance(a,int);v=core.join([self.mem.get(a+i,('memory',self.epoch,a+i))for i in range(n)]);self.reads.append((self.epoch,self.write_epoch,a,n,v));return v
 def store(self,a,n,v,record=True):
  assert isinstance(a,int)
  if record:
   self.write_epoch+=1
   if not core.STACK-256<=a<core.STACK+256:self.public_writes.append((self.epoch,a,n,core.mask(v,(1<<(8*n))-1)))
  for i in range(n):self.mem[a+i]=core.byte(v,n-1-i)
 def frame(self):return tuple(self.mem.get(core.STACK-48+i,('entry-private',i))for i in range(68)),tuple(sorted(self.pairs.items()))
 def public(self):return tuple((a,self.mem.get(a,('memory',self.epoch,a)))for a in sorted(self.public_addresses))
 def execute(self,pc):
  w=self.code[pc];op,rs,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op in(33,37):
   self.visits.append(pc);a=core.add(self.r[rs],core.u(((w&65535)^32768)-32768));v=self.load(a,2);self.r[rt]=core.u((v^32768)-32768)if op==33 and isinstance(v,int)else('sx16',v)if op==33 else v;self.r[0]=0
  elif op==17 and(rs==20 and fn==32 or rs==16 and fn in(0,1,2,7)):
   self.visits.append(pc);name='cvt.s.w'if rs==20 else{0:'add.s',1:'sub.s',2:'mul.s',7:'neg.s'}[fn];operands=(self.f[fs],)if rs==20 or fn==7 else(self.f[fs],self.f[rt]);value=(name,*operands,self.fcsr);self.fp.append(value);self.f[fd]=value;self.fcsr=('after-FP',len(self.fp),self.fcsr,name,operands)
  else:super().execute(pc)
 def call(self,target):
  assert target in(SYMBOLS['func_151149AC'],SYMBOLS['func_1511F31C'],SYMBOLS['sinf'],SYMBOLS['cosf'])
  args=(self.f[12],)if target in(SYMBOLS['sinf'],SYMBOLS['cosf'])else(self.r[4],);self.calls.append((target,args,self.public(),self.frame(),self.r[:],self.f[:],self.fcsr));self.epoch+=1
  for a in self.public_addresses:self.mem[a]=('provider-public-byte',self.epoch,a)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=('provider-GPR',self.epoch,reg)
  for reg in range(20):self.f[reg]=('provider-FPR',self.epoch,reg)
  self.r[2]=ALT if target==SYMBOLS['func_151149AC']else('provider-result',self.epoch);self.f[0]=('provider-float',self.epoch);self.lo=self.hi=('provider-HILO',self.epoch);self.fcsr=('provider-FCSR',self.epoch)
  for i in range(4):self.store(self.r[29]+4*i,4,('provider-home',self.epoch,i),False)
 def run(self):
  pc=ENTRY
  for _ in range(200):
   if pc==core.RETURN:break
   w=self.code[pc];op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
   if op==3:self.visits.append(pc);self.r[31]=pc+8;self.execute(pc+4);self.call(((pc+4)&0xf0000000)|((w&0x3ffffff)<<2));pc+=8
   elif op in(4,5):
    a,b=self.r[rs],self.r[rt];assert isinstance(a,int)and isinstance(b,int),(pc,a,b);taken=(a==b)if op==4 else(a!=b);self.branches.append((op,taken));self.visits.append(pc);self.execute(pc+4);pc=pc+4+(((w&65535)^32768)-32768)*4 if taken else pc+8
   elif op==0 and fn==8:target=self.r[rs];self.visits.append(pc);self.execute(pc+4);pc=target
   else:self.execute(pc);pc+=4
  else:raise AssertionError('Unbounded')
  assert self.r[29]==core.STACK and all(self.r[i]==self.before[i]for i in(*range(16,24),28,30,31))and self.f[20:]==self.before_f[20:];return self
def observe(m):return m.public(),m.public_writes,m.calls,m.frame(),m.r,m.f[20:],m.f[0],m.fcsr,m.lo,m.hi,m.branches,m.fp

def main():
 raw,refs=payload(o/'selected-final/owner-candidate.o','func_15117DA4');truth,tr=payload(o/'original-target.o','func_15117DA4');ws=bound_blob(raw,refs,SYMBOLS);retail=bound_blob(truth,tr,SYMBOLS);cases=0;seen=set();outputs=[OUTPUT,*[POINT+i for i in range(-8,88,4)],*[ALT+i for i in range(-8,88,4)]];controls=[]
 with patch.object(core,'ENTRY',ENTRY):
  for kind,category in[(0x8006,53),(0x8006,0),(0x8005,53)]:
   for output in outputs:
    a,b=Machine(ws,kind,category,output).run(),Machine(retail,kind,category,output).run();assert observe(a)==observe(b),(kind,category,hex(output));cases+=1;seen.update(a.visits)
  reference=Machine(retail,0x8006,53,OUTPUT).run()
  for name,find,change in [('ordered-add-operands',lambda i,w:i>74 and w>>26==17 and w>>21&31==16 and w&63==0,lambda w:(w&~((31<<16)|(31<<11)))|((w>>11&31)<<16)|((w>>16&31)<<11)),('translation-offset',lambda i,w:w==0x86180010,lambda w:w+2),('captured-Z-load',lambda i,w:i>74 and w>>26==49 and w&65535==8,lambda w:w-4),('rotation-sign',lambda i,w:w>>26==17 and w>>21&31==16 and w&63==1,lambda w:w-1)]:
   bad=ws[:];i=next(i for i,w in enumerate(bad)if find(i,w));bad[i]=change(bad[i]);m=Machine(bad,0x8006,53,OUTPUT).run();assert observe(m)!=observe(reference),name;controls.append(dict(name=name,supported_complete_execution=True,rejected=True))
 assert len(seen)==102
 q=dict(raw_sha256=hashlib.sha256(raw).hexdigest(),words=102,frame=48,structural_cases=cases,alias_locations=len(outputs),all102_words_visited=True,arbitrary_initial_record_bits_and_provider_public_byte_epochs=True,ordered_FP_operators_operands_and_FCSR_transitions_equal=True,full_provider_physical_GPR_FPR_state_and_complete_frame_equal=True,all_physical_GPRs_saved_FPRs_and_machine_F0_equal_at_return=True,ordered_public_writes_full_public_memory_and_private_frame_equal=True,no_commutative_FP_rewrite_or_private_frame_map=True,raw_scratch_FPR_and_fault_prefix_equality_not_claimed=True,not_an_IEEE_emulator_or_SMT_solver=True,effective_controls=controls,source_installed=p.installed(),matching_credit=0);(o/'symbolic.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
