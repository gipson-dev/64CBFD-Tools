"""Check that the callee may change globals subsequently loaded by retail."""
from tools.tests.game_actor_associated_1511473c_common import *
count=0
for index,flag,match,mode in itertools.product((-1,0,1),(0,1),(False,True),(2,3,4,5,6,7)):
 m=fixture(index,2,200,0.5,1.5,flag,match,mode)
 put(m,record+0x140+index*0xa0+0x64,bits(3.0))
 expected=m.copy()
 if mode&1:put(expected,actor+0x76,1234,2)
 if mode&2:put(expected,sym('D_800A2F60'),bits(2.0))
 if mode&4:put(expected,sym('D_800DBEF4'),record+0x140)
 current=read(expected,actor+0x76,2)
 pos=(read(expected,sym('D_800DBEF4'))+index*0xa0+0x64)&0xffffffff
 product=floating(bits(floating(read(expected,pos))*floating(read(expected,sym('D_800A2F60')))))
 result=math.trunc(floating(bits(float(current)+product)))
 put(expected,actor+0x76,result,2)
 if flag and match:put(expected,actor+0x7a,result,2)
 models=[]
 for label in ('retail','raw','guarded'):
  q=Oracle(programs[label],m.copy(),(actor,index&0xffffffff),mode).run()
  assert public(q.memory)==public(expected),(index,flag,match,mode,label)
  models.append(q)
 assert models[0].trace==models[1].trace==models[2].trace
 count+=1
assert count==72
print(json.dumps(dict(cases_per_stream=count,callee_mutates_record_pointer_and_scale=True,uncredited=True)),flush=True)
