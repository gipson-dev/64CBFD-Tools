from pathlib import Path
from dataclasses import dataclass
import itertools,json,random,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,FLOAT,RANDOM,EMIT=0x151a91ac,0x150ada68,0x150ada20,0x1513c650
TABLE,OWNER,POS,OWNER2,POS2=0x8008f9a4,0x30000,0x31000,0x32000,0x33000
SYMS=dict(D_8008F9A4=TABLE,func_150ADA68=FLOAT,func_150ADA20=RANDOM,func_1513C650=EMIT)
u32=lambda n:n&0xffffffff
fb=lambda f:bits(rounded(f))
@dataclass(frozen=True)
class Case:
 randf:int=0
 draws:tuple=(0,1,2,3)
 mutation:int=0
 phase:int=0
 seed:int=0
 owner:int=OWNER
 pos:int=POS
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,768)}
 for base in (OWNER,OWNER2,POS,POS2):m.update({base+i:(i*19+c.seed*7+(base>>8))&255 for i in range(256)})
 for i,v in enumerate((-32768,-1,0x1234)):put(m,TABLE+2*i,v,2)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+768}
def data(m,p,n):return bytes(m[p+i] for i in range(n))
def effect(m,c,index):
 if c.mutation&1:
  for i,v in enumerate((0x7fff,0x0102,0xff80)):put(m,TABLE+2*i,v,2)
  for owner in (OWNER,OWNER2):m[owner+1]=(0x50+c.seed+index)&255;m[owner+12]=(0xa0+c.seed+index)&255
  for pos in (POS,POS2):
   for i in range(3):put(m,pos+4*i,u32(0x3f800000+c.seed+index*16+i))
 if c.mutation&2 and index==0:
  put(m,STACK+c.phase,OWNER2);put(m,STACK+c.phase+4,POS2)
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase;put(m,home,c.owner);put(m,home+4,c.pos)
 choices=[read(m,TABLE+2*i,2) for i in range(3)]
 calls=[(FLOAT,())];effect(m,c,0)
 rangebits=fb(rounded(floating(c.randf)*50.0)+50.0)
 calls.append((RANDOM,()));effect(m,c,1)
 p=home-0x2c;pick=c.draws[0]%3
 for off,v,n in ((0,0x1701,4),(4,60,2),(6,choices[pick],1),(7,0,1),(8,0,4),(12,0,4),(16,160,1),(17,255,1),(18,0,1),(19,0,1),(20,0,1),(21,255,1),(22,0,1),(23,7,1),(24,0x3b0002,4)):put(m,p+off,v,n)
 for i in range(1,4):calls.append((RANDOM,()));effect(m,c,i+1)
 owner=read(m,home);pos=read(m,home+4)
 args=(p,1,0,owner+0x58,read(m,pos),read(m,pos+4),read(m,pos+8),rangebits,rangebits,c.draws[1]&255,(c.draws[3]&1)+(c.draws[2]&1),3,255,0,m[owner+12],m[owner+1])
 calls.append((EMIT,args))
 return m,calls,[data(m,p,40)]
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None):
  self.observed=[];self.ordinal=0;super().__init__(words,initial,c,entry=entry,s=SYMS,connected=connected,arguments=(c.owner,c.pos,0x87654321,0x12345678));self.before_f=self.f[:]
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and rs==16 and fn in (0,2):
   x,y=floating(self.f[rd]),floating(self.f[rt]);self.f[fd]=fb(x+y if fn==0 else x*y);self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  if t==ENTRY:a=tuple(self.arguments(4))
  elif t in (FLOAT,RANDOM):a=()
  else:assert t==EMIT;a=tuple(self.arguments(16));self.observed.append(data(self.memory,a[0],40))
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  if t==FLOAT:effect(self.memory,self.case,0)
  elif t==RANDOM:
   effect(self.memory,self.case,self.ordinal+1);answer=self.case.draws[self.ordinal];self.ordinal+=1
  else:assert t==EMIT
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
  if t==FLOAT:self.f[0]=self.case.randf
  elif t==RANDOM:self.r[2]=answer
def state(m):return (m.r,m.f,m.memory,m.trace,m.calls,m.events,m.observed,m.hi,m.lo)
def verify(m,initial,c):
 expected,calls,obs=reference(initial,c)
 assert (public(m.memory),m.calls,m.observed)==(public(expected),calls,obs),c
 assert m.r[29]==m.before[29] and all(m.r[i]==m.before[i] for i in (*range(16,24),28,30,31)) and m.f[20:]==m.before_f[20:]
def load():
 root=Path.cwd();out=root/'conker/build/game-random-emitter-151a91ac-screen';rom=(root/'conker/conker.us.bin').read_bytes();symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
 programs=[bound_blob(*payload(out/f,'func_151A91AC'),symbols) for f in ('retail.o','selected.o','guarded.o')]
 assert programs[0]==programs[2] and len(programs[0])==len(programs[1])==92
 assert [i for i,(a,b) in enumerate(zip(programs[0],programs[1])) if a!=b]==[52,54,56,59]
 assert struct.unpack_from('>I',rom,0x234430)[0]==ENTRY
 # func_151A8CEC dispatches through D_8008F970. The table's first entry
 # is this callback; a0 is the actor, a1 is its caller's position array.
 assert struct.unpack_from('>9I',rom,0x1d634c)==(0x82020026,0x02602025,0x13c20007,0x0002c880,0x02d94021,0x8d190000,0x02202825,0x8fa6005c,0x0320f809)
 # Both real RNG helpers update the same 64-bit global seed.
 assert struct.unpack_from('>2I',rom,0xDAED0)==(0x3c048009,0xdc8485b0)
 assert struct.unpack_from('>2I',rom,0xDAF04)==(0x3c018009,0xfc2485b0)
 assert struct.unpack_from('>2I',rom,0xDAF18)==(0x3c048009,0xdc8485b0)
 assert struct.unpack_from('>2I',rom,0xDAF4C)==(0x3c018009,0xfc2485b0)
 # The downstream constructor copies all 40 bytes, including 12 retained bytes.
 assert struct.unpack_from('>4I',rom,0x16988c)==(0x26840018,0x02002825,0x0c008bb0,0x24060028)
 return rom,programs
def cases():
 patterns=((0,1,2,3),(0xffffffff,0x100,0x80000000,0x7fffffff),(2,255,1,0),(1,0x12345678,0xffffffff,0x80000001))
 for rand,draws,mutation,phase,seed in itertools.product((fb(0.),fb(.25),fb(.5),fb(1.),fb(-.25)),patterns,range(4),(0,8),(0,1,127,255)):
  yield Case(rand,draws,mutation,phase,seed)
def run():
 rom,programs=load();count=0;seen=set()
 for c in cases():
  initial=fixture(c);states=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();verify(m,initial,c);states.append(state(m));seen.update(m.visits)
  assert states[0]==states[2];count+=1
 aliases=0
 for owner,pos in ((OWNER,OWNER),(OWNER,OWNER+4),(OWNER,OWNER+12),(OWNER+4,OWNER),(OWNER+12,OWNER)):
  c=Case(owner=owner,pos=pos);initial=fixture(c);states=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();verify(m,initial,c);states.append(state(m))
  assert states[0]==states[2];aliases+=1
 assert len(seen&set(range(ENTRY,ENTRY+368,4)))==92
 caller_cases=0
 window=struct.unpack_from('>10I',rom,0x1d634c);start,end=0x151a8e9c,0x151a8ec4
 for mutation,phase,seed in itertools.product((0,1),(0,8),(0,1,127,255)):
  home=STACK+phase;c=Case(mutation=mutation,phase=phase,seed=seed,pos=home+0x64)
  initial=fixture(c);initial[OWNER+0x4e]=0;put(initial,0x8008f970,ENTRY);put(initial,home+0x5c,0x12345678)
  expected,calls,obs=reference(initial,c)
  for program in programs:
   code=dict(zip(range(ENTRY,ENTRY+368,4),program));code[end]=0
   m=Oracle(window,initial,c,entry=start,connected=code);m.r[16]=OWNER+0x28;m.r[17]=home+0x64;m.r[18]=0x101;m.r[19]=OWNER;m.r[22]=0x8008f970;m.r[30]=0xffffffff
   m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary missing')
   assert (public(m.memory),m.calls,m.observed)==(public(expected),[(ENTRY,(OWNER,home+0x64,0x12345678,1))]+calls,obs),c
  caller_cases+=1
 stack_aliases=0
 for phase,seed,offset in itertools.product((0,8),(0,1,127,255),(0,4,8,12,16,20,24,28)):
  c=Case(phase=phase,seed=seed,pos=STACK+phase-0x2c+offset);initial=fixture(c);states=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();verify(m,initial,c);states.append(state(m))
  assert states[0]==states[2];stack_aliases+=1
 prefixes=0
 for c in (Case(),Case(randf=fb(.5),mutation=1),Case(mutation=2),Case(randf=fb(1.),mutation=3,phase=8)):
  initial=fixture(c);whole=Oracle(programs[0],initial,c);whole.run()
  for cut in range(whole.all_accesses):
   states=[]
   for program in (programs[0],programs[2]):
    m=Oracle(program,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('missing access boundary')
    states.append(state(m))
   assert states[0]==states[1];prefixes+=1
 print(json.dumps(dict(cases=count,executions=(count+aliases+caller_cases+stack_aliases)*3,caller_window_cases=caller_cases,public_overlap_cases=aliases,guest_stack_overlap_cases=stack_aliases,access_prefixes=prefixes,observed_words=92,descriptor_bytes=40,defined_descriptor_bytes=28,retained_bytes=12,indirect_caller='func_151A8CEC',finite_fp_only=True,all_helpers_modeled=True,full_caller_behavior_claimed=False)),flush=True)
if __name__=='__main__':run()
