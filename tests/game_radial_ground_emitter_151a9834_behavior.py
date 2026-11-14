from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_direction_update_151a7a90_behavior as states
ENTRY,RANDOM,PLANE,GROUND=0x151a9834,0x150ada68,0x1514373c,0x15046c80
ORIGIN,INFO,TAG,TABLE,HEIGHT,FACTOR=0x30000,0x31000,0x32000,0x8008fa60,0x800a8f68,0x800a8f6c
CB0,CB1,ALT=0x151dbbd4,0x150df4b8,0x22000000
u32=lambda v:v&0xffffffff
fb=lambda v:bits(rounded(v))
@dataclass(frozen=True)
class Case:
 ground:int=0
 count:int=3
 selector:int=0
 channel:int=0xef
 context:int=0x87654321
 minimum:int=0xc0a00000
 radius:int=0x40000000
 hits:int=0xffffffff
 answer:int=1
 mutation:int=0
 phase:int=0
 seed:int=0
 origin:int=ORIGIN
 tag:int=TAG
def args(c):return c.origin,c.minimum,c.radius,c.ground,u32(c.count),u32(c.selector),c.tag,u32(c.channel),u32(c.context)
def homes(c):
 base=STACK+c.phase-0xb0;return base+0x80,base+0x74,c.ground or base+0x8c
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2304)}
 for p,n in ((c.origin,16),(INFO,36),(TAG,16)):
  m.update({p+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for i,v in enumerate((1.25,4.,-2.5)):put(m,c.origin+4*i,fb(v))
 if c.ground:
  m.update({c.ground+i:(i*29+c.seed*11+0x5a)&255 for i in range(36)});put(m,c.ground,fb(2.25));put(m,c.ground+24,0x12345678);m[c.ground+28]=0xa5;m[c.ground+29]=0x3c;put(m,c.ground+32,0x87654321)
 put(m,HEIGHT,0x47c34ff3);put(m,FACTOR,0x40490fdb);put(m,TABLE,CB0);put(m,TABLE+4,CB1);return m
def public(m):return {a:v for a,v in m.items() if not STACK-2048<=a<STACK+2304}
def vector(m,p):return tuple(read(m,p+4*i) for i in range(3))
def sample(c,n):return fb((.125,.75,.5,-.25,0.,1.)[(n+c.seed)%6])
def cosine(a):return fb(floating(fb(floating(a)*.125))+.5)
def sine(a):return fb(floating(fb(floating(a)*.25))-.25)
def effect(m,c,stage,ordinal,point,ground):
 if c.mutation&1:
  if stage=='random':
   put(m,FACTOR,fb(9.));put(m,HEIGHT,fb(17.));put(m,c.origin+4,fb(floating(read(m,c.origin+4))+10.))
  if stage=='plane':
   put(m,c.origin,fb(floating(read(m,c.origin))+7.));put(m,c.origin+8,fb(floating(read(m,c.origin+8))-3.))
  if stage=='ground':put(m,TABLE+(c.selector&255)*4,ALT if ordinal&1 else CB1)
 if c.mutation&2 and stage=='callback':
  put(m,c.origin,fb(floating(read(m,c.origin))+1.));put(m,c.origin+8,fb(floating(read(m,c.origin+8))-2.));put(m,point+4,fb(floating(read(m,point+4))+1.));put(m,ground,fb(floating(read(m,ground))+4.));put(m,TABLE+(c.selector&255)*4,CB0)
  if c.tag:m[c.tag]^=0x33
def query(m,point,ground,ordinal):
 for i,delta in enumerate((.25,.5,-.75)):put(m,point+4*i,fb(floating(read(m,point+4*i))+delta))
 put(m,ground,fb(floating(read(m,point+4))-2.));put(m,ground+24,read(m,ground+24)^0x10203);m[ground+28]^=0x80;m[ground+29]=(m[ground+29]+1)&255;put(m,ground+32,0xabc00000+ordinal)
def reference(initial,c,connected=False,trig=None):
 m=dict(initial);calls=[];obs=[];point,submitted,ground=homes(c);rng=0
 if not c.ground:put(m,ground,read(m,HEIGHT));put(m,ground+24,0);m[ground+28]=7;m[ground+29]=0;put(m,ground+32,0)
 put(m,point+4,read(m,c.origin+4));factor=read(m,FACTOR) if c.count>0 else 0
 for iteration in range(max(0,c.count)):
  first=sample(c,rng);calls.append((RANDOM,()));effect(m,c,'random',rng,point,ground);rng+=1
  second=sample(c,rng);calls.append((RANDOM,()));effect(m,c,'random',rng,point,ground);rng+=1
  angle=fb(floating(fb(floating(first)+floating(first)))*floating(factor));radius=fb(floating(second)*floating(c.radius));calls.append((PLANE,(angle,radius,point,point+8)))
  if connected:calls.extend(((trig['cosf'],(angle,)),(trig['sinf'],(angle,))))
  put(m,point,fb(floating(radius)*floating(sine(angle))));put(m,point+8,fb(floating(radius)*floating(cosine(angle))));effect(m,c,'plane',iteration,point,ground)
  put(m,point,fb(floating(read(m,point))+floating(read(m,c.origin))));put(m,point+8,fb(floating(read(m,point+8))+floating(read(m,c.origin+8))))
  calls.append((GROUND,(point,0,c.minimum,ground)));obs.append((GROUND,(vector(m,point),bytes(m[ground+i] for i in range(36)))));query(m,point,ground,iteration);effect(m,c,'ground',iteration,point,ground)
  if c.hits>>iteration&1 and u32(c.answer):
   for i,v in enumerate((read(m,point),read(m,ground),read(m,point+8))):put(m,submitted+4*i,v)
   target=read(m,TABLE+(c.selector&255)*4);calls.append((target,(submitted,ground,c.tag,c.channel&255,u32(c.context))));obs.append((target,(vector(m,submitted),m[c.tag] if c.tag else None)));effect(m,c,'callback',iteration,point,ground)
 return m,calls,obs
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None,trig=None):
  self.observed=[];self.draws=0;self.queries=0;self.planes=0;self.trig=trig or {};super().__init__(words,initial,c,entry=entry,arguments=args(c),connected=connected);self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in (0,1,2,6):
   if fn==6:self.f[fd]=self.f[fs]
   else:
    a,b=floating(self.f[fs]),floating(self.f[ft]);self.f[fd]=fb(a+b if fn==0 else a-b if fn==1 else a*b)
   self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  sizes={ENTRY:9,RANDOM:0,PLANE:4,GROUND:4,CB0:5,CB1:5,ALT:5,**{v:1 for v in self.trig.values()}};assert t in sizes,hex(t);a=tuple(self.arguments(sizes[t]))
  if t==PLANE:a=(self.f[12],self.f[14],*a[2:])
  if t in self.trig.values():a=(self.f[12],)
  self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==GROUND:self.observed.append((t,(vector(self.memory,a[0]),bytes(self.memory[a[3]+i] for i in range(36)))))
  if t in (CB0,CB1,ALT):self.observed.append((t,(vector(self.memory,a[0]),self.memory[a[2]] if a[2] else None)))
 def hook(self,t):
  c=self.case;m=self.memory;point,submitted,ground=homes(c);a=self.calls[-1][1];value=0;float_value=None
  if t==RANDOM:float_value=sample(c,self.draws);effect(m,c,'random',self.draws,point,ground);self.draws+=1
  elif t==PLANE:
   put(m,a[2],fb(floating(a[1])*floating(sine(a[0]))));put(m,a[3],fb(floating(a[1])*floating(cosine(a[0]))));effect(m,c,'plane',self.planes,point,ground);self.planes+=1
  elif t==GROUND:
   query(m,a[0],a[3],self.queries);effect(m,c,'ground',self.queries,point,ground);value=u32(c.answer) if c.hits>>self.queries&1 else 0;self.queries+=1
  elif t in (CB0,CB1,ALT):effect(m,c,'callback',self.queries-1,point,ground)
  elif t==self.trig.get('cosf'):float_value=cosine(a[0])
  elif t==self.trig.get('sinf'):float_value=sine(a[0]);effect(m,c,'plane',self.planes,point,ground);self.planes+=1
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=u32(0xa5000000+reg)
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
  if float_value is not None:self.f[0]=float_value
def cases():
 for i,(ground,count,hits,selector,mutation,phase,answer) in enumerate(itertools.product((0,INFO),(-1,0,1,3),(0,5,15),(0,0x12340001),(0,1,2,3),(0,8),(1,256))):
  yield Case(ground=ground,count=count,hits=hits,selector=selector,mutation=mutation,phase=phase,answer=answer,seed=i%3,channel=0x876500ef if i&1 else 0)
 for radius,answer in itertools.product((0.,-0.,-2.),(1,0x80000000)):yield Case(radius=fb(radius),answer=answer)
 yield Case(count=0,selector=255,tag=0)
def load():
 r=Path.cwd();o=r/'conker/build/game-radial-ground-emitter-151a9834-screen';sy={v[1]:v[2][1] for v in symbol_rows((r/'conker/build/conker.us.elf').read_bytes())};programs=[bound_blob(*payload(o/f,'func_151A9834'),sy) for f in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[1]==programs[2] and len(programs[0])==102
 rom=(r/'conker/conker.us.bin').read_bytes();plane=bound_blob(*payload(r/'conker/build/src/game_16EE20.c.o','func_1514373C'),sy);assert len(plane)==22 and tuple(plane)==struct.unpack_from('>22I',rom,0x170bec);code=dict(zip(range(PLANE,PLANE+88,4),plane));return rom,programs,code,{n:sy[n] for n in ('cosf','sinf')}
def verify(m,initial,c,connected=False,trig=None):
 expected,calls,obs=reference(initial,c,connected,trig);assert (public(m.memory),m.calls,m.observed)==(public(expected),calls,obs),c
 for p,n in ((c.origin,12),(homes(c)[2],36)):
  assert bytes(m.memory[p+i] for i in range(n))==bytes(expected[p+i] for i in range(n)),(c,hex(p))
def run():
 rom,programs,plane,trig=load();count=0;seen=set()
 for c in cases():
  initial=fixture(c);ss=[]
  for p in programs:m=Oracle(p,initial,c);m.run();verify(m,initial,c);ss.append(states.machine_state(m));seen.update(m.visits)
  assert ss[0]==ss[1]==ss[2];count+=1
 assert len(seen)==102
 coupled=0
 for ground,mutation,phase in itertools.product((0,INFO),(0,1,2,3),(0,8)):
  c=Case(ground=ground,mutation=mutation,phase=phase,count=2,hits=3);initial=fixture(c)
  for p in programs:m=Oracle(p,initial,c,connected=plane,trig=trig);m.run();verify(m,initial,c,True,trig)
  coupled+=1
 callers=0;windows=((0x150df468,0x150df4a4),(0x151cffac,0x151cffdc),(0x15136ec4,0x15136eec))
 for which,variant,mutation,phase in itertools.product(range(3),(0,1),(0,3),(0,8)):
  home=STACK+phase
  if which==0:c=Case(origin=home+0x48,ground=home+0x70,count=3+variant,selector=1,tag=0,minimum=fb(-996.),radius=fb(250.),context=0x81,phase=phase,mutation=mutation)
  elif which==1:c=Case(ground=INFO if variant else 0,count=7+variant,tag=home+0x9f,minimum=fb(-1996.),radius=fb(200.),phase=phase,mutation=mutation)
  else:c=Case(origin=home+0xac,ground=home+0x7c,count=18+variant,tag=home+0x47,minimum=fb(-496.),radius=fb(500.),phase=phase,mutation=mutation)
  initial=fixture(c);owner=0x33000;initial.update({owner+i:(i*19+0xa5)&255 for i in range(256)});initial[owner+12]=c.channel&255;initial[owner+1]=c.context&255
  expected,calls,obs=reference(initial,c);pc,end=windows[which];window=struct.unpack_from('>'+str((end-pc)//4)+'I',rom,pc-0x15000000+0x2d4b0)
  for p in programs:
   code=dict(zip(range(ENTRY,ENTRY+408,4),p));code[end]=0;m=Oracle(window,initial,c,entry=pc,connected=code)
   if which==0:m.r[16]=owner;m.r[12]=variant;m.f[8]=fb(4.);m.f[10]=fb(1000.)
   elif which==1:m.r[10]=variant;m.r[15]=c.channel&255;m.r[14]=u32(c.context);m.r[16]=c.origin;m.r[17]=c.ground;m.f[4]=c.minimum
   else:m.r[11]=c.count;m.r[12]=c.tag;m.r[15]=c.channel&255;m.r[24]=u32(c.context);m.f[16]=c.minimum;m.f[0]=c.radius
   m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('missing caller boundary')
   assert (public(m.memory),m.calls,m.observed)==(public(expected),[(ENTRY,args(c))]+calls,obs),(which,c)
   for ptr,n in ((c.origin,12),(homes(c)[2],36)):
    assert bytes(m.memory[ptr+i] for i in range(n))==bytes(expected[ptr+i] for i in range(n)),(which,c,hex(ptr))
   assert m.r[29]==home
  callers+=1
 aliases=0
 for kind,phase,mutation in itertools.product(range(3),(0,8),(0,3)):
  point,submitted,ground=homes(Case(phase=phase));c=Case(phase=phase,mutation=mutation)
  if kind==0:c=replace(c,origin=STACK+phase+0x180)
  elif kind==1:c=replace(c,origin=point)
  else:c=replace(c,ground=point-4)
  initial=fixture(c)
  for p in programs:m=Oracle(p,initial,c);m.run();verify(m,initial,c)
  aliases+=1
 prefixes=0
 for c in (Case(count=0),Case(ground=INFO,count=1,hits=0),Case(count=2,mutation=3),Case(count=1,answer=256)):
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
 report=dict(cases=count,observed_words=len(seen),coupled_plane_cases=coupled,actual_plane_words=22,caller_windows=3,caller_window_cases=callers,guest_alias_cases=aliases,access_prefixes=prefixes,trig_and_ground_providers_modeled=True)
 o=Path.cwd()/'conker/build/game-radial-ground-emitter-151a9834-screen';(o/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':run()
