"""Compare original and guarded instruction streams at each guest access cut."""
from pathlib import Path
import importlib.util,json,sys
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-menu-load-151e22bc-durable'
from tools.tests import game_menu_load_151e22bc_guest as g
programs=[g.programs[0][0],g.programs[-1][0]];assert programs[0]==programs[1]
cuts=0
for c in (g.Case(0,1,0,0),g.Case(8,-128,255,-2),g.Case(9,0,5,12)):
    initial,_=g.fixture(c);good=g.Machine(programs[0],initial.copy(),c).run()
    for cut in range(good.all_accesses):
        models=[]
        for p in programs:
            m=g.Machine(p,initial.copy(),c);m.cut=cut
            try:m.run()
            except AccessBoundary:pass
            else:raise AssertionError(('ineffective cut',cut))
            models.append(m)
        assert complete(models[0])==complete(models[1]) and models[0].trace==models[1].trace,(c,cut)
        cuts+=1
report={'cases':3,'fault_prefixes':cuts,'guarded_equals_retail':True,'callee_modeled':True,
        'raw_c_fault_order_qualified':False,'uncredited':True}
(out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
