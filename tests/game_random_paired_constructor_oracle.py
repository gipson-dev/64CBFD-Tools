import itertools,struct,sys
from pathlib import Path
from dataclasses import dataclass
from tools.experiments import game_random_paired_constructor_screen as packet
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
RNG=0x150ada20;RF=0x150ada68;FACTORY=0x151303bc;COPY=0x10022ec0;OWNER=0x30000;OUT=0x50000;ENTRY=0x150c60d8
@dataclass(frozen=True)
class Case:
 phase:int=0;owner:int=OWNER;success:int=1;seed:int=0

def program(path,name):
 t,fs,refs=parse_object(path);f=fs[name];a=f['value'];start=0x41c if name.endswith('60D8') else 0x45c
 return bound_blob(t[a:a+f['size']],{i-a:v for i,v in refs.items()if a<=i<a+f['size']},{**{f'D_800A{x:04X}':0x800a0000+x for x in range(start,start+32,4)},'func_150ADA20':RNG,'func_150ADA68':RF,'func_151303BC':FACTORY,'memcpy':COPY})
def fixture(c,name):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*23+0xa5)&255 for i in range(-2048,2048)}
 for base,n in ((OWNER,256),(OUT,512)):
  for i in range(n):m.setdefault(base+i,(i*19+c.seed*11+0x4a)&255)
 put(m,c.owner+0x60,bits(12.5))
 start=0x41c if name.endswith("60D8") else 0x45c
 for i,x in enumerate(range(start,start+32,4)):put(m,0x800a0000+x,bits((i+1)*0.125))
 return m
class Machine(FactoryOracle):
 def __init__(self,ws,c,m,name):
  self.c=c;self.rng=0;self.frng=0;super().__init__(ws,m,c,entry=int(name[5:],16),s={},arguments=(0,0,bits(3.5),bits(1.25),0x12345678,bits(-2.5),c.owner));self.f[12]=bits(1.5);self.f[14]=bits(-4.0)
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==7:
   self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
  else:super().execute(w)
 def record_call(self,t):
  if t==FACTORY:
   a=tuple(self.r[4:7]);snap=bytes(self.memory[a[0]+i] for i in range(112));self.calls.append((t,a,snap))
  elif t==COPY:
   a=tuple(self.r[4:7]);snap=bytes(self.memory[a[1]+i] for i in range(a[2]));self.calls.append((t,a,snap))
  else:
   assert t in (RNG,RF),hex(t);self.calls.append((t,(),()))
 def hook(self,t):
  if t==RNG:
   values=(0xffffffff,0,0xffffffff,100,0,5,123456789,0x80000000);value=values[(self.rng+self.c.seed)%len(values)];self.rng+=1
  elif t==RF:
   values=(0.0,0.25,0.5,0.75,1.0);value=bits(values[(self.frng+self.c.seed)%len(values)]);self.frng+=1
  elif t==FACTORY:
   value=OUT if self.c.success else 0
   if value:
    data=self.calls[-1][2]
    for i,b in enumerate(data):self.memory[OUT+0x10+i]=b
  else:
   assert t==COPY;a=self.calls[-1][1];data=self.calls[-1][2]
   for i,b in enumerate(data):self.memory[a[0]+i]=b
   value=a[0]
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
  if t==RF:self.f[0]=value
  else:self.r[2]=value

def observed(w,c,name,include_owner=False):
 m=Machine(w,c,fixture(c,name),name).run();home=STACK+c.phase
 public={a:v for a,v in m.memory.items() if not home-2048<=a<home+2048}
 owner=bytes(m.memory[c.owner+i] for i in range(128)) if include_owner else b''
 return public,m.calls,owner

def ordinary(state):
 result={}
 for name in state:
  raw=program(state[name]['after'],name);retail=program(state[name]['retail'],name);count=0
  for phase,success,seed in itertools.product((0,8),(0,1),range(5)):
   c=Case(phase=phase,success=success,seed=seed)
   assert observed(raw,c,name)==observed(retail,c,name),(name,c);count+=1
  result[name]=count
 return result

def aliases(state):
 result={}
 for name in state:
  raw=program(state[name]['after'],name);retail=program(state[name]['retail'],name);equal=0;different=[];call_diffs=[]
  for delta,success in itertools.product(range(-0x180,0x41,4),(0,1)):
   c=Case(owner=STACK+delta,success=success);a=observed(raw,c,name,True);b=observed(retail,c,name,True)
   if a==b:equal+=1
   else:
    different.append((delta,success))
    if a[1]!=b[1]:
     changed=[(i,[(j,x,y)for j,(x,y)in enumerate(zip(aa[2],bb[2])) if x!=y]) for i,(aa,bb) in enumerate(zip(a[1],b[1])) if aa!=bb]
     call_diffs.append((delta,success,changed))
  assert [(x[0],x[1])for x in call_diffs]==[(-268,1),(-260,1)],call_diffs
  assert all(x[2][0][0]==15 and [v[0]for v in x[2][0][1]]==[36,37] for x in call_diffs),call_diffs
  result[name]={'equal':equal,'different':len(different),'payload_differences':len(call_diffs)}
 return result
