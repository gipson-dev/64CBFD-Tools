"""Both original dispatch tables and actual caller with all parent streams."""
import json,struct
from tools.experiments import game_actor_bound_burst_150b7b40_match as source
from tools.tests import game_actor_bound_burst_150b7b40_callers as original
g=original.g

def main():
 previous=g.p;g.p=source.OUT
 try:caller,tables,states,sha=original.prepare()
 finally:g.p=previous
 live=(source.ROOT/'conker/build/conker.us.elf').read_bytes()
 at=source.elf_slot_offset(live,original.CALLER,1008)
 assert list(struct.unpack('>252I',live[at:at+1008]))==caller
 expected={};reports=[]
 for label,words in source.programs():
  count=calls=0;seen=set()
  for state in states:
   for index,case in enumerate(g.cases()):
    if case.null:continue
    m=original.Oracle(caller,words,tables,state,case).run()
    assert m.boundaries==1 and m.r[2]==0
    assert tuple(m.r[16:24])+tuple(m.r[28:])==m.saved and tuple(m.f[20:])==m.saved_fp
    result=(m.calls,g.public(m.memory),m.r[2],g.data(m.memory,g.STACK+case.phase-56,72));key=state,index
    if label=='retail':expected[key]=result
    else:assert result==expected[key],(label,state,case)
    seen.update(m.visits&set(range(g.ENTRY,g.ENTRY+4*len(words),4)));count+=1;calls+=len(m.calls)
  unseen=set(range(g.ENTRY,g.ENTRY+4*len(words),4))-seen
  assert len(unseen)==2 and sorted(words[(at-g.ENTRY)//4]for at in unseen)==sorted((0x8fbf007c,0x3c013f80))
  reports.append(dict(stream=label,words=len(words),cases=count,parent_words_covered=len(seen),provider_calls=calls,saved_ABI=True,caller_owned_bytes=72,caller_return_zero=True))
 report=dict(passes=True,streams=reports,caller_words=252,caller_sha256=sha,actual_GNU_ROM_and_current_ELF_verified=True,states=states,slot=255,context=1,child_providers_modeled=True,c_match_credit=0)
 (source.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
