from tools.tests.game_actor_associated_1511473c_common import *
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
# Probe exceptional values under this explicitly modeled FCSR rule.
special=[0x00000000,0x80000000,0x00000001,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc12345,0x4effffff,0x4f000000,0x4f7fffff,0x4f800000,0xbf7fffff,0xbf800000]
for b in special:
 m=fixture(0,1,0,1.,0.,1,True,0);put(m,record+0xa0+0x64,b)
 for label in ('retail','raw','guarded'):
  q=Oracle(programs[label],m.copy(),(actor,0)).run();assert public(q.memory)==model(m,0,1,0,True),(hex(b),label)
# Compare complete retail and normalized machine state at each modeled access fault.
faults=0
for index,n,flag,match,has in [(-1,0,1,True,True),(0,1,1,True,True),(0,1,1,False,True),(0,1,0,True,True),(0,0,1,True,True),(0,1,1,True,False)]:
 m=fixture(index,n,65535,0.5,1.5,flag,match,1);args=(actor if has else 0,index&0xffffffff)
 done=Oracle(programs['retail'],m.copy(),args,1).run()
 for cut in range(done.all_accesses):
  snapshots=[]
  for label in ('retail','guarded'):
   q=Oracle(programs[label],m.copy(),args,1);q.cut=cut
   try:q.run();raise AssertionError(('untriggered',cut))
   except AccessBoundary:pass
   snapshots.append((q.memory,q.r,q.f,q.fcsr,q.hi,q.lo,q.calls,q.events,q.trace,q.current_pc,q.delay_of))
  assert snapshots[0]==snapshots[1],cut;faults+=1
print(json.dumps(dict(exceptional_patterns=len(special),fault_prefixes=faults,scope='modeled FCSR and retail/guarded literal streams',uncredited=True)),flush=True)
