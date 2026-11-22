"""Complete raw/padded/retail state equality at every selected access prefix."""
from pathlib import Path
import json,sys
from tools.experiments import game_sprite_frame_update_15168870_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_sprite_frame_update_15168870_guest as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def prefix(m):return(m.memory,m.trace,m.calls,m.observations,m.r,m.f,m.hi,m.lo)
def main():
 paths=[out/'frames-mod32/candidate.o',out/'qualified-owner/game_1944C0.c.o',out/'original-target.o'];count=0
 cases=(g.Case(frames=1),g.Case(position=-2,speed=1,ticks=0),g.Case(mode=1),g.Case(position=-1,speed=0,mode=2),g.Case(position=-1,speed=0,callback=False),g.Case(alias=2,frames=0,flags=64),g.Case(mode=16),g.Case(speed=0,index=-1))
 for c in cases:
  full=[]
  for path in paths:
   m=g.Oracle(g.words(path),g.fixture(c),c);m.run();g.check(m,c);full.append(m)
  assert len({m.all_accesses for m in full})==1
  for cut in range(full[0].all_accesses):
   states=[]
   for path in paths:
    m=g.Oracle(g.words(path),g.fixture(c),c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing access cut')
    states.append(prefix(m))
   assert states[0]==states[1]==states[2],(c,cut);count+=1
 r=dict(access_fault_triples=count,discriminating_cases=len(cases),full_memory_GPR_FPR_HI_LO_trace_calls_and_observations_equal=True,
  limits='Emitted guest access boundaries only. FCSR, timing, asynchronous memory changes and faults inside contracted providers are not modeled.',source_installed=packet.installed(),matching_credit=0)
 (out/'faults.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
