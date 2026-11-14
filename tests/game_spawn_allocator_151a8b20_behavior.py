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
ENTRY,COPY,FACTORY,RESET,LOOKUP,HEIGHT=0x151a8b20,0x10022ec0,0x15149130,0x1510f800,0x1510fd20,0x15144598
INPUT,OWNER,OWNER2,OUTPUT,MARK=0x30000,0x31000,0x32000,0x40000,0x50000
D1,D2=0x800a8f50,0x800a8f54
SYMS=dict(memcpy=COPY,func_15149130=FACTORY,func_1510F800=RESET,func_1510FD20=LOOKUP,func_15144598=HEIGHT,D_800A8F50=D1,D_800A8F54=D2)
u32=lambda n:n&0xffffffff
s16=lambda n:((n&65535)^32768)-32768
fb=lambda f:bits(rounded(f))
@dataclass(frozen=True)
class Case:
 flags:int=6
 owner:int=OWNER
 lifetime:int=-1
 extra:int=44
 channel:int=0x123400ff
 context:int=0x87654321
 mutation:int=0
 outcome:int=1
 phase:int=0
 seed:int=0
 source:int=INPUT
 output:int=OUTPUT
def arguments(c):return tuple(map(u32,(c.source,c.lifetime,c.extra,c.channel,c.context)))
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-768,768)}
 for base in (INPUT,OWNER,OWNER2,OUTPUT):m.update({base+i:(i*19+c.seed*7+(base>>8))&255 for i in range(768)})
 m[INPUT]=c.flags;put(m,INPUT+4,c.owner)
 for at,value in ((INPUT+16,fb(-12.75)),(INPUT+24,fb(32766.75)),(INPUT+32,fb(-3.500000238418579 if c.seed else -3.5)),(D1,fb(.5)),(D2,fb(.3 if c.seed else .25))):put(m,at,value)
 for p in (OWNER,OWNER2):
  for i,v in enumerate((-32768,0,32767)):put(m,p+2*i,v,2)
 put(m,MARK,0);return m
def public(m):return {a:v for a,v in m.items() if not STACK-768<=a<STACK+768}
def data(m,p,n):return bytes(m[p+i] for i in range(n))
def effect(m,c,stage):
 state=c.output+40
 if c.mutation&1:
  if stage=='snapshot':m[INPUT]^=0x80;put(m,INPUT+4,OWNER2);put(m,D1,fb(2.))
  if stage=='payload':m[state]^=6;put(m,state+4,OWNER2);put(m,state+32,fb(4.))
  if stage=='reset':
   for p in (OWNER,OWNER2):put(m,p,100,2);put(m,p+4,-100,2)
   put(m,state+16,fb(42.));put(m,state+24,fb(-42.));put(m,D2,fb(.5))
  if stage=='lookup':m[state]^=2;put(m,state+4,0);put(m,state+32,fb(5.))
 if c.mutation&2 and stage=='snapshot':
  home=STACK+c.phase
  for i,v in enumerate((0x12348001,1024,0xabcdef80,0xfedcba98),1):put(m,home+4*i,v)
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase
 for i,v in enumerate(arguments(c)):put(m,home+4*i,v)
 p=home-92;packet=data(m,c.source,40)
 for i,v in enumerate(packet):m[p+i]=v
 calls=[(COPY,(p,c.source,40))];obs=[('COPY',packet)];effect(m,c,'snapshot')
 for at,n in ((p+68,4),(p+72,1),(p+73,1),(p+76,4),(p+40,4)):put(m,at,0,n)
 put(m,p+44,read(m,D1));life=s16(read(m,home+4));args=(u32(300 if life==-1 else life),0xffffffff,0x25,0xffffffff,int(life!=-1),0x22,u32(read(m,home+8)+88),read(m,home+12)&255,read(m,home+16))
 calls.append((FACTORY,args));put(m,MARK,0x11223344)
 if not c.outcome:return m,calls,obs,0
 state=c.output+40;packet=data(m,p,88);calls.append((COPY,(state,p,88)));obs.append(('COPY',packet))
 for i,v in enumerate(packet):m[state+i]=v
 effect(m,c,'payload')
 if m[state]&4:
  if m[state]&2 and read(m,state+4):owner=read(m,state+4);x=float(s16(read(m,owner,2)));z=float(s16(read(m,owner+4,2)))
  else:x=floating(read(m,state+16));z=floating(read(m,state+24))
  calls.append((RESET,(0,)));effect(m,c,'reset');calls.append((LOOKUP,(u32(int(x)),u32(int(z)))));effect(m,c,'lookup');put(m,state+80,0x60000+c.seed)
 else:put(m,state+80,0)
 if m[state]&2 and read(m,state+4):
  owner=read(m,state+4);calls.append((HEIGHT,(owner,)));put(m,MARK,0x55667788);put(m,state+84,fb(-2.25))
 else:
  value=floating(read(m,state+32));put(m,state+84,fb(rounded(value*value)*floating(read(m,D2))))
 return m,calls,obs,c.output
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None):
  self.observed=[];self.copies=0;super().__init__(words,initial,c,entry=entry,s=SYMS,connected=connected,arguments=arguments(c));self.before_f=self.f[:]
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and rs==16 and fn==13:self.f[fd]=u32(int(floating(self.f[rd])));self.r[0]=0
  elif op==17 and rs==20 and fn==32:self.f[fd]=fb(float((self.f[rd]^0x80000000)-0x80000000));self.r[0]=0
  elif op==17 and rs==16 and fn==2:self.f[fd]=fb(floating(self.f[rd])*floating(self.f[rt]));self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  counts={ENTRY:5,COPY:3,FACTORY:9,RESET:1,LOOKUP:2,HEIGHT:1};a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==COPY:self.observed.append(('COPY',data(self.memory,a[1],a[2])))
 def hook(self,t):
  a=self.calls[-1][1]
  if t==COPY:
   dest,src,n=a;assert n in (40,88);packet=data(self.memory,src,n)
   for i,v in enumerate(packet):self.memory[dest+i]=v
   effect(self.memory,self.case,'snapshot' if self.copies==0 else 'payload');self.copies+=1;answer=dest
  elif t==FACTORY:put(self.memory,MARK,0x11223344);answer=self.case.output if self.case.outcome else 0
  elif t==RESET:effect(self.memory,self.case,'reset');answer=0xabcdef00
  elif t==LOOKUP:effect(self.memory,self.case,'lookup');answer=0x60000+self.case.seed
  else:assert t==HEIGHT;put(self.memory,MARK,0x55667788);answer=fb(-2.25)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=answer
  if t==HEIGHT:self.f[0]=answer
def state(m):return (m.r,m.f,m.memory,m.trace,m.calls,m.events,m.observed,m.hi,m.lo)
def verify(m,initial,c):
 expected,calls,obs,answer=reference(initial,c)
 assert (public(m.memory),m.calls,m.observed,m.r[2])==(public(expected),calls,obs,answer),c
 if c.outcome:assert data(m.memory,c.output+40,88)==data(expected,c.output+40,88),c
 assert m.r[29]==m.before[29] and all(m.r[i]==m.before[i] for i in (*range(16,24),28,30,31)) and m.f[20:]==m.before_f[20:]
def load():
 r=Path.cwd();o=r/'conker/build/game-spawn-allocator-151a8b20-screen';rom=(r/'conker/conker.us.bin').read_bytes();symbols={a[1]:a[2][1] for a in symbol_rows((r/'conker/build/conker.us.elf').read_bytes())};programs=[bound_blob(*payload(o/f,'func_151A8B20'),symbols) for f in ('retail.o','selected.o','guarded.o')]
 assert programs[0]==programs[2] and len(programs[0])==115 and len(programs[1])==114
 return rom,programs
def cases():
 for flags,owner,life,extra,mutation,outcome,phase,seed in itertools.product((0,2,4,6,255),(0,OWNER),(-1,0x12348001),(-88,44),range(4),(0,1),(0,8),(0,1)):
  yield Case(flags=flags,owner=owner,lifetime=life,extra=extra,mutation=mutation,outcome=outcome,phase=phase,seed=seed)
def run():
 rom,programs=load();seen=set();count=0
 for c in cases():
  initial=fixture(c);states=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();verify(m,initial,c);states.append(state(m));seen.update(m.visits)
  assert states[0]==states[2];count+=1
 missing=set(range(ENTRY,ENTRY+460,4))-seen
 assert missing=={ENTRY+0x11c},[hex(x) for x in sorted(missing)]
 caller_cases=0
 windows=((0x151a9180,0x1d6630,2,0x151a9188,0x30,2,1,0),(0x151a94a4,0x1d6954,9,0x151a94c8,0x70,15,44,0x87654321),(0x15012078,0x3f528,9,0x1501209c,0x20,7,0,0),(0x1515aa44,0x187ef4,7,0x1515aa60,0x60,15,44,0))
 for pc,off,n,end,shift,flags,extra,context in windows:
  window=struct.unpack_from('>%dI'%n,rom,off)
  assert 0x0d46a2c8 in window
  for mutation,outcome,phase,seed in itertools.product((0,1),(0,1),(0,8),(0,1)):
   home=STACK+phase;c=Case(flags=flags,extra=extra,channel=255,context=context,mutation=mutation,outcome=outcome,phase=phase,seed=seed,source=home+shift)
   initial=fixture(c)
   for i,v in enumerate(data(initial,INPUT,40)):initial[c.source+i]=v
   if shift!=0x70:
    for i in range(5):put(initial,c.source+16+i*4,0)
   if shift==0x70:put(initial,home+0xb0,0xffffffff);put(initial,home+0xb4,255)
   expected,calls,obs,answer=reference(initial,c)
   for program in programs:
    code=dict(zip(range(ENTRY,ENTRY+4*len(program),4),program));code[end]=0
    m=Oracle(window,initial,c,entry=pc,connected=code);m.r[15]=context if shift==0x70 else OWNER;m.r[8]=31;m.r[9]=0xabcdef12;m.r[3]=0x8008f9ac
    if shift==0x60:m.r[15]=home+0x54;m.r[1]=read(initial,home+0x54)
    if shift==0x70:m.f[8]=read(initial,c.source+28);m.f[10]=read(initial,c.source+32)
    if shift==0x20:m.f[4]=read(initial,c.source+8);m.f[6]=read(initial,c.source+12)
    m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller boundary missing')
    assert (public(m.memory),m.calls,m.observed,m.r[2])==(public(expected),[(ENTRY,arguments(c))]+calls,obs,answer),c
   caller_cases+=1
 aliases=0
 for phase,flags,kind in itertools.product((0,8),(0,6),range(3)):
  home=STACK+phase;source=(OUTPUT+40,INPUT,home-92)[kind];output=home-132 if kind==1 else OUTPUT
  c=Case(flags=flags,phase=phase,source=source,output=output);initial=fixture(c)
  if source!=INPUT:
   for i,v in enumerate(data(initial,INPUT,40)):initial[source+i]=v
  states=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();verify(m,initial,c);states.append(state(m))
  assert states[0]==states[2];aliases+=1
 prefixes=0
 for c in (Case(),Case(mutation=1),Case(mutation=2),Case(mutation=3,outcome=0,phase=8)):
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
 print(json.dumps(dict(cases=count,executions=(count+caller_cases+aliases)*3,caller_window_cases=caller_cases,guest_overlap_cases=aliases,access_prefixes=prefixes,observed_words=114,unreachable_retail_load='0x151A8C3C',payload_bytes=88,retained_payload_bytes=30,helpers_modeled=True,full_caller_behavior_claimed=False)),flush=True)
if __name__=='__main__':run()
