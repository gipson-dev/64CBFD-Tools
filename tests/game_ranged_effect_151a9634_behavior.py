from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,FLOAT,RANDOM,EMIT,COPY=0x151a9634,0x150ada68,0x150ada20,0x1514b8e4,0x10022ec0
OWNER,POS,OWNER2,POS2,OUTPUT=0x30000,0x31000,0x32000,0x33000,0x40000
SYMS=dict(func_150ADA68=FLOAT,func_150ADA20=RANDOM,func_1514B8E4=EMIT,memcpy=COPY)
u32=lambda n:n&0xffffffff
s16=lambda n:((n&65535)^32768)-32768
fb=lambda f:bits(rounded(f))
@dataclass(frozen=True)
class Case:
 flags:int=0
 draws:tuple=(0,1,2,3)
 floats:tuple=(0,0x3f000000,0x3f800000)
 span:int=4
 mutation:int=0
 outcome:int=1
 phase:int=0
 seed:int=0
 owner:int=OWNER
 pos:int=POS
 output:int=OUTPUT
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-768,768)}
 for base in (OWNER,OWNER2,POS,POS2,OUTPUT):m.update({base+i:(i*19+c.seed*7+(base>>8))&255 for i in range(768)})
 for owner in (OWNER,OWNER2):
  p=owner+0x80
  for off,v in ((0,fb(10.)),(4,fb(-2.)),(8,fb(5.)),(12,fb(3.)),(32,fb(1.5)),(36,fb(.25))):put(m,p+off,v)
  for off,v in ((16,-32760),(18,c.span),(20,32760),(22,c.span),(24,250),(26,c.span),(28,-32768),(30,32767)):put(m,p+off,v,2)
  m[p+40]=c.flags
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-768<=a<STACK+768}
def data(m,p,n):return bytes(m[p+i] for i in range(n))
def effect(m,c,index):
 if c.mutation&1:
  for owner in (OWNER,OWNER2):
   p=owner+0x80;m[owner+1]=(0x50+c.seed+index)&255;m[owner+12]=(0xa0+c.seed+index)&255
   m[p+40]=(c.flags^index)&255
   for off,v in ((0,fb(2.+index)),(4,fb(-1.-index)),(8,fb(.5)),(12,fb(.25)),(32,fb(5.+index)),(36,fb(2.))):put(m,p+off,v)
   for off,v in ((16,10+index),(18,6),(20,20+index),(22,4),(24,30+index),(26,8)):put(m,p+off,v,2)
 if c.mutation&2 and index in (0,2,5):
  put(m,STACK+c.phase,OWNER2 if index!=2 else OWNER)
  put(m,STACK+c.phase+4,POS2 if index!=2 else POS)
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase;put(m,home,c.owner);put(m,home+4,c.pos);calls=[]
 for i in range(3):
  calls.append((FLOAT,()));effect(m,c,i)
  if i==0:p=read(m,home)+0x80
  base,span=((0,8),(4,12),(32,36))[i]
  value=fb(rounded(floating(c.floats[i])*floating(read(m,p+span)))+floating(read(m,p+base)))
  put(m,home+(-8,-4,-20)[i],value)
 calls.append((RANDOM,()));effect(m,c,3)
 lifetime=u32(c.draws[0]%(u32(s16(read(m,p+22,2))+1))+s16(read(m,p+20,2)));put(m,home-16,lifetime,2)
 calls.append((RANDOM,()));effect(m,c,4)
 calls.append((RANDOM,()));effect(m,c,5);flags=m[p+40]
 if flags&1:tag=0x71
 else:
  calls.append((RANDOM,()));effect(m,c,6);tag=0x13 if c.draws[3]&1 else 0x14;flags=m[p+40]
 mode=0 if flags&2 else 2
 count=s16(c.draws[1]%(u32(s16(read(m,p+18,2))+1))+s16(read(m,p+16,2)))
 variant=(c.draws[2]%(u32(s16(read(m,p+26,2))+1))+s16(read(m,p+24,2)))&255
 owner=read(m,home);a=(read(m,home+4),home-8,u32(count),variant,0,0,fb(1.),fb(1.),0x21,0x23,2,tag,mode,u32(s16(read(m,p+28,2))),u32(s16(read(m,p+30,2))),8,m[owner+12],m[owner+1])
 observations=[('EMIT',data(m,home-8,8))];calls.append((EMIT,a))
 if c.outcome:
  packet=data(m,home-20,8);calls.append((COPY,(c.output+0x160,home-20,8)));observations.append(('COPY',packet))
  for i,b in enumerate(packet):m[c.output+0x160+i]=b
 return m,calls,observations
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None):
  self.observed=[];self.float_n=0;self.int_n=0;super().__init__(words,initial,c,entry=entry,s=SYMS,connected=connected,arguments=(c.owner,c.pos,0x87654321,0x12345678));self.before_f=self.f[:]
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and rs==16 and fn in (0,2):
   x,y=floating(self.f[rd]),floating(self.f[rt]);self.f[fd]=fb(x+y if fn==0 else x*y);self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  if t==ENTRY:a=tuple(self.arguments(4))
  elif t in (FLOAT,RANDOM):a=()
  elif t==EMIT:a=tuple(self.arguments(18));self.observed.append(('EMIT',data(self.memory,a[1],8)))
  else:
   assert t==COPY;a=tuple(self.arguments(3));self.observed.append(('COPY',data(self.memory,a[1],a[2])))
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  if t==FLOAT:index=self.float_n;answer=self.case.floats[index];self.float_n+=1;effect(self.memory,self.case,index)
  elif t==RANDOM:index=self.int_n;answer=self.case.draws[index];self.int_n+=1;effect(self.memory,self.case,3+index)
  elif t==EMIT:answer=self.case.output if self.case.outcome else 0
  else:
   assert t==COPY;dest,src,n=self.calls[-1][1];assert n==8;packet=data(self.memory,src,n)
   for i,b in enumerate(packet):self.memory[dest+i]=b
   answer=dest
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
  if t==FLOAT:self.f[0]=answer
  else:self.r[2]=answer
def state(m):return (m.r,m.f,m.memory,m.trace,m.calls,m.events,m.observed,m.hi,m.lo)
def verify(m,initial,c):
 expected,calls,obs=reference(initial,c)
 assert (public(m.memory),m.calls,m.observed)==(public(expected),calls,obs),c
 assert m.r[29]==m.before[29] and all(m.r[i]==m.before[i] for i in (*range(16,24),28,30,31)) and m.f[20:]==m.before_f[20:]
def load():
 root=Path.cwd();out=root/'conker/build/game-ranged-effect-151a9634-screen';rom=(root/'conker/conker.us.bin').read_bytes();symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
 programs=[bound_blob(*payload(out/f,'func_151A9634'),symbols) for f in ('retail.o','selected.o','guarded.o')]
 assert programs[0]==programs[1]==programs[2] and len(programs[0])==128
 assert struct.unpack_from('>I',rom,0x234434)[0]==ENTRY
 return rom,programs
def cases():
 for flags,span,mutation,outcome,phase,seed in itertools.product((0,1,2,3,255),(0,4,32767,-2,-32768),(0,1,2,3),(0,1),(0,8),(0,255)):
  draws=(0xffffffff,0x80000000,0x12345678,seed&1) if seed else (2,3,4,0)
  yield Case(flags=flags,draws=draws,span=span,mutation=mutation,outcome=outcome,phase=phase,seed=seed)
def run():
 rom,programs=load();count=0;seen=set()
 for c in cases():
  initial=fixture(c);states=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();verify(m,initial,c);states.append(state(m));seen.update(m.visits)
  assert states[0]==states[1]==states[2];count+=1
 assert len(seen&set(range(ENTRY,ENTRY+512,4)))==125
 caller_cases=0
 window=struct.unpack_from('>10I',rom,0x1d634c);start,end=0x151a8e9c,0x151a8ec4
 for mutation,outcome,phase,seed in itertools.product((0,1),(0,1),(0,8),(0,255)):
  home=STACK+phase;c=Case(mutation=mutation,outcome=outcome,phase=phase,seed=seed,pos=home+0x64)
  initial=fixture(c);initial[OWNER+0x4e]=1;put(initial,0x8008f974,ENTRY);put(initial,home+0x5c,0x12345678)
  expected,calls,obs=reference(initial,c)
  for program in programs:
   code=dict(zip(range(ENTRY,ENTRY+512,4),program));code[end]=0
   m=Oracle(window,initial,c,entry=start,connected=code);m.r[16]=OWNER+0x28;m.r[17]=home+0x64;m.r[18]=0x101;m.r[19]=OWNER;m.r[22]=0x8008f970;m.r[30]=0xffffffff
   m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary missing')
   assert (public(m.memory),m.calls,m.observed)==(public(expected),[(ENTRY,(OWNER,home+0x64,0x12345678,1))]+calls,obs),c
  caller_cases+=1
 aliases=0
 for phase,seed,kind in itertools.product((0,8),(0,255),range(3)):
  dest=(OWNER,OWNER+0x80,STACK+phase-20)[kind]
  c=Case(phase=phase,seed=seed,pos=OWNER+0x80,output=dest-0x160);initial=fixture(c);states=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();verify(m,initial,c);states.append(state(m))
  assert states[0]==states[1]==states[2];aliases+=1
 prefixes=0
 for c in (Case(),Case(mutation=1),Case(mutation=2),Case(flags=1,outcome=0,mutation=3,phase=8)):
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
 print(json.dumps(dict(cases=count,executions=(count+caller_cases+aliases)*3,caller_window_cases=caller_cases,guest_overlap_cases=aliases,access_prefixes=prefixes,observed_nontrap_words=125,retained_copy_bytes=2,zero_divisor_execution_claimed=False,helpers_modeled=True,full_caller_behavior_claimed=False)),flush=True)
if __name__=='__main__':run()
