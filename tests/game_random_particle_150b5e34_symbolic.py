"""Scoped branch-class proof of public boundaries with a checked private spill map."""
from pathlib import Path
import itertools,json,sys
from unittest.mock import patch
sys.path.insert(0,str(Path.cwd()))
from tools.tests import game_radial_angle_150c16c0_symbolic as core
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_random_particle_150b5e34_match as p
r,o=p.ROOT,p.OUT;ENTRY=0x150b5e34;POINT=0x30000;RNG=0x150ada20;FRNG=0x150ada68;FACTORY=0x15130280
class Machine(core.Machine):
 def __init__(self,words,bits,raw=False):
  self.initializing=True;self.raw=raw;self.bits=bits;self.integer_calls=0;self.public_writes=[];self.fp_ops=[];self.fcsr=('entry-FCSR',)
  super().__init__(words);self.initializing=False;self.r[4]=POINT;self.mem={a:v for a,v in self.mem.items()if a<core.STACK+12}
 def canonical(self,a):
  off=a-(core.STACK-152)
  if self.raw and 0x20<=off<0x28:return a+(4 if off<0x24 else-4)
  return a
 def store(self,a,n,v,record=True):
  assert isinstance(a,int)
  assert core.STACK-152<=a and a+n<=core.STACK+12 or self.initializing and not record and core.STACK+16<=a and a+n<=core.STACK+60,(a,n)
  if record and a>=core.STACK:self.public_writes.append((self.epoch,a,n,core.mask(v,(1<<(8*n))-1)))
  for i in range(n):self.mem[a+i]=core.byte(v,n-1-i)
 def load(self,a,n):
  assert isinstance(a,int)
  assert core.STACK-152<=a and a+n<=core.STACK+12 or POINT<=a and a+n<=POINT+12,(a,n)
  private=core.STACK-152<=a<core.STACK
  return core.join([self.mem.get(a+i,('entry-private-byte',self.canonical(a+i))if private else('public-byte',self.epoch,a+i))for i in range(n)])
 def frame(self):
  # Involution20..23<->24..27 only. Neither range is passed to a provider.
  return tuple(self.load(self.canonical(core.STACK-152+i),1)for i in range(152))
 def execute(self,pc):
  w=self.code[pc];op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
  value=self.r[rs]
  if op==12 and w&65535==1 and isinstance(value,tuple)and value[0]=='RNG-bit-class':
   self.visits.append(pc);self.r[rt]=value[2];self.r[0]=0;return
  super().execute(pc)
  if op==17 and rs==16 and fn in(0,2):
   event=self.f[w>>6&31];self.fp_ops.append((self.epoch,event));self.fcsr=('ordered-FP-state',self.fcsr,event)
 def call(self,target):
  assert target in(RNG,FRNG,FACTORY),hex(target);n=6 if target==FACTORY else 0
  args=tuple(self.r[4+i]if i<4 else self.load(self.r[29]+4*i,4)for i in range(n));packet=()
  if target==FACTORY:
   assert args[0]==core.STACK-112;packet=tuple(self.load(args[0]+i,1)for i in range(112))
  self.calls.append((target,args,packet,self.fcsr,self.frame()));self.epoch+=1
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=('provider-GPR',self.epoch,reg)
  for reg in range(20):self.f[reg]=('provider-FPR',self.epoch,reg)
  self.hi=self.lo=('provider-hi-lo',self.epoch);self.fcsr=('provider-FCSR',self.epoch)
  if target==RNG:
   self.r[2]=('RNG-all32',self.epoch)if self.integer_calls==0 else('RNG-bit-class',self.epoch,self.bits[self.integer_calls-1]);self.integer_calls+=1
  elif target==FRNG:self.f[0]=('float-provider-result',self.epoch)
  else:
   self.r[2]=('allocation-pointer-or-null',self.epoch)
   for i in range(112):self.mem[args[0]+i]=('provider-packet-write',self.epoch,i)
  for i in range(max(4,n)):self.store(self.r[29]+4*i,4,('provider-outgoing-home',self.epoch,i),False)
 def finish(self):
  pc=ENTRY
  for step in range(300):
   if pc==core.RETURN:break
   w=self.code[pc];op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
   if op==3:self.visits.append(pc);self.r[31]=pc+8;self.execute(pc+4);self.call(((pc+4)&0xf0000000)|((w&0x3ffffff)<<2));pc+=8
   elif op in(4,5):
    a,b=self.r[rs],self.r[rt];assert isinstance(a,int)and isinstance(b,int),(pc,a,b);taken=(a==b)if op==4 else(a!=b);self.branches.append((op,taken));self.visits.append(pc);self.execute(pc+4);pc=pc+4+((((w&65535)^32768)-32768)*4)if taken else pc+8
   elif op==0 and fn==8:target=self.r[rs];assert isinstance(target,int);self.visits.append(pc);self.execute(pc+4);pc=target
   else:self.execute(pc);pc+=4
  else:raise AssertionError('Unbounded symbolic execution')
  assert self.r[29]==core.STACK and all(self.r[i]==self.before[i]for i in(*range(16,24),28,30,31))and self.f[20:]==self.before_f[20:]
  assert self.r[2]==('allocation-pointer-or-null',5)and self.integer_calls==3 and len(self.calls)==5
  return self
def observe(m):return m.calls,m.public_writes,m.fp_ops,m.frame(),m.r,m.f,m.hi,m.lo,m.fcsr
def main():
 raw,refs=payload(o/'selected-final/owner-candidate.o','func_150B5E34');truth,tr=payload(o/'original-target.o','func_150B5E34');assert refs==tr and len(raw)==len(truth)==460
 symbols=dict(func_150ADA20=RNG,func_150ADA68=FRNG,func_15130280=FACTORY);words=bound_blob(raw,refs,symbols);original=bound_blob(truth,tr,symbols)
 assert words[0x13c//4]==0xafa30024 and words[0x148//4]==0x8fa30024 and original[0x13c//4]==0xafa30020 and original[0x148//4]==0x8fa30020
 branches=list(itertools.product((0,1),repeat=2));visits=set();references={}
 with patch.object(core,'ENTRY',ENTRY):
  for bits in branches:
   a=Machine(words,bits,True).finish();b=Machine(original,bits).finish();assert observe(a)==observe(b),bits;visits.update(b.visits);references[bits]=observe(b)
 assert len(visits)==115,len(visits)
 controls=[]
 mutations=[('modulus-seven',lambda w:w&0xfc00ffff==0x24000007,lambda w:w-1),('lifetime-base',lambda w:w&0xfc00ffff==0x24000004,lambda w:w+1),('resource',lambda w:w&0xfc00ffff==0x34000005,lambda w:w^1),('float-multiply-to-add',lambda w:w>>26==17 and w>>21&31==16 and w&63==2,lambda w:w&~63),('extent-constant',lambda w:w>>26==15 and w&65535==0x43fa,lambda w:w+1),('first-position-word',lambda w:w>>26==35 and w>>21&31==10 and w&65535==0,lambda w:w+4),('first-random-flag',lambda w:w>>26==12 and w&65535==1,lambda w:w&~65535),('mode-home-byte',lambda w:w>>26==36 and w&65535==0x9f,lambda w:w-1),('descriptor-flags',lambda w:w>>26==13 and w&65535==0xc200,lambda w:w^0x100),('factory-kind',lambda w:w==0x24050001,lambda w:w+1)]
 with patch.object(core,'ENTRY',ENTRY):
  for name,find,change in mutations:
   bad=list(words);at=next(i for i,w in enumerate(bad)if find(w));bad[at]=change(bad[at]);rejected=0
   for bits in branches:
    m=Machine(bad,bits,True).finish();rejected+=observe(m)!=references[bits]
   assert rejected,name;controls.append(dict(name=name,word=at,supported_complete_execution=True,rejected_branch_classes=rejected))
 module=sys.modules[__name__];rebases=0
 for group,(entry,low)in enumerate([(ENTRY,0),(0x250b5e34,0x7ff8),(0x350b5e34,0x8000),(0x450b5e34,0xfff8)]):
  values=dict(ENTRY=entry,POINT=0x30000+group*0x20000,RNG=(entry&0xf0000000)+0x210000+low,FRNG=(entry&0xf0000000)+0x230000+low,FACTORY=(entry&0xf0000000)+0x250000+low)
  with patch.multiple(module,**values),patch.multiple(core,ENTRY=entry,STACK=0x42008+group*0x20000):
   syms=dict(func_150ADA20=RNG,func_150ADA68=FRNG,func_15130280=FACTORY)
   for bits in branches:assert observe(Machine(bound_blob(raw,refs,syms),bits,True).finish())==observe(Machine(bound_blob(truth,tr,syms),bits).finish())
   rebases+=1
 q=dict(words=115,frame=152,raw_word_differences=21,raw_direct_word_values_and_bindings=94,provider_boundaries=5,ordered_FP_ops=2,complete_packet_bytes=112,initialized_packet_bytes=98,unspecified_packet_bytes=14,all_115_words_executed_across_four_low_bit_classes=True,low_bit_classes=4,rebased_proofs=rebases,effective_supported_controls=controls,checked_private_spill_bytes=4,private_frame_bijection='raw20..23 <->24..27; retail identity; one flag spill physically24 to20',full_mapped_private_frame_at_each_provider_and_return=True,all_return_registers_and_FCSR_equal=True,all_unsigned_lifetime_RNG_values_symbolic=True,remaining31_flag_RNG_bits_symbolic=True,public_position_bits_and_provider_epochs_symbolic=True,providers_preserve_unpassed_private_frame_and_incoming_homes=True,provider_may_write_complete_passed_packet=True,raw_physical_private_bytes_and_fault_order_not_claimed=True,not_general_SMT_or_all_contexts=True,source_installed=p.installed(),matching_credit=0)
 (o/'symbolic-controls.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
