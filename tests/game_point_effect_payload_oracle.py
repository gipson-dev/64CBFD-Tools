"""Sparse point payload, live resolver mutations and original factory consumption."""
from dataclasses import dataclass
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY,OWNER,ALT,MATRIX,MARK=0x15193660,0x30000,0x31000,0x60000,0x70000
POINT,FACTORY,INTEGER,FLOAT,VECTOR,SPAWN,FLAG=0x15142314,0x15152520,0x150ADA20,0x150ADA68,0x15143794,0x15157898,0x800C3E90
U32=lambda v:v&0xFFFFFFFF
HALF=lambda v:((v&65535)^32768)-32768
GAPS=(118,119)
FIELDS=((0,8,4),(4,7,4),(0x14,0,2),(0x16,255,2),(0x18,-33,2),(0x1A,24,2),(0x30,40,2),(0x32,35,2),(0x34,160,4),(0x38,19,4),(0x3C,0,4),(0x70,33,1),(0x71,15,1),(0x72,25,2),(0x74,10,2))
FLOAT_FIELDS=((0x1C,2),(0x20,3),(0x24,4),(0x28,5),(0x2C,6),(0x44,7),(0x48,8),(0x50,0),(0x58,0),(0x5C,1),(0x64,1))

@dataclass(frozen=True)
class Case:
 owner:int=OWNER
 active:int=1
 attached:int=MATRIX
 mode:int=0x876543FF
 extra:int=0x80000001
 pattern:int=0
 mutation:int=0
 fixed:int=0
 phase:int=0
 seed:int=0
 lazy:bool=False

def cases():
 rows=[Case(mode=0x87650000|mode,extra=U32(mode*0x87654321),pattern=mode%8,mutation=mode%4,fixed=mode%2,phase=phase,seed=mode%8)for mode,phase in itertools.product(range(256),(0,8))]
 rows.extend(Case(owner=owner,active=active,attached=attached,fixed=fixed,mutation=mutation,phase=phase,pattern=i%8,mode=(0,1,255,256,0x80000000,0xFFFFFFFF)[i%6],extra=(0,1,0x80000000,0xFFFFFFFF)[i%4],seed=i%8)for i,(owner,active,attached,fixed,mutation,phase)in enumerate(itertools.product((0,OWNER,ALT),(0,1,256,0x80000000),(0,MATRIX),(0,1),(0,1,2,3,4,8,12),(0,8))))
 rows.extend((Case(owner=0,lazy=True),Case(active=0,lazy=True),Case(attached=0,lazy=True)))
 return rows

def constants(c,after=False):
 values=tuple(bits(v)for v in((.5,1.,2.,4.,8.,16.,32.,64.,128.),(0.,-0.,1.,-1.,.25,.5,2.,3.,4.),(-1.,2.,-3.,4.,-5.,6.,-7.,8.,-9.),(.125,.25,.5,1.,2.,4.,8.,16.,32.),(1e-20,2e-20,3e-20,4e-20,5e-20,6e-20,7e-20,8e-20,9e-20),(0.,0.,0.,0.,0.,0.,0.,0.,0.))[c.pattern%6])
 if c.pattern>=6:
  values=list(values);values[c.seed%9]=0x7FC12345 if c.pattern==6 else 0x7FA12345
 if after and c.mutation&1:values=[bits((i+1)*.75)for i in range(9)]
 return tuple(values)

def point(c):
 if not c.fixed:return tuple(bits((c.seed-4)*(.25+i))for i in range(3))
 highs=(32767,-32768,-1);lows=(-32768,32767,c.seed*257)
 return tuple(bits(floating(bits(float(lows[i])))+floating(bits(float(highs[i]*65536))))for i in range(3))

def point_words(c):
 return tuple(bits(floating(v)/65536.)for v in point(c))if c.fixed else point(c)

def data(m,p,n):return bytes(m[p+i]for i in range(n))
def fixture(c,s):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+165)&255 for i in range(-4096,2048)}
 for base,n in((OWNER,0x1D8),(ALT,0x1D8),(MATRIX,0x300),(MARK,256)):m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 if c.owner:put(m,c.owner,c.active);put(m,c.owner+0x1D4,c.attached)
 if c.lazy:
  if c.owner and not c.active:
   for i in range(4):m.pop(c.owner+0x1D4+i)
  return m
 m[FLAG]=c.fixed
 for j,v in enumerate(constants(c)):put(m,s['symbols']['D_800A%04X'%(0x81C0+4*j)],v)
 for i,v in enumerate(point_words(Case(seed=c.seed))):put(m,MATRIX+640+48+4*i,v)
 if c.fixed:
  for i,v in enumerate((32767,-32768,-1)):put(m,MATRIX+640+24+2*i,v,2)
  for i,v in enumerate((-32768,32767,c.seed*257)):put(m,MATRIX+640+56+2*i,v,2)
 return m

def effect(m,c,s,p,home=None):
 home=STACK+c.phase if home is None else home
 if c.mutation&1:
  for j,v in enumerate(constants(c,True)):put(m,s['symbols']['D_800A%04X'%(0x81C0+4*j)],v)
 if c.mutation&2:put(m,c.owner,0);put(m,c.owner+0x1D4,0)
 if c.mutation&4:put(m,home+4,0xABCDE080);put(m,home+8,0xDEADBEEF)
 if c.mutation&8:
  for i in GAPS:m[p+i]=0xD0+i-118

def reference(initial,c,s,home=None):
 m=dict(initial);home=STACK+c.phase if home is None else home;p=home-120
 if not c.owner or not c.active or not c.attached:return m,[],[]
 calls=[(s['point'],(c.attached,10,p+8))]
 for i,v in enumerate(point_words(c)):put(m,p+8+4*i,v)
 effect(m,c,s,p,home=home)
 for at,v,n in FIELDS:put(m,p+at,v,n)
 for i in range(8):m[p+0x68+i]=255
 for at,index in FLOAT_FIELDS:put(m,p+at,read(m,s['symbols']['D_800A%04X'%(0x81C0+4*index)]))
 for at in(0x40,0x4C,0x54,0x60):put(m,p+at,0)
 mode=0x80 if c.mutation&4 else c.mode&255;extra=0xDEADBEEF if c.mutation&4 else c.extra
 calls.append((s['factory'],(p,mode,U32(extra))));return m,calls,[(p,data(m,p,120))]

def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-4096<=a<STACK+c.phase+2048}
def ri(index,c):return(0,1,255,0xFFFFFFFF)[(index+c.seed)%4]
def rf(index,c):return bits((0.,.25,.5,.75)[(index+c.seed)%4])
def fm(a,b):return bits(floating(a)*floating(b))
def fa(a,b):return bits(floating(a)+floating(b))

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None,target=ENTRY):
  self.c,self.s,self.target,self.home=c,s,target,STACK+c.phase;self.packets=[];self.spawns=[];self.rng_i=self.rng_f=0;self.point_done=False;self.connected_point=bool(connected and s['point']in connected)
  super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=(c.owner,c.mode,c.extra))
 def get(self,p,n):
  if getattr(self,'recording',False)and self.own_instruction:assert all(p+i in self.memory for i in range(n)),('unmapped read',hex(p),n)
  return super().get(p,n)
 def execute(self,w):
  if self.connected_point and not self.point_done and self.current_pc==self.target+60:effect(self.memory,self.c,self.s,self.home-120,home=self.home);self.point_done=True
  op,rs,rt=w>>26,w>>21&31,w>>16&31
  if op not in(34,38,42,46):return super().execute(w)
  # Original consumer copies its aligned color words using big-endian unaligned pairs.
  prior=self.own_instruction;self.own_instruction=True
  try:
   at=U32(self.r[rs]+(((w&65535)^32768)-32768));base=at&~3;lane=at&3
   if op==34:
    n=4-lane;v=self.get(at,n);mask=(1<<(8*lane))-1;self.r[rt]=U32(v<<(8*lane))|(self.r[rt]&mask)
   elif op==38:
    n=lane+1;v=self.get(base,n);mask=U32(~((1<<(8*n))-1));self.r[rt]=(self.r[rt]&mask)|v
   elif op==42:
    n=4-lane;self.put(at,self.r[rt]>>(8*lane),n)
   else:
    n=lane+1;self.put(base,self.r[rt]&((1<<(8*n))-1),n)
   self.r[0]=0
  finally:self.own_instruction=prior
 def record_call(self,t):
  counts={self.target:3,self.s['point']:3,self.s['factory']:3,INTEGER:0,FLOAT:0,VECTOR:4,SPAWN:9};assert t in counts,hex(t)
  a=tuple(U32(v)for v in self.arguments(counts[t]));self.calls.append((t,a))
  if t==self.target:self.home=self.r[29]
  if t==self.s['factory']:self.packets.append((a[0],data(self.memory,a[0],120)))
  if t==SPAWN:self.spawns.append((a,data(self.memory,a[0],88),data(self.memory,a[1],48)))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1];value=0x76543210;fvalue=None
  if t==self.s['point']:
   assert a==(c.attached,10,self.home-112)
   for i,v in enumerate(point_words(c)):put(self.memory,a[2]+4*i,v)
   effect(self.memory,c,self.s,self.home-120,home=self.home);self.point_done=True
  elif t==INTEGER:value=ri(self.rng_i,c);self.rng_i+=1
  elif t==FLOAT:fvalue=rf(self.rng_f,c);self.rng_f+=1
  elif t==VECTOR:
   assert a[0]==U32(HALF(a[0]))and a[1]==U32(HALF(a[1]))
   vector=(bits(HALF(a[0])*.125),bits(HALF(a[1])*.25),fm(a[2],bits(.5)))
   for i,v in enumerate(vector):put(self.memory,a[3]+4*i,v)
  elif t==SPAWN:put(self.memory,MARK+4*(len(self.spawns)-1),len(self.spawns))
  else:assert t==self.s['factory']
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=U32(value)
  if fvalue is not None:self.f[0]=fvalue

def programs(output,layout):
 s=json.loads((output/'private-layout-v6.json').read_text())['layouts'][layout];entry=s['entry'];words=[]
 for label in('original','C','raw'):
  image=(output/('layout-%d-%s.elf'%(layout,label))).read_bytes();at=elf_slot_offset(image,entry,404);words.append(list(struct.unpack_from('>101I',image,at)))
 assert words[0]==words[1];return entry,s,words
def fullstate(m):return m.memory,m.r,m.f,m.trace,m.calls,m.packets,m.spawns,m.hi,m.lo,m.current_pc,m.delay_of,m.all_accesses
def visible(m):return m.memory,[m.r[i]for i in(*range(16,24),28,29,30,31)],m.f[20:],m.trace,m.calls,m.packets,m.spawns,m.hi,m.lo,m.current_pc,m.delay_of,m.all_accesses
def compare(models,c,expected,calls,packets):
 for m in models:
  assert(public(m.memory,c),m.calls,m.packets)==(public(expected,c),calls,packets),(c,m.calls,calls)
  assert m.r[29]==STACK+c.phase
 assert fullstate(models[0])==fullstate(models[1]),c
 assert visible(models[0])==visible(models[2]),c
def qualify(root,output):
 count=0;seen=set();modes=set()
 for layout in range(3):
  entry,s,words=programs(output,layout)
  for c in cases():
   initial=fixture(c,s);expected,calls,packets=reference(initial,c,s);models=[Oracle(code,initial,c,s,entry,target=entry).run()for code in words];compare(models,c,expected,calls,packets);count+=1;seen.update(v-layout*0x1000000 for m in models for v in m.visits)
   if packets:modes.add(calls[-1][1][1]);assert all(packets[0][1][i]==(0xD0+i-118 if c.mutation&8 else initial[packets[0][0]+i])for i in GAPS)
 assert seen==set(range(ENTRY,ENTRY+404,4))and modes==set(range(256))
 prefixes=0;entry,s,words=programs(output,0)
 for c in(Case(owner=0),Case(active=0,lazy=True),Case(attached=0,lazy=True),Case(),Case(mutation=15,phase=8)):
  initial=fixture(c,s);full=Oracle(words[0],initial,c,s,entry).run()
  for cut in range(full.all_accesses):
   models=[]
   for code in words:
    m=Oracle(code,initial,c,s,entry);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Access prefix did not fire')
    models.append(m)
   assert fullstate(models[0])==fullstate(models[1]);assert visible(models[0])==visible(models[2]);prefixes+=1
 return dict(success=True,corpus=len(cases()),cases=count,executions=count*3,layouts=3,covered_words=101,all256_mode_bytes=True,initialized_payload_bytes=118,untouched_padding_bytes=2,access_prefix_triples=prefixes,raw_caller_clobbered_scratch_not_equated=True,all_memory_and_saved_roles_and_calls_and_traces_equal=True)

def factory_reference(initial,c,s,rootcalls,packets):
 p,packet=packets[0];home=STACK+c.phase;sp=home-152-256;desc=sp+0xA4;vector=sp+0x70
 memory=dict(initial);calls=list(rootcalls);spawns=[];ni=nf=0
 get=lambda at,n=4:int.from_bytes(packet[at:at+n],'big')
 def integer():
  nonlocal ni
  calls.append((INTEGER,()));value=ri(ni,c);ni+=1;return value
 def real():
  nonlocal nf
  calls.append((FLOAT,()));value=rf(nf,c);nf+=1;return value
 count=get(0)+(integer()%(get(4)+1))
 for at,v,n in((0,get(0x70,1)|2,1),(1,0,1),(2,1,1),(3,255,1),(4,255,1),(8,get(0x34),4),(12,get(0x38),4),(16,0,4),(20,0x220405,4),(24,0x40200,4),(28,1,4),(32,0x38,4),(36,128,4),(40,32,4),(44,0,1),(45,8,1),(56,0,1),(60,0,4),(64,0,1),(65,2,1),(84,get(0x72,2),2),(86,get(0x74,2),2)):
  put(memory,desc+at,v,n)
 for i in range(8):memory[desc+48+i]=packet[0x68+i]
 for i in range(12):memory[desc+68+i]=packet[8+i]
 for number in range(count):
  life=HALF(get(0x30,2))+integer()%(HALF(get(0x32,2))+1);put(memory,desc+6,life,2)
  values=[fm(real(),bits(360.))for _ in range(3)]
  values.append(fa(fm(real(),get(0x4C)),get(0x48)))
  first,second=integer(),integer();sample=real()
  yaw=HALF(first%(HALF(get(0x16,2))+1)+HALF(get(0x14,2)))
  pitch=HALF(second%(HALF(get(0x1A,2))+1)+HALF(get(0x18,2)))
  radius=fa(fm(sample,get(0x20)),get(0x1C));calls.append((VECTOR,(U32(yaw),U32(pitch),radius,sp+0x80)))
  values.extend((bits(yaw*.125),bits(pitch*.25),fm(radius,bits(.5))))
  for amplitude,base in((0x5C,0x50),(0x60,0x54),(0x64,0x58),(0x2C,0x28),(0x44,0x40)):
   values.append(fa(fm(real(),get(amplitude)),get(base)))
  assert len(values)==12
  scale=values.pop();values.append(get(0x24))
  for i,v in enumerate(values):put(memory,vector+4*i,v)
  _,mode,extra=rootcalls[-1][1];args=(desc,vector,get(0x3C),scale,0,0,0,mode,extra)
  calls.append((SPAWN,args));spawns.append((args,data(memory,desc,88),data(memory,vector,48)));put(memory,MARK+4*number,number+1)
 return memory,calls,spawns

def helpers(root,output):
 rom=(root/'conker/conker.us.bin').read_bytes();image=(root/'conker/build/conker.us.elf').read_bytes();connected={}
 for entry,offset,n in((POINT,0x16F7C4,49),(FACTORY,0x17F9D0,213)):
  raw=rom[offset:offset+4*n]
  if entry==POINT:
   at=elf_slot_offset(image,entry,4*n);assert image[at:at+4*n]==raw
  connected.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,raw)))
 entry,s,words=programs(output,0);seen=set();count=0;particle_counts=set();retained_factory_at=elf_slot_offset(image,FACTORY,12);assert image[retained_factory_at:retained_factory_at+12]!=rom[0x17F9D0:0x17F9DC]
 for seed,fixed,mutation,phase in itertools.product(range(4),(0,1),(0,1,2,3,4,8,12),(0,8)):
  c=Case(seed=seed,fixed=fixed,mutation=mutation,phase=phase,pattern=0,mode=(0,255,0x80000000,0xFFFFFFFF)[seed],extra=(0,1,0x80000000,0xFFFFFFFF)[seed]);initial=fixture(c,s)
  expected,rootcalls,packets=reference(initial,c,s);expected,calls,spawns=factory_reference(expected,c,s,rootcalls,packets)
  models=[Oracle(code,initial,c,s,entry,connected=connected).run()for code in words]
  compare(models,c,expected,calls,packets)
  for m in models:assert m.spawns==spawns,(c,m.spawns[:1],spawns[:1])
  seen.update(v for m in models for v in m.visits);particle_counts.add(len(spawns));count+=1
 traps={pc for pc,w in connected.items()if w&0xFC00003F==13}
 assert len(traps)==4 and set(connected)-traps<=seen and not(traps&seen)
 return dict(success=True,cases=count,executions=count*3,point_words=49,factory_words=213,covered_nontrap_helper_words=len(set(connected)-traps),unreachable_division_traps=4,particle_counts=sorted(particle_counts),retained_point_equals_original=True,factory_is_still_an_unrestored_stub=True,original_factory_only_executed_in_test=True,independent_all_spawn_arguments_and_descriptor_vector_snapshots=True,opaque_integer_float_spherical_and_spawn_providers=True,private_stack_mutations_guest_only=True)
