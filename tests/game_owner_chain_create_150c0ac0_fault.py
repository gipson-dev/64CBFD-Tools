from tools.tests.game_owner_chain_create_150c0ac0_common import *
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
copy_words=struct.unpack_from('>11I',(conker/'conker.us.bin').read_bytes(),0x22ec0);code=dict(zip(range(COPY,COPY+44,4),copy_words));count=0
cases=[Scenario(3,0,0,1,0),Scenario(3,0,2,1,0),Scenario(3,0,1,0,0),Scenario(0,0,1,1,0),Scenario(5,2,1,1,0),Scenario(5,2,1,1,3),Scenario(3,0,1,1,0,0xff,1,DESC,DESC),Scenario(3,2,0,1,1)]
for c in cases:
 m=fixture(c);done=Oracle(programs['retail'],m.copy(),c,connected=code)
 try:done.run()
 except (AssertionError,KeyError):pass
 for cut in range(done.all_accesses):
  states=[]
  for name in ('retail','raw','guarded'):
   q=Oracle(programs[name],m.copy(),c,connected=code);q.cut=cut
   try:q.run();raise AssertionError(('unreached cut',cut,c))
   except AccessBoundary:pass
   states.append((q.memory,q.r,q.f,q.hi,q.lo,q.calls,q.events,q.trace,q.current_pc,q.delay_of))
  assert states[0]==states[1]==states[2],(c,cut);count+=1
print(json.dumps(dict(fault_prefixes=count,streams=3,connected_original_memcpy=True,full_modeled_machine_state=True,uncredited=True)),flush=True)
