from pathlib import Path
import json,struct,sys
from unittest.mock import patch
sys.path.insert(0,str(Path.cwd()))
from tools.tests import game_radial_angle_150c16c0_symbolic as s
from tools.experiments import game_angular_extended_150b2eb4_match as p
o=p.OUT;ENTRY=0x150b2eb4;FRNG=0x150ada68;ANGLE=0x151423d8;FACTORY=0x15132a4c
class Machine(s.Machine):
 def execute(self,pc):
  w=self.code[pc];op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==0:self.visits.append(pc);self.r[rt]=self.f[fs];self.r[0]=0
  elif op==17 and fmt==16 and fn==13:self.visits.append(pc);self.f[fd]=('ftrunc-w-s',self.f[fs]);self.events.append(('FP',self.f[fd]))
  else:super().execute(pc)
 def call(self,target):
  n=0 if target==FRNG else 1 if target==ANGLE else 6 if target==FACTORY else None;assert n is not None
  args=tuple(self.r[4+i]if i<4 else self.load(self.r[29]+4*i,4)for i in range(n));self.calls.append((target,args));self.events.append(('CALL',target,args));self.epoch+=1
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=('call-clobber',self.epoch,'r',reg)
  for reg in range(20):self.f[reg]=('call-clobber',self.epoch,'f',reg)
  self.r[2]=('call-result',self.epoch);self.f[0]=('call-float-result',self.epoch)
  self.mem={a:v for a,v in self.mem.items()if s.STACK-192<=a<s.STACK}
  if target==FACTORY:
   at=args[0];assert isinstance(at,int)and s.STACK-192<=at and at+124<=s.STACK
   for i in range(124):self.mem.pop(at+i,None)
  for i in range(max(4,n)):self.store(self.r[29]+4*i,4,('outgoing-home',self.epoch,i),False)

def main():
 raw,rr=s.payload(o/'selected-final/owner-candidate.o','func_150B2EB4');truth,tr=s.payload(o/'original-target.o','func_150B2EB4');assert rr==tr
 base={name:int(name.split('_',1)[1],16)for pairs in rr.values()for _,name in pairs}
 def compare(symbols,entry):
  global FRNG,ANGLE,FACTORY
  with patch.multiple(s,ENTRY=entry),patch.multiple(sys.modules[__name__],FRNG=symbols['func_150ADA68'],ANGLE=symbols['func_151423D8'],FACTORY=symbols['func_15132A4C']):
   a=Machine(s.bound_blob(raw,rr,symbols)).run();b=Machine(s.bound_blob(truth,tr,symbols)).run()
   if a.events!=b.events:
    i=next(i for i,(x,y)in enumerate(zip(a.events,b.events))if x!=y);print('TRACE DIFFERENCE',i,repr(a.events[i]),repr(b.events[i]),flush=True)
   assert a.events==b.events and a.branches==b.branches;return a,b
 a,b=compare(base,ENTRY);valid=0
 for region,low in[(0x150b2eb4,0),(0x250b2eb4,0x7ff8),(0x350b2eb4,0x8000),(0x450b2eb4,0xfff8)]:
  calls=sorted(n for n in base if n.startswith('func_'));data=sorted(n for n in base if n.startswith('D_'));symbols={n:(region&0xf0000000)+0x210000+0x20000*i+low for i,n in enumerate(calls)};symbols.update({n:0x80100000+0x20000*i+low for i,n in enumerate(data)});compare(symbols,region);valid+=1
 ws=s.bound_blob(raw,rr,base);controls=[]
 mutations=[('resource',next(i for i,w in enumerate(ws)if w&0xfc00ffff==0x2400001c),lambda w:w+1),('slot-home',142,lambda w:w-4),('flags',next(i for i,w in enumerate(ws)if w&0xfc00ffff==0x240009e8),lambda w:w^1),('factory-resource',next(i for i,w in enumerate(ws)if w==0x24050003),lambda w:w-1),('multiply-to-add',next(i for i,w in enumerate(ws)if w>>26==17 and w>>21&31==16 and w&63==2),lambda w:w&~63)]
 with patch.object(s,'ENTRY',ENTRY):
  for name,i,mutate in mutations:
   changed=ws[:];changed[i]=mutate(changed[i]);m=Machine(changed).run();assert m.events!=b.events;controls.append(dict(name=name,supported_execution=True,rejected_by_trace_comparison=True))
  symbols=dict(base);symbols['D_8009FB94']=symbols['D_8009FB90'];m=Machine(s.bound_blob(raw,rr,symbols)).run();assert m.events!=b.events;controls.append(dict(name='coefficient-binding',supported_execution=True,rejected_by_trace_comparison=True))
 q=dict(raw_words=181,retail_words=181,raw_frame=192,retail_frame=192,word_differences=29,bindings_equal=True,ordered_memory_FP_call_events=len(a.events),calls=len(a.calls),all_reachable_words=len(set(a.visits)),rebased_proofs=valid,effective_supported_trace_controls=controls,arbitrary_provider_results_and_public_epochs=True,factory_may_overwrite_full124_descriptor=True,scoped_structural_proof_not_general_SMT=True,source_installed=p.installed(),matching_credit=0)
 (o/'symbolic-controls.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)


 return q

if __name__=='__main__':main()
