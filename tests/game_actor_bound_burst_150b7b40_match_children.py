"""Actual production children in the retail, raw and normalized parent streams."""
from pathlib import Path
from dataclasses import replace
import hashlib,json,struct,sys,time
from tools.tests import game_actor_bound_burst_150b7b40_oracle as parent
from tools.experiments import game_actor_bound_burst_150b7b40_match as match_source
from tools.tests import game_burst_emitter_150b82d0_oracle as burst
from tools.tests import game_scaled_radial_150b85c0_oracle as radial
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
source=match_source;p=source.OUT;elf=(source.FROZEN/'conker/build/conker.us.elf').read_bytes();rom=(source.FROZEN/'conker/conker.us.bin').read_bytes();symbols={v[1]:v[2][1]for v in symbol_rows(elf)}
children={}
for entry,offset,count in((parent.BURST,0xE5780,188),(parent.RADIAL,0xE5A70,119)):
 blob=elf[elf_slot_offset(elf,entry,4*count):][:4*count];assert len(blob)==4*count
 # Independently selected retail ranges are verified below using the address-to-ROM offset.
 at=0xE4FF0+(entry-parent.ENTRY);assert blob==rom[at:at+4*count],hex(entry)
 live=(source.ROOT/'conker/build/conker.us.elf').read_bytes();live_at=elf_slot_offset(live,entry,4*count);assert live[live_at:live_at+4*count]==blob
 children[entry]=list(struct.unpack('>'+str(count)+'I',blob))
connected={entry+4*i:w for entry,words in children.items()for i,w in enumerate(words)}
class Oracle(parent.Oracle):
 def __init__(self,words,c,base,success,mutation):
  initial=parent.fixture(c);at=elf_slot_offset(elf,0x8009FD68,36);initial.update({0x8009FD68+i:b for i,b in enumerate(elf[at:at+36])})
  for address,n in((burst.OUTPUT,32),(burst.MARK,4),(burst.INPUT,0x120)):
   initial.update({address+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
  self.child=None;self.child_records=[];self.verified=0;self.success=success;self.mutation=mutation
  super().__init__(words,c,entry=base,initial=initial,connected=connected)
 def finish_child(self):
  active=self.child;t=active['target'];expected,service,result=active['expected']
  assert active['service'].calls==service.calls,('child calls',hex(t))
  assert self.r[2]==result,('child V0',hex(t),self.r[2],result)
  assert parent.public(self.memory)==parent.public(expected),('child public',hex(t))
  assert tuple(self.r[16:24])+tuple(self.r[28:])==active['saved']and tuple(self.f[20:])==active['saved_fp'],('child ABI',hex(t))
  if t==parent.BURST:
   for i in range(4):assert parent.data(self.memory,active['service'].vector(i),12)==parent.data(expected,service.vector(i),12)
   for address,n in zip(active['arguments'][:4],(12,4,4,4)):assert parent.data(self.memory,address,n)==parent.data(expected,address,n)
  else:assert parent.data(self.memory,active['home']-112,112)==parent.data(expected,active['home']-112,112)
  self.child_records.append((t,active['service'].calls));self.verified+=1;self.child=None
 def execute(self,w):
  if self.child is not None and self.current_pc==self.child['continue']:self.finish_child()
  return super().execute(w)
 def record_call(self,t):
  if self.child is not None:
   n={burst.RNG:0,burst.REAL:0,burst.DIRECTION:4,burst.SUBMIT:13}if self.child['target']==parent.BURST else{radial.RNG:0,radial.FACTORY:5}
   assert t in n,(hex(t),hex(self.child['target']));self.child_pending=t,tuple(self.arguments(n[t]));return
  super().record_call(t)
  if t in(parent.BURST,parent.RADIAL):
   home=self.r[29];argv=tuple(self.arguments(6 if t==parent.BURST else 5))
   if t==parent.BURST:
    c=burst.Case(initial=(0,25,0xffffffff,0x80000000)[self.case.profile],mutation=3 if self.mutation else 0,success=self.success,phase=self.case.phase,seed=self.case.seed)
    expected=burst.reference(self.memory,c,home=home,arguments=argv);expected=(expected[0],expected[1],expected[1].last_result);service=burst.Service(self.memory,c,home=home,arguments=argv)
   else:
    c=radial.Case(slot=self.case.seed,success=self.success,mutation=7 if self.mutation else 0,profile=self.case.profile,phase=self.case.phase,seed=self.case.seed,context=argv[4]);expected=radial.reference(self.memory,c,home=home,arguments=argv);service=radial.Service(self.memory,c)
   self.child=dict(target=t,home=home,arguments=argv,expected=expected,service=service,continue_=self.r[31],saved=tuple(self.r[16:24])+tuple(self.r[28:]),saved_fp=tuple(self.f[20:]));self.child['continue']=self.child.pop('continue_')
 def hook(self,t):
  if self.child is None:return super().hook(t)
  active=self.child;assert self.child_pending[0]==t;answer=active['service'].invoke(*self.child_pending);n=13 if t==burst.SUBMIT else 5 if t==radial.FACTORY else 4
  for i in range(n):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=answer&0xffffffff
  if t==burst.REAL:self.f[0]=answer

def main():
 start=time.monotonic();smoke=False;cases=list(parent.cases());cases=cases[:2]+[cases[-1]]if smoke else cases;reports=[];expected={}
 for label,words in source.programs():
  base=parent.ENTRY if label=='retail'else 0x15200000
  seen=set();count=invocations=provider_calls=0
  for success in(0,1):
   for mutation in(0,1):
    for i,c in enumerate(cases):
     m=Oracle(words,c,base,success,mutation).run();assert m.child is None and m.verified==2*int(not c.null);assert tuple(m.r[16:24])+tuple(m.r[28:])==m.saved and tuple(m.f[20:])==m.saved_fp
     result=(m.calls,m.child_records,parent.public(m.memory),m.r[2]);key=success,mutation,i
     if label=='retail':expected[key]=result
     else:
      assert result==expected[key],('parent connected mismatch',key,c,next(j for j,(x,y)in enumerate(zip(result,expected[key]))if x!=y))
     seen.update(m.visits);count+=1;invocations+=m.verified;provider_calls+=sum(len(v)for _,v in m.child_records)
  report=dict(stream=label,cases=count,verified_child_invocations=invocations,child_provider_calls=provider_calls,burst_words_covered=len(seen&set(range(parent.BURST,parent.BURST+752,4))),radial_words_covered=len(seen&set(range(parent.RADIAL,parent.RADIAL+476,4))))
  reports.append(report);print(json.dumps(report),flush=True)
 report=dict(passes=True,smoke=smoke,streams=reports,seconds=round(time.monotonic()-start,3),actual_production_children_and_ROM_verified=True,source_installed=source.installed(),c_match_credit=0);(p/('smoke-report.json'if smoke else'connected-report.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

 return report

def controls():
 global connected
 raw=source.programs()[1][1];retail=source.programs()[0][1]
 case=parent.Case(model=1,floor=1,profile=3,mutation=3,phase=8,seed=255);reports=[];original=connected
 try:
  for target,constant,label in((parent.BURST,75,'burst-duration'),(parent.RADIAL,35,'radial-duration')):
   words=children[target];at=[i for i,w in enumerate(words)if w>>26==9 and w&65535==constant];assert len(at)==1
   connected=original.copy();address=target+4*at[0];connected[address]^=1
   try:Oracle(raw,case,0x15200000,1,1).run()
   except AssertionError as error:
    reason=str(error);assert 'child calls'in reason,(label,reason);reports.append(dict(label=label,rejected=True,reason=reason))
   else:raise AssertionError(('ineffective child corruption',label))
 finally:connected=original
 baseline=Oracle(retail,case,parent.ENTRY,1,1).run();bad=raw[:]
 at=[i for i,w in enumerate(bad)if w>>26==3 and (((parent.ENTRY+4)&0xf0000000)|((w&0x3ffffff)<<2))==parent.BURST];assert len(at)==1
 bad[at[0]]=(bad[at[0]]&0xfc000000)|((parent.RADIAL>>2)&0x3ffffff);changed=Oracle(bad,case,0x15200000,1,1).run()
 assert (baseline.calls,baseline.child_records,parent.public(baseline.memory))!=(changed.calls,changed.child_records,parent.public(changed.memory))
 reports.append(dict(label='parent-child-route',rejected=True));report=dict(passes=True,effective_negatives=reports,c_match_credit=0)
 (source.OUT/'child-controls.json').write_text(json.dumps(report,indent=2)+'\n');return report
