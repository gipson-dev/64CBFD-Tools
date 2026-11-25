"""Scoped structural boundary proof; private spills/order are not architectural outputs."""
from pathlib import Path
import json,struct,sys
from unittest.mock import patch
sys.path.insert(0,str(Path.cwd()))
from tools.tests import game_radial_angle_150c16c0_symbolic as core
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_dual_actor_emitter_150b37c8_match as p
o=p.OUT;ENTRY=0x150b37c8;FRNG=0x150ada68;RNG=0x150ada20;SUBMIT=0x1513c73c;FACTORY=0x15147da0;TEMPLATE=0x80088700
ACTOR,RECORD,POSITIONS=0x30000,0x32000,0x51000
class Machine(core.Machine):
 def __init__(self,words):
  self.public_writes=[];self.fp_ops=[];self.snapshots=[];self.initializing=True;super().__init__(words);self.initializing=False;self.r[4]=ACTOR
  self.mem={a:v for a,v in self.mem.items()if a<core.STACK+24}
  for at,value in[(ACTOR+0x94,POSITIONS),(ACTOR+0x98,RECORD)]:self.store(at,4,value,False)
  for i in range(6):self.mem[TEMPLATE+i]=('entry-template-byte',i)
 def store(self,a,n,v,record=True):
  assert isinstance(a,int),('Symbolic store not supported',a)
  assert core.STACK-248<=a and a+n<=core.STACK+24 or RECORD<=a and a+n<=RECORD+64 or ACTOR<=a and a+n<=ACTOR+0xa0 or self.initializing and not record and core.STACK+16<=a and a+n<=core.STACK+60,(a,n)
  if record and not core.STACK-248<=a<core.STACK:self.public_writes.append((self.epoch,a,n,core.mask(v,(1<<(n*8))-1)))
  for i in range(n):self.mem[a+i]=core.byte(v,n-1-i)
 def load(self,a,n):
  if isinstance(a,int):
   if core.STACK-248<=a<core.STACK:default=lambda at:('entry-private-byte',at)
   else:
    assert core.STACK<=a and a+n<=core.STACK+24 or ACTOR<=a and a+n<=ACTOR+0xa0 or RECORD<=a and a+n<=RECORD+64 or TEMPLATE<=a and a+n<=TEMPLATE+6 or POSITIONS-128*20<=a and a+n<=POSITIONS+128*20,('Read outside known bounded object',a,n)
    default=lambda at:('public-byte',self.epoch,at)
   return core.join([self.mem.get(a+i,default(a+i))for i in range(n)])
  # Symbolic address trees are retained, not evaluated at one sampled index.
  # Validate their complete bounded index class, then preserve all initial bytes.
  terms=list(a[1:])if isinstance(a,tuple)and a[0]=='add'else[a];const=sum(t for t in terms if isinstance(t,int));expr=[t for t in terms if not isinstance(t,int)];assert len(expr)==1,(a,n)
  x=expr[0]
  if core.STACK-248<=const<core.STACK:
   assert const==core.STACK-60 and n==2 and x[0]=='shl'and x[2]==1 and x[1][0]=='umod'and x[1][2]in(1,2,3),(a,n)
   return('choice16',x[1],tuple(self.load(core.STACK-60+2*i,2)for i in range(3)))
  assert POSITIONS<=const<=POSITIONS+8 and n==4,('Symbolic public base',a,n)
  # Both legal code streams use either ((sx8*4+sx8)*4) or sx8*20.
  if x[0]=='mul32':
   left,right=x[1:];assert right==20 and left[0]=='sx8',(a,n)
  else:
   assert x[0]=='shl'and x[2]==2 and x[1][0]=='add',(a,n);inside=list(x[1][1:]);assert len(inside)==2
   root=next(t for t in inside if t[0]=='sx8');shifted=next(t for t in inside if t[0]=='shl');assert shifted==('shl',root,2),(a,n)
  return('indexed-public-word',self.epoch,a,n)
 def execute(self,pc):
  w=self.code[pc];op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
  if op in(32,33,37):
   self.visits.append(pc);at=core.add(self.r[rs],core.u(((w&65535)^32768)-32768));value=self.load(at,1 if op==32 else 2)
   if op in(32,33):value=core.u((value^(128 if op==32 else 32768))-(128 if op==32 else 32768))if isinstance(value,int)else('sx8'if op==32 else'sx16',value)
   self.r[rt]=value;self.r[0]=0;return
  if op==0 and fn==0x19:
   self.visits.append(pc);a,b=self.r[rs],self.r[rt]
   assert isinstance(b,int)and b==20 and isinstance(a,tuple)and a[0]=='sx8'
   self.lo=('mul32',a,b);self.hi=('mul32-high',a,b);return
  super().execute(pc)
  if w>>26==17 and w>>21&31==16 and fn in(0,1,2):
   # Core stores the exact ordered FP-expression node; preserve rounding epoch.
   self.fp_ops.append((self.epoch,self.f[w>>6&31]))
 def call(self,target):
  n={FRNG:0,RNG:0,SUBMIT:14,FACTORY:15}[target];args=tuple(self.r[4+i]if i<4 else self.load(self.r[29]+4*i,4)for i in range(n))
  snapshots=()
  spans=[]
  if target==SUBMIT:spans=[(args[0],40)];assert args[0]==core.STACK-48
  elif target==FACTORY:
   spans=[(args[0],28),(args[1],32),(args[11],32)];assert [a for a,n in spans]==[core.STACK-88,core.STACK-120,core.STACK-152]
  snapshots=tuple(tuple(self.mem.get(a+i,('entry-private-byte',a+i))for i in range(length))for a,length in spans)
  self.calls.append((target,args,snapshots));self.epoch+=1
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=('call-clobber',self.epoch,'r',reg)
  for reg in range(20):self.f[reg]=('call-clobber',self.epoch,'f',reg)
  self.r[2]=('call-result',self.epoch);self.f[0]=('call-float-result',self.epoch);self.hi=self.lo=('call-hi-lo',self.epoch)
  self.mem={a:v for a,v in self.mem.items()if core.STACK-248<=a<core.STACK}
  for pointer,length in spans:
   assert core.STACK-248<=pointer and pointer+length<=core.STACK
   for i in range(length):self.mem[pointer+i]=('bounded-provider-write',self.epoch,pointer,i)
  for i in range(max(4,n)):self.store(self.r[29]+4*i,4,('outgoing-home',self.epoch,i),False)
 def finish(self):
  self.run();assert self.r[2]==1 and self.r[29]==core.STACK and all(self.r[i]==self.before[i]for i in(*range(16,24),28,30,31))and self.f[20:]==self.before_f[20:];return self

def main():
 raw,refs=payload(o/'selected-final/owner-candidate.o','func_150B37C8');truth,tr=payload(o/'original-target.o','func_150B37C8');assert refs==tr
 names={n for a in refs.values()for _,n in a};base=dict(func_150ADA20=RNG,func_150ADA68=FRNG,func_1513C73C=SUBMIT,func_15147DA0=FACTORY,D_80088700=TEMPLATE)
 with patch.object(core,'ENTRY',ENTRY):
  a=Machine(bound_blob(raw,refs,base)).finish();b=Machine(bound_blob(truth,tr,base)).finish()
  assert a.public_writes==b.public_writes,'Public/ABI writes differ'
  assert a.fp_ops==b.fp_ops,('FP operation order differs',a.fp_ops,b.fp_ops)
  assert a.calls==b.calls,'Provider arguments or complete passed private objects differ'
  assert len(set(a.visits))==len(set(b.visits))==184
 module=sys.modules[__name__];rebases=0
 for group,(entry,low)in enumerate([(0x150b37c8,0),(0x250b37c8,0x7ff8),(0x350b37c8,0x8000),(0x450b37c8,0xfff8)]):
  names=sorted(n for n in base if n.startswith('func_'));symbols={n:(entry&0xf0000000)+0x210000+0x20000*i+low for i,n in enumerate(names)};symbols['D_80088700']=0x80100000+low
  values=dict(ENTRY=entry,FRNG=symbols['func_150ADA68'],RNG=symbols['func_150ADA20'],SUBMIT=symbols['func_1513C73C'],FACTORY=symbols['func_15147DA0'],TEMPLATE=symbols['D_80088700'],ACTOR=0x30000+group*0x20000,RECORD=0x32000+group*0x20000,POSITIONS=0x51000+group*0x20000)
  with patch.multiple(core,ENTRY=entry,STACK=0x42008+group*0x20000),patch.multiple(module,**values):
   left=Machine(bound_blob(raw,refs,symbols)).finish();right=Machine(bound_blob(truth,tr,symbols)).finish()
   assert(left.calls,left.public_writes,left.fp_ops)==(right.calls,right.public_writes,right.fp_ops);rebases+=1
 words=bound_blob(raw,refs,base);controls=[]
 def observation(m):return m.calls,m.public_writes,m.fp_ops
 mutations=[('flags',next(i for i,w in enumerate(words)if w&0xfc00ffff==0x24000011),lambda w:w^1),('duration',next(i for i,w in enumerate(words)if w&0xfc00ffff==0x24000096),lambda w:w+1),('resource',next(i for i,w in enumerate(words)if w&0xfc00ffff==0x34000002),lambda w:w^1),('first-mask',next(i for i,w in enumerate(words)if w&0xfc00ffff==0x300000ff),lambda w:w^0x80),('provider-tag',next(i for i,w in enumerate(words)if w==0x24050001),lambda w:w+1),('FP-multiply-to-add',next(i for i,w in enumerate(words)if w>>26==17 and w>>21&31==16 and w&63==2),lambda w:w&~63),('wrong-public-byte',next(i for i,w in enumerate(words)if w>>26==40 and w>>21&31==16 and w&65535==0x20),lambda w:w+1),('private-spill-alias',next(i for i,w in enumerate(words)if w==0xafa2005c),lambda w:w-4)]
 with patch.object(core,'ENTRY',ENTRY):
  reference=Machine(bound_blob(truth,tr,base)).finish()
  for name,index,mutate in mutations:
   changed=list(words);changed[index]=mutate(changed[index]);model=Machine(changed).finish();assert observation(model)!=observation(reference),name
   controls.append(dict(name=name,word=index,supported_complete_execution=True,rejected_by_observation=True))
  altered=dict(base);altered['D_80088700']=RECORD;model=Machine(bound_blob(raw,refs,altered)).finish();assert observation(model)!=observation(reference)
  controls.append(dict(name='template-binding-to-valid-record',supported_complete_execution=True,rejected_by_observation=True))
 q=dict(body_words=184,frame=248,word_differences=85,all_184_words_executed=True,provider_boundaries=len(a.calls),ordered_FP_ops=len(a.fp_ops),ordered_public_and_ABI_writes=len(a.public_writes),rebased_proofs=rebases,effective_supported_controls=controls,provider_arguments_and_complete_passed_private_bytes_equal=True,all_signed_byte_indices_symbolic=True,all_unsigned_RNG_results_symbolic=True,all_initial_template_bytes_symbolic=True,arbitrary_provider_public_epochs_and_results=True,unpassed_private_spills_and_private_store_order_not_outputs=True,normal_nonvolatile_mapped_single_thread_memory=True,not_general_SMT_or_fault_order_proof=True,source_installed=p.installed(),matching_credit=0)
 (o/'symbolic-controls.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
