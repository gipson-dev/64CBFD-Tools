"""All complete parent/leaf combinations with real retained registrations."""
from pathlib import Path
import json,struct,sys
from tools.experiments import game_render_list_parent_151674f8_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_render_list_parent_151674f8_guest as q
g,p=q.g,q.p
def main():
 parents={k:g.bound_blob(*g.payload(o/path,'func_151674F8'),g.SYMS)for k,path in dict(raw='selected/candidate.o',padded='qualified-owner/game_1944C0.c.o',retail='original-target.o').items()}
 leaves={k:g.bound_blob(*g.payload(q.u/path,'func_15168118'),g.SYMS)for k,path in dict(raw='selected-v2/candidate.o',padded='qualified-owner/game_1944C0.c.o',retail='original-target.o').items()}
 cases=p.rows();counts={a+'/'+b:0 for a in parents for b in leaves};coverage={a:set()for a in parents}
 image=(o/'image-qualification/linked.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes()
 for col,at in((5,0x230074),(66,0x230CD8)):
  value=int.from_bytes(rom[at:at+4],'big');slot=g.elf_slot_offset(image,p.DESC+col*52+8,4)
  assert value==g.ENTRY==int.from_bytes(image[slot:slot+4],'big')
 for c in cases:
  memory,nodes=p.fixture(c);truth=q.Parent(parents['retail'],leaves['retail'],memory,c,nodes).run();want=q.state(truth)
  for a,parent in parents.items():
   for b,leaf in leaves.items():
    m=q.Parent(parent,leaf,memory,c,nodes).run();assert q.state(m)==want,(a,b,c)
    counts[a+'/'+b]+=len(m.called_targets);coverage[a].update(m.visits)
 report=dict(cases_per_combination=len(cases),complete_parent_leaf_combinations=len(counts),leaf_invocations=counts,actual_ROM_and_private_ELF_registrations_checked=True,public_memory_ordered_provider_events_target_arguments_and_returned_cursors_equal=True,unexecuted_parent_words={a:[i for i in range(348)if p.PARENT+4*i not in v]for a,v in coverage.items()},source_installed=packet.installed(),matching_credit=0,limits='All raw/padded/retail complete parents by all raw/padded/retail complete qualified renderer leaves. Range, stage and graphics providers remain bounded contracts; actual range and all callers are checked separately. Range local pointer identity is abstracted after aligned distinct frame-bound validation.')
 (o/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
