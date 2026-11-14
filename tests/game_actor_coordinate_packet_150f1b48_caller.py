"""Execute the original actor-type dispatch call window and returned cursor."""
from pathlib import Path
import importlib.util,itertools,json,struct,sys
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-coordinate-packet-150f1b48-durable'
from tools.tests import game_actor_coordinate_packet_150f1b48_guest as g
programs=[g.programs[0],bound_blob(*payload(out/'generated-guarded.o','func_150F1B48'),g.symbols)]
assert programs[0]==programs[1]
start,end=0x15034114,0x15034120;window=list(struct.unpack_from('>3I',g.rom,start-0x15000000+0x2d4b0))
class Caller(FactoryOracle):
    def __init__(self,program,m,output,slot):
        connected={g.entry+4*i:w for i,w in enumerate(program)};connected[end]=0
        super().__init__(window,m,Case(),entry=start,s={},arguments=(),connected=connected)
        self.r[5]=slot;self.r[6]=output;self.code=WindowCode(self.code,self);self.code.ends=(end,)
    def record_call(self,t):
        assert t==g.entry;self.calls.append((t,self.r[4],self.r[5]))
cases=0
for slot,value,dt,active,offset in itertools.product(range(4),(-32768,0,32767),(0,1,0xffffffff),(0,1),(None,0,18)):
    output=g.separate if offset is None else g.state+offset;initial=g.fixture(slot,value,dt,active,output);expected=g.reference(initial,slot,output)
    for p in programs:
        machine=Caller(p,initial.copy(),output,slot)
        try:machine.run()
        except WindowBoundary:pass
        else:raise AssertionError('Expected dispatcher continuation')
        assert machine.memory==expected and machine.r[16]==output+24
        assert machine.calls==[(g.entry,output,slot)]
    cases+=1
report={'caller':'func_15033FE0','call_site':'0x15034114','cases':cases,'streams':2,'bounded_window_only':True,'uncredited':True}
(out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
