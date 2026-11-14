from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,rounded
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_direction_update_151a7a90_behavior as states
ENTRY,FACTORY,COPY,ZERO,ALLOC=0x151a8624,0x151a7950,0x10022ec0,0x100226f0,0x15167a68
OWNER,POSITION,OFFSET,PACKED,OUTPUT,DEST,OTHER,AMPLITUDE=0x30000,0x31000,0x32000,0x33000,0x50000,0x52000,0x53000,0x800a8de0
u32=lambda v:v&0xffffffff
s16=lambda v:((v&65535)^32768)-32768
fb=lambda v:bits(rounded(v))
@dataclass(frozen=True)
class Case:
 owner:int=OWNER
 position:int=POSITION
 offset:int=OFFSET
 packed:int=PACKED
 matrix:int=255
 lifetime:int=-1
 kind:int=1
 mode:int=0xe7
 second:int=-1
 extra:int=4
 channel:int=0xff
 context:int=0x87654321
 outcome:int=1
 mutation:int=0
 phase:int=0
 seed:int=0
 minimum:int=0x3e800000
 range:int=0x3fc00000
 scale:int=0x40200000
 amplitude:int=0x429f8000
def args(c):return c.owner,c.position,u32(c.matrix),u32(c.lifetime),c.minimum,c.range,c.packed,c.scale,c.offset,u32(c.kind),u32(c.mode),u32(c.second),u32(c.extra),u32(c.channel),u32(c.context)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2304)}
 for p,n in ((OWNER,256),(POSITION,32),(OFFSET,32),(PACKED,16),(OUTPUT,512),(DEST,64),(OTHER,64)):
  m.update({p+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 if c.owner:
  m.update({c.owner+i:(i*29+c.seed*11+0x5a)&255 for i in range(256)});m[c.owner+59]=0x87
 for p,values in ((c.position,(fb(1.25),fb(-2.5),fb(3.75))),(c.offset,(fb(-.5),fb(1.5),0x80000000))):
  if p:
   for i,v in enumerate(values):put(m,p+4*i,v)
 put(m,AMPLITUDE,c.amplitude);return m
def public(m):return {a:v for a,v in m.items() if not STACK-2048<=a<STACK+2304}
def effect(m,c,stage):
 if c.mutation&1 and stage=='factory':
  m[c.owner+59]^=0x7f
  for i in range(3):put(m,c.position+4*i,fb(20.+i))
  if c.offset:
   for i in range(3):put(m,c.offset+4*i,fb(-20.-i))
  for i in range(4):m[c.packed+i]^=0x55
  put(m,AMPLITUDE,fb(2.))
 if c.mutation&2 and stage=='copy':put(m,OUTPUT+96,OTHER)
def build(initial,c):
 m=dict(initial);base=STACK+c.phase-0xa0;cache=base+0x24;desc=base+0x4c
 if not c.owner:return m,cache,desc
 local=bytes(m[c.position+i] for i in range(12))
 for i,v in enumerate(local):m[cache+8+i]=v
 m[cache+20]=c.matrix&255;m[cache+37]=0;put(m,cache,c.owner);m[cache+4]=m[c.owner+59];m[cache+36]=c.mode&255
 offset=bytes(m[c.offset+i] for i in range(12)) if c.offset else bytes(12)
 for i,v in enumerate(offset):m[cache+24+i]=v
 put(m,desc,300 if s16(c.lifetime)==-1 else c.lifetime,2);put(m,desc+2,9,2);put(m,desc+4,c.minimum);put(m,desc+8,c.range);m[desc+12]=int(s16(c.lifetime)!=-1);put(m,desc+16,read(m,AMPLITUDE))
 packed=bytes(m[c.packed+i] for i in range(4))
 for i,v in enumerate(packed):m[desc+20+i]=v
 put(m,desc+24,c.scale);m[desc+28]=1;m[desc+29]=c.second&255
 for at in range(32,72,4):put(m,desc+at,0)
 put(m,desc+72,fb(1.));m[desc+76]=2
 return m,cache,desc
def reference(initial,c,connected=False):
 m,cache,desc=build(initial,c);calls=[];observed=[]
 if not c.owner:return m,calls,observed,0
 calls.append((FACTORY,(desc,u32(c.extra+40),c.channel&255,u32(c.context))));observed.append((FACTORY,bytes(m[desc+i] for i in range(80))))
 if connected:calls.append((ALLOC,(0x2d,u32(c.context),u32(c.extra+40+9*24+128),1,c.channel&255,1)))
 effect(m,c,'factory')
 if not c.outcome:return m,calls,observed,0
 if connected:
  calls.append((COPY,(OUTPUT+16,desc,80)));observed.append((COPY,bytes(m[desc+i] for i in range(80))))
  for i in range(80):m[OUTPUT+16+i]=m[desc+i]
  put(m,OUTPUT+100,OUTPUT+128);put(m,OUTPUT+104,0);put(m,OUTPUT+96,OUTPUT+128+9*24)
  for at in (128,132,136,128+9*24-24,128+9*24-20):put(m,OUTPUT+at,0)
  put(m,OUTPUT+128+9*24-16,fb(1.));calls.append((ZERO,(OUTPUT+108,16)))
  for i in range(16):m[OUTPUT+108+i]=0
  put(m,OUTPUT+124,9*64+320)
 else:put(m,OUTPUT+96,DEST)
 dst=read(m,OUTPUT+96);calls.append((COPY,(dst,cache,40)));chunk=bytes(m[cache+i] for i in range(40));observed.append((COPY,chunk))
 for i,v in enumerate(chunk):m[dst+i]=v
 effect(m,c,'copy');return m,calls,observed,OUTPUT
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,connected=None,actual=False):
  self.observed=[];self.actual=actual;super().__init__(words,initial,c,entry=ENTRY,arguments=args(c),connected=connected);self.before_f=self.f[:]
 def execute(self,w):
  op,rs,rt=w>>26,w>>21&31,w>>16&31
  if op not in (34,38,42,46):return super().execute(w)
  prior=self.own_instruction;self.own_instruction=True;self.dispatched_word=w
  try:
   p=u32(self.r[rs]+s16(w));offset=p&3;aligned=p&~3
   if op==34:self.r[rt]=u32((self.r[rt]&((1<<(offset*8))-1))|(self.get(p,4-offset)<<(offset*8)))
   elif op==38:
    mask=(1<<((offset+1)*8))-1;self.r[rt]=u32((self.r[rt]&~mask)|self.get(aligned,offset+1))
   elif op==42:self.put(p,self.r[rt]>>(offset*8),4-offset)
   else:self.put(aligned,self.r[rt],offset+1)
   self.r[0]=0
  finally:self.own_instruction=prior
 def record_call(self,t):
  counts={FACTORY:4,COPY:3,ZERO:2,ALLOC:6};assert t in counts,hex(t);a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==FACTORY:self.observed.append((t,bytes(self.memory[a[0]+i] for i in range(80))))
  if t==COPY:self.observed.append((t,bytes(self.memory[a[1]+i] for i in range(a[2]))))
 def hook(self,t):
  c=self.case;a=self.calls[-1][1];m=self.memory;value=0
  if t in (FACTORY,ALLOC):
   effect(m,c,'factory');value=OUTPUT if c.outcome else 0
   if value and t==FACTORY:put(m,OUTPUT+96,DEST)
  elif t==COPY:
   chunk=bytes(m[a[1]+i] for i in range(a[2]))
   for i,v in enumerate(chunk):m[a[0]+i]=v
   effect(m,c,'copy');value=0x12345678
  else:assert t==ZERO
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=u32(0xa5000000+reg)
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def cases():
 for i,(owner,lifetime,offset,kind,mutation,phase,packed) in enumerate(itertools.product((0,OWNER),(-32768,-1,0,32767),(0,OFFSET),(0,1,2,255),(0,1,2,3),(0,8),(PACKED,PACKED+1))):
  yield Case(owner=owner,lifetime=lifetime,offset=offset,kind=kind,mutation=mutation,phase=phase,packed=packed,matrix=(0,0x123400ff)[i%2],mode=(0,0x345600e7)[i%2],second=(-1,0x12340080)[i%2],channel=(0,0x876500ff)[i%2],seed=i%3)
 for outcome,alignment in itertools.product((0,1),range(4)):
  yield Case(outcome=outcome,packed=PACKED+alignment,matrix=0xabcd0080,lifetime=0xabcdffff,second=0xabcd0080,extra=0x7fffffff)
 yield Case(owner=0,position=0,offset=0,packed=0)
def load():
 r=Path.cwd();o=r/'conker/build/game-attached-direction-constructor-151a8624-screen';sy={v[1]:v[2][1] for v in symbol_rows((r/'conker/build/conker.us.elf').read_bytes())};programs=[bound_blob(*payload(o/f,'func_151A8624'),sy) for f in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[1]==programs[2]
 rom=(r/'conker/conker.us.bin').read_bytes();factory=bound_blob(*payload(r/'conker/build/src/game/generated_1D4E00.c.o','func_151A7950'),sy);assert len(factory)==80 and tuple(factory)==struct.unpack_from('>80I',rom,0x1d4e00)
 code={}
 for pc,offset,n in ((FACTORY,0x1d4e00,80),(COPY,0x22ec0,11),(ZERO,0x226f0,39)):code.update(zip(range(pc,pc+4*n,4),struct.unpack_from('>'+str(n)+'I',rom,offset)))
 return programs,code
def run():
 programs,helpers=load();count=0;seen=set()
 for alignment in range(4):
  c=Case();initial=fixture(c);m=Oracle(programs[0],initial,c);m.r[4]=PACKED+alignment;m.r[1]=0xdeadbeef;m.execute((34<<26)|(4<<21)|(1<<16));m.execute((38<<26)|(4<<21)|(1<<16)|3);assert m.r[1]==read(initial,PACKED+alignment)
  before=dict(m.memory);m.r[4]=DEST+alignment;m.r[1]=0x12345678;m.execute((42<<26)|(4<<21)|(1<<16));m.execute((46<<26)|(4<<21)|(1<<16)|3);assert read(m.memory,DEST+alignment)==0x12345678 and all(m.memory[p]==v for p,v in before.items() if not DEST+alignment<=p<DEST+alignment+4)
 for c in cases():
  initial=fixture(c);expected,calls,obs,value=reference(initial,c);machine_states=[]
  for p in programs:
   m=Oracle(p,initial,c);m.run();assert (public(m.memory),m.calls,m.observed,m.r[2])==(public(expected),calls,obs,value),c;machine_states.append(states.machine_state(m));seen.update(m.visits)
  assert machine_states[0]==machine_states[1]==machine_states[2];count+=1
 assert len(seen)==117
 coupled=0
 for outcome,mutation,offset,phase in itertools.product((0,1),(0,1),(0,OFFSET),(0,8)):
  c=Case(outcome=outcome,mutation=mutation,offset=offset,phase=phase);initial=fixture(c);expected,calls,obs,value=reference(initial,c,True)
  for p in programs:
   m=Oracle(p,initial,c,connected=helpers,actual=True);m.run();assert (public(m.memory),m.calls,m.observed,m.r[2])==(public(expected),calls,obs,value),(c,'coupled')
  coupled+=1
 aliases=0
 for kind,phase,outcome in itertools.product(range(4),(0,8),(0,1)):
  base=STACK+phase-0xa0;c=Case(phase=phase,outcome=outcome,mutation=1)
  if kind==0:c=replace(c,position=base+0x2c)
  elif kind==1:c=replace(c,offset=base+0x30)
  elif kind==2:c=replace(c,packed=base+0x5c)
  else:c=replace(c,owner=STACK+phase+0x180)
  initial=fixture(c);expected,calls,obs,value=reference(initial,c)
  for p in programs:
   m=Oracle(p,initial,c);m.run();assert (public(m.memory),m.calls,m.observed,m.r[2])==(public(expected),calls,obs,value),(c,'alias')
   assert bytes(m.memory[c.owner+i] for i in range(256))==bytes(expected[c.owner+i] for i in range(256)),c
  aliases+=1
 prefixes=0
 for c in (Case(owner=0),Case(outcome=0),Case(mutation=3),Case(offset=0,lifetime=0)):
  initial=fixture(c);whole=Oracle(programs[0],initial,c);whole.run()
  for cut in range(whole.all_accesses):
   ss=[]
   for p in (programs[0],programs[1]):
    m=Oracle(p,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('missing fired boundary')
    ss.append(states.machine_state(m))
   assert ss[0]==ss[1];prefixes+=1
 report=dict(cases=count,observed_words=len(seen),coupled_factory_cases=coupled,actual_helper_words=130,guest_alias_cases=aliases,unaligned_merge_probes=4,access_prefixes=prefixes,padding_checked_in_guest=True,helpers_modeled=True)
 o=Path.cwd()/'conker/build/game-attached-direction-constructor-151a8624-screen';(o/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':run()
