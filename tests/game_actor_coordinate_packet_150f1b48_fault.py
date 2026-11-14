"""Compare retail/guarded guest memory-access fault prefixes."""
from pathlib import Path
import importlib.util,json,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-coordinate-packet-150f1b48-durable'
from tools.tests import game_actor_coordinate_packet_150f1b48_guest as g
programs=[g.programs[0],bound_blob(*payload(out/'generated-guarded.o','func_150F1B48'),g.symbols)];assert programs[0]==programs[1]
cuts=0
for slot,value,dt,active,offset in ((0,0,1,0,None),(1,-32768,0xffffffff,1,None),(2,5461,2,0,18),(3,-6554,1,1,12)):
    output=g.separate if offset is None else g.state+offset;initial=g.fixture(slot,value,dt,active,output);args=(output,slot)
    good=FactoryOracle(programs[0],initial.copy(),Case(),entry=g.entry,s={},arguments=args).run()
    for cut in range(good.all_accesses):
        pair=[]
        for p in programs:
            m=FactoryOracle(p,initial.copy(),Case(),entry=g.entry,s={},arguments=args);m.cut=cut
            try:m.run()
            except AccessBoundary:pass
            else:raise AssertionError(('ineffective access cut',cut))
            pair.append(m)
        assert complete(pair[0])==complete(pair[1]) and pair[0].trace==pair[1].trace,(slot,cut)
        cuts+=1
report={'cases':4,'fault_prefixes':cuts,'guarded_equals_retail':True,'uncredited':True}
(out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
