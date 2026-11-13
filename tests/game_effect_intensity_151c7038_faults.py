"""Compare observable guest access-fault prefixes across the two bodies."""
from tools.tests import game_effect_intensity_151c7038_oracle as d
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

def states(ws,c):
    original=d.fixture(c);full=d.Machine(ws,c,original.copy()).run();seen=set()
    for cut in range(full.all_accesses):
        m=d.Machine(ws,c,original.copy());m.cut=cut
        try:m.run();raise AssertionError(('no fault',cut))
        except AccessBoundary:pass
        changes=tuple(sorted((k,v) for k,v in d.public(m.memory).items() if original.get(k)!=v))
        seen.add((changes,tuple(m.calls),tuple(d.external_trace(m))))
    return full.all_accesses,seen

def run(state):
    raw=d.words(state['after']);retail=d.words(state['retail']);padded=d.words(state['generated'])
    cuts=0;cases=0
    for kind,mutation in ((0xe9,0),(0xe9,3),(0xe8,0)):
        c=d.Case(0,kind,0x3f800000,0x12345678,1,mutation,0)
        before,observed=states(raw,c);after,expected=states(retail,c);third,actual=states(padded,c)
        assert observed==expected==actual,c
        cuts+=before+after+third;cases+=1
    return {'cases':cases,'fault_cuts':cuts,'scope':'guest instruction-order prefixes'}
