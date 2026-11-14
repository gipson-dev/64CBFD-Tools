from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,ALLOC,COPY,EMIT=0x151a9390,0x151a8b20,0x10022ec0,0x1516284c
TABLE,OWNER,OWNER2,POS,POS2,OUTPUT,PAYLOAD=0x8008f9ac,0x30000,0x31000,0x32000,0x33000,0x40000,0x50000
SYMS=dict(D_8008F9AC=TABLE,func_151A8B20=ALLOC,memcpy=COPY,func_1516284C=EMIT)
u32=lambda n:n&0xffffffff
s16=lambda n:((n&65535)^32768)-32768
fb=lambda f:bits(rounded(f))
@dataclass(frozen=True)
class Case:
 flags:int=31
 selector:int=0
 owner:int=OWNER
 position:int=POS
 lifetime:int=-1
 channel:int=0x123400ff
 context:int=0x87654321
 parameter0:int=0x3f800001
 parameter1:int=0x80000000
 mutation:int=0
 outcome:int=1
 phase:int=0
 seed:int=0
 output:int=OUTPUT
def arguments(c):return tuple(map(u32,(c.flags,c.selector,c.owner,c.position,c.parameter0,c.parameter1,c.lifetime,c.channel,c.context)))
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-768,768)}
 for base in (OWNER,OWNER2,POS,POS2,OUTPUT):m.update({base+i:(i*19+c.seed*7+(base>>8))&255 for i in range(768)})
 for index in range(9):
  p=TABLE+20*index;put(m,p,fb(1.+index));put(m,p+4,fb(-2.-index));put(m,p+16,PAYLOAD+index*256)
  for off in range(8,16):m[p+off]=(off*11+index*7)&255
  for delta in (0,128):
   for off in range(44):m[PAYLOAD+index*256+delta+off]=(off*23+index*17+delta+c.seed)&255
 for p in (OWNER,OWNER2):
  for i,v in enumerate((-32768,0,32767)):put(m,p+2*i,v,2)
 for p in (POS,POS2):
  for i,v in enumerate((fb(-12.75),fb(0.5),fb(32766.75))):put(m,p+4*i,v)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-768<=a<STACK+768}
def data(m,p,n):return bytes(m[p+i] for i in range(n))
def effect(m,c,index):
 if c.mutation&1:
  for j in range(9):
   p=TABLE+j*20;put(m,p+16,PAYLOAD+j*256+128)
   for off in range(8,13):m[p+off]=(c.seed+index*7+off)&255
  for p in (POS,POS2):
   for i in range(3):put(m,p+4*i,fb(float(-20+c.seed+index*3+i)+.75))
  for p in (OWNER,OWNER2):
   for i in range(3):put(m,p+2*i,c.seed+index*17+i,2)
 if c.mutation&2:
  home=STACK+c.phase;put(m,home+8,OWNER2);put(m,home+12,POS2 if index==0 else 0);put(m,home+24,0x12348001 if index==0 else 0xffffffff)
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase
 for i,v in enumerate(arguments(c)):put(m,home+4*i,v)
 calls=[];observed=[];flags=c.flags&255;selector=c.selector&255
 if selector>=9:return m,calls,observed
 table=TABLE+20*selector;p=home-40
 m[p]=((flags&2)!=0)*8|1|((c.owner!=0)*2)|((flags&1)!=0)*4
 put(m,p+4,c.owner);put(m,p+8,read(m,table));put(m,p+12,read(m,table+4))
 for i in range(12):m[p+16+i]=m[c.position+i] if c.position else 0
 put(m,p+28,c.parameter0);put(m,p+32,c.parameter1);m[p+36]=2;m[p+37]=255;m[p+38]=1
 calls.append((ALLOC,(p,u32(s16(c.lifetime)),44,c.channel&255,u32(c.context))));observed.append(('REQUEST',data(m,p,40)));effect(m,c,0)
 if c.outcome:
  dest=c.output+128;src=read(m,table+16);packet=data(m,src,44);calls.append((COPY,(dest,src,44)));observed.append(('COPY',packet))
  for i,v in enumerate(packet):m[dest+i]=v
  effect(m,c,1)
  if flags&8:m[dest+40]|=1
  if flags&16:m[dest+40]|=2
 if flags&4:
  life=s16(read(m,home+24));owner=read(m,home+8);position=read(m,home+12);h=home-56;coords=home-68
  m[h]=(life!=-1)|2;m[h+1]=2;put(m,h+2,300 if life==-1 else life,2);m[h+4]=m[table+11]
  for i in range(3):put(m,coords+4*i,int(floating(read(m,position+4*i))) if position else s16(read(m,owner+2*i,2)))
  calls.append((EMIT,(h,coords,m[table+8],m[table+9],m[table+10],255,0,0,m[table+12],255,1)))
  observed.append(('HEADER',data(m,h,6),data(m,coords,12)))
 return m,calls,observed
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None):
  self.observed=[];super().__init__(words,initial,c,entry=entry,s=SYMS,connected=connected,arguments=arguments(c));self.before_f=self.f[:]
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and rs==16 and fn==13:self.f[fd]=u32(int(floating(self.f[rd])));self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  if t==ENTRY:a=tuple(self.arguments(9))
  elif t==ALLOC:a=tuple(self.arguments(5));self.observed.append(('REQUEST',data(self.memory,a[0],40)))
  elif t==COPY:a=tuple(self.arguments(3));self.observed.append(('COPY',data(self.memory,a[1],a[2])))
  else:assert t==EMIT;a=tuple(self.arguments(11));self.observed.append(('HEADER',data(self.memory,a[0],6),data(self.memory,a[1],12)))
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  if t==ALLOC:effect(self.memory,self.case,0);answer=self.case.output if self.case.outcome else 0
  elif t==COPY:
   dest,src,n=self.calls[-1][1];assert n==44;packet=data(self.memory,src,n)
   for i,v in enumerate(packet):self.memory[dest+i]=v
   effect(self.memory,self.case,1);answer=dest
  else:assert t==EMIT;answer=0xaabbccdd
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=answer
def state(m):return (m.r,m.f,m.memory,m.trace,m.calls,m.events,m.observed,m.hi,m.lo)
def verify(m,initial,c):
 expected,calls,observed=reference(initial,c)
 assert (public(m.memory),m.calls,m.observed)==(public(expected),calls,observed),c
 assert m.r[29]==m.before[29] and all(m.r[i]==m.before[i] for i in (*range(16,24),28,30,31)) and m.f[20:]==m.before_f[20:]
def load():
 r=Path.cwd();o=r/'conker/build/game-template-effect-151a9390-screen';rom=(r/'conker/conker.us.bin').read_bytes();symbols={a[1]:a[2][1] for a in symbol_rows((r/'conker/build/conker.us.elf').read_bytes())};programs=[bound_blob(*payload(o/f,'func_151A9390'),symbols) for f in ('retail.o','selected.o','guarded.o')]
 assert programs[0]==programs[2] and len(programs[0])==len(programs[1])==169
 assert sum(a==b for a,b in zip(programs[0],programs[1]))==159
 return rom,programs
def cases():
 for flags,selector,position,life,mutation,outcome,phase in itertools.product((0,4,5,8,16,31,0x123456ff),(0,8,9,0x12340001),(0,POS),(-1,0x12348001),range(4),(0,1),(0,8)):
  yield Case(flags=flags,selector=selector,position=position,lifetime=life,mutation=mutation,outcome=outcome,phase=phase)
 for flags in (0,31):yield Case(flags=flags,owner=0,position=POS)
def run():
 rom,programs=load();seen=set();count=0
 for c in cases():
  initial=fixture(c);states=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();verify(m,initial,c);states.append(state(m));seen.update(m.visits)
  assert states[0]==states[2];count+=1
 assert len(seen&set(range(ENTRY,ENTRY+676,4)))==169
 caller_cases=0
 for pc,romoff,n,end,shift in ((0x150251d4,0x52684,15,0x15025210,0xf8),(0x15027724,0x54bd4,9,0x15027748,0x650)):
  window=struct.unpack_from('>%dI'%n,rom,romoff)
  for mutation,outcome,phase in itertools.product((0,1),(0,1),(0,8)):
   home=STACK+phase;c=Case(flags=5,selector=1,owner=0,position=home+shift,parameter0=fb(.75),parameter1=fb(100.),lifetime=-1,channel=0xabcd00fe,context=1,mutation=mutation,outcome=outcome,phase=phase)
   initial=fixture(c)
   for i in range(3):put(initial,c.position+4*i,read(initial,POS+4*i))
   expected,calls,observed=reference(initial,c)
   for program in programs:
    code=dict(zip(range(ENTRY,ENTRY+676,4),program));code[end]=0
    m=Oracle(window,initial,c,entry=pc,connected=code);m.r[3]=POS;m.r[14]=1;m.r[24]=0xffffffff;m.r[25]=c.channel
    m.f[4]=c.parameter0 if shift==0xf8 else read(initial,POS+8);m.f[6]=c.parameter1 if shift==0xf8 else c.parameter0;m.f[10]=read(initial,POS)
    m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller boundary missing')
    assert (public(m.memory),m.calls,m.observed)==(public(expected),[(ENTRY,(5,1,0,c.position,c.parameter0,c.parameter1,0xffffffff,c.channel,1))]+calls,observed),c
   caller_cases+=1
 aliases=0
 for phase,mutation,kind in itertools.product((0,8),(0,1),range(3)):
  home=STACK+phase;dest=(PAYLOAD,TABLE,OUTPUT+128)[kind]
  c=Case(flags=24,phase=phase,mutation=mutation,position=home-32 if kind==2 else POS,output=dest-128)
  initial=fixture(c);states=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();verify(m,initial,c);states.append(state(m))
  assert states[0]==states[2];aliases+=1
 prefixes=0
 for c in (Case(),Case(mutation=1),Case(mutation=2),Case(mutation=3,position=0,outcome=0,phase=8)):
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
 print(json.dumps(dict(cases=count,executions=(count+caller_cases+aliases)*3,caller_window_cases=caller_cases,guest_overlap_cases=aliases,access_prefixes=prefixes,observed_words=169,request_retained_bytes=4,header_retained_bytes=1,helpers_modeled=True,full_caller_behavior_claimed=False)),flush=True)
if __name__=='__main__':run()
