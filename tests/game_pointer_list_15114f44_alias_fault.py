from tools.tests.game_pointer_list_15114f44_common import *
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
count=faults=0
for target,flag,resume,mutation in itertools.product(('list','count','result','marker','mode','home'),(0,1),(False,True),(0,1,2,3)):
 if not resume and mutation:continue
 m=fixture(0x12,(1,1),flag);bases={'list':sym('D_800DBDD8'),'count':sym('D_800DBE18'),'result':sym('D_800DBF9C'),'marker':sym('D_8003C8E0'),'mode':sym('D_800BE9F0'),'home':STACK}
 addr=bases[target]
 for i in range(12):m.setdefault(addr+i,0x5a)
 for i,v in enumerate(args):put(m,STACK+4*i,v)
 put(m,sym('D_800DBDD8'),addr)
 want,calls,trap=model(m,args,resume,mutation);models=[]
 for label in ('retail','raw','guarded'):
  q=Oracle(programs[label],m.copy(),args,resume,mutation)
  try:q.run();observed=False
  except SyscallBoundary:observed=True
  assert (public(q.memory),len(q.calls),observed)==(want,calls,trap),(target,flag,resume,mutation,label)
  models.append(q)
 assert trace(models[0])==trace(models[1])==trace(models[2]);count+=1
for mode,counts,pattern,resume,mutation in [(0,(1,1),0,False,0),(0x12,(-1,1),0,False,0),(0x13,(3,1),1,False,0),(0x36,(3,1),10,True,1),(0x12,(3,3),10,True,2)]:
 m=fixture(mode,counts,pattern);done=Oracle(programs['retail'],m.copy(),args,resume,mutation)
 try:done.run()
 except SyscallBoundary:pass
 for cut in range(done.all_accesses):
  states=[]
  for label in ('retail','guarded'):
   q=Oracle(programs[label],m.copy(),args,resume,mutation);q.cut=cut
   try:q.run();raise AssertionError(('fault not reached',cut))
   except AccessBoundary:pass
   states.append((q.memory,q.r,q.f,q.hi,q.lo,q.calls,q.events,q.trace,q.current_pc,q.delay_of))
  assert states[0]==states[1];faults+=1
print(json.dumps(dict(alias_cases=count,aliased_locations=6,fault_prefixes=faults,original_guarded_complete_state=True,uncredited=True)),flush=True)
