from tools.tests.game_pointer_list_15114f44_common import *
args=(0x11223344,0x55667788,0x99aabbcc);count=0;traps=0
for mode,n0,n1,pattern,resume,mutate in itertools.product((0,0x12,0x13,0x36,0x37),(-1,0,1,3),(-1,0,1,3),range(11),(False,True),(0,1,2,3)):
 if not resume and mutate:continue
 m=fixture(mode,(n0,n1),pattern);want,calls,trap=model(m,args,resume,mutate);models=[]
 for label in ('retail','raw','guarded'):
  q=Oracle(programs[label],m.copy(),args,resume,mutate)
  try:q.run();observed=False
  except SyscallBoundary:observed=True
  assert (public(q.memory),len(q.calls),observed)==(want,calls,trap),(label,mode,n0,n1,pattern,resume,mutate,[(hex(k),public(q.memory).get(k),want.get(k)) for k in set(public(q.memory))|set(want) if public(q.memory).get(k)!=want.get(k)][:12],len(q.calls),calls,observed,trap,q.trace[-15:],q.r[:16])
  models.append(q)
 assert trace(models[0])==trace(models[1])==trace(models[2]),(mode,n0,n1,pattern,resume,mutate)
 assert models[0].memory==models[2].memory and models[0].r==models[2].r
 count+=1;traps+=int(trap)
print(json.dumps(dict(cases_per_stream=count,trapped_cases=traps,streams=3,real_syscall_entry_executed_to_boundary=True,synthetic_resume_cases=True,uncredited=True)),flush=True)
