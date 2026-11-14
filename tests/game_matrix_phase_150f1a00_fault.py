"""Compare retail and guarded guest state at each fired access cut."""
from pathlib import Path
import json
from tools.tests import game_matrix_phase_150f1a00_guest as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-matrix-phase-150f1a00-durable'
guarded=g.candidate_words(out/'generated-guarded.o')
assert guarded==g.retail
cuts=0
for flags,phase,ticks,cosine,mutation in ((0,0,1,0.,0),(3,-32768,0xffffffff,1.,1),(12,32767,0x7fffffff,-1.,0),(15,-1,1,1.,1)):
 initial=g.fixture(flags,phase,ticks)
 good=g.Oracle(g.retail,initial.copy(),cosine,mutation).run()
 for cut in range(good.root_accesses):
  pair=[]
  for code in (g.retail,guarded):
   m=g.Oracle(code,initial.copy(),cosine,mutation);m.root_fault=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('ineffective access cut',cut))
   pair.append(m)
  assert complete(pair[0])==complete(pair[1]),(flags,cut)
  cuts+=1
report={'cases':4,'fault_prefixes':cuts,'guarded_equals_retail':True,'uncredited':True}
(out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
