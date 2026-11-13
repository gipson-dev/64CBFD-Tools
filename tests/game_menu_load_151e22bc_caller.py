"""Original caller window through its post-load state-store branch."""
from pathlib import Path
import importlib.util,itertools,json,struct,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-menu-load-151e22bc-durable'
from tools.tests import game_menu_load_151e22bc_guest as g
START=0x151e04e0;END=0x151e09c0;STATE=0x800e0a96
parent=list(struct.unpack_from('>5I',g.rom,0x20d990))
class Caller(g.Machine):
    def __init__(self,program,m,c):
        connected={g.ENTRY+4*i:w for i,w in enumerate(program)}
        FactoryOracle.__init__(self,parent,m,c,entry=START,s={},arguments=(),connected=connected)
        self.r[17]=0x55;self.code=WindowCode(self.code,self);self.code.ends=(END,)
    def record_call(self,t):
        if t==g.ENTRY:self.calls.append(t)
        else:super().record_call(t)
programs=[g.programs[0][0],g.programs[-1][0]];assert programs[0]==programs[1]
cases=0
for index,alias,value in itertools.product((-1,0,5,7,8,9),(0,-2,12),(-128,1)):
    c=g.Case(index,value,255,alias);initial,rec=g.fixture(c);initial[STATE]=0x83
    expected=g.reference(initial,c,rec);expected[STATE]=0x55
    for p in programs:
        m=Caller(p,initial.copy(),c)
        try:m.run()
        except WindowBoundary:pass
        else:raise AssertionError('Expected continuation boundary')
        public={a:v for a,v in m.memory.items() if not g.STACK-512<=a<g.STACK+512}
        assert public==expected and m.calls==[g.ENTRY,g.CALLEE],(c,m.calls)
    cases+=1
report={'caller':'func_151E0424','window_start':hex(START),'continuation':hex(END),
        'cases':cases,'streams':len(programs),'callee_modeled':True,'bounded_window_only':True,'uncredited':True}
(out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
