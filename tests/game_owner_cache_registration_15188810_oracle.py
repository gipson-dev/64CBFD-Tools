"""Independent counted-owner list contract, actual helper code and private-home mapping."""
from dataclasses import dataclass
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_keyed_buffer_registration_oracle import append
from tools.tests.game_table_payload_spawn_oracle import Oracle as PartialWordOracle

ENTRY=0x15188810
OWNER,NODES,OTHER,NEW,BUFFER=0x28000,0x30000,0x38000,0x60000,0x70000
HEAD,TABLE,JUMP=0x800DF7C8,0x800C4ED0,0x80096DF8
ALLOC,COUNT,FREE,ZERO,APPEND,CORE=0x10003C40,0x1502DB20,0x10004074,0x100226F0,0x15188A58,0x10003C6C
SPECIAL={59,117,130,136,144,150,152,156,157,159,160,177,178,180}
TIMERS=(-0x80000000,-32769,-32768,-1,0,32767,32768,65535,0x7FFFFFFF)
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:(n^0x80000000)-0x80000000
signed16=lambda n:((n&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
 nodes:int=0
 match:int=-1
 old:int=-1
 timer:int=32768
 mode:int=0xA5A50080
 count:int=2
 type:int=59
 outcome:int=2
 mutation:int=0
 phase:int=0
 residue:int=0
 node:int=NEW
 buffer:int=BUFFER

def symbols():return dict(D_800DF7C8=HEAD,allocate_memory=ALLOC,func_1502DB20=COUNT,func_10004074=FREE,bzero=ZERO,func_15188A58=APPEND)
def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;m={STACK+i:(i*17+165)&255 for i in range(-2048,1024)}
 for p,n in((OWNER,256),(NODES,512),(OTHER,32),(NEW,64),(BUFFER-16,4112),(s['D_800DF7C8']-4,12)):
  m.update({p+i:(i*13+89)&255 for i in range(n)})
 m[OWNER+4]=c.type
 for i in range(256):put(m,TABLE+2*i,1+i%3+(4 if i in SPECIAL else 0),2)
 put(m,TABLE+2*c.type,c.count+(4 if c.type in SPECIAL else 0),2)
 for i in range(4):
  p=NODES+32*i;put(m,p+16,OWNER if i==c.match or c.match==4 and i in(0,2)else OWNER+0x10000+i);put(m,p+12,NODES+32*(i+1)if i+1<c.nodes else 0);put(m,p+6,c.old,2)
 put(m,OTHER+12,0);put(m,OTHER+16,OWNER+0x5555);put(m,s['D_800DF7C8'],NODES if c.nodes else 0)
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def count_value(m,t):return u32(read(m,TABLE+2*t,2)-(4 if t in SPECIAL else 0))
def effect(m,c,s,stage,home):
 if stage==0:
  if c.mutation&1:put(m,OTHER+12,read(m,s['D_800DF7C8']));put(m,s['D_800DF7C8'],OTHER)
  if c.mutation&2:m[OWNER+4]^=0x5A
  if c.mutation&4:put(m,home+60,0x8123CD34);put(m,home+64,0xFFFFFF80)
 if stage==1 and c.mutation&8:
  m[c.node+5]=0xED
  for i in range(4096):m[c.buffer+i]=0xD3
 if stage==2 and c.mutation&16:m[c.node+4]=0xAB;put(m,c.node+6,0x8123,2)

def reference(initial,c=Case(),s=None,entered=None):
 s=symbols()if s is None else s;m=dict(initial);home=(STACK+c.phase if entered is None else entered)-56
 put(m,home+60,c.timer);put(m,home+64,c.mode);calls=[];p=read(m,s['D_800DF7C8'])
 while p:
  if read(m,p+16)==OWNER:
   if signed16(read(m,p+6,2))<signed(u32(c.timer)):put(m,p+6,c.timer,2)
   m[p+4]=c.mode&255;return m,calls
  p=read(m,p+12)
 def call(t,a,stage=None):
  calls.append((t,tuple(map(u32,a))))
  if stage is not None:effect(m,c,s,stage,home)
 call(s['allocate_memory'],(24,1,0,0),0)
 if c.outcome==0:return m,calls
 t=m[OWNER+4];call(s['func_1502DB20'],(t,));count=count_value(m,t)
 if count==0:call(s['func_10004074'],(c.node,));return m,calls
 size=u32(count*384);call(s['allocate_memory'],(size,1,1,1),1)
 if c.outcome==1:call(s['func_10004074'],(c.node,));return m,calls
 for off,v in((0,0),(1,3),(2,0),(3,20)):m[c.node+off]=v
 m[c.node+4]=read(m,home+64)&255;timer=read(m,home+60)
 put(m,c.node+8,c.buffer+c.residue);put(m,c.node+16,OWNER);put(m,c.node+20,0);put(m,c.node+6,timer,2)
 call(s['bzero'],(c.buffer+c.residue,size))
 for i in range(max(0,signed(size))):m[c.buffer+c.residue+i]=0
 effect(m,c,s,2,home);call(s['func_15188A58'],(c.node,s['D_800DF7C8']));append(m,c.node,s['D_800DF7C8'])
 return m,calls

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=symbols()if s is None else s;self.home=STACK+c.phase-56;self.allocations=0
  super().__init__(words,memory,c,entry=entry,arguments=(OWNER,u32(c.timer),u32(c.mode)),connected=connected)
 def execute(self,w):
  if w>>26 in(34,38,42,46):return PartialWordOracle.execute(self,w)
  return super().execute(w)
 def record_call(self,t):
  counts={ENTRY:3,self.s['allocate_memory']:4,self.s['func_1502DB20']:1,self.s['func_10004074']:1,self.s['bzero']:2,self.s['func_15188A58']:2,CORE:5,0x15188A9C:1}
  assert t in counts,('Unbounded owner registration provider',hex(t));a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==ENTRY:self.home=self.r[29]-56
 def hook(self,t):
  a=self.calls[-1][1];c=self.c;s=self.s;value=0xDEADBEEF
  if t in(s['allocate_memory'],CORE):
   stage=self.allocations;self.allocations+=1;effect(self.memory,c,s,stage,self.home);value=(c.node if c.outcome else 0)if stage==0 else(c.buffer+c.residue if c.outcome==2 else 0)
  elif t==s['func_1502DB20']:value=count_value(self.memory,a[0])
  elif t==s['func_10004074']:assert a==(c.node,)
  elif t==s['bzero']:
   n=max(0,signed(a[1]));assert n<=4096
   for i in range(n):self.put(a[0]+i,0,1)
   effect(self.memory,c,s,2,self.home)
  elif t==s['func_15188A58']:append(self.memory,*a)
  elif t==0x15188A9C:assert a==(OWNER,)
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def swapped(memory,entered):
 m=dict(memory);a,b=entered-24,entered-20
 for i in range(4):m[a+i],m[b+i]=m[b+i],m[a+i]
 return m
def state(m,raw=False,entered=None):
 entered=STACK+m.c.phase if entered is None else entered;memory=swapped(m.memory,entered)if raw else m.memory
 def events(rows):
  result=[]
  for row in rows:
   if raw and len(row)>=4 and row[0]in('R','W'):
    kind,p,n,v,*rest=row
    if entered-24<=p<entered-20:p+=4
    elif entered-20<=p<entered-16:p-=4
    row=(kind,p,n,v,*rest)
   result.append(row)
  return result
 return memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,events(m.events),events(m.trace),m.current_pc,m.delay_of,m.all_accesses

def helper_code(rom):
 code={}
 for e,p,n in((ALLOC,0x3C40,11),(COUNT,0x5AFD0,25),(ZERO,0x226F0,40),(APPEND,0x1B5F08,17)):
  import struct
  code.update(zip(range(e,e+4*n,4),struct.unpack_from('>%dI'%n,rom,p)))
 return code
