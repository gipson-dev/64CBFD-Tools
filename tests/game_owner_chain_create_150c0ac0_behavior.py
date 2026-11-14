from tools.tests.game_owner_chain_create_150c0ac0_common import *
count=0
for n,flag,resource,allocation,mutation,slot in itertools.product((-32768,-2,-1,0,1,3,5,20),(0,2),(0,1,2),(0,1),(0,1,2,3),(0xff,0x12345680)):
 if flag and not resource and allocation and mutation&1:continue
 c=Scenario(n,flag,resource,allocation,mutation,slot);m=fixture(c);want,calls,ret=reference(m,c);models=[]
 for name in ('retail','raw','guarded'):
  q=Oracle(programs[name],m.copy(),c).run();assert (public(q.memory),q.calls,q.r[2])==(want,calls,ret),(name,c,q.calls,calls,hex(q.r[2]),hex(ret));models.append(q)
 assert tr(models[0])==tr(models[1])==tr(models[2]),c
 assert models[0].memory==models[2].memory and models[0].r==models[2].r
 count+=1
print(json.dumps(dict(cases_per_stream=count,streams=3,descriptor_flags_counts_slots_and_allocator_mutations=True,uncredited=True)),flush=True)
