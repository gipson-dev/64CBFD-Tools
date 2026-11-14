from tools.tests.game_owner_chain_create_150c0ac0_common import *
passed=0;faults=0
for delta,n,flag,mutation in itertools.product((-0x18,0,4),(0,1,3,5),(0,2),(0,1,2,3)):
 c=Scenario(n,flag,1,1,mutation,0xff,1,DESC,DESC+delta);m=fixture(c)
 try:want,calls,ret=reference(m,c);unmapped=False
 except (KeyError,AssertionError):unmapped=True
 models=[]
 for name in ('retail','raw','guarded'):
  q=Oracle(programs[name],m.copy(),c)
  try:q.run();qfault=False
  except (KeyError,AssertionError):qfault=True
  assert qfault==unmapped,(delta,n,flag,mutation,name,qfault,unmapped)
  if not qfault:assert (public(q.memory),q.calls,q.r[2])==(want,calls,ret),(delta,n,flag,mutation,name)
  models.append(q)
 assert tr(models[0])==tr(models[1])==tr(models[2]),(delta,n,flag,mutation)
 assert models[0].memory==models[2].memory and models[0].r==models[2].r
 if unmapped:faults+=1
 else:passed+=1
print(json.dumps(dict(overlapping_cases=passed+faults,normal=passed,unmapped_fault=faults,copy_provider='forward byte loop',uncredited=True)),flush=True)
