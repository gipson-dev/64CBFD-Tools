from pathlib import Path
from dataclasses import dataclass,replace
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
ENTRY,TRANSFORM,COLLISION,HIT,LENGTH,ORIENT=0x151a87f8,0x15143134,0x150ac9c0,0x15145c90,0x15143e64,0x15146078
RECORD,CACHE,TARGET,MATRICES,CACHE2,TARGET2=0x30000,0x31000,0x32000,0x40000,0x34000,0x35000
u32=lambda v:v&0xffffffff
fb=lambda v:bits(rounded(v))
@dataclass(frozen=True)
class Case:
 active:int=1
 identity:int=0x80
 mismatch:int=0
 kind:int=0
 matrix:int=1
 index:int=255
 latched:int=0
 flags:int=0xa7
 collision:int=1
 accepted:int=1
 length:float=2.5
 mutation:int=0
 phase:int=0
 seed:int=0
 record:int=RECORD
 cache:int=CACHE
 target:int=TARGET
def homes(c,raw=False):
 base=STACK+c.phase-0x90
 return (base+0x5c,base+0x78,base+0x6c) if raw else (base+0x78,base+0x7c,base+0x60)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-768,768)}
 for p,n in ((c.record,256),(c.cache,64),(c.target,512),(CACHE2,64),(TARGET2,512)):
  m.update({p+i:(i*19+c.seed*7)&255 for i in range(n)})
 put(m,c.record+96,c.cache);put(m,c.cache,c.target);m[c.cache+4]=c.identity;m[c.cache+20]=c.index;m[c.cache+37]=c.latched
 put(m,c.target,c.active);m[c.target+4]=c.kind;m[c.target+59]=c.identity^c.mismatch;put(m,c.target+468,MATRICES if c.matrix else 0);m[c.record+28]=c.flags
 for p,values in ((c.record+48,(2.,4.,6.)),(c.record+60,(7.,11.,15.)),(c.record+72,(20.,21.,22.)),(c.cache+8,(1.25,-2.5,3.75)),(c.cache+24,(.5,-.75,1.25)),(c.target+20,(-3.,4.,-5.))):
  for i,v in enumerate(values):put(m,p+4*i,fb(v))
 put(m,c.record+84,fb(13.));put(m,c.record+88,fb(17.));return m
def public(m):return {a:v for a,v in m.items() if not STACK-768<=a<STACK+768}
def vector(m,p):return tuple(read(m,p+4*i) for i in range(3))
def effect(m,c,stage):
 if c.mutation&1:
  if stage=='transform':
   put(m,c.record+96,CACHE2);put(m,c.cache,TARGET2);m[c.record+28]^=0x80
   for i in range(3):put(m,c.target+20+4*i,fb(8.+i));put(m,c.cache+24+4*i,fb(-.25-i))
  elif stage=='collision':m[c.cache+37]^=0x80;m[c.record+28]^=0x40
  elif stage=='hit':m[c.cache+37]^=0x40;m[c.record+28]^=0x20
  elif stage=='length':put(m,c.record+84,fb(99.));put(m,c.record+88,fb(41.));m[c.record+28]^=0x10
  elif stage=='orient':m[c.record+28]^=8
 if c.mutation&2 and stage=='transform':m[c.cache+37]^=1
def reference(initial,c,raw=False):
 m=dict(initial);calls=[];observed=[];hit,delta,temp=homes(c,raw);cache=read(m,c.record+96);target=read(m,cache)
 def call(t,a,obs=None):
  calls.append((t,tuple(map(u32,a))))
  if obs is not None:observed.append((t,obs))
 if not read(m,target) or m[cache+4]!=m[target+59] or m[target+4]==255:return m,calls,observed,0
 matrices=read(m,target+468)
 if not matrices:m[c.record+28]&=253;return m,calls,observed,1
 source=vector(m,cache+8);call(TRANSFORM,(cache+8,c.record+48,matrices+m[cache+20]*64),source)
 for i,v in enumerate(source):put(m,c.record+48+4*i,fb(floating(v)+i+1.))
 effect(m,c,'transform')
 if not m[cache+37]&1:
  start=vector(m,c.record+48);difference=tuple(fb(floating(start[i])-rounded(floating(read(m,target+20+4*i))+floating(read(m,cache+24+4*i)))) for i in range(3))
  a=(*start,*difference,0,0,c.record+60,c.record+64,c.record+68,0,hit,0,0);call(COLLISION,a)
  for i in range(3):put(m,c.record+60+4*i,fb(floating(start[i])+4.+i))
  put(m,hit,0x12345678);effect(m,c,'collision')
  if not c.collision:m[c.record+28]&=253;return m,calls,observed,1
  call(HIT,(read(m,hit),));effect(m,c,'hit')
  if not c.accepted:m[c.record+28]&=253;return m,calls,observed,1
  m[cache+37]|=1
 for i in range(3):put(m,delta+4*i,fb(floating(read(m,c.record+60+4*i))-floating(read(m,c.record+48+4*i))))
 values=vector(m,delta);call(LENGTH,(delta,),values);effect(m,c,'length');put(m,c.record+84,fb(c.length))
 if c.length!=0.:
  put(m,c.record+88,fb(1./c.length));call(ORIENT,(delta,temp,c.record+72),(values,read(m,c.record+88)))
  for i,v in enumerate(values):put(m,temp+4*i,fb(floating(v)+10.));put(m,c.record+72+4*i,fb(floating(v)+20.))
  effect(m,c,'orient');m[c.record+28]|=2
 else:m[c.record+28]&=253
 return m,calls,observed,1
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None):
  self.observed=[];super().__init__(words,initial,c,entry=entry,arguments=(c.record,),connected=connected);self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in (0,1,3,50):
   a,b=floating(self.f[fs]),floating(self.f[ft])
   if fn==50:self.condition=a==b
   else:self.f[fd]=fb(a+b if fn==0 else a-b if fn==1 else a/b)
   self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  counts={ENTRY:1,TRANSFORM:3,COLLISION:15,HIT:1,LENGTH:1,ORIENT:3};a=tuple(self.arguments(counts[t]))
  if t==COLLISION:a=(self.f[12],self.f[14],*a[2:])
  self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t in (TRANSFORM,LENGTH):self.observed.append((t,vector(self.memory,a[0])))
  if t==ORIENT:self.observed.append((t,(vector(self.memory,a[0]),read(self.memory,self.case.record+88))))
 def hook(self,t):
  m=self.memory;c=self.case;a=self.calls[-1][1];answer=0
  if t==TRANSFORM:
   values=vector(m,a[0])
   for i,v in enumerate(values):put(m,a[1]+4*i,fb(floating(v)+i+1.))
   effect(m,c,'transform')
  elif t==COLLISION:
   for i,p in enumerate(a[8:11]):put(m,p,fb(floating(a[i])+4.+i))
   put(m,a[12],0x12345678);effect(m,c,'collision');answer=c.collision
  elif t==HIT:effect(m,c,'hit');answer=c.accepted
  elif t==LENGTH:effect(m,c,'length');answer=fb(c.length)
  else:
   assert t==ORIENT;values=vector(m,a[0])
   for i,v in enumerate(values):put(m,a[1]+4*i,fb(floating(v)+10.));put(m,a[2]+4*i,fb(floating(v)+20.))
   effect(m,c,'orient');answer=c.seed
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=u32(answer);self.hi,self.lo=0xa5000010,0xa5000011
  if t==LENGTH:self.f[0]=answer
def cases():
 for i,(valid,matrix,latched,collision,accepted,length,mutation,phase) in enumerate(itertools.product(range(4),(0,1),(0,0x81),(0,1),(0,1),(0.,-0.,2.5,-2.5),range(4),(0,8))):
  yield Case(active=0 if valid==1 else 0x80000000,mismatch=int(valid==2),kind=255 if valid==3 else 1,matrix=matrix,latched=latched,collision=collision,accepted=accepted,length=length,mutation=mutation,phase=phase,seed=i%2,index=(0,1,255)[i%3],identity=(0,128,255)[i%3])
def state(m):return m.memory,m.r,m.f,m.trace,m.calls,m.events,m.observed,m.hi,m.lo,m.condition
def verify(m,initial,c,raw=False):
 expected,calls,obs,answer=reference(initial,c,raw);assert (public(m.memory),m.calls,m.observed,m.r[2])==(public(expected),calls,obs,answer),c
 for p,n in ((c.record+28,1),(c.record+48,44),(c.record+96,4),(c.cache,38)):
  assert bytes(m.memory[p+i] for i in range(n))==bytes(expected[p+i] for i in range(n)),(c,hex(p))
 assert m.r[29]==m.before[29] and all(m.r[i]==m.before[i] for i in (*range(16,24),28,30,31)) and m.f[20:]==m.before_f[20:]
def run():
 r=Path.cwd();o=r/'conker/build/game-attached-direction-151a87f8-screen';sy={a[1]:a[2][1] for a in symbol_rows((r/'conker/build/conker.us.elf').read_bytes())};programs=[bound_blob(*payload(o/f,'func_151A87F8'),sy) for f in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2]
 count=0;seen=set()
 for c in cases():
  initial=fixture(c);states=[]
  for i,p in enumerate(programs):m=Oracle(p,initial,c);m.run();verify(m,initial,c,raw=i==1);states.append(state(m));seen.update(m.visits)
  assert states[0]==states[2];count+=1
 missing=set(range(ENTRY,ENTRY+552,4))-seen;assert missing=={0x151a8844,0x151a89fc},[hex(a) for a in sorted(missing)]
 caller_cases=0;rom=(r/'conker/conker.us.bin').read_bytes();pc,end=0x151a7af0,0x151a7b1c;window=struct.unpack_from('>11I',rom,0x1d4fa0);assert struct.unpack_from('>I',rom,0x234404)[0]==ENTRY
 for valid,mutation,phase,length in itertools.product((0,1),(0,1),(0,8),(0.,2.5)):
  c=Case(active=valid,mutation=mutation,phase=phase,length=length);initial=fixture(c);put(initial,0x8008f944,ENTRY)
  for i,p in enumerate(programs):
   expected,calls,obs,answer=reference(initial,c,raw=i==1);code=dict(zip(range(ENTRY,ENTRY+552,4),p));code[end]=0;m=Oracle(window,initial,c,entry=pc,connected=code);m.r[16]=c.record;m.r[12]=4;m.r[8]=0xabcdef12;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('missing caller boundary')
   assert (public(m.memory),m.calls,m.observed,m.r[2],m.r[9],m.r[8])==(public(expected),[(ENTRY,(c.record,))]+calls,obs,answer,int(answer==0),0xabcdef12),c
  caller_cases+=1
 aliases=0
 for kind,phase,latched,length in itertools.product((0,1),(0,8),(0,1),(0.,2.5)):
  c=Case(phase=phase,latched=latched,length=length,cache=STACK+phase-0x30 if kind==0 else CACHE,target=TARGET if kind==0 else RECORD)
  initial=fixture(c);initial[c.target+59]=c.identity
  states=[]
  for p in (programs[0],programs[2]):m=Oracle(p,initial,c);m.run();verify(m,initial,c);states.append(state(m))
  assert states[0]==states[1];aliases+=1
 prefixes=0
 for c in (Case(mutation=1),Case(length=0.),Case(collision=0),Case(matrix=0)):
  initial=fixture(c);whole=Oracle(programs[0],initial,c);whole.run()
  for cut in range(whole.all_accesses):
   states=[]
   for p in (programs[0],programs[2]):
    m=Oracle(p,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('missing fired boundary')
    states.append(state(m))
   assert states[0]==states[1];prefixes+=1
 report=dict(cases=count,executions=(count+caller_cases)*3+aliases*2,caller_window_cases=caller_cases,guest_alias_cases=aliases,observed_words=len(seen),unreachable_retail_words=['0x151A8844','0x151A89FC'],access_prefixes=prefixes,helpers_modeled=True,raw_temporary_homes_separate=True)
 (o/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':run()
