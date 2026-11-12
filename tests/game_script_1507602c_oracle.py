"""Bounded guest model for the path-duration command; helper is modeled."""
from dataclasses import dataclass
import itertools, math
from tools.experiments import game_script_1507602c_match as match
from tools.tests import test_game_point_interval_effect_match as g
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object

ENTRY=0x1507602c;HELPER=0x15075548;ACTORS=(0x30000,0x60000);TABLE=0x50000;PATHS=(0x51000,0x52000)
CURRENT=0x800d154c;NODES=0x800d2104;CMD=0x800d1891;FACTOR=0x8009a140
put,read,STACK=g.put,g.read,g.STACK
f=g.floating;b=g.bits

@dataclass(frozen=True)
class Case:
    actor:int;path:int;index:int;speed:float;phase:int
    mode:int=0;amount:int=0;fcsr:int=0x800004

def fixture(c):
    m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
    for a in ACTORS:
        m.update({a+i:(i*13+91)&255 for i in range(0x340)})
        put(m,a+0x13f,c.path,1);put(m,a+0x14,b(0.));put(m,a+0x1c,b(0.));put(m,a+0x24,b(2.))
    for base in PATHS:m.update({base+i:0 for i in range(32)})
    for path,(points) in enumerate((((17,23),(3,4),(30,40)),((31,47),(-6,-8),(-60,-80)))):
        for i,(x,z) in enumerate(points):put(m,PATHS[path]+i*8,x&65535,2);put(m,PATHS[path]+i*8+4,z&65535,2)
    for i,path in enumerate(PATHS):put(m,TABLE+4*i,path)
    put(m,NODES,TABLE);put(m,CURRENT,ACTORS[c.actor^1]);put(m,CMD,c.index,1);put(m,FACTOR,0x3daaaa7e)
    return m

def public(m):return {k:v for k,v in m.items() if not STACK-1024<=k<STACK+1024}

def reference(initial,c):
    m=dict(initial);actor=ACTORS[c.actor];put(m,CURRENT,actor);put(m,actor+0x44,b(c.speed))
    put(m,actor+0x21e,c.index,1)
    distance=(2. if c.path else 1.)*(50. if c.index else 5.)
    duration=f(b(2.*f(b(distance/c.speed))))
    if duration<12.:
        adjusted=f(b(c.speed*f(b(duration*f(read(m,FACTOR))))));put(m,actor+0x44,b(adjusted));duration=12.
    put(m,actor+0x21c,int(f(b(duration*100.)))&65535,2)
    put(m,actor+0x20,b(f(b(f(b(2.*duration))*0.5))))
    put(m,actor+0x223,4,1)
    return public(m)

class Oracle(g.Oracle):
    def __init__(self,code,c):
        self.case=c;super().__init__(code,fixture(c),c,entry=ENTRY);self.fcsr=0x800004
    def execute(self,w):
        op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if op==17 and rs in (2,6) or (op==17 and rs==16 and fn==36):AreaOracle.execute(self,w)
        elif op==17 and rs==16 and fn in (3,4):
            x=f(self.f[rd]);self.f[fd]=b(x/f(self.f[rt]) if fn==3 else math.sqrt(x));self.r[0]=0
        else:super().execute(w)
    def record_call(self,target):
        assert target==HELPER;self.calls.append((target,()))
    def hook(self,target):
        assert target==HELPER;put(self.memory,CURRENT,ACTORS[self.case.actor]);put(self.memory,ACTORS[self.case.actor]+0x44,b(self.case.speed))
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)]

def run(state):
    _,padded=match.pad_both(state)
    d,fs,rs=parse_object(padded);v=fs[match.NAME];a=v['value'];n=v['size'];refs={k-a:x for k,x in rs.items() if a<=k<a+n}
    syms={v[1]:v[2][1] for v in symbol_rows((match.ROOT/'conker/build/conker.us.elf').read_bytes())}
    codes=(state['raw_words'],state['retail_words'],tuple(bound_blob(d[a:a+n],refs,syms)))
    assert codes[0]==codes[1]==codes[2]
    cases=[Case(*x) for x in itertools.product(range(2),range(2),range(2),(.5,1.,2.,5.,10.,100.),(0,8))]
    visits=set()
    for c in cases:
        expected=reference(fixture(c),c)
        for code in codes:
            m=Oracle(code,c).run();assert public(m.memory)==expected,c
            assert m.calls==[(HELPER,())] and m.fcsr==0x800004 and m.r[29]==STACK+c.phase
            visits.update(m.visits)
    return dict(cases=len(cases),bodies=len(codes),words_visited=len(visits),scope='bounded finite values; modeled movement setup helper; FCSR exception flags not modeled')
