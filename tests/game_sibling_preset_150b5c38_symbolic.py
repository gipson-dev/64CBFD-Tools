"""Private boundary proof for all127 words, complete frame and116-byte packet."""
from pathlib import Path
import json,sys
from unittest.mock import patch
sys.path.insert(0,str(Path.cwd()))
from tools.tests import game_radial_angle_150c16c0_symbolic as core
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_sibling_preset_150b5c38_match as p
r,o=p.ROOT,p.OUT;ENTRY=0x150b5c38;POINT=0x30000;SUBMIT=0x15152b38;OTHER=0x150b5e34;TAIL=0x150b6000;COEFF=(0x8009fcac,0x8009fcb0,0x8009fcb4,0x8009fcb8)
class Machine(core.Machine):
 def __init__(self,words):
  self.initializing=True;self.public_writes=[];self.frames=[];self.fcsr=('entry-FCSR',);super().__init__(words);self.initializing=False;self.r[4]=POINT;self.mem={a:v for a,v in self.mem.items()if a<core.STACK+12}
 def store(self,a,n,v,record=True):
  assert isinstance(a,int)
  assert core.STACK-144<=a and a+n<=core.STACK+12 or self.initializing and not record and core.STACK+16<=a and a+n<=core.STACK+60,(a,n)
  if record and a>=core.STACK:self.public_writes.append((self.epoch,a,n,core.mask(v,(1<<(8*n))-1)))
  for i in range(n):self.mem[a+i]=core.byte(v,n-1-i)
 def load(self,a,n):
  assert isinstance(a,int),(a,n)
  assert core.STACK-144<=a and a+n<=core.STACK+12 or POINT<=a and a+n<=POINT+12 or any(c<=a and a+n<=c+4 for c in COEFF),(a,n)
  private=core.STACK-144<=a<core.STACK
  return core.join([self.mem.get(a+i,('entry-private-byte',a+i)if private else('public-byte',self.epoch,a+i))for i in range(n)])
 def frame(self):return tuple(self.mem.get(core.STACK-144+i,('entry-private-byte',core.STACK-144+i))for i in range(144))
 def call(self,target):
  assert target in(SUBMIT,OTHER,TAIL);args=tuple(self.r[4:7]);packet=()
  if target==SUBMIT:
   assert args[0]==core.STACK-116;packet=tuple(self.load(args[0]+i,1)for i in range(116))
  else:assert args[0]==POINT;packet=tuple(self.load(POINT+i,1)for i in range(12))
  self.calls.append((target,args,packet,self.fcsr,self.frame()));self.epoch+=1
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=('provider-GPR',self.epoch,reg)
  for reg in range(20):self.f[reg]=('provider-FPR',self.epoch,reg)
  self.r[2]=('provider-result',self.epoch);self.hi=self.lo=('provider-hi-lo',self.epoch);self.fcsr=('provider-FCSR',self.epoch)
  self.mem={a:v for a,v in self.mem.items()if core.STACK-144<=a<core.STACK+12}
  if target==SUBMIT:
   for i in range(116):self.mem[args[0]+i]=('provider-packet-write',self.epoch,i)
  for i in range(4):self.store(self.r[29]+4*i,4,('provider-outgoing-home',self.epoch,i),False)
 def finish(self):
  self.run();assert self.r[29]==core.STACK and all(self.r[i]==self.before[i]for i in(*range(16,24),28,30,31))and self.f[20:]==self.before_f[20:];return self
 def run(self):
  # The reused callback core has a return-one assertion; this callback is void.
  pc=ENTRY
  for step in range(300):
   if pc==core.RETURN:return self
   w=self.code[pc];op,rs,fn=w>>26,w>>21&31,w&63
   if op==3:self.visits.append(pc);self.r[31]=pc+8;self.execute(pc+4);self.call(((pc+4)&0xf0000000)|((w&0x3ffffff)<<2));pc+=8
   elif op==0 and fn==8:target=self.r[rs];assert isinstance(target,int);self.visits.append(pc);self.execute(pc+4);pc=target
   else:assert op not in(1,2,4,5,6,7,20,21,22,23);self.execute(pc);pc+=4
  raise AssertionError('Unbounded symbolic execution')
def observe(m):return m.calls,m.public_writes,m.frame(),m.r,m.f,m.hi,m.lo,m.fcsr
def main():
 raw,refs=payload(o/'selected-final/owner-candidate.o','func_150B5C38');truth,tr=payload(o/'original-target.o','func_150B5C38');assert refs==tr and len(raw)==len(truth)==508
 symbols=dict(func_15152B38=SUBMIT,func_150B5E34=OTHER,func_150B6000=TAIL,**dict(zip(('D_8009FCAC','D_8009FCB0','D_8009FCB4','D_8009FCB8'),COEFF)))
 with patch.object(core,'ENTRY',ENTRY):
  a=Machine(bound_blob(raw,refs,symbols)).finish();b=Machine(bound_blob(truth,tr,symbols)).finish();assert observe(a)==observe(b);assert len(set(a.visits))==len(set(b.visits))==127
 controls=[];words=bound_blob(raw,refs,symbols)
 with patch.object(core,'ENTRY',ENTRY):
  for name,find,change in[
   ('base-count',lambda w:w>>26==9 and w&65535==13,lambda w:w+1),
   ('header-short-range',lambda w:w>>26==9 and w&65535==15,lambda w:w+1),
   ('resource-word',lambda w:w>>26==13 and w&65535==5,lambda w:w^1),
   ('first-position-word',lambda w:w>>26==35 and w>>21&31==25 and w&65535==0,lambda w:w+4),
   ('mode-home-byte',lambda w:w>>26==36 and w&65535==0x97,lambda w:w-1),
   ('zero-control-byte',lambda w:w>>26==40 and w&65535==0x8d,lambda w:w-1)]:
   bad=list(words);at=next(i for i,w in enumerate(bad)if find(w));bad[at]=change(bad[at]);m=Machine(bad).finish();assert observe(m)!=observe(b);assert len(set(m.visits))==127;controls.append(dict(name=name,word=at,supported_complete_execution=True,rejected=True))
  altered=dict(symbols);altered['D_8009FCAC']=COEFF[1];m=Machine(bound_blob(raw,refs,altered)).finish();assert observe(m)!=observe(b);controls.append(dict(name='coefficient-binding',supported_complete_execution=True,rejected=True))
  altered=dict(symbols);altered['func_150B6000']=OTHER;m=Machine(bound_blob(raw,refs,altered)).finish();assert observe(m)!=observe(b);controls.append(dict(name='third-provider-binding',supported_complete_execution=True,rejected=True))
 module=sys.modules[__name__];rebases=0
 for group,(entry,low)in enumerate([(ENTRY,0),(0x250b5c38,0x7ff8),(0x350b5c38,0x8000),(0x450b5c38,0xfff8)]):
  coeff=tuple(0x80100000+0x10000*i+low for i in range(4));values=dict(ENTRY=entry,POINT=0x30000+group*0x20000,SUBMIT=(entry&0xf0000000)+0x210000+low,OTHER=(entry&0xf0000000)+0x230000+low,TAIL=(entry&0xf0000000)+0x250000+low,COEFF=coeff)
  with patch.multiple(module,**values),patch.multiple(core,ENTRY=entry,STACK=0x42008+group*0x20000):
   syms=dict(func_15152B38=SUBMIT,func_150B5E34=OTHER,func_150B6000=TAIL,**dict(zip(('D_8009FCAC','D_8009FCB0','D_8009FCB4','D_8009FCB8'),COEFF)));left=Machine(bound_blob(raw,refs,syms)).finish();right=Machine(bound_blob(truth,tr,syms)).finish();assert observe(left)==observe(right);rebases+=1
 q=dict(words=127,frame=144,raw_word_differences=51,provider_boundaries=3,complete_packet_bytes=116,full_private_frame_at_each_call_and_return=True,all_return_registers_and_FCSR_equal=True,all_127_words_executed=True,rebased_proofs=rebases,effective_supported_controls=controls,public_bits_and_provider_epochs_symbolic=True,providers_preserve_unpassed_incoming_homes=True,provider_writes_to_complete_passed_packet=True,raw_private_write_and_fault_order_not_claimed=True,not_general_SMT_or_all_contexts=True,source_installed=p.installed(),matching_credit=0)
 (o/'symbolic-controls.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
