"""Compare modeled access-prefix faults for retail and guarded code."""
import json
from tools.tests import game_height_emitter_150e971c_guest_screen as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
cuts=0;counts=[]
for height,flag,mutation in ((-5.,10,0),(-5.,10,2),(11.,10,0),(-5.,9,0),(10.,10,1)):
 initial=g.fixture(height,flag,0);good=g.Oracle(g.truth,initial.copy(),mutation).run();counts.append(good.all_accesses)
 for cut in range(good.all_accesses):
  pair=[]
  for code in (g.truth,g.guarded):
   m=g.Oracle(code,initial.copy(),mutation);m.cut=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('ineffective access cut',cut))
   pair.append(m)
  assert complete(pair[0])==complete(pair[1]) and pair[0].trace==pair[1].trace
  cuts+=1
assert counts==[43,43,6,7,43] and cuts==142
report={'cases':len(counts),'per_case':counts,'fault_prefixes':cuts,'retail_equals_guarded':True,'uncredited':True}
(g.out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
