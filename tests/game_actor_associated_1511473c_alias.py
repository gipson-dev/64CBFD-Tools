from tools.tests.game_actor_associated_1511473c_common import *
# Point each record's float field into live actor or global storage.
def dynamic_model(m,index,mode):
 m=m.copy()
 if mode:put(m,actor+0x76,1234,2)
 val=read(m,actor+0x76,2);p=(read(m,sym('D_800DBEF4'))+index*0xa0+0x64)&0xffffffff;x=floating(read(m,p));scale=floating(read(m,sym('D_800A2F60')));result=floating(bits(float(val)+floating(bits(x*scale))))
 value=math.trunc(result) if -1<result<4294967296 else 0xffffffff
 put(m,actor+0x76,value,2)
 if m[actor+0x137] and read(m,sym('D_800CBDA0')+4,2)==index+1:put(m,actor+0x7a,value,2)
 return public(m)
count=0
for index,v,flag,mode,target in itertools.product((-1,0,1),(0,0x3f80,65535),(0,1),(0,1),(actor+0x74,actor+0x78,actor+0x134,sym('D_800DBEF0'),sym('D_800DBEF4'),sym('D_800A2F60'),sym('D_800CBDA0')+4)):
 m=fixture(index,2,v,0.5,0.,flag,True,mode);put(m,sym('D_800DBEF4'),target-index*0xa0-0x64);want=dynamic_model(m,index,mode);models=[]
 for label in ('retail','raw','guarded'):
  q=Oracle(programs[label],m.copy(),(actor,index&0xffffffff),mode).run();assert public(q.memory)==want,(index,v,flag,mode,hex(target),label);models.append(q)
 assert models[0].trace==models[1].trace==models[2].trace;count+=1
print(json.dumps(dict(cases_per_stream=count,overlapping_float_sources=7,access_traces_equal=True,uncredited=True)),flush=True)
