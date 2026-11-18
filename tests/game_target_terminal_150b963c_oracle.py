"""Independent cached-target, bounce, steering and complete terminal descriptors."""
from dataclasses import dataclass
import itertools,json,math
from tools.experiments import game_target_terminal_150b963c_screen as s
from tools.tests import test_game_point_interval_effect_match as g
ENTRY=s.ENTRY;STACK=g.STACK
ACTOR,FIRST,SECOND,ALTERNATE,OUTPUT,SPRAY_OUTPUT=0x30000,0x70000,0x71000,0x72000,0x50000,0x60000
RESOLVE,TRIG,RNG,REAL,QUERY,FACTORY,COPY,SPRAY,SOUND=0x15083e90,0x151423d8,0x150ada20,0x150ada68,0x15046c80,0x1513d594,0x10022ec0,0x15151a38,0x10010f88
put,read=g.put,g.read;sym=s.symbols()
CACHE1,CACHE2,DESTINATION,SOUND_ID=(sym[n]for n in('D_80088730','D_80088720','D_80088724','D_80088740'))
CONSTANTS=tuple(sym['D_8009FD'+n]for n in('E0','E4','E8','EC','F0','F4','F8','FC'))+(sym['D_8009FE00'],)
ASSET=sym['D_800A4AA0']

@dataclass(frozen=True)
class Case:
 actor:int=ACTOR;mode:int=0;amount:int=0;phase:int=0;fcsr:int=0
 first_mode:int=3;second_mode:int=3;resolve_first:int=1;resolve_second:int=1
 distance:int=0x41200000;radius:int=0;speed:int=0x41a00000
 random_bit:int=0;query:int=1;success:int=1;mutation:int=0;flags:int=0

def layout(h,kind):
 shift=8 if kind=='raw'else 0;b=h-384
 return {n:b+off+shift for n,off in(('burst',0x104),('extra',0xfc),('spray',0x74),('position',0x15c))}
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+2048}
def add(a,b):return g.single(g.floating(a)+g.floating(b))
def sub(a,b):return g.single(g.floating(a)-g.floating(b))
def trunc(a):return g.u32(math.trunc(g.floating(a)))
def randoms(c):return(c.random_bit,0xffffffff-c.flags,c.flags&1,c.flags>>1,0xffffff00|c.flags)
def fixture(c,kind='retail',home=None):
 h=STACK+c.phase if home is None else home;m={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
 m.update({CACHE2+i:(i*13+91)&255 for i in range(36)})
 for base,n in((ACTOR,384),(FIRST,128),(SECOND,128),(ALTERNATE,128),(OUTPUT,512),(SPRAY_OUTPUT,136)):
  m.update({base+i:(i*13+91)&255 for i in range(n)})
 for n,size in(('burst',88),('extra',8),('spray',136),('position',12)):
  for i in range(size):m[layout(h,kind)[n]+i]=(i*29+0x61)&255
 for off,v in((0x10,c.radius),(0x38,c.distance),(0x3c,0),(0x40,0),(0x20,g.bits(1.25)),(0x24,g.bits(-2.5)),(0x28,g.bits(3.75)),(0x44,g.bits(4.25)),(0x48,g.bits(5.5)),(0x4c,g.bits(6.75)),(0x60,0x12340000),(0x128,0x12345678),(0x14c,0x23456789),(0x168,0x34567890)):put(m,ACTOR+off,v)
 m[ACTOR+1]=5;m[ACTOR+0xc]=255;m[ACTOR+0x72]=1
 for base,mode in((FIRST,c.first_mode),(SECOND,c.second_mode),(ALTERNATE,3)):
  put(m,base,0 if mode==1 else 0x87654321);m[base+0x3b]=2 if mode==2 else 1
  for off,v in((0x14,0.),(0x18,0.),(0x1c,0.)):put(m,base+off,g.bits(v))
  put(m,base+0x3c,c.speed if base==FIRST else g.bits(27.5));put(m,base+0x76,0xc1ff if base!=ALTERNATE else 0x7f03,2)
 put(m,CACHE1,FIRST if c.first_mode else 0);put(m,CACHE2,SECOND if c.second_mode else 0)
 for i,v in enumerate((11.25,-12.5,13.75)):put(m,DESTINATION+4*i,g.bits(v))
 values=(2500.,1.299999952,1.299999952,.001000000047,.000009999999747,3.100000143,.7050000429,.3100000024,.200000003)
 for at,v in zip(CONSTANTS,values):put(m,at,g.bits(v))
 put(m,SOUND_ID,0x1234);return m

def resolver_effect(m,c,index):
 if c.mutation&1:
  put(m,ACTOR+0x20,g.bits(6.25));put(m,ACTOR+0x10,g.bits(3.));put(m,DESTINATION+4,g.bits(-24.5))
 return (FIRST if c.resolve_first else 0)if index==0 else(SECOND if c.resolve_second else 0)
def rng_effect(m,c,index,roles):
 if c.mutation&2:
  put(m,CACHE1,ALTERNATE);put(m,ACTOR+0x128,0x55667788)
  if index>0:put(m,roles['position'],g.bits(-14.5))
def trig_effect(m,c,index):
 if c.mutation&4:
  put(m,CACHE1,ALTERNATE);put(m,ALTERNATE+0x76,0xff80,2);put(m,ALTERNATE+0x3c,g.bits(31.25))
 return g.bits(.5 if index==0 else -.25)
def real_effect(m,c,index,roles):
 if c.mutation&8:
  put(m,ACTOR+0x60,0x76540000);put(m,ACTOR+0x128,0x66778899)
  put(m,CONSTANTS[3],g.bits(.002));put(m,CONSTANTS[4],g.bits(.00002));put(m,CACHE1,ALTERNATE)
 return g.bits(.5 if index==0 else .25)
def query_effect(m,c,roles):
 for i in range(36):m[ACTOR+0x110+i]=(i*37+0x31)&255
 put(m,ACTOR+0x110,g.bits(7.5));put(m,roles['position'],g.bits(-1.25));put(m,roles['position']+8,g.bits(3.75))
def factory_effect(m,c,roles):
 if c.success:
  for i in range(88):m[OUTPUT+0x10+i]=m[roles['burst']+i]
 if c.mutation&16:
  for off,v in((0x38,-9.5),(0x3c,10.25),(0x40,11.75)):put(m,ACTOR+off,g.bits(v))
  put(m,ACTOR+0x14c,0x778899aa);put(m,ACTOR+0x168,0x8899aabb);m[ACTOR+0xc]=0x33;m[ACTOR+1]=7;put(m,CONSTANTS[5],g.bits(.875))
def spray_effect(m,c,roles):
 for i in range(136):m[SPRAY_OUTPUT+i]=m[roles['spray']+i]
 if c.mutation&32:
  for off,v in((0x38,19.5),(0x3c,-20.25),(0x40,21.75)):put(m,ACTOR+off,g.bits(v))

def reference(initial,c,kind='retail',home=None):
 h=STACK+c.phase if home is None else home;m=dict(initial);roles=layout(h,kind);calls=[];obs=[];a=ACTOR;ri=fi=0
 def field(base,off,v,n=4):put(m,base+off,v,n)
 def resolve(index,cache):
  calls.append((RESOLVE,(1,)));put(m,cache,resolver_effect(m,c,index));return read(m,cache)
 def rng():
  nonlocal ri
  calls.append((RNG,()));value=randoms(c)[ri];rng_effect(m,c,ri,roles);ri+=1;return value
 def real():
  nonlocal fi
  calls.append((REAL,()));v=real_effect(m,c,fi,roles);fi+=1;return v
 target=read(m,CACHE1)
 if not target or not read(m,target)or m[target+0x3b]!=1:target=resolve(0,CACHE1)
 close=False
 if target:
  delta=[sub(read(m,a+dst),read(m,target+src))for dst,src in((0x38,0x14),(0x3c,0x18),(0x40,0x1c))]
  distance=add(add(g.product(delta[0],delta[0]),g.product(delta[1],delta[1])),g.product(delta[2],delta[2]))
  radius=read(m,a+0x10);close=g.floating(distance)<g.floating(add(g.product(radius,radius),read(m,CONSTANTS[0])))
 if close:
  if g.floating(read(m,target+0x3c))>15. and rng()&1:
   angle=read(m,read(m,CACHE1)+0x76,2)>>8;calls.append((TRIG,(angle,)));sine=trig_effect(m,c,0)
   angle=((read(m,read(m,CACHE1)+0x76,2)>>8)+64)&255;calls.append((TRIG,(angle,)));cosine=trig_effect(m,c,1)
   m[a+0x71]=1;put(m,a+0x60,read(m,a+0x60)|0x7d);m[a+0x73]=m[a+0x75]=1;m[a+0x78]=0
   put(m,a+0x44,g.product(g.product(read(m,read(m,CACHE1)+0x3c),sine),read(m,CONSTANTS[1])))
   put(m,a+0x48,add(g.product(real(),g.bits(15.)),g.bits(10.)))
   value=g.product(g.product(read(m,read(m,CACHE1)+0x3c),cosine),read(m,CONSTANTS[2]));put(m,a+0x64,300,2);put(m,a+0x60,read(m,a+0x60)|0x80)
   for off in(0x20,0x24,0x28):put(m,a+off,0)
   put(m,a+0x4c,value);return public(m),calls,obs,1
  point=roles['position']
  for off,v in((0,read(m,a+0x38)),(4,add(read(m,a+0x3c),g.bits(100.))),(8,read(m,a+0x40))):field(point,off,v)
  calls.append((QUERY,(point,0,sub(read(m,a+0x3c),g.bits(2000.)),a+0x110)));query_effect(m,c,roles)
  if c.query:
   put(m,point+4,read(m,a+0x110));d=roles['burst'];extra=roles['extra']
   for off,v,n in((0x54,25,2),(0x56,10,2),(0,4,1),(1,0,1),(2,0x3b02,2)):field(d,off,v,n)
   field(d,4,rng()%31+40,2);field(d,8,0);field(d,12,0)
   for off in range(16,20):field(d,off,255,1)
   value=g.product(add(g.product(real(),g.bits(25.)),g.bits(25.)),read(m,CONSTANTS[3]));field(d,0x14,value);field(d,0x18,value)
   for i in range(12):m[d+0x1c+i]=m[point+i]
   field(d,0x40,0xc5c0001)
   for off,v in((0x44,255),(0x45,255),(0x46,0),(0x47,7)):field(d,off,v,1)
   for off in range(0x28,0x40,4):field(d,off,0)
   value=g.product(add(g.product(real(),g.bits(80.)),g.bits(50.)),read(m,CONSTANTS[4]));field(extra,0,value);field(d,0x50,read(m,a+0x128))
   first,second,third=rng(),rng(),rng();args=(d,ASSET,24,0,0,(second&1)+((first&1)<<1),third&255,g.bits(500.),g.bits(500.),0,a+0x114,read(m,a+0x14c),read(m,a+0x168),0,8,m[a+0xc],m[a+1]);calls.append((FACTORY,args));obs.append(('burst',data(m,d,88)));factory_effect(m,c,roles)
   if c.success:
    calls.append((COPY,(OUTPUT+0x128,extra,8)));obs.append(('extra',data(m,extra,8)))
    for i in range(8):m[OUTPUT+0x128+i]=m[extra+i]
  d=roles['spray']
  for i in range(12):m[d+i]=m[a+0x38+i]
  for off,v in((0x24,6),(0x26,6),(0x28,0),(0x2a,255),(0x2c,-64),(0x2e,30),(0x30,3),(0x32,3),(0x34,30),(0x36,20),(0x80,10),(0x82,25)):field(d,off,v,2)
  for off,v in((0xc,g.bits(3.)),(0x10,read(m,CONSTANTS[5])),(0x14,read(m,CONSTANTS[6])),(0x18,read(m,CONSTANTS[7])),(0x1c,g.bits(5.)),(0x20,g.bits(7.)),(0x3c,1),*((off,0)for off in range(0x40,0x54,4)),(0x58,read(m,a+0x14c)),(0x5c,read(m,a+0x168)),(0x60,0),(0x64,0x220005),(0x68,0x1d0600),(0x6c,1),(0x70,0x3b),(0x74,0x80),(0x78,0x20),(0x84,read(m,a+0x128))):field(d,off,v)
  for off,v in((0x38,1),(0x39,33),(0x3a,72),(0x54,0),(0x55,154),(0x56,101),(0x7c,0),(0x7d,7)):field(d,off,v,1)
  calls.append((SPRAY,(d,m[a+0xc],m[a+1])));obs.append(('spray',data(m,d,136)));spray_effect(m,c,roles)
  calls.append((SOUND,(read(m,SOUND_ID),25000,0,0,0,*(trunc(read(m,a+off))for off in(0x38,0x3c,0x40)),1000,4000)));return public(m),calls,obs,0
 target=read(m,CACHE2)
 if not target or not read(m,target)or m[target+0x3b]!=1:target=resolve(1,CACHE2)
 if target:
  put(m,DESTINATION,read(m,target+0x14));put(m,DESTINATION+4,add(read(m,target+0x18),g.bits(50.)));put(m,DESTINATION+8,read(m,target+0x1c))
 values=[read(m,a+off)for off in(0x20,0x24,0x28)];factor=read(m,CONSTANTS[8])
 for i,v in enumerate(values):put(m,a+0x20+4*i,add(v,g.product(factor,sub(read(m,DESTINATION+4*i),v))))
 return public(m),calls,obs,1

class Oracle(g.Oracle):
 def __init__(self,words,c,kind='retail',initial=None,home=None,entry=ENTRY,connected=None):
  self.cc=c;self.kind=kind;self.home=STACK+c.phase if home is None else home;self.roles=layout(self.home,kind);self.i=self.j=self.k=0;self.obs=[]
  super().__init__(words,fixture(c,kind,self.home)if initial is None else initial,c,entry=entry,connected=connected);self.r[4]=ACTOR
 def execute(self,w):
  op,rs=w>>26,w>>21&31
  if op in(42,46):
   at=g.u32(self.r[rs]+((w&65535)^32768)-32768);v=self.r[w>>16&31];k=at&3
   if op==42:self.put(at,v>>(8*k),4-k)
   else:self.put(at&~3,v,k+1)
  else:super().execute(w)
 def record_call(self,t):
  n={RESOLVE:1,TRIG:1,RNG:0,REAL:0,QUERY:4,FACTORY:17,COPY:3,SPRAY:3,SOUND:10}[t];args=tuple(map(g.u32,self.arguments(n)));self.calls.append((t,args))
  if t in(FACTORY,SPRAY,COPY):self.obs.append(('burst'if t==FACTORY else'spray'if t==SPRAY else'extra',data(self.memory,args[1]if t==COPY else args[0],88 if t==FACTORY else 136 if t==SPRAY else 8)))
 def hook(self,t):
  c=self.cc;m=self.memory;args=self.calls[-1][1];value=0x12345678;floating=None
  if t==RESOLVE:
   index=0 if len([x for x in self.calls if x[0]==RESOLVE])==1 and(c.first_mode!=3)else 1
   value=resolver_effect(m,c,index)
  elif t==TRIG:floating=trig_effect(m,c,self.k);self.k+=1
  elif t==RNG:rng_effect(m,c,self.i,self.roles);value=randoms(c)[self.i];self.i+=1
  elif t==REAL:floating=real_effect(m,c,self.j,self.roles);self.j+=1
  elif t==QUERY:query_effect(m,c,self.roles);value=c.query
  elif t==FACTORY:factory_effect(m,c,self.roles);value=OUTPUT if c.success else 0
  elif t==COPY:
   for i in range(args[2]):m[args[0]+i]=m[args[1]+i]
   value=args[0]
  elif t==SPRAY:spray_effect(m,c,self.roles)
  else:assert t==SOUND
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=g.u32(value)
  if floating is not None:self.f[0]=floating

def cases():
 for i,(distance,speed,random_bit,query,success,mutation,phase)in enumerate(itertools.product((0.,49.999,50.,50.001,100.),(15.,15.000001,20.),(0,1),(0,1),(0,1),(0,1,2,4,8,16,32,63),(0,8))):
  yield Case(distance=g.bits(distance),speed=g.bits(speed),random_bit=random_bit,query=query,success=success,mutation=mutation,phase=phase,flags=i%4,first_mode=(i//2)%4,second_mode=(i//8)%4,resolve_first=(i//32)%2,resolve_second=(i//64)%2)

def run(state):
 count=0;seen={'raw':set(),'retail':set()}
 for c in cases():
  for kind in('retail','raw'):
   initial=fixture(c,kind);want=reference(initial,c,kind);m=Oracle(state[kind+'_words'],c,kind,initial);before,fp=m.r[:],m.f[:];m.run()
   actual=public(m.memory),m.calls,m.obs,m.r[2]
   assert actual==want,(kind,c,actual[1:],want[1:])
   assert m.r[16:24]==before[16:24]and m.r[28:]==before[28:]and m.f[20:]==fp[20:]
   seen[kind].update(m.visits)
  count+=1
 report=dict(passes=True,cases=count,programs=2,retail_words_visited=len(seen['retail']),raw_words_visited=len(seen['raw']),unvisited_retail_words=[i for i in range(438)if ENTRY+4*i not in seen['retail']],complete88_and136_descriptors=True,all8_extra_bytes=True,cached_target_refresh=True,provider_mutations=True,source_installed=False,c_match_credit=0)
 (s.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
