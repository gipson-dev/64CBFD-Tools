"""Original registered-update caller window through its next-node boundary."""
from pathlib import Path
import importlib.util,itertools,json,struct,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-linked-effect-151d2c40-durable'
from tools.tests import game_actor_linked_effect_151d2c40_guest as g
START=0x15167164;END=0x1516719c;DESCRIPTOR=0x8008c10c;DEPTH=0x800dd190;NEXT=0x800dd198
assert DESCRIPTOR==0x8008b4a8+0x3d*0x34 and struct.unpack_from('>I',g.rom,0x230bcc)[0]==g.ENTRY
parent=list(struct.unpack_from('>14I',g.rom,0x194614))
class Caller(g.Machine):
    def __init__(self,program,m,c):
        connected={g.ENTRY+4*i:w for i,w in enumerate(program)}
        FactoryOracle.__init__(self,parent,m,c,entry=START,s={},arguments=(),connected=connected)
        self.r[16]=g.EFFECT;self.r[17]=NEXT+4;self.r[18]=DESCRIPTOR;self.r[19]=DEPTH;self.r[20]=NEXT
        self.code=WindowCode(self.code,self);self.code.ends=(END,)
    def record_call(self,t):
        if t==g.ENTRY:self.calls.append((t,(self.r[4],)))
        else:super().record_call(t)
programs=[list(struct.unpack_from('>91I',g.rom,0x2000f0)),bound_blob(*payload(out/'guarded.o','func_151D2C40'),g.symbols)]
assert programs[0]==programs[1]
cases=0
for gate,flags,answer,phase in itertools.product(range(6),(0,1),(0,1),(0,8)):
    c=g.Case(gate,flags,0,1,0,1,answer,0,phase);initial=g.fixture(c)
    initial[DEPTH]=1
    for i in range(16):initial[NEXT+i]=0xa5
    g.put(initial,DESCRIPTOR,g.ENTRY);g.put(initial,g.EFFECT+8,0)
    expected,calls=g.reference(initial,c);g.put(expected,NEXT+4,0);expected[DEPTH]=0
    for p in programs:
        m=Caller(p,initial.copy(),c)
        try:m.run()
        except WindowBoundary:pass
        else:raise AssertionError('Expected registered-list continuation')
        assert g.public(m.memory)==expected and m.calls==[(g.ENTRY,(g.EFFECT,))]+calls,(c,m.calls,calls)
    cases+=1
report={'caller':'func_151670C0','descriptor_index':0x3d,'descriptor':hex(DESCRIPTOR),
        'window_start':hex(START),'continuation':hex(END),'cases':cases,'streams':2,
        'helpers_modeled':True,'bounded_window_only':True,'uncredited':True}
(out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
