"""Non-finite modeled inputs and guest instruction-access fault prefixes."""
import itertools
from tools.tests import game_random_effect_pair_150d6388_oracle as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

def nonfinite(state):
    count=0
    for name,value,phase,mut in itertools.product(g.ENTRIES,
            (0,0x80000000,1,0x3f800000,0xbf800000,0x7f7fffff,0x7fc12345,0x7f800000,0xff800000),
            (0,8),(0,1,2,7)):
        c=g.Case(phase=phase,selector=0x123456a5,floats=(value,value,value),integer=0xffffffff,mutation=mut)
        initial=g.fixture(c);expected,calls,draws=g.reference(initial,name,c)
        for obj in (state['after'],state['retail'][name],state['generated']):
            m=g.Machine(g.words(obj,name),name,c,initial.copy()).run()
            assert(g.public(m.memory),m.calls,m.draws)==(expected,calls,draws),(name,c)
        count+=1
    return {'cases':count,'scope':'modeled non-finite inputs; not hardware FPU proof'}

def faults(state):
    total=0
    for name,mut in itertools.product(g.ENTRIES,(0,1,2,7)):
        c=g.Case(selector=0x123456a5,mutation=mut);initial=g.fixture(c)
        bodies=[g.words(obj,name)for obj in (state['after'],state['retail'][name],state['generated'])]
        full=g.Machine(bodies[0],name,c,initial.copy()).run()
        for cut in range(full.all_accesses):
            states=[]
            for ws in bodies:
                m=g.Machine(ws,name,c,initial.copy());m.cut=cut
                try:m.run();raise AssertionError(('no fault',cut))
                except AccessBoundary:pass
                states.append((m.memory,m.calls,m.draws,m.r,m.f,m.hi,m.lo))
            assert states[0]==states[1]==states[2],(name,c,cut);total+=3
    return {'cases':8,'fault_cuts':total,'scope':'modeled guest instruction-access cuts'}
