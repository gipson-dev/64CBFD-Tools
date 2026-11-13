"""Compare guarded retail guest state at each bounded access cut."""
from pathlib import Path
import importlib.util,json,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-settings-validator-151dd9e4-durable'
from tools.tests import game_settings_validator_151dd9e4_guest as g
cuts=0
for mode,index,value in ((0,0,0),(0,6,255),(1,16,128),(1,22,127)):
    initial=g.memory(index,value,mode);good=FactoryOracle(g.programs[0],initial.copy(),Case(),entry=g.entry,s={},arguments=()).run()
    for cut in range(good.all_accesses):
        pair=[]
        for p in (g.programs[0],g.programs[2]):
            m=FactoryOracle(p,initial.copy(),Case(),entry=g.entry,s={},arguments=());m.cut=cut
            try:m.run()
            except AccessBoundary:pass
            else:raise AssertionError(('ineffective cut',cut))
            pair.append(m)
        assert complete(pair[0])==complete(pair[1]) and pair[0].trace==pair[1].trace,(mode,index,value,cut)
        cuts+=1
report={'cases':4,'fault_prefixes':cuts,'guarded_equals_retail':True,'uncredited':True}
(out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
