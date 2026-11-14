from tools.tests.game_owner_chain_create_150c0ac0_common import *
copy_words=struct.unpack_from('>11I',(conker/'conker.us.bin').read_bytes(),0x22ec0);copy_code=dict(zip(range(COPY,COPY+44,4),copy_words));count=0
for n,flag,resource,mutation,delta in itertools.product((0,1,3,5),(0,2),(1,2),(0,1,2,3),(-0x18,0,4,0x20000)):
 c=Scenario(n,flag,resource,1,mutation,0xff,1,DESC,DESC+delta);m=fixture(c)
 if not flag and resource==2:continue
 want,calls,ret=reference(m,c);models=[]
 for name in ('retail','raw','guarded'):
  q=Oracle(programs[name],m.copy(),c,connected=copy_code).run();assert (public(q.memory),q.calls,q.r[2])==(want,calls,ret),(name,c);models.append(q)
 assert tr(models[0])==tr(models[1])==tr(models[2]);assert models[0].memory==models[1].memory==models[2].memory and models[0].r==models[1].r==models[2].r;count+=1
print(json.dumps(dict(cases_per_stream=count,original_memcpy_words=11,allocator_modeled=True,overlapping_copy_cases_included=True,uncredited=True)),flush=True)
