import itertools,struct,sys
from pathlib import Path
from dataclasses import dataclass
from tools.experiments import game_paired_ground_constructor_match as packet
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
TRANSFORM=0x15143134;QUERY=0x15045800;COLOR=0x151d8e20;RF=0x150ada68;RNG=0x150ada20;FACTORY=0x1513c73c;COPY=0x10022ec0
ACTOR=0x30000;CTX=0x48000;OUT=0x50000;MATRIX=0x60000;COLORS=0x800ab414
@dataclass(frozen=True)
class Case:
 phase:int=0;ctx:int=CTX;actor:int=ACTOR;matrix:int=0;hit:int=1;success:int=1;seed:int=0

def symbols(name):
 first=name.endswith('6460');p=0x43c if first else 0x47c
 return {'D_800887D0' if first else 'D_800887E0':0x800887d0 if first else 0x800887e0,f'D_800A{p:04X}':0x800a0000+p,f'D_800A{p+4:04X}':0x800a0000+p+4,'D_800AB414':COLORS,'func_15143134':TRANSFORM,'func_15045800':QUERY,'func_151D8E20':COLOR,'func_150ADA68':RF,'func_150ADA20':RNG,'func_1513C73C':FACTORY,'memcpy':COPY}
def program(path,name):
 t,fs,refs=parse_object(path);f=fs[name];a=f['value'];return bound_blob(t[a:a+f['size']],{i-a:r for i,r in refs.items()if a<=i<a+f['size']},symbols(name))
def fixture(c,name):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*31+0xa5)&255 for i in range(-2048,2048)}
 for base,n in ((ACTOR,1024),(CTX,512),(OUT,512),(MATRIX,128),(COLORS,768)):
  for i in range(n):m.setdefault(base+i,(i*29+c.seed*13+0x5a)&255)
 put(m,c.ctx+0x18,c.actor);put(m,c.actor+0x1d4,MATRIX if c.matrix else 0)
 for i,v in enumerate((1.25,4.5,-3.0)):put(m,c.actor+0x14+i*4,bits(v))
 s=symbols(name);start=s['D_800887D0' if name.endswith('6460') else 'D_800887E0']
 for i,v in enumerate((0.5,1.0,-0.5)):put(m,start+i*4,bits(v))
 for i,key in enumerate(x for x in s if x.startswith('D_800A0')):put(m,s[key],bits(0.25+i*.125))
 return m
class Machine(FactoryOracle):
 def __init__(self,ws,c,m,name):
  self.c=c;self.rng=0;self.first=name.endswith('6460');super().__init__(ws,m,c,entry=int(name[5:],16),s={},arguments=(c.ctx,))
 def record_call(self,t):
  counts={TRANSFORM:3,QUERY:4,COLOR:0,RF:0,RNG:0,FACTORY:14,COPY:3};assert t in counts,hex(t)
  a=tuple(self.arguments(counts[t]));snap=b''
  if t==TRANSFORM:snap=bytes(self.memory[a[0]+i] for i in range(12))
  if t==QUERY:snap=bytes(self.memory[a[0]+i] for i in range(12))
  if t==FACTORY:snap=bytes(self.memory[a[0]+i] for i in range(40))
  if t==COPY:snap=bytes(self.memory[a[1]+i] for i in range(a[2]))
  self.calls.append((t,a,snap))
 def hook(self,t):
  a=self.calls[-1][1];c=self.c
  if t==TRANSFORM:
   for i,v in enumerate((11.0,22.0,33.0)):put(self.memory,a[1]+i*4,bits(v))
   value=0
  elif t==QUERY:put(self.memory,a[3],bits(77.25));value=c.hit
  elif t==COLOR:value=3+c.seed
  elif t==RF:value=bits((c.seed%5)*.25)
  elif t==RNG:
   v=(0xffffffff,0,0x12345678);value=v[(self.rng+c.seed)%3];self.rng+=1
  elif t==FACTORY:value=OUT if c.success else 0
  else:
   assert t==COPY and a[2]==32;payload=self.calls[-1][2]
   for i,b in enumerate(payload):self.memory[a[0]+i]=b
   value=a[0]
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
  if t==RF:self.f[0]=value
  else:self.r[2]=value

def observe(ws,c,name,include=False):
 m=Machine(ws,c,fixture(c,name),name).run();home=STACK+c.phase
 public={a:v for a,v in m.memory.items()if not home-2048<=a<home+2048}
 return public,m.calls,m.r[2],(bytes(m.memory[c.ctx+i]for i in range(128)) if include else b''),(bytes(m.memory[c.actor+i]for i in range(512)) if include else b'')

def programs(state,name):
 ws=[program(state[name][label],name)for label in ('after','retail','generated','generic')];assert ws[1]==ws[2]==ws[3];return ws

def expected(c,name):
 from tools.tests.game_animation_timeline_oracle import floating
 home=STACK+c.phase;mem=fixture(c,name);d=home-0x54;p=home-0x74;index=3+c.seed
 for off,val,size in ((0,0x20300,4),(4,300,2),(6,0x38,1),(8,0,4),(12,16384,4),(16,150,1),(17,255,1),(21,255,1),(22,0,1),(23,6,1),(24,0x440001,4)):
  put(mem,d+off,val,size)
 for i in range(3):mem[d+18+i]=mem[COLORS+index*3+i]
 put(mem,p,c.ctx);mem[p+4]=1
 for off,val in ((8,.25),(12,32768.0),(16,0.0),(28,.375)):put(mem,p+off,bits(val))
 for off,val in ((20,0),(22,10),(24,10)):put(mem,p+off,val,2)
 point=(11.0,22.0,33.0)if c.matrix else (1.25,4.5,-3.0)
 scale=(100.0 if name.endswith('6460') else 200.0)+(50.0 if name.endswith('6460') else 100.0)*((c.seed%5)*.25)
 ints=[(0xffffffff,0,0x12345678)[(i+c.seed)%3]for i in range(3)]
 args=(home-0x54,8 if name.endswith('6460') else 9,2 if name.endswith('6460') else 3,c.ctx+0x38,bits(point[0]),bits(77.25),bits(point[2]),bits(scale),bits(scale),ints[0]&255,((ints[2]&1)<<1)+(ints[1]&1),32,mem[c.ctx+0xc],mem[c.ctx+1])
 return bytes(mem[d+i] for i in range(40)),bytes(mem[p+i]for i in range(32)),point,args

def ordinary(state):
 result={}
 for name in state:
  ws=programs(state,name);count=0
  for phase,matrix,hit,success,seed in itertools.product((0,8),(0,1),(0,1),(0,1),range(5)):
   c=Case(phase=phase,matrix=matrix,hit=hit,success=success,seed=seed);desc,payload,point,args=expected(c,name);states=[]
   for w in ws:
    m=Machine(w,c,fixture(c,name),name).run();home=STACK+phase
    q=next(x for x in m.calls if x[0]==QUERY);assert q==(QUERY,(home-0x2c,0,bits(point[1]-200.0),c.ctx+0x34),struct.pack('>III',bits(point[0]),bits(point[1]+200.0),bits(point[2])))
    calls=[x for x in m.calls if x[0]==FACTORY]
    if hit:
     assert calls==[(FACTORY,args,desc)],(name,c,'factory',calls,args)
     copies=[x for x in m.calls if x[0]==COPY]
     if success:
      assert copies==[(COPY,(OUT+0xb0,home-0x74,32),payload)] and m.r[2]==OUT,(name,c,'copy')
     else:assert not copies and m.r[2]==0
    else:assert not calls and m.r[2]==0
    public={a:v for a,v in m.memory.items()if not home-2048<=a<home+2048};states.append((public,m.calls,m.r[2]))
   assert states.count(states[0])==4,(name,c);count+=1
  result[name]=count
 return result

def observe_stop(w,c,name):
 m=Machine(w,c,fixture(c,name),name);exception=''
 try:m.run()
 except (AssertionError,KeyError) as e:
  if not (str(e).startswith("('saved register',") or str(e).startswith("('unowned jump',") or str(e).startswith("('unmapped read',") or isinstance(e,KeyError)):raise
  exception=type(e).__name__+':'+str(e)
 home=STACK+c.phase;public={a:v for a,v in m.memory.items()if not home-2048<=a<home+2048}
 span=lambda base,n:tuple(m.memory.get(base+i)for i in range(n))
 return exception,public,m.calls,span(c.ctx,128),span(c.actor,512)

def aliases(state):
 report={}
 for name in state:
  ws=programs(state,name);count=0;faults=0
  for role,delta,matrix,hit,success in itertools.product(('ctx','actor'),range(-0x180,0x41,4),(0,1),(0,1),(0,1)):
   c=Case(matrix=matrix,hit=hit,success=success,**{role:STACK+delta});states=[observe_stop(w,c,name)for w in ws]
   assert states.count(states[0])==4,(name,c,[(x[0],len(x[2]))for x in states]);faults+=bool(states[0][0]);count+=1
  report[name]={'cases':count,'incomplete':faults}
 return report
