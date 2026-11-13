from pathlib import Path
from importlib.machinery import SourceFileLoader
import itertools
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests import game_state_trajectory_15072f10_oracle as G

def run():
 programs=G.programs();cuts=0;private=0
 for pitch,timer,mutation,output in itertools.product((-128,127),(-32768,0),(0,7),(0,1)):
  c=G.Case(pitch=pitch,timer=timer,angle=0xffff,offset=-23,mutation=mutation,output=output);initial=G.fixture(c);full=G.Machine(programs[0],c,initial.copy()).run()
  for cut in range(full.all_accesses):
   machines=[]
   for w in programs:
    m=G.Machine(w,c,initial.copy());m.cut=cut
    try:m.run();raise AssertionError(('missing cut',cut))
    except AccessBoundary:pass
    machines.append(m)
   retail=machines[0];assert all((m.memory,m.calls,m.trace)==(retail.memory,retail.calls,retail.trace)for m in machines[2:]),(c,cut,'padded')
   assert (G.public(machines[1].memory,c),machines[1].calls)==(G.public(retail.memory,c),retail.calls),(c,cut,'raw')
   private+=machines[1].memory!=retail.memory;cuts+=1
 print('cases',16,'access cuts',cuts,'raw private differences',private)
