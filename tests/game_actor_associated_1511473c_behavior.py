from tools.tests.game_actor_associated_1511473c_common import *
count=0
for index,n,v,scale,increment,flag,match,mode,has in itertools.product((-1,0,1),(-1,0,2),(0,32767,65535),(0.,0.5),(-1.5,0.,1.5),(0,1),(False,True),(0,1),(False,True)):
 m=fixture(index,n,v,scale,increment,flag,match,mode);want=model(m,index,n,mode,has);args=(actor if has else 0,index&0xffffffff);models=[]
 for label in ('retail','raw','guarded'):
  got=Oracle(programs[label],m.copy(),args,mode).run();assert public(got.memory)==want,(label,index,n,v,scale,increment,flag,match,mode,has);models.append(got)
  assert len(got.calls)==int(has and index<n)
 assert models[0].trace==models[1].trace==models[2].trace and models[0].r==models[2].r and models[0].f==models[2].f and models[0].fcsr==models[2].fcsr
 count+=1
print(json.dumps({'cases_per_stream':count,'streams':3,'model':'bounded finite IEEE single and modeled FCSR truncation','uncredited':True}),flush=True)
