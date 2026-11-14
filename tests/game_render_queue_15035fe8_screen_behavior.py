from pathlib import Path
from dataclasses import dataclass
import itertools,json,random,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,HELPER,COUNT,QUEUE,OUTPUT=0x15035fe8,0x1502ccfc,0x800c3f00,0x800c3f08,0x50000
SYMS=dict(D_800C3F00=COUNT,D_800C3F08=QUEUE,func_1502CCFC=HELPER)
@dataclass(frozen=True)
class Case:
 count:int=3
 skip:int=0
 mutation:int=0
 phase:int=0
 seed:int=0
 view:int=7
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,768)}
 m.update({COUNT+i:0 for i in range(0,8+12*6)})
 m.update({OUTPUT+i:0x5a for i in range(-8,256)})
 m[COUNT]=c.count
 for i in range(6):
  p=QUEUE+i*12;put(m,p,0x20000+i*0x100)
  for j,v in enumerate((20+i,30+i,40+i,50+i,60+i,0,0,1 if c.skip>>i&1 else 0)):m[p+4+j]=v
 return m
def mutate(m,c,n):
 if n==0 and c.mutation==1:m[COUNT]=1
 if n==0 and c.mutation==2:m[COUNT]=6
 if n==0 and c.mutation==3:m[COUNT]=0
def reference(initial,c):
 m=dict(initial);p=OUTPUT;calls=[];params=[]
 if m[COUNT]:
  for off,v in ((4,0x00200004),(0,0xd9ffffff),(8,0xd9eeffff),(12,0),(16,0xe2001e01),(20,0)):put(m,p+off,v)
  p+=24;n=m[COUNT];i=0
  while i<n:
   q=QUEUE+i*12
   if not m[q+11]:
    args=(p,m[q+8],c.view,read(m,q),m[q+4],0,1);param=(m[q+5],m[q+6],m[q+7],255)
    calls.append(args);params.append(param);put(m,p,0xabc00000+i);put(m,p+4,0xdef00000+i);p+=8;mutate(m,c,len(calls)-1);n=m[COUNT]
   i+=1
 return m,calls,params,p
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c):
  self.observed=[];super().__init__(words,initial,c,entry=ENTRY,s=SYMS,arguments=(OUTPUT,c.view));self.before_f=self.f[:]
 def record_call(self,t):
  assert t==HELPER;args=tuple(self.arguments(8));self.calls.append((t,args));self.events.append(('CALL',t,args))
  self.observed.append(tuple(read(self.memory,args[5]+i*4) for i in range(4)))
 def hook(self,t):
  assert t==HELPER;a=self.calls[-1][1];i=(a[3]-0x20000)//0x100
  put(self.memory,a[0],0xabc00000+i);put(self.memory,a[0]+4,0xdef00000+i);mutate(self.memory,self.case,len(self.calls)-1)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=a[0]+8
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+768}
def trace(m):return tuple(x for x in m.trace if not STACK-512<=x[1]<STACK+768)
def normalized_calls(m):return [(a[0],a[1],a[2],a[3],a[4],a[6],a[7]) for t,a in m.calls]
def run():
 root=Path.cwd();out=root/'conker/build/game-render-queue-15035fe8-screen';rom=(root/'conker/conker.us.bin').read_bytes();truth=struct.unpack_from('>88I',rom,0x63498)
 symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
 raw=bound_blob(*payload(out/'v7-2.o','func_15035FE8'),symbols);programs=(truth,raw);count=trace_differences=param_address_differences=0
 for n,skip,mutation,phase in itertools.product(range(7),(0,0x15,0x2a,0x3f),range(4),(0,8)):
  c=Case(n,skip,mutation,phase,seed=n+skip);initial=fixture(c);want,calls,params,result=reference(initial,c);pair=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run()
   assert (public(m.memory),normalized_calls(m),m.observed,m.r[2])==(public(want),calls,params,result),c
   assert m.r[29]==m.before[29] and all(m.r[i]==m.before[i] for i in (*range(16,24),28,30,31)) and m.f[20:]==m.before_f[20:]
   pair.append(m)
  trace_differences+=trace(pair[0])!=trace(pair[1])
  param_address_differences+=tuple(a[5] for t,a in pair[0].calls)!=tuple(a[5] for t,a in pair[1].calls)
  count+=1
 controls={'graphics_command':(0x3c0fd9ff,0x3c0fd9fe),'alpha_parameter':(0x240f00ff,0x240f00fe),'helper_flag':(0x24190001,0x24190002),'output_stride':(0x26310008,0x26310010)}
 c=Case(count=3);initial=fixture(c);want,calls,params,result=reference(initial,c);killed=[]
 for name,(before,after) in controls.items():
  broken=list(truth);assert before in broken;broken[broken.index(before)]=after
  m=Oracle(broken,initial,c)
  try:m.run();agrees=(public(m.memory),normalized_calls(m),m.observed,m.r[2])==(public(want),calls,params,result)
  except (AssertionError,KeyError,IndexError):agrees=False
  assert not agrees,name
  killed.append(name)
 assert trace_differences==0 and param_address_differences==0
 print(json.dumps(dict(cases=count,executions=count*2,public_state_and_helper_values_match=True,ordered_public_trace_differences=trace_differences,helper_parameter_address_differences=param_address_differences,negative_controls=killed,helper_modeled=True,not_installed=True)),flush=True)
if __name__=='__main__':run()
