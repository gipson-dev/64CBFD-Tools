"""Normalized full access prefixes and raw public provider boundaries."""
from pathlib import Path
import json,sys
from tools.experiments import game_render_list_parent_151674f8_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_render_list_parent_151674f8_native as n
g=n.g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def streams():return{k:g.bound_blob(*g.payload(o/p,'func_151674F8'),g.SYMS)for k,p in dict(raw='selected/candidate.o',padded='qualified-owner/game_1944C0.c.o',retail='original-target.o').items()}
class Model(n.Model):
 def __init__(self,*a):super().__init__(*a);self.boundaries=[]
 def hook(self,t):
  super().hook(t);self.boundaries.append((g.public(self.memory),self.log[:],self.r[2]))
def main():
 cases=[n.Case(),n.Case(shape=0),n.Case(shape=3,stages=True,stage_mask=15),n.Case(shape=3,draw_mode=1,budget=3),n.Case(shape=3,draw_mode=0,budget=3),n.Case(shape=3,stages=True,before_effect=3,clear_next=True,view=-32768),n.Case(shape=3,draw_mode=2,draw_effect=14,after_effect=12,stages=True,initial_depth=4)]
 words=streams();count=providers=0
 for c in cases:
  memory,nodes=n.fixture(c);complete={k:Model(ws,memory,c,nodes).run()for k,ws in words.items()}
  assert complete['raw'].boundaries==complete['padded'].boundaries==complete['retail'].boundaries,c
  providers+=len(complete['raw'].boundaries);assert complete['padded'].all_accesses==complete['retail'].all_accesses
  for cut in range(complete['padded'].all_accesses):
   states=[]
   for k in('padded','retail'):
    m=Model(words[k],memory,c,nodes);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing actual access boundary')
    states.append((m.memory,m.trace,m.calls,m.log,m.r,m.f,m.hi,m.lo,m.boundaries))
   assert states[0]==states[1],(c,cut);count+=1
 report=dict(normalized_full_access_prefix_pairs=count,raw_padded_retail_public_provider_boundary_triples=providers,discriminating_cases=len(cases),normalized_full_memory_GPR_FPR_trace_and_HI_LO_equal=True,source_installed=packet.installed(),matching_credit=0,limits='Raw temporary registers and intermediate private fault states differ; full fault identity is claimed only for normalized versus retail. Raw public boundaries retain the explicit bounded providers. No asynchronous/FCSR/hardware/gameplay claim.')
 (o/'faults.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
