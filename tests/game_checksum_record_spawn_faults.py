import itertools
from pathlib import Path
from tools.tests import game_checksum_record_spawn_oracle as g
from tools.experiments import game_checksum_record_spawn_match as packet
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def run():
 O=packet.OUT;programs=[g.words(O/(x+'.o'))for x in ('retail','after','generated','generic')];cuts=0;private=0
 for owner,count,fail,mismatch in itertools.product((0,g.OWNER),(0,2),(0,9),(0,1)):
  c=g.Case(owner=owner,count=count,fail=fail,mismatch=mismatch);full=g.Machine(programs[0],c).run()
  for cut in range(full.all_accesses):
   machines=[]
   for w in programs:
    m=g.Machine(w,c);m.cut=cut
    try:m.run();raise AssertionError(('missing cut',c,cut))
    except AccessBoundary:pass
    machines.append(m)
   retail=machines[0]
   assert all((m.memory,m.calls,m.trace)==(retail.memory,retail.calls,retail.trace)for m in machines[2:]),(c,cut,'padded')
   public=lambda m:{a:v for a,v in m.memory.items()if not g.STACK-2048<=a<g.STACK+2048}
   assert (public(machines[1]),machines[1].calls)==(public(retail),retail.calls),(c,cut,'raw public')
   private+=machines[1].memory!=retail.memory;cuts+=1
 print('cases',16,'access cuts',cuts,'raw private differences',private)
