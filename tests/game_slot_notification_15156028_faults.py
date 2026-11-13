from pathlib import Path
import itertools,runpy,sys
from tools.experiments.game_slot_notification_15156028_match import ROOT as root, OUT as out
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
g=runpy.run_module('tools.tests.game_slot_notification_15156028_guest');Machine=g['Machine'];fixture=g['fixture'];programs=(g['retail'],g['padded']);count=0
def state(m):return(m.memory,m.r,m.f,m.trace,m.events,m.calls,m.current_pc,m.delay_of,m.all_accesses)
for first,second,tag,kind,phase,alias in itertools.product((-811,0,25*812),(0,812),(0,1,255),(0,45,2),(0,8),(0,1,2)):
 initial,args=fixture(first,second,tag,kind,phase,alias);good=Machine(programs[0],initial,args,phase).run()
 for cut in range(good.all_accesses):
  pair=[]
  for program in programs:
   m=Machine(program,initial,args,phase);m.cut=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('missing fault',first,second,tag,kind,phase,alias,cut))
   assert m.all_accesses==cut;pair.append(m)
  assert state(pair[0])==state(pair[1]),(first,second,tag,kind,phase,alias,cut);count+=1
print(count,'matched retail and padded guest access-fault prefixes; instruction boundary model only',flush=True)
