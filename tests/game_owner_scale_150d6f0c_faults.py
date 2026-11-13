"""Compare external-write and call prefixes at modeled memory faults."""
from tools.tests import game_owner_scale_150d6f0c_oracle as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def states(ws,c):
 initial=g.fixture(c);full=g.Machine(ws,c,initial.copy()).run();seen=set()
 for cut in range(full.all_accesses):
  m=g.Machine(ws,c,initial.copy());m.cut=cut
  try:m.run();raise AssertionError(('no fault',cut))
  except AccessBoundary:pass
  changes=tuple(sorted((k,v)for k,v in g.public(m.memory).items()if initial.get(k)!=v));writes=tuple(e for e in m.trace if e[0]=='W' and not g.STACK-512<=e[1]<g.STACK+512);seen.add((changes,tuple(m.calls),writes))
 return full.all_accesses,seen

def run(state):
    a,b,c=[g.words(state[x]) for x in ('after','retail','generated')];total=0
    for word,match,mutation in ((0,1,0),(1,0,0),(1,1,0),(1,1,3)):
     case=g.Case(0,word,match,0x3f800000,0x42c80000,0x3f800000,mutation,0);runs=[states(ws,case)for ws in(a,b,c)];assert runs[0][1]==runs[1][1]==runs[2][1],case;total+=sum(x[0]for x in runs)
    return {'cases':4,'fault_cuts':total,'scope':'external writes and calls; read order differs'}
