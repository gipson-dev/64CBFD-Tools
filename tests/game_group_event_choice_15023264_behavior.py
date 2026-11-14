from pathlib import Path
from dataclasses import dataclass
import itertools,json,random,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,HELPER=0x15023264,0x15023bb0
COUNT,TABLE,DEFAULTS,ARGSAVED,RESULT=0x800c363a,0x800c3688,0x800c35f0,0x800c35b0,0x800c35f8
RECORD,EVENT,DEFAULT=0x30000,0x40000,0x50000
SYMS=dict(D_800C363A=COUNT,D_800C3688=TABLE,D_800C35F0=DEFAULTS,func_15023BB0=HELPER)
u32=lambda x:x&0xffffffff
@dataclass(frozen=True)
class Case:
 group:int=0
 count:int=3
 present:int=7
 events:int=7
 scores:tuple=(17,8,21,6,19,0)
 values:tuple=(10,11,12,13,14,15)
 defaults:int=0
 mutation:int=0
 phase:int=0
 seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*11+0xa5)&255 for i in range(-512,768)}
 for g in range(2):
  m[COUNT+g]=c.count if g==c.group else 0
  put(m,DEFAULTS+4*g,DEFAULT+g*0x100);put(m,ARGSAVED+4*g,0x12345678+g)
  for i in range(6):
   put(m,TABLE+g*120+i*4,RECORD+g*0x1000+i*0x100 if c.present>>i&1 else 0)
   put(m,DEFAULT+g*0x100+i*8,1 if c.defaults>>i&1 else 2,2)
   put(m,EVENT+g*0x1000+i*0x100+2,c.values[i],2)
 m[RESULT]=0x9c
 return m
def mutate(m,c,index):
 if c.mutation==1 and index==0:m[COUNT+c.group]=1
 if c.mutation==2 and index==0:m[COUNT+c.group]=6
 if c.mutation==3 and index==1:m[COUNT+c.group]=0
def reference(initial,c):
 m=dict(initial);n=m[COUNT+c.group];selected=-1;best=99999;i=0;calls=[]
 while i<n:
  rec=read(m,TABLE+c.group*120+i*4)
  if rec:
   event=EVENT+c.group*0x1000+i*0x100 if c.events>>i&1 else 0
   calls.append((HELPER,(rec+0x18,3,i,STACK+c.phase-0x14,0,0,0,0,0,0,c.group)))
   mutate(m,c,i);score=c.scores[i]
   if event and score<best:
    best=score;v=read(m,event+2,2);selected=(v^0x8000)-0x8000
  i+=1;n=m[COUNT+c.group]
 if selected==-1:
  selected=0
  for i in range(n):
   if read(m,read(m,DEFAULTS+c.group*4)+i*8,2)==1:selected=i;break
 return m,calls,u32(selected)
class Oracle(FactoryOracle):
 def __init__(self,program,initial,c,entry=ENTRY,connected=None):
  super().__init__(program,initial,c,entry=entry,s=SYMS,connected=connected,arguments=(c.group,0x12345678+c.group));self.before_f=self.f[:]
 def record_call(self,t):
  counts={ENTRY:2,HELPER:11};args=tuple(self.arguments(counts[t]));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  assert t==HELPER;args=self.calls[-1][1];i=args[2];c=self.case
  assert args==(RECORD+c.group*0x1000+i*0x100+0x18,3,i,STACK+c.phase-0x14,0,0,0,0,0,0,c.group),args
  event=EVENT+c.group*0x1000+i*0x100 if c.events>>i&1 else 0
  put(self.memory,args[3],event);mutate(self.memory,c,i)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(c.scores[args[2]])
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+768}
def state(m):return (m.r,m.f,m.memory,m.trace,m.calls,m.events,m.hi,m.lo)
def verify(m,initial,c):
 expected,calls,result=reference(initial,c)
 assert (public(m.memory),m.calls,m.r[2])==(public(expected),calls,result),c
 assert m.r[29]==m.before[29] and all(m.r[i]==m.before[i] for i in (*range(16,24),28,30,31)) and m.f[20:]==m.before_f[20:]
def load():
 root=Path.cwd();out=root/'conker/build/game-group-event-choice-15023264-screen';rom=(root/'conker/conker.us.bin').read_bytes();symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
 programs=[bound_blob(*payload(out/f,'func_15023264'),symbols) for f in ('retail.o','selected.o','guarded.o')]
 assert programs[0]==programs[1]==programs[2] and len(programs[0])==86
 return rom,programs
def corpus():
 rng=random.Random(0x15023264);cases=[]
 for i in range(1024):
  scores=tuple(rng.choice((-2147483648,-1,0,5,99998,99999,100000,2147483647)) for _ in range(6))
  values=tuple(rng.choice((-32768,-2,-1,0,1,32767)) for _ in range(6))
  cases.append(Case(group=i&1,count=rng.randrange(7),present=rng.randrange(64),events=rng.randrange(64),scores=scores,values=values,defaults=rng.randrange(64),mutation=i%4,phase=8*((i//4)&1),seed=i&255))
 return cases
def run():
 rom,programs=load();seen=set();cases=corpus()
 for c in cases:
  initial=fixture(c);states=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();verify(m,initial,c);states.append(state(m));seen.update(m.visits)
  assert states[0]==states[1]==states[2]
 assert len(seen&set(range(ENTRY,ENTRY+344,4)))>=84, sorted(set(range(ENTRY,ENTRY+344,4))-seen)
 pc,end,off=0x15020f44,0x15020f60,0x4e3f4;window=struct.unpack_from('>7I',rom,off)
 for c in cases[:128]:
  initial=fixture(c);expected,calls,result=reference(initial,c);expected[RESULT]=result&255
  for program in programs:
   code=dict(zip(range(ENTRY,ENTRY+344,4),program));code[end]=0
   m=Oracle(window,initial,c,entry=pc,connected=code);m.r[4]=c.group;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller did not reach boundary')
   assert (public(m.memory),m.calls,m.r[2])==(public(expected),[(ENTRY,(c.group,0x12345678+c.group))]+calls,result),c
 prefixes=0
 for c in (Case(count=0),Case(count=3),Case(count=3,mutation=1),Case(count=1,mutation=2)):
  initial=fixture(c);whole=Oracle(programs[0],initial,c);whole.run()
  for cut in range(whole.all_accesses):
   states=[]
   for program in programs:
    m=Oracle(program,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('missing access boundary')
    states.append(state(m))
   assert states[0]==states[1]==states[2];prefixes+=1
 print(json.dumps(dict(cases=len(cases),executions=len(cases)*3,original_caller_window_cases=128,access_prefixes=prefixes,observed_instruction_words=len(seen & set(range(ENTRY,ENTRY+344,4))),helper_is_modeled=True,full_caller_behavior_claimed=False)),flush=True)
if __name__=='__main__':run()
