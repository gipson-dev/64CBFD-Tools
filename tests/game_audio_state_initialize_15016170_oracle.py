"""SDK heap protocol, all state bytes and reverse pan address contract."""
from dataclasses import dataclass
import struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_table_payload_spawn_oracle import Oracle as PartialOracle
from tools.tests.game_seeded_sprite_oracle import Oracle as SignedAddOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY,ZERO,ALLOC,SET,CALLBACK=0x15016170,0x100226F0,0x10012844,0x151F3C34,0x151F3C4C
STATE,TABLE,REGISTER=0x800E0D80,0x8002BC10,0x800E0DFC
HEAPS=(0x30000,0x31000)
BUFFER,OTHER_BUFFER=0x50000,0x60000
QUEUE,HOOK=0x15043A00,0x151F3C1C
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
half=lambda n:((n&65535)^32768)-32768
data=lambda m,p,n:bytes(m[u32(p+i)]for i in range(n))

@dataclass(frozen=True)
class Case:
 heap:int=HEAPS[0]
 results:tuple=(0x70000,0x71000,0x72000)
 left:int=0x59C9
 right:int=0x5AE4
 mutation:int=0
 phase:int=0
 pattern:int=0
 real_heap:int=0
 limit:int=4096
 current:int=0
 buffer_alias:int=0
 table_alias:int=0

def symbols():return dict(D_800E0D80=STATE,D_8002BC10=TABLE,bzero=ZERO,alHeapDBAlloc=ALLOC,func_151F3C34=SET,func_151F3C4C=CALLBACK)
def table(c,s):return s['D_800E0D80']-110 if c.table_alias else s['D_8002BC10']
def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;m={STACK+i:(i*17+c.pattern*7+165)&255 for i in range(-2048,1024)}
 for p,n in((s['D_800E0D80']-128,416),(BUFFER,4096),(OTHER_BUFFER,4096),*[(h,16)for h in HEAPS]):m.update({p+i:(i*13+c.pattern*7+89)&255 for i in range(n)})
 for i in range(128):put(m,s['D_8002BC10']+2*i,(i*251+c.pattern*17)&32767,2)
 put(m,table(c,s)+128,c.left,2);put(m,table(c,s)+126,c.right,2)
 for h,base in zip(HEAPS,(s['D_800E0D80']if c.buffer_alias else BUFFER,OTHER_BUFFER)):
  put(m,h,base);put(m,h+4,base+c.current);put(m,h+8,c.limit);put(m,h+12,0x12345678)
 put(m,REGISTER,0x89ABCDEF);put(m,0x800E0E00,0x87654321);return m

def effect(m,c,s,stage,home):
 if c.mutation&1 and stage==0:put(m,home,HEAPS[1])
 if c.mutation&2 and stage in(1,2):put(m,home,HEAPS[0]if read(m,home)==HEAPS[1]else HEAPS[1])
 if c.mutation&4:
  for off in(0,4,0x18,0x34,0x98,0x9F):m[s['D_800E0D80']+off]=(c.pattern*17+stage*31+off)&255
 if c.mutation&8 and stage==3:
  put(m,table(c,s)+128,c.left^65535,2);put(m,table(c,s)+126,c.right^65535,2)

def allocate(m,h,size):
 n=(size+15)&~15;cur=read(m,h+4);end=u32(read(m,h)+read(m,h+8));nextcur=u32(cur+n)
 if nextcur<=end:put(m,h+4,nextcur);return cur
 return 0

def reference(initial,c=Case(),s=None,home=None,heap=None):
 s=symbols()if s is None else s;home=STACK+c.phase if home is None else home;heap=c.heap if heap is None else heap;m=dict(initial);calls=[];snapshots=[];d=s['D_800E0D80'];put(m,home,heap)
 def call(t,args):calls.append((t,tuple(map(u32,args))));snapshots.append(data(m,d,160))
 call(s['bzero'],(d,160))
 for i in range(160):m[d+i]=0
 effect(m,c,s,0,home)
 for i,(size,off)in enumerate(((80,8),(1088,0x74),(8,0x5C)),1):
  h=read(m,home);call(s['alHeapDBAlloc'],(0,0,h,1,size));v=allocate(m,h,size)if c.real_heap else c.results[i-1];effect(m,c,s,i,home)
  if i<3:put(m,d+off,v)
  else:third=v
 put(m,d+0xC,64,2);index=half(read(m,d+0xC,2))*2;put(m,d+0x96,64,2);aux=read(m,d+0x96,2);put(m,d+0xE,32767,2)
 put(m,d+0x5C,third);put(m,d+0x84,0);put(m,d+0x88,32767);m[d+0x9A]=0;put(m,d+0x32,0,2);put(m,d+0x30,0,2);put(m,d+0x94,aux,2)
 left=half(read(m,u32(s['D_8002BC10']+index),2));gain=half(read(m,d+0xE,2));put(m,d+0x10,signed(u32(left*gain))>>15,2)
 right=half(read(m,u32(s['D_8002BC10']+254-index),2));put(m,d+0x24,1,2);put(m,d+0x14,32764,2);put(m,d+0x16,0,2);put(m,d+0x12,signed(u32(right*gain))>>15,2)
 call(s['func_151F3C34'],(s['func_151F3C4C'],));put(m,REGISTER,s['func_151F3C4C']);return m,calls,snapshots

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None,arguments=None):
  self.c=c;self.s=symbols()if s is None else s;self.home=STACK+c.phase;self.allocation=0;self.snapshots=[]
  super().__init__(words,memory,c,entry=entry,arguments=(c.heap,)if arguments is None else arguments,connected=connected)
 def execute(self,w):
  if w>>26 in(34,38,42,46):return PartialOracle.execute(self,w)
  if w>>26==0 and w&63==32:return SignedAddOracle.execute(self,w)
  return super().execute(w)
 def record_call(self,t):
  n={self.s['bzero']:2,self.s['alHeapDBAlloc']:5,self.s['func_151F3C34']:1,ENTRY:1,QUEUE:3,HOOK:1}[t];a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==ENTRY:self.home=self.r[29]
  if t in(self.s['bzero'],self.s['alHeapDBAlloc'],self.s['func_151F3C34']):self.snapshots.append(data(self.memory,self.s['D_800E0D80'],160))
  if t==self.s['alHeapDBAlloc']:self.allocation+=1
 def hook(self,t):
  a=self.calls[-1][1];v=0x81234560
  if t==self.s['bzero']:
   for i in range(a[1]):self.memory[u32(a[0]+i)]=0
   effect(self.memory,self.c,self.s,0,self.home)
  elif t==self.s['alHeapDBAlloc']:
   v=allocate(self.memory,a[2],a[4])if self.c.real_heap else self.c.results[self.allocation-1];effect(self.memory,self.c,self.s,self.allocation,self.home)
  elif t==self.s['func_151F3C34']:put(self.memory,REGISTER,a[0])
  elif t==HOOK:put(self.memory,0x800E0E00,a[0])
  else:assert t==QUEUE
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(v)

def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.snapshots,m.current_pc,m.delay_of,m.all_accesses)
def observable(m,raw_fault=False):
 pc=m.root_entry+39*4 if raw_fault and m.current_pc==m.root_entry+38*4 else m.current_pc
 return(m.memory,m.r[16:24],m.r[28:32],m.f[20:],m.hi,m.lo,m.calls,m.events,m.trace,m.snapshots,pc,m.delay_of,m.all_accesses)
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def helpers(rom):
 code={}
 for e,p,n in((ZERO,0x226F0,40),(ALLOC,0x12844,35),(SET,0x2210E4,6)):code.update(zip(range(e,e+4*n,4),struct.unpack_from('>%dI'%n,rom,p)))
 return code
