"""Compare every modeled guest memory-access prefix of retail and guarded code."""
from pathlib import Path
import importlib.util, json, sys
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-line-record-1512dd50-durable'
from tools.tests import game_line_record_1512dd50_guest as g
programs = [bound_blob(*payload(out/p, 'func_1512DD50'), {'func_150AD930':g.HELPER})
            for p in ('retail.o','explicit-padded.o')]
assert programs[0] == programs[1]
cuts = 0
for case in (g.Case((1,-2,3),3,(.5,1.,2.,-.25),0x80000081,0xffffffff,0xe1),
             g.Case((-32768,32767,-1),-2,(-1.25,.75,-.5,2.),0,0x7fffffff,0x14,8)):
    initial = g.fixture(case)
    good = g.Machine(programs[0],initial.copy(),case).run()
    for cut in range(good.all_accesses):
        models = []
        for program in programs:
            m = g.Machine(program,initial.copy(),case)
            m.cut = cut
            try:
                m.run()
            except AccessBoundary:
                pass
            else:
                raise AssertionError(('ineffective cut',cut))
            models.append(m)
        assert complete(models[0]) == complete(models[1]) and models[0].trace == models[1].trace, cut
        cuts += 1
report = {'cases':2,'fault_prefixes':cuts,'connected_retail_helper':True,
          'raw_candidate_fault_order_compared':False,'guest_model_not_hardware':True}
(out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n')
print(report,flush=True)
