"""Ordered access-prefix parity, excluding raw PCs and volatile temporaries."""
from pathlib import Path
from dataclasses import replace
import json,sys
from tools.experiments import game_column_event_walker_1516944c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_column_event_walker_1516944c_guest as p
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def main():
 paths=[out/'assign-1/candidate.o',out/'qualified-owner/game_1944C0.c.o',out/'original-target.o'];helpers=p.helper_code();count=0
 cases=(p.Case(),replace(p.Case(),empty=True,phase=8),replace(p.Case(),pattern=0,mode=15),replace(p.Case(),pattern=1,mode=15),replace(p.Case(),real_helpers=True,opcode=15,tag=0x39),replace(p.Case(),mode=64))
 def prefix(m):return(m.memory,m.trace,m.calls,m.observations,m.r[16:24],m.r[28:31],m.f[20:])
 for c in cases:
  full=[]
  for path in paths:
   m=p.Oracle(p.words(path),p.fixture(c),c,connected=helpers if c.real_helpers else None);m.run();p.check(m,c);full.append(m)
  assert len({m.all_accesses for m in full})==1
  for cut in range(full[0].all_accesses):
   states=[]
   for path in paths:
    m=p.Oracle(p.words(path),p.fixture(c),c,connected=helpers if c.real_helpers else None);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing access boundary')
    states.append(prefix(m))
   assert states[0]==states[1]==states[2],(c,cut);count+=1
 r=dict(access_fault_triples=count,discriminating_cases=len(cases),all_memory_and_ordered_access_traces_equal=True,
  calls_observations_saved_GPR_and_FPR_equal=True,limits='Raw PCs, caller-volatile temporaries, cycle timing and internal return PCs are not equated; entry RA is checked on completion. FCSR and fault internals of the recursive provider extension are not modeled.',source_installed=packet.installed(),matching_credit=0)
 (out/'faults.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
