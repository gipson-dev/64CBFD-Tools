"""Compare every fired guest memory-access prefix for both instruction streams."""
import json
from tools.tests import game_actor_effect_dispatch_150b3ab0_guest as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
cuts=0
for active,mutation in ((0,0),(1,0),(2,0),(2,1)):
 actor=0 if active==0 else g.ACTOR; frame=g.FRAME if active==2 else 0
 initial=g.fixture(1,frame);args=(actor,0x123400ff,mutation,(0xffffffff,15,3))
 good=g.Oracle(g.truth,initial.copy(),*args).run()
 for cut in range(good.all_accesses):
  pair=[]
  for code in (g.truth,g.candidate):
   m=g.Oracle(code,initial.copy(),*args);m.cut=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('ineffective access cut',cut))
   pair.append(m)
  assert complete(pair[0])==complete(pair[1]) and pair[0].trace==pair[1].trace and pair[0].records==pair[1].records,(active,mutation,cut)
  cuts+=1
report={'cases':4,'fault_prefixes':cuts,'retail_equals_c':True,'uncredited':True}
(g.out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
