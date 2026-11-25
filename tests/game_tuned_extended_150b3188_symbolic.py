"""Private structural trace, both factory outcomes; not adoption evidence alone."""
from pathlib import Path
import json,struct,sys
from unittest.mock import patch
sys.path.insert(0,str(Path.cwd()))
from tools.tests import game_angular_extended_150b2eb4_symbolic as prior
core=prior.s
from tools.experiments import game_tuned_extended_150b3188_match as p
o=p.OUT;ENTRY=0x150b3188;ANGLE=0x151423d8;FRNG=0x150ada68;TWEAK=0x151422dc;FACTORY=0x15132a4c;COPY=0x10022ec0
class Machine(prior.Machine):
 def __init__(self,words,outcome):self.outcome=outcome;super().__init__(words)
 def execute(self,pc):
  w=self.code[pc];op,fmt,fs,fd,fn=w>>26,w>>21&31,w>>11&31,w>>6&31,w&63
  if op==33:
   self.visits.append(pc);rs,rt=w>>21&31,w>>16&31;imm=((w&65535)^32768)-32768;v=self.load(core.add(self.r[rs],core.u(imm)),2);self.r[rt]=core.u((v^32768)-32768)if isinstance(v,int)else('sx16',v);self.r[0]=0
  elif op==17 and fmt==20 and fn==32:self.visits.append(pc);self.f[fd]=('fcvt-s-w',self.f[fs]);self.events.append(('FP',self.f[fd]))
  else:super().execute(pc)
 def call(self,target):
  n={ANGLE:1,FRNG:0,TWEAK:7,FACTORY:6,COPY:3}[target]
  args=tuple(self.r[4+i]if i<4 else self.load(self.r[29]+4*i,4)for i in range(n));self.calls.append((target,args));self.events.append(('CALL',target,args));self.epoch+=1
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=('call-clobber',self.epoch,'r',reg)
  for reg in range(20):self.f[reg]=('call-clobber',self.epoch,'f',reg)
  self.r[2]=('call-result',self.epoch);self.f[0]=('call-float-result',self.epoch);self.mem={a:v for a,v in self.mem.items()if core.STACK-248<=a<core.STACK}
  if target==FACTORY:
   at=args[0];assert isinstance(at,int)and core.STACK-248<=at and at+124<=core.STACK
   for i in range(124):self.mem.pop(at+i,None)
   self.r[2]=('nonnull-factory-pointer',self.epoch)if self.outcome else 0
  if target==COPY:
   assert args[2]in(0,4)and isinstance(args[1],int);self.r[2]=args[0]
  for i in range(max(4,n)):self.store(self.r[29]+4*i,4,('outgoing-home',self.epoch,i),False)
 def run(self):
  pc=ENTRY
  for steps in range(500):
   if pc==core.RETURN:break
   w=self.code[pc];op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
   if op==3:
    self.visits.append(pc);self.r[31]=pc+8;self.execute(pc+4);self.call(((pc+4)&0xf0000000)|((w&0x3ffffff)<<2));pc+=8
   elif op in(4,5):
    a,b=self.r[rs],self.r[rt]
    if isinstance(a,int)and isinstance(b,int):equal=a==b
    else:assert isinstance(a,tuple)and a[0]=='nonnull-factory-pointer'and b==0;equal=False
    taken=equal if op==4 else not equal;self.branches.append((op,taken));self.visits.append(pc);self.execute(pc+4);pc=pc+4+((((w&65535)^32768)-32768)*4)if taken else pc+8
   elif op==0 and fn==8:
    target=self.r[rs];assert isinstance(target,int);self.visits.append(pc);self.execute(pc+4);pc=target
   else:self.execute(pc);pc+=4
  else:raise AssertionError('Unbounded execution')
  assert self.r[2]==1 and self.r[29]==core.STACK and all(self.r[i]==self.before[i]for i in(*range(16,24),28,30,31))and self.f[20:]==self.before_f[20:];return self

def main():
 raw,rr=core.payload(o/'selected-final/owner-candidate.o','func_150B3188');truth,tr=core.payload(o/'original-target.o','func_150B3188');assert rr==tr
 base={name:(COPY if name=='memcpy'else int(name.split('_',1)[1],16))for pairs in rr.values()for _,name in pairs}
 def compare(symbols,entry,outcome):
  values=dict(ENTRY=entry,ANGLE=symbols['func_151423D8'],FRNG=symbols['func_150ADA68'],TWEAK=symbols['func_151422DC'],FACTORY=symbols['func_15132A4C'],COPY=symbols['memcpy'])
  with patch.multiple(core,ENTRY=entry),patch.multiple(sys.modules[__name__],**values):
   a=Machine(core.bound_blob(raw,rr,symbols),outcome).run();b=Machine(core.bound_blob(truth,tr,symbols),outcome).run();assert a.events==b.events and a.branches==b.branches;return a,b
 rows=[];visits=set()
 for outcome in(0,1):
  a,b=compare(base,ENTRY,outcome);visits|=set(a.visits);rows.append(dict(outcome=outcome,events=len(a.events),calls=len(a.calls),executed_words=len(set(a.visits)),branches=a.branches))
 rebases=0
 for region,low in[(0x150b3188,0),(0x250b3188,0x7ff8),(0x350b3188,0x8000),(0x450b3188,0xfff8)]:
  calls=sorted(n for n in base if n.startswith('func_')or n=='memcpy');data=sorted(n for n in base if n.startswith('D_'));symbols={n:(region&0xf0000000)+0x210000+0x20000*i+low for i,n in enumerate(calls)};symbols.update({n:0x80100000+0x20000*i+low for i,n in enumerate(data)})
  for outcome in(0,1):compare(symbols,region,outcome);rebases+=1
 ws=core.bound_blob(raw,rr,base);controls=[]
 with patch.object(core,'ENTRY',ENTRY):
  reference=Machine(core.bound_blob(truth,tr,base),1).run()
  mutations=[('duration-default',next(i for i,w in enumerate(ws)if w&0xfc00ffff==0x2400012c),lambda w:w+1),('resource',next(i for i,w in enumerate(ws)if w&0xfc00ffff==0x2400001c),lambda w:w+1),('slot-home',next(i for i,w in enumerate(ws)if w&0xfc00ffff==0x90000133),lambda w:w-4),('multiply-to-add',next(i for i,w in enumerate(ws)if w>>26==17 and w>>21&31==16 and w&63==2),lambda w:w&~63),('copy-zero-bytes',next(i for i,w in enumerate(ws)if w==0x24060004),lambda w:w-4)]
  for name,i,mutate in mutations:
   changed=ws[:];changed[i]=mutate(changed[i]);m=Machine(changed,1).run();assert m.events!=reference.events or m.branches!=reference.branches;controls.append(dict(name=name,supported_execution=True,rejected_by_trace_comparison=True))
  symbols=dict(base);symbols['D_8009FBA4']=symbols['D_8009FBA8'];m=Machine(core.bound_blob(raw,rr,symbols),1).run();assert m.events!=reference.events;controls.append(dict(name='coefficient-binding',supported_execution=True,rejected_by_trace_comparison=True))
 assert len(visits)==329
 q=dict(raw_words=329,frame=248,word_differences=32,bindings_equal=True,outcomes=rows,union_reachable_words=329,rebased_outcome_proofs=rebases,effective_supported_controls=controls,arbitrary_o32_provider_values_and_public_epochs=True,nonnull_factory_pointer_is_symbolic_valid_disjoint_region=True,factory_may_overwrite_descriptor124_but_not_private_payload4=True,CVT_signed32_to_float_and_TRUNC_recorded=True,scoped_structural_proof_not_general_SMT=True,source_installed=p.installed(),matching_credit=0)
 (o/'symbolic-controls.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)


 return q

if __name__=='__main__':main()
