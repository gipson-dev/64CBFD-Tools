from tools.tests.game_impact_random_151ac408_oracle import *
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def run():
 streams=programs();cuts=0
 for c in (Case(0,-2,0,0,0,0,0),Case(8,2,255,1,0xffffffff,7,2),Case(0,0,127,0,40,3,3),Case(8,2,128,1,41,1,4)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   results=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError(('missing cut',c,cut))
    except AccessBoundary:pass
    results.append(m)
   a=results[0];assert all((m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace)==(a.memory,a.r,a.f,a.hi,a.lo,a.condition,a.trace) for m in results[1:]),(c,cut);cuts+=1
 print('retail and C streams:',cuts,'access-boundary prefixes across four cases',flush=True)
