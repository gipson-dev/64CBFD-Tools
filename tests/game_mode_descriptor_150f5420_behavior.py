from pathlib import Path
from dataclasses import dataclass
import itertools,json,random,struct
from tools.tests import game_packed_argument_descriptor_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x150F5420
SYMS=dict(D_800917F8=0x800917F8,D_80091930=0x80091930,D_8009193C=0x8009193C,D_80091948=0x80091948,func_15169968=g.CREATE)
u32=lambda x:x&0xffffffff
@dataclass(frozen=True)
class Case:
 args:tuple=(1,2,3,0)
 result:int=g.OUTPUT
 phase:int=0
 seed:int=0
 mutation:int=0
 connected:bool=False
def fields(c):
 a,b,d,mode=c.args; total=u32(a+b+d)
 if mode==0: asset,x,y,kind,flag,unit,step=SYMS['D_800917F8'],160,192,10,32,4096,24
 elif mode==2: asset,x,y,kind,flag,unit,step=SYMS['D_80091948'],240,186,9,16,0,8
 else: asset,x,y,kind,flag,unit,step=SYMS['D_80091930' if mode==1 else 'D_8009193C'],270,124,9,16,0,8
 return [(0,asset,4),(8,u32(a<<16)|b,4),(12,u32(d<<16)|total,4),(16,10000,4),(20,total,2),(22,0,2),(24,0,2),(28,0x43120000,4),(32,0x42c80000,4),(36,0,2),(38,0,2),(40,unit,2),(42,unit,2),(44,x,2),(46,y,2),*[(48+i,v,1) for i,v in enumerate((kind,1,255,255,255,0,step,17))],(57,flag,1)]
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,768)}
 m.update({g.OUTPUT+i:(i*29+c.seed*11+0x59)&255 for i in range(-8,128)})
 return m
def effect(m,c):
 if c.mutation:
  put(m,g.packet(c)+20,0xfedc,2);m[g.packet(c)+4]^=0x55
def reference(initial,c):
 m=dict(initial);p=g.packet(c)
 for at,value,n in fields(c):put(m,p+at,value,n)
 observed=g.data(m,p,60);calls=[(g.CREATE,(p,))]
 if c.connected:calls.extend(((g.CTOR,(p,255)),(g.ALLOC,(94,0,76,0,255,1))))
 effect(m,c)
 if c.result:
  if c.connected:calls.append((g.COPY,(p,c.result+16,60)))
  for i,b in enumerate(g.data(m,p,60)):m[c.result+16+i]=b
 return m,calls,[observed]
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None):
  self.observed=[];super().__init__(words,initial,c,entry=entry,s=SYMS,connected=connected,arguments=c.args);self.before_f=self.f[:]
 def record_call(self,t):
  counts={ENTRY:4,g.CREATE:1,g.CTOR:2,g.ALLOC:6,g.COPY:3}
  args=tuple(self.arguments(counts[t]));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==g.CREATE:self.observed.append(g.data(self.memory,args[0],60))
 def hook(self,t):
  c=self.case;args=self.calls[-1][1]
  if t in (g.CREATE,g.ALLOC):
   assert args==((g.packet(c),) if t==g.CREATE else (94,0,76,0,255,1)),args
   effect(self.memory,c);answer=c.result
   if t==g.CREATE and c.result:
    for i,b in enumerate(g.data(self.memory,g.packet(c),60)):self.memory[c.result+16+i]=b
  else:
   assert t==g.COPY and args==(g.packet(c),c.result+16,60),args
   for i,b in enumerate(g.data(self.memory,args[0],args[2])):self.memory[args[1]+i]=b
   answer=0xaabbccdd
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(answer)
def verify(m,initial,c):
 expected,calls,obs=reference(initial,c)
 assert (g.public(m.memory),m.calls,m.observed,m.r[2])==(g.public(expected),calls,obs,c.result),c
 assert g.data(m.memory,g.packet(c),60)==g.data(expected,g.packet(c),60),c
 assert m.r[29]==m.before[29] and all(m.r[i]==m.before[i] for i in (*range(16,24),28,30,31)) and m.f[20:]==m.before_f[20:]
def run():
 root=Path.cwd();out=root/'conker/build/game-mode-descriptor-150f5420-screen';conker=root/'conker';g.rom=(conker/'conker.us.bin').read_bytes()
 symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())}
 programs=[bound_blob(*payload(out/f,'func_150F5420'),symbols) for f in ('retail.o','selected.o','guarded.o')]
 assert programs[0]==programs[1]==programs[2] and len(programs[0])==92
 vals=(0,1,0xffff,0x10000,0x7fffffff,0x80000000,0xffffffff)
 rows=[(v,1,3) for v in vals]+[(1,v,3) for v in vals]+[(1,2,v) for v in vals]+[(v,v,v) for v in vals]
 rng=random.Random(0x150f5420);rows += [tuple(rng.getrandbits(32) for _ in range(3)) for i in range(32)]
 rows=list(dict.fromkeys(rows));count=0;visited=set()
 for row,mode,result,phase,mutation,connected in itertools.product(rows,(0,1,2,3,0xffffffff),(0,g.OUTPUT),(0,8),(0,1),(False,True)):
  c=Case((*row,mode),result,phase,row[0]&255,mutation,connected);initial=fixture(c);states=[]
  for program in programs:
   m=Oracle(program,initial,c,connected=g.helpers() if connected else None);m.run();verify(m,initial,c);states.append(g.state(m));visited.update(m.visits)
  assert states[0]==states[1]==states[2];count+=1
 assert len(visited & set(range(ENTRY,ENTRY+368,4)))==92
 print(json.dumps(dict(cases=count,executions=count*3,reachable_words=92,descriptor_bytes=60,defined_bytes=51,retained_stack_bytes=9,original_provider_words=34,allocation_and_bcopy_are_modelled=True,uncredited=True)),flush=True)
if __name__=='__main__':run()
