"""Compare ordered memory/call/FCSR prefixes without equating differing PCs."""
from pathlib import Path
import json,sys
from tools.experiments import game_view_light_script_150ecc70_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_view_light_script_150ecc70_guest as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def main():
 cases=(g.Case(),g.Case(value=-2147483648,mode=7,phase=8),g.Case(replies=(0,0,0,0),mode=7),g.Case(enabled=0),g.Case(value=360),g.Case(value=1191,colors=(g.bits(4294967296.),)*3))
 count=0
 def prefix(m):return(m.memory,m.trace,m.calls,m.observations,m.fcsr,m.r[16:24],m.r[28:31])
 for c in cases:
  full=[g.check(ws,c)for ws in g.streams()];assert full[0].all_accesses==full[1].all_accesses
  for cut in range(full[0].all_accesses):
   pair=[]
   for ws in g.streams():
    m=g.Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing access boundary')
    except AccessBoundary:pass
    pair.append(prefix(m))
   assert pair[0]==pair[1],(c,cut);count+=1
 r=dict(access_fault_pairs=count,discriminating_cases=len(cases),all_memory_and_access_trace_equal=True,
  saved_registers_FCSR_and_calls_equal=True,limits='Raw PCs, internal call return addresses, caller-volatile GPR/FPR values and cycle timing are not equated; entry RA restoration is checked on completion.',source_installed=packet.installed(),matching_credit=0)
 (out/'faults.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
