"""Point-pair updater: cached/live deltas, byte gate, original helpers and caller."""
from dataclasses import dataclass,replace
import math,struct
from tools.experiments import game_type46_record_update_150c5568_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
RECORD,ALT,ACTOR,MATRICES=0x200000,0x210000,0x220000,0x230000
TABLE,LENGTH,RELEASE,CB0,CB1=0x80088760,0x15143E64,0x1516972C,0x150C5B88,0x150C5BD4
COUNT,CURSORS,DESCRIPTORS=0x800DD190,0x800DD198,0x8008B4A8
DETACH,FALLBACK,TRANSFORM=0x151696DC,0x15169804,0x15143134
WINDOW,END,WINDOW_ROM=0x15167164,0x1516719C,0x194614
POINTS=((0,0x80000000,0x3F800000,0,0,0),(0x3FA00000,0xC1900000,0x42C80000,0xBF000000,0x40000000,0x40400000),(1,0x80000001,0x00800000,0,0,0),(0x7FC12345,0x3F800000,0x40000000,0,0,0))
u32=lambda v:v&0xFFFFFFFF
signed8=lambda v:((v&255)^128)-128
sub=lambda a,b:bits(floating(a)-floating(b))

@dataclass(frozen=True)
class Case:
 flags:int=1
 selector:int=0
 points:tuple=POINTS[1]
 callback_result:int=1
 length_result:int=0x41280000
 mode:int=0
 gate:int=1
 phase:int=0
 record:int=RECORD
 seed:int=0

def symbols():return dict(D_80088760=TABLE,func_15143E64=LENGTH,func_1516972C=RELEASE)
def callback(index):return CB0 if index==0 else CB1 if index==1 else 0x18000000+4*(index&255)
def delta(m,p):return tuple(sub(read(m,p+0x18+4*i),read(m,p+0x24+4*i))for i in range(3))
def observe(m,p):return(p,read(m,p+0x10),m[p+0x30],*(read(m,p+x)for x in(0x18,0x1C,0x20,0x24,0x28,0x2C,0xC0)))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}

def fixture(c=Case(),s=None):
 s=s or symbols();m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,2304)}
 for p in(RECORD,ALT,c.record):
  for i in range(0x200):m.setdefault(p+i,(i*13+c.seed+0x59)&255)
  m[p]=70;m[p+1]=0;put(m,p+4,0);put(m,p+8,0);put(m,p+0x10,c.flags);m[p+0x30]=c.selector&255;m[p+0x38]=0;put(m,p+0xC0,0xC1200000)
  for i,v in enumerate(c.points):put(m,p+0x18+4*i,v)
 for index in range(-128,256):put(m,u32(s['D_80088760']+4*index),callback(index))
 return m

def callback_effect(m,c,p,home):
 axis=c.seed%3
 if c.mode&1:put(m,p+0x24+axis*4,bits(floating(read(m,p+0x24+axis*4))+1.0))
 if c.mode&2:
  for off in(0x18+axis*4,0x24+axis*4):put(m,p+off,bits(floating(read(m,p+off))+1.0))
 if c.mode&4:put(m,home,ALT)
 if c.mode&8:put(m,home-5,c.gate,1)
 if c.mode&16:
  for i,v in enumerate((0,0x3F800000,0x40000000)):put(m,home-20+4*i,v)
 if c.mode&1024:put(m,p+0x10,read(m,p+0x10)&~1)

def length_effect(m,c,p,home):
 if c.mode&32:put(m,home,ALT)
 if c.mode&64:put(m,p+0x20,0xC1980000)
 if c.mode&128:put(m,home-5,c.gate,1)

def release_effect(m,c,p):
 if c.mode&256:m[p+0x3C]^=0x55
 if c.mode&512:
  for i in range(0x200):m.pop(p+i,None)

def reference(initial,c=Case(),s=None,home=None):
 s=s or symbols();home=STACK+c.phase if home is None else home;m=dict(initial);p=c.record;calls=[];vectors=[];snapshots=[]
 if not read(m,p+0x10)&1:return m,calls,vectors,snapshots
 old=delta(m,p);gate=0;index=signed8(m[p+0x30])
 if index!=-1:
  put(m,home-5,0,1);put(m,home,p)
  for i,v in enumerate(old):put(m,home-20+4*i,v)
  calls.append((read(m,u32(s['D_80088760']+4*index)),(p,)));snapshots.append(observe(m,p));callback_effect(m,c,p,home)
  p=read(m,home);gate=read(m,home-5,1);old=tuple(read(m,home-20+4*i)for i in range(3))
  if u32(c.callback_result)==0:gate=1
 if not gate:
  new=delta(m,p)
  for i,v in enumerate(new):put(m,home-32+4*i,v)
  if any(floating(a)!=floating(b)for a,b in zip(new,old)):
   put(m,home-5,gate,1);put(m,home,p);calls.append((s['func_15143E64'],(home-32,)));vectors.append(new);snapshots.append(observe(m,p));length_effect(m,c,p,home)
   p=read(m,home);gate=read(m,home-5,1);put(m,p+0xC0,c.length_result)
 if gate:calls.append((s['func_1516972C'],(p,)));snapshots.append(observe(m,p));release_effect(m,c,p)
 return m,calls,vectors,snapshots

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None):
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=s or symbols(),connected=connected,arguments=(c.record,));self.record=c.record;self.vectors=[];self.snapshots=[];self.target_entries=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==4:self.f[w>>6&31]=bits(math.sqrt(floating(self.f[w>>11&31])))
  else:super().execute(w)
 def record_call(self,t):
  if t==source.ENTRY:self.target_home=self.r[29];self.record=self.r[4];self.target_entries.append(self.record);args=(self.record,)
  elif t==self.syms['func_15143E64']:
   args=(self.r[4],);self.vectors.append(tuple(read(self.memory,args[0]+4*i)for i in range(3)));self.snapshots.append(observe(self.memory,self.record))
  elif t==self.syms['func_1516972C']:self.record=self.r[4];args=(self.record,);self.snapshots.append(observe(self.memory,self.record))
  elif t in(CB0,CB1)or 0x18000000<=t<0x18000400:self.record=self.r[4];args=(self.record,);self.snapshots.append(observe(self.memory,self.record))
  else:raise AssertionError(hex(t))
  self.calls.append((t,args));self.events.append(('CALL',t,args))
 def clobber(self,value=0xA5000002):
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
 def hook(self,t):
  if t==self.syms['func_15143E64']:length_effect(self.memory,self.case,self.record,self.target_home);self.clobber();self.f[0]=self.case.length_result
  elif t==self.syms['func_1516972C']:release_effect(self.memory,self.case,self.record);self.clobber()
  else:
   callback_effect(self.memory,self.case,self.record,self.target_home)
   if self.case.mode&4:self.record=ALT
   self.clobber(self.case.callback_result)

def full_state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace,m.vectors,m.snapshots,m.target_entries)

HELPERS=((CB0,0xF3038,19),(CB1,0xF3084,40),(LENGTH,0x171314,12),(RELEASE,0x196BDC,28),(DETACH,0x196B8C,20))
@dataclass(frozen=True)
class ConnectedCase(Case):
 live:int=1
 identity:int=0xA7
 saved_identity:int=0xA7
 matrix:bool=False
 actor_points:tuple=(0x3F800000,0x40000000,0x40400000)
 transformed:tuple=(0xC0000000,0x40800000,0x40C00000)
 record_type:int=70
 depth:int=2
 cursor_match:bool=True
 next_record:int=0

def descriptor_pointer(index):return DESCRIPTORS+index*0x34
def connected_fixture(c,rom):
 assert c.mode==0;m=fixture(c)
 for i in range(0x400):m[ACTOR+i]=(i*7+0x59)&255;m[MATRICES+i]=(i*3+0x29)&255
 put(m,ACTOR,c.live);m[ACTOR+0x3B]=c.identity;put(m,ACTOR+0x1D4,MATRICES if c.matrix else 0)
 for i,v in enumerate(c.actor_points):put(m,ACTOR+0x14+4*i,v)
 for p in(RECORD,ALT,c.record):
  m[p]=c.record_type;put(m,p+0xC8,ACTOR);m[p+0xCC]=c.saved_identity;m[p+0xCD]=2
  for i,v in enumerate((0x3F000000,0xBF800000,0x40000000)):put(m,p+0xD0+4*i,v)
 put(m,c.record+8,c.next_record);m[COUNT]=c.depth&255
 for i in range(8):put(m,CURSORS+4*i,c.record if c.cursor_match and i%2==0 else ALT)
 # The two authentic callback entries and all 101 descriptor rows are retained.
 for i,b in enumerate(rom[0x22FF68:0x22FF68+101*0x34]):m[DESCRIPTORS+i]=b
 put(m,TABLE,CB0);put(m,TABLE+4,CB1)
 return m

def detach_reference(m,p):
 count=signed8(m[COUNT])
 for i in range(max(0,count)):
  if read(m,CURSORS+4*i)==p:put(m,CURSORS+4*i,read(m,p+8))

def connected_reference(initial,c,home=None):
 home=STACK+c.phase if home is None else home;m=dict(initial);p=c.record;calls=[];vectors=[];snapshots=[]
 if not read(m,p+0x10)&1:return m,calls,vectors,snapshots
 old=delta(m,p);gate=0;selector=signed8(m[p+0x30])
 if selector!=-1:
  t=read(m,TABLE+selector*4);calls.append((t,(p,)));snapshots.append(observe(m,p));alive=read(m,ACTOR)!=0
  accepted=alive and(selector==0 or m[p+0xCC]==m[ACTOR+0x3B])
  if accepted:
   if selector==1 and read(m,ACTOR+0x1D4):
    calls.append((TRANSFORM,(p+0xD0,p+0x24,MATRICES+128)));new=c.transformed
   else:new=tuple(read(m,ACTOR+0x14+4*i)for i in range(3))
   for i,v in enumerate(new):put(m,p+0x24+4*i,v)
  else:gate=1
 if not gate:
  new=delta(m,p)
  if any(floating(a)!=floating(b)for a,b in zip(new,old)):
   calls.append((LENGTH,(home-32,)));vectors.append(new);snapshots.append(observe(m,p));squares=[bits(floating(v)*floating(v))for v in new]
   value=bits(math.sqrt(floating(bits(floating(bits(floating(squares[0])+floating(squares[1])))+floating(squares[2])))));put(m,p+0xC0,value)
 if gate:
  calls.append((RELEASE,(p,)));snapshots.append(observe(m,p));calls.append((DETACH,(p,)));detach_reference(m,p)
  if m[p]>=2:
   target=read(m,descriptor_pointer(m[p])+0x28);calls.append((target or FALLBACK,(p,)));m[p+0x3C]^=0x55
 return m,calls,vectors,snapshots

def helper_code(rom):
 code={}
 for entry,pos,n in HELPERS:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,pos)))
 return code

class ConnectedOracle(Oracle):
 def __init__(self,words,memory,c,rom,entry=None,connected=None):
  code=helper_code(rom);code.update(connected or{});super().__init__(words,memory,c,entry=entry,connected=code)
 def record_call(self,t):
  if t in(source.ENTRY,CB0,CB1,LENGTH,RELEASE):return super().record_call(t)
  count=3 if t==TRANSFORM else 1;args=tuple(map(u32,self.arguments(count)));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  if t==TRANSFORM:
   a=self.calls[-1][1];assert a==(self.record+0xD0,self.record+0x24,MATRICES+128),a
   assert tuple(read(self.memory,a[0]+4*i)for i in range(3))==(0x3F000000,0xBF800000,0x40000000)
   for i,v in enumerate(self.case.transformed):put(self.memory,a[1]+4*i,v)
  else:self.memory[self.r[4]+0x3C]^=0x55
  self.clobber()

def caller_machine(rom,words,c):
 initial=connected_fixture(c,rom);code=dict(zip(range(source.ENTRY,source.ENTRY+316,4),words));code[END]=0
 m=ConnectedOracle(struct.unpack_from('>14I',rom,WINDOW_ROM),initial,c,rom,entry=WINDOW,connected=code)
 m.r[16]=c.record;m.r[17]=CURSORS+4*c.depth;m.r[18]=descriptor_pointer(70);m.r[19]=COUNT;m.r[20]=CURSORS;m.before=m.r[:]
 m.code=WindowCode(m.code,m);m.code.ends=(END,);return m,initial
