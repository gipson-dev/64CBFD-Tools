"""Check every fired retail and guarded guest access prefix in bounded cases."""
from pathlib import Path
import importlib.util,json
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-effect-config-1519c09c-durable'
from tools.tests import game_effect_config_1519c09c_guest as g
guarded=g.bound_blob(*g.payload(out/'generated-guarded.o','func_1519C09C'),g.symbols);assert guarded==g.retail
cuts=0
for vals,outcome,mutation,overlap in (((0.,-0.,1.75),0,0,0),((-10.75,42.9,-1.25),1,0,0),((123456.,-654321.,32767.75),1,1,1)):
 initial,position=g.fixture(vals,g.bits(-.75),overlap,1);params=(0x12340011,0x87650022,0xdead0033,0xbeef0044,0xcafe0055,0x34567890)
 good=g.Oracle(g.retail,initial.copy(),position,params,outcome,mutation).run()
 for cut in range(good.all_accesses):
  pair=[]
  for code in (g.retail,guarded):
   m=g.Oracle(code,initial.copy(),position,params,outcome,mutation);m.cut=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('ineffective access cut',cut))
   pair.append(m)
  assert complete(pair[0])==complete(pair[1]) and pair[0].trace==pair[1].trace,(vals,cut)
  cuts+=1
report={'cases':3,'fault_prefixes':cuts,'guarded_equals_retail':True,'uncredited':True}
(out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
