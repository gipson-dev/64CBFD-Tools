"""Compare fired access cuts for the identical retail and C guest streams."""
from pathlib import Path
import importlib.util,json
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-linked-effect-constructor-151ceaac-durable'
from tools.tests import game_linked_effect_constructor_151ceaac_guest as g
assert g.retail==g.candidate
cuts=0
for owner,attachment,mode,success,mutation in ((g.OWNER,0,0,0,0),(0,g.ATTACH,1,1,0),(g.OWNER,g.ATTACH,255,1,1)):
 initial=g.fixture(1);args=(owner,attachment,mode,0xab,0x87654321,success,mutation)
 good=g.Oracle(g.retail,initial.copy(),*args).run()
 for cut in range(good.all_accesses):
  pair=[]
  for code in (g.retail,g.candidate):
   m=g.Oracle(code,initial.copy(),*args);m.cut=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('ineffective access cut',cut))
   pair.append(m)
  assert complete(pair[0])==complete(pair[1]) and pair[0].trace==pair[1].trace,(owner,cut)
  cuts+=1
report={'cases':3,'fault_prefixes':cuts,'retail_equals_c':True,'uncredited':True}
(out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
