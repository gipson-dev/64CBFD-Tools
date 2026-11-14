"""Compare fired access prefixes for retail and private guarded streams."""
import json
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.game_motion_crossing_150e6230_guest import *
cuts=0;counts=[]
for enabled,dotvalue,sign,selector,mutation in ((0,1.,1.,-1,0),(1,-1.,-1.,0,0),(1,-1.,1.,-1,0),(1,-1.,1.,0,0),(1,-1.,-1.,0,3)):
 initial=fixture(enabled,sign,selector,0);good=Oracle(truth,initial.copy(),dotvalue,mutation,0x1fe).run();counts.append(good.all_accesses)
 for cut in range(good.all_accesses):
  pair=[]
  for code in (truth,guarded):
   m=Oracle(code,initial.copy(),dotvalue,mutation,0x1fe);m.cut=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('ineffective access cut',cut))
   pair.append(m)
  assert complete(pair[0])==complete(pair[1]) and pair[0].trace==pair[1].trace
  cuts+=1
assert counts==[16,32,33,36,36] and cuts==153
report={'cases':len(counts),'per_case':counts,'fault_prefixes':cuts,'retail_equals_guarded':True,'uncredited':True}
(out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
