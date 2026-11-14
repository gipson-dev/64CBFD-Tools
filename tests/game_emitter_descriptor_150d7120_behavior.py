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
ENTRY=0x150d7120;PRE=(0x151c04f8,0x151c05a4,0x151c05f0);EMIT=0x1514fce8
P,P2=0x30000,0x31000
SYMS=dict(D_800A0AE0=0x800a0ae0,D_800A0AE4=0x800a0ae4,D_800A0AE8=0x800a0ae8,func_151C04F8=PRE[0],func_151C05A4=PRE[1],func_151C05F0=PRE[2],func_1514FCE8=EMIT)
u32=lambda x:x&0xffffffff
@dataclass(frozen=True)
class Case:
 slot:int=0xff
 context:int=1
 mutation:int=0
 phase:int=0
 seed:int=0
 position:int=P
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,768)}
 for base in (P,P2):
  for i in range(32):m[base+i]=(i*19+c.seed*7+(base>>8))&255
 for i,n in enumerate(('D_800A0AE0','D_800A0AE4','D_800A0AE8')):put(m,SYMS[n],(0x80000000,0x7fc12345,0x3f800001)[i])
 return m
def data(m,p,n):return bytes(m[p+i] for i in range(n))
def public(m):return {a:v for a,v in m.items()if not STACK-512<=a<STACK+768}
def effect(m,c,index,position):
 if c.mutation&1:
  for i in range(3):put(m,position+i*4,u32(0x10203040+c.seed+index*0x100+i))
  put(m,SYMS['D_800A0AE0']+index*4,0x40000000+index+c.seed)
 if c.mutation&2 and index==0:
  home=STACK+c.phase;put(m,home,P2);put(m,home+4,0x12340080);put(m,home+8,0xfedcba98)
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase
 put(m,home,c.position);put(m,home+4,c.slot);put(m,home+8,c.context)
 calls=[]
 for i,fn in enumerate(PRE):
  a=(read(m,home),read(m,home+4)&255,read(m,home+8));calls.append((fn,a));effect(m,c,i,a[0])
 p=home-0x5c
 for off,v in ((0,0),(2,255),(4,-64),(6,71),(0x4c,25),(0x4e,15),(0x50,100),(0x52,100),(0x54,12),(0x56,20)):put(m,p+off,v,2)
 for off,v in ((8,6),(12,4),(0x1c,0x41b80000),(0x20,0x41f00000),(0x24,0x42340000),(0x28,0x42540000),(0x2c,0x434b0000),(0x30,0x43cf0000),(0x34,7),(0x38,3),(0x3c,0x41700000)):put(m,p+off,v)
 for i in range(3):put(m,p+0x10+4*i,read(m,read(m,home)+4*i))
 for i in range(3):put(m,p+0x40+4*i,read(m,SYMS['D_800A0AE0']+4*i))
 m[p+0x58]=0;calls.append((EMIT,(p,read(m,home+4)&255,read(m,home+8))))
 return m,calls,[data(m,p,92)]
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None):
  self.observed=[];super().__init__(words,initial,c,entry=entry,s=SYMS,connected=connected,arguments=(c.position,c.slot,c.context));self.before_f=self.f[:]
 def record_call(self,t):
  counts={ENTRY:3,PRE[0]:3,PRE[1]:3,PRE[2]:3,EMIT:3};a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==EMIT:self.observed.append(data(self.memory,a[0],92))
 def hook(self,t):
  a=self.calls[-1][1]
  if t in PRE:effect(self.memory,self.case,PRE.index(t),a[0])
  else:assert t==EMIT
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=0xaabbccdd
def state(m):return (m.r,m.f,m.memory,m.trace,m.calls,m.events,m.observed,m.hi,m.lo)
def verify(m,initial,c):
 expected,calls,obs=reference(initial,c)
 assert (public(m.memory),m.calls,m.observed)==(public(expected),calls,obs),c
 assert m.r[29]==m.before[29] and all(m.r[i]==m.before[i] for i in (*range(16,24),28,30,31)) and m.f[20:]==m.before_f[20:]
def load():
 root=Path.cwd();out=root/'conker/build/game-emitter-descriptor-150d7120-screen';rom=(root/'conker/conker.us.bin').read_bytes();symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
 programs=[bound_blob(*payload(out/f,'func_150D7120'),symbols) for f in ('retail.o','selected.o','guarded.o')]
 assert programs[0]==programs[1]==programs[2] and len(programs[0])==91
 return rom,programs
def run():
 rom,programs=load();count=0;seen=set()
 for slot,context,mutation,phase,seed in itertools.product((0,1,0xff,0x12345678),(0,1,0xffffffff),(0,1,2,3),(0,8),(0,1,127,255)):
  c=Case(slot,context,mutation,phase,seed);initial=fixture(c);states=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();verify(m,initial,c);states.append(state(m));seen.update(m.visits)
  assert states[0]==states[1]==states[2];count+=1
 assert len(seen&set(range(ENTRY,ENTRY+364,4)))==91
 caller_cases=0
 for pc,off,end,shift in ((0x150824b4,0xaf964,0x150824c4,8),(0x1505480c,0x81cbc,0x1505481c,0x14)):
  window=struct.unpack_from('>4I',rom,off)
  for mutation,phase,seed in itertools.product((0,1,2,3),(0,8),(0,1,127,255)):
   c=Case(0xff,1,mutation,phase,seed);initial=fixture(c);expected,calls,obs=reference(initial,c)
   for program in programs:
    code=dict(zip(range(ENTRY,ENTRY+364,4),program));code[end]=0
    m=Oracle(window,initial,c,entry=pc,connected=code);m.r[16]=P-shift;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller boundary missing')
    assert (public(m.memory),m.calls,m.observed)==(public(expected),[(ENTRY,(P,0xff,1))]+calls,obs),c
   caller_cases+=1
 aliases=0
 for phase,offset,seed in itertools.product((0,8),(0,4,8,12),(0,1,127,255)):
  c=Case(phase=phase,seed=seed,position=STACK+phase-0x5c+offset);initial=fixture(c);states=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();verify(m,initial,c);states.append(state(m))
  assert states[0]==states[1]==states[2];aliases+=1
 prefixes=0
 for c in (Case(),Case(mutation=1),Case(mutation=2),Case(mutation=3,phase=8)):
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
 print(json.dumps(dict(cases=count,executions=count*3,caller_window_cases=caller_cases,guest_stack_alias_cases=aliases,access_prefixes=prefixes,observed_words=91,descriptor_bytes=92,retained_bytes=3,all_helpers_modeled=True,full_caller_behavior_claimed=False)),flush=True)
if __name__=='__main__':run()
