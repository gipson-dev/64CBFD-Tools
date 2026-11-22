"""Normalized full access prefixes and raw public-store boundary observations."""
from pathlib import Path
import json,sys
from tools.experiments import game_compact_sprite_update_15167e0c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_compact_sprite_update_15167e0c_guest as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
class Stores(g.Oracle):
 def __init__(self,*args,**kw):super().__init__(*args,**kw);self.store_snapshots=[]
 def put(self,p,v,n):
  super().put(p,v,n)
  if getattr(self,'own_instruction',False)and not g.STACK-2048<=p<g.STACK+512:self.store_snapshots.append((p,n,v&((1<<(8*n))-1),g.public(self.memory),self.calls[:],self.observations[:]))
def main():
 count=stores=0;cases=(g.Case(flags=2),g.Case(remaining=0,mode=258),g.Case(mode=16),g.Case(remaining=0,mode=32),g.Case(alias=2,flags=2),g.Case(index=-1,callback=False,completion=-1))
 allwords={k:g.words(v)for k,v in g.paths().items()}
 for c in cases:
  complete=[]
  for k,words in allwords.items():
   m=Stores(words,g.fixture(c),c);m.run();g.check(m,c);complete.append(m)
  assert complete[0].store_snapshots==complete[1].store_snapshots==complete[2].store_snapshots,c;stores+=len(complete[0].store_snapshots)
  assert complete[1].all_accesses==complete[2].all_accesses
  for cut in range(complete[1].all_accesses):
   states=[]
   for k in('padded','retail'):
    m=g.Oracle(allwords[k],g.fixture(c),c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing access boundary')
    states.append((m.memory,m.trace,m.calls,m.observations,m.r,m.f,m.hi,m.lo))
   assert states[0]==states[1],(c,cut);count+=1
 r=dict(normalized_full_access_prefix_pairs=count,raw_padded_retail_public_store_boundary_triples=stores,discriminating_cases=len(cases),normalized_full_memory_GPR_FPR_trace_and_HI_LO_equal=True,
  raw_all_public_store_states_and_ordered_calls_equal=True,source_installed=packet.installed(),matching_credit=0,
  limits='Raw load order and private flag home differ, so raw full access/GPR/private-byte fault identity is not claimed. Normalized/retail are compared at every access; raw public state is compared at every public store. No FCSR/timing/asynchronous or provider-internal fault model.')
 (out/'faults.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
