"""Six complete retail callers connected to each complete constructor stream."""
from pathlib import Path
from dataclasses import replace
import hashlib,importlib.util,itertools,json,struct,sys
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments import game_bone_hit_151aabc4_recovery as source
from tools.tests import game_bone_hit_151aabc4_oracle as g
R,P=source.ROOT,source.OUT
GLOBAL=0x800D154C
PARENTS=((0x1506FDF0,0),(0x1506FE1C,1),(0x1506FE48,0),(0x1506FE74,1),(0x1506FEA0,2),(0x1506FECC,3))
class Caller(g.Oracle):
 def __init__(self,words,initial,c,entry,parent,bone):
  code=dict(zip(range(g.ENTRY,g.ENTRY+len(words)*4,4),words));self.expected_bone=bone;self.target_calls=[]
  FactoryOracle.__init__(self,parent,initial,c,entry=entry,s={},arguments=(0x87654321,),connected=code)
  self.service=g.Service(self.memory,c,0);self.saved=tuple(self.r[16:24]);self.saved_fp=tuple(self.f[20:])
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(self.arguments(2));assert args==(0 if self.case.route==1 else g.A,self.expected_bone),('caller args',args,self.expected_bone)
   self.target_calls.append(args);self.service.home=self.r[29]
  else:super().record_call(t)
def main():
 rom=(R/'conker/conker.us.bin').read_bytes();elf=(R/'conker/build/conker.us.elf').read_bytes();helpers=[]
 for entry,size in((g.SELECT,76),(g.BONE,196),(g.PREP,356),(g.QUERY,644),(g.EMIT,452),(g.TRAIL,672)):
  truth=rom[entry-0x14FD2B50:entry-0x14FD2B50+size];at=elf_slot_offset(elf,entry,size)
  helpers.append(dict(entry=hex(entry),words=size//4,production_literal=elf[at:at+size]==truth,retail_sha256=hashlib.sha256(truth).hexdigest()))
 at=elf_slot_offset(elf,g.TABLE,4);table=list(elf[at:at+4]);at=elf_slot_offset(elf,g.COEF,20);coefficients=['0x%08X'%v for v in struct.unpack_from('>5I',elf,at)]
 report=[];streams=g.programs();negatives=[]
 for entry,bone in PARENTS:
  parent=list(struct.unpack_from('>11I',rom,entry-0x14FD2B50));at=elf_slot_offset(elf,entry,44);assert elf[at:at+44]==struct.pack('>11I',*parent)
  frame=(-parent[0])&65535;assert frame==24
  counts={};coverage=set()
  for label,words in streams.items():
   n=0
   for seed,route,hit,mutation,phase in itertools.product((0,197),range(3),(0,1),(0,1,2,4,8,16,31),(0,8)):
    c=g.Case(seed=seed,bone=bone,route=route,hit=hit,mutation=mutation,phase=phase);initial=g.fixture(c);g.put(initial,GLOBAL,0 if route==1 else g.A)
    expected,calls=g.reference(initial,replace(c,phase=c.phase-frame));m=Caller(words,initial,c,entry,parent,bone).run()
    assert len(m.target_calls)==1 and m.service.calls==calls and g.public(m.memory)==g.public(expected)
    assert tuple(m.r[16:24])==m.saved and tuple(m.f[20:])==m.saved_fp
    coverage.update(m.visits&set(range(entry,entry+44,4)));n+=1
   counts[label]=n
  assert len(coverage)==11
  indices=[i for i,w in enumerate(parent)if w==0x00002825 or w>>26==9 and w>>21&31==0 and w>>16&31==5];assert len(indices)==1
  bad=parent[:];bad[indices[0]]=0x24050004;c=g.Case(bone=bone);initial=g.fixture(c);g.put(initial,GLOBAL,g.A)
  try:Caller(streams['raw'],initial,c,entry,bad,bone).run()
  except AssertionError:negatives.append(hex(entry))
  else:raise AssertionError(('ineffective caller selector control',entry))
  report.append(dict(entry=hex(entry),selected_bone=bone,words=11,words_visited=11,production_literal=True,cases_per_stream=counts))
 result=dict(callers=report,helpers=helpers,actual_bone_table=table,actual_coefficient_words=coefficients,effective_caller_controls=negatives,complete_callers_executed=True,helpers_executed=False,source_installed=source.installed(),c_match_credit=0)
 (P/'callers-report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
