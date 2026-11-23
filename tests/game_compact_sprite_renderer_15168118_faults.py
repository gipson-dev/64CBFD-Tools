"""Every normalized/retail access prefix; raw public-provider boundaries."""
from pathlib import Path
import json,sys
from tools.experiments import game_compact_sprite_renderer_15168118_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_compact_sprite_renderer_15168118_guest as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def streams():
 return {k:g.bound_blob(*g.payload(out/p,'func_15168118'),g.SYMS)for k,p in dict(raw='selected-v2/candidate.o',padded='qualified-owner/game_1944C0.c.o',retail='original-target.o').items()}
class Boundaries(g.Oracle):
 def __init__(self,*a,**kw):super().__init__(*a,**kw);self.public_boundaries=[]
 def hook(self,t):
  super().hook(t);self.public_boundaries.append((g.public(self.memory),self.observations[:],self.r[2]))
def main():
 count=providers=0;cases=(g.Case(),g.Case(flags=0x300,effect=7,width=-2000,height=-500,yaw=-720.5,pitch=-30),g.Case(flags=1,frame_table=True,position=-32768),g.Case(flags=16,special=1),g.Case(texture_type=3,special=2),g.Case(flags=12,width=-1,height=-1,orientation=255,view=1))
 words=streams()
 for c in cases:
  memory=g.fixture(c);g.put(memory,g.SYMS['D_800D2C9C'],0x40000);complete=[]
  for k,ws in words.items():
   m=Boundaries(ws,memory,c);m.run();complete.append(m)
  assert complete[0].public_boundaries==complete[1].public_boundaries==complete[2].public_boundaries,c;providers+=len(complete[0].public_boundaries)
  assert complete[1].all_accesses==complete[2].all_accesses
  for cut in range(complete[1].all_accesses):
   states=[]
   for k in('padded','retail'):
    m=g.Oracle(words[k],memory,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing actual access boundary')
    states.append((m.memory,m.trace,m.calls,m.observations,m.r,m.f,m.hi,m.lo))
   assert states[0]==states[1],(c,cut);count+=1
 report=dict(normalized_full_access_prefix_pairs=count,raw_padded_retail_public_provider_boundary_triples=providers,discriminating_cases=len(cases),normalized_full_memory_GPR_FPR_trace_and_HI_LO_equal=True,source_installed=packet.installed(),matching_credit=0,limits='Raw schedules/registers/private homes differ; raw full access and private fault identity are not claimed. Raw public state is compared after every bounded provider call. No FCSR/timing/asynchronous/provider-internal fault model.')
 (out/'faults.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
