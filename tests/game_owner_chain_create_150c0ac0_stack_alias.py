from tools.tests.game_owner_chain_create_150c0ac0_common import *
statuses=[]
c=Scenario(count=3,flags=2,resource=0,allocate=1,mutation=0,desc=STACK-0x20,result=OUTPUT);m=fixture(c);models=[]
for name in ('retail','raw','guarded'):
 q=Oracle(programs[name],m.copy(),c)
 try:q.run();status='return'
 except (AssertionError,KeyError) as e:status='fault:'+str(e)[:60]
 statuses.append(status)
 print(name,'status',status,'result',hex(q.r[2]),'calls',q.calls,'flag',hex(q.memory[c.desc+0x18]),flush=True);models.append(q)
assert models[0].r==models[1].r==models[2].r and models[0].memory==models[1].memory==models[2].memory
assert tr(models[0])==tr(models[1])==tr(models[2])
assert statuses==["fault:('unmapped read', 255, 4)"]*3
print('private-stack overlap agrees across retail, direct C, and padded output',flush=True)
