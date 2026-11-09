"""Endpoint events: ordered big-endian state, original dispatcher and release path."""
from dataclasses import dataclass,replace
import struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import game_type46_record_update_150c5568_oracle as release
from tools.tests import game_actor_category_callback_oracle as category
from tools.experiments import game_endpoint_event_update_150ef910_match as source
OWNER,EVENT,MARK=0x200000,0x210000,0x220000
ENTRY=source.ENTRY;RELEASE=0x1516972C;DETACH=0x151696DC
PARENT,PARENT_ROM=0x1513DF9C,0x16B44C
TABLE,SWITCH=0x80089F64,0x800A5188
u32=lambda v:v&0xFFFFFFFF
signed8=lambda v:(v&255)-256 if v&128 else v&255

@dataclass(frozen=True)
class Case:
 command:int=0x2D
 first:int=0x300000
 second:int=0x310000
 before:int=0x300000
 after:int=0x310000
 first_identity:int=0x12
 second_identity:int=0x34
 event_identity:int=0x12
 discriminator:int=0xA7
 event_code:int=0xA7
 before_identity:int=0x56
 after_identity:int=0xE7
 owner:int=OWNER
 event:int=EVENT
 phase:int=0
 seed:int=0
 mode:int=0
 flags:int=0x400000
 category:int=7
 record_type:int=70
 depth:int=3
 cursor_match:bool=True
 next_record:int=0x240000

def arguments(c):return(c.owner,c.event,u32(c.command))
def symbols():return dict(func_1516972C=RELEASE)
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def observe(m,c):return(bytes(m[c.owner+0x110+i]for i in range(16)),bytes(m[c.event+i]for i in range(12)))

def fixture(c=Case()):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2304)}
 for base,size in((OWNER-64,0x300),(EVENT-64,128),(MARK,32)):
  m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(size)})
 p=c.owner+0x110;put(m,p,c.first);put(m,p+8,c.second);m[p+4]=c.first_identity;m[p+12]=c.second_identity;m[p+13]=c.discriminator
 put(m,c.event,c.before);put(m,c.event+4,c.after);m[c.event+8]=c.before_identity;m[c.event+9]=c.after_identity
 if c.command&255!=45:m[c.event+4]=c.event_identity;m[c.event+5]=c.event_code
 m[c.owner]=c.record_type;put(m,c.owner+8,c.next_record);put(m,c.owner+0x58,c.flags);m[c.owner+0x19]=c.category
 return m

def effect(m,c,p=None):
 p=c.owner if p is None else p;put(m,MARK,p);put(m,MARK+4,u32(c.command)&255)
 if c.mode&1:m[p+0x3C]^=0x55
 if c.mode&2:put(m,p+0x110,0x13579000)
 if c.mode&4:
  for i in range(4):put(m,STACK+c.phase+4*i,0xABCDEF00+i)
 if c.mode&8:
  for a in range(p-64,p+0x240):m.pop(a,None)

def reference(initial,c=Case(),helper=RELEASE,connected=False):
 m=dict(initial);p=c.owner+0x110;e=c.event;cmd=c.command&255;calls=[];snapshots=[];remove=False
 if cmd==0:
  current,first=read(m,p),read(m,e);identity,tag=m[p+4],m[e+4]
  remove=current==first or tag==identity
 elif cmd==45:
  current,first=read(m,p),read(m,e)
  if first==current:put(m,p,read(m,e+4));m[p+4]=m[e+9]
  elif read(m,e+4)==current:put(m,p,read(m,e));m[p+4]=m[e+8]
  if read(m,e)==read(m,p+8):put(m,p+8,read(m,e+4));m[p+12]=m[e+9]
  elif read(m,e+4)==read(m,p+8):put(m,p+8,read(m,e));m[p+12]=m[e+8]
 elif cmd==67:
  remove=(read(m,e)==read(m,p)or m[e+4]==m[p+4])and m[e+5]==m[p+13]
 if remove:
  calls.append((helper,(c.owner,)));snapshots.append(observe(m,c))
  if connected:
   calls.append((DETACH,(c.owner,)));release.detach_reference(m,c.owner)
   if m[c.owner]>=2:
    t=read(m,release.descriptor_pointer(m[c.owner])+0x28)or release.FALLBACK
    calls.append((t,(c.owner,)));m[c.owner+0x3C]^=0x55
  else:effect(m,c)
 return m,calls,snapshots

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,syms=None,connected=None):
  self.snapshots=[];self.target_entries=[];self.syms=syms or symbols()
  super().__init__(words,memory,c,entry=entry,s=self.syms,connected=connected,arguments=arguments(c))
 def record_call(self,t):
  if t==ENTRY:self.target_entries.append(tuple(map(u32,self.arguments(3))));args=self.target_entries[-1]
  elif t==self.syms['func_1516972C']:args=(u32(self.r[4]),);self.snapshots.append(observe(self.memory,self.case))
  elif t in category.CALLBACKS:args=tuple(map(u32,self.arguments(3)))
  else:args=(u32(self.r[4]),)
  self.calls.append((t,args));self.events.append(('CALL',t,args))
 def clobber(self):
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
 def hook(self,t):
  if t==self.syms['func_1516972C']:effect(self.memory,self.case,self.r[4])
  elif t in category.CALLBACKS:
   put(self.memory,MARK,t);put(self.memory,MARK+4,self.r[6]&255)
  else:raise AssertionError(hex(t))
  self.clobber()

def full_state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace,m.snapshots,m.target_entries)

def connected_fixture(c,rom):
 assert c.mode==0;m=fixture(c);m[release.COUNT]=c.depth&255
 for i in range(8):put(m,release.CURSORS+4*i,c.owner if c.cursor_match and i%2==0 else EVENT)
 for i,b in enumerate(rom[0x22FF68:0x22FF68+101*0x34]):m[release.DESCRIPTORS+i]=b
 return m

HELPERS=((RELEASE,0x196BDC,28),(DETACH,0x196B8C,20))
def helper_code(rom):
 code={}
 for entry,pos,n in HELPERS:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,pos)))
 return code

class ConnectedOracle(Oracle):
 def __init__(self,words,memory,c,rom,entry=ENTRY,connected=None):
  code=helper_code(rom);code.update(connected or{});super().__init__(words,memory,c,entry,connected=code)
 def hook(self,t):
  if t in category.CALLBACKS:return super().hook(t)
  # The descriptor destructor/fallback is bounded, not a full free path.
  self.memory[self.r[4]+0x3C]^=0x55;self.clobber()

def caller_machine(rom,words,c):
 m=connected_fixture(c,rom)
 for i,t in enumerate(category.CALLBACKS):put(m,TABLE+4*i,t)
 for i,off in enumerate(category.OFFSETS):put(m,SWITCH+4*i,PARENT+off)
 code=dict(zip(range(ENTRY,ENTRY+316,4),words))
 return ConnectedOracle(struct.unpack_from('>53I',rom,PARENT_ROM),m,c,rom,entry=PARENT,connected=code),m

def caller_reference(initial,c):
 index=category.MAPPING[c.category]if c.flags&0x400000 and c.category<13 else 0
 target=category.CALLBACKS[index];args=(c.owner,c.event,c.command&255)
 if target==ENTRY:
  m,calls,snaps=reference(initial,c,connected=True);return m,[(target,args)]+calls,snaps,[args]
 m=dict(initial);put(m,MARK,target);put(m,MARK+4,c.command&255)
 return m,[(target,args)],[],[]
