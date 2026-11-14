"""Compare fired access prefixes for retail and privately guarded bodies."""
import json
from tools.tests import game_timed_motion_150f48d0_guest as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
guarded=bound_blob(*payload(g.out/'guarded.o','func_150F48D0'),g.syms);assert guarded==g.truth
cuts=0
for actor,timer,tick,mutation in ((g.NORMAL,0.,2.,0),(g.NORMAL,12.,.5,1),(g.TICK-0x20,12.,.5,0),(g.TICK-0x44,12.,.5,1)):
 initial=g.fixture(actor,timer,tick,0);good=g.Oracle(g.truth,initial.copy(),actor,mutation).run()
 for cut in range(good.all_accesses):
  pair=[]
  for words in (g.truth,guarded):
   m=g.Oracle(words,initial.copy(),actor,mutation);m.cut=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('ineffective access cut',cut))
   pair.append(m)
  assert complete(pair[0])==complete(pair[1]) and pair[0].trace==pair[1].trace
  cuts+=1
report={'cases':4,'fault_prefixes':cuts,'retail_equals_guarded':True,'uncredited':True}
(g.out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
