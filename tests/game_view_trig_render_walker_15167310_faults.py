"""Access prefixes: full normalized state; raw public state and measured frame."""
from pathlib import Path
import json,sys
from tools.experiments import game_view_trig_render_walker_15167310_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_view_trig_render_walker_15167310_guest as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def main():
 count=0;cases=(g.Case(shape=4),g.Case(shape=4,mode=8,depth=2),g.Case(count=-1,shape=2,mode=4))
 for c in cases:
  allwords={k:g.words(v)for k,v in g.paths().items()};full={}
  for k,words in allwords.items():
   m=g.Oracle(words,g.fixture(c),c);m.run();g.check(m,c);full[k]=m
  assert len({m.all_accesses for m in full.values()})==1
  for cut in range(full['raw'].all_accesses):
   states={}
   for k,words in allwords.items():
    m=g.Oracle(words,g.fixture(c),c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing access prefix')
    states[k]=m
   raw,pad,ret=[states[k]for k in('raw','padded','retail')]
   state=lambda m:(m.memory,m.trace,m.calls,m.observations,m.r,m.f,m.hi,m.lo)
   public_frame=lambda m:(m.memory,m.trace,m.calls,m.observations,m.f,m.r[28:30],m.hi,m.lo)
   assert state(pad)==state(ret),(c,cut,'Normalized full state')
   assert public_frame(raw)==public_frame(pad),(c,cut,'Raw public and frame state')
   count+=1
 r=dict(access_fault_triples=count,discriminating_cases=len(cases),padded_retail_full_GPR_FPR_memory_trace_equal=True,raw_public_memory_measured_frame_FPR_trace_equal=True,
  limits='Raw compiler temporary and descriptor-base registers differ; raw full-GPR fault identity is not claimed. Guest access boundaries only; no FCSR, asynchronous changes or helper faults.',source_installed=packet.installed(),matching_credit=0)
 (out/'faults.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
