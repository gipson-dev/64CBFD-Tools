"""Compare observable guest memory-fault prefixes."""
from tools.tests import game_owner_velocity_150d6cc4_oracle as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def states(ws,c):
 initial=g.fixture(c);full=g.Machine(ws,c,initial.copy()).run();seen=set()
 for cut in range(full.all_accesses):
  m=g.Machine(ws,c,initial.copy());m.cut=cut
  try:m.run();raise AssertionError(('no fault',cut))
  except AccessBoundary:pass
  changes=tuple(sorted((k,v)for k,v in g.public(m.memory).items()if initial.get(k)!=v));trace=tuple(e for e in m.trace if not g.STACK-512<=e[1]<g.STACK+512);seen.add((changes,tuple(m.calls),trace))
 return full.all_accesses,seen

def run(state):
    bodies=[g.words(state[x])for x in ('after','retail','generated')];total=0
    for word,identity,mutation in ((0,1,0),(1,0,0),(1,1,0),(1,1,3)):
     c=g.Case(0,word,identity,0x3f000000,2,0x3e800000,mutation,0);runs=[states(ws,c)for ws in bodies];assert runs[0][1]==runs[1][1]==runs[2][1],c;total+=sum(x[0]for x in runs)
    return {'cases':4,'fault_cuts':total,'scope':'external read/write and call prefixes'}
