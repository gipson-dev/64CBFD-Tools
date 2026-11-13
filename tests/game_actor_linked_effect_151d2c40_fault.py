"""Compare retail/guarded memory-access fault prefixes in bounded guest runs."""
from pathlib import Path
import importlib.util,json,struct,sys
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-linked-effect-151d2c40-durable'
from tools.tests import game_actor_linked_effect_151d2c40_guest as g
programs=[list(struct.unpack_from('>91I',g.rom,0x2000f0)),bound_blob(*payload(out/'guarded.o','func_151D2C40'),g.symbols)]
assert programs[0]==programs[1]
cases=[g.Case(1,0,0,0,-1,-1,0,0),g.Case(0,1,0,1,0,1,1,0),
       g.Case(0,0,0,0,1,-1,0,0),g.Case(0,0,0,0,-1,-1,1,2,8)]
cuts=0
for c in cases:
    initial=g.fixture(c);good=g.Machine(programs[0],initial.copy(),c).run()
    for cut in range(good.all_accesses):
        pair=[]
        for p in programs:
            m=g.Machine(p,initial.copy(),c);m.cut=cut
            try:m.run()
            except AccessBoundary:pass
            else:raise AssertionError(('ineffective cut',c,cut))
            pair.append(m)
        assert complete(pair[0])==complete(pair[1]) and pair[0].trace==pair[1].trace,(c,cut)
        cuts+=1
report={'cases':len(cases),'fault_prefixes':cuts,'guarded_equals_retail':True,
        'helpers_modeled':True,'raw_c_fault_order_qualified':False,'uncredited':True}
(out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
