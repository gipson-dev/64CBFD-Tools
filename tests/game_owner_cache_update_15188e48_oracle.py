"""Matrix-history reference, observable access prefixes and original helper execution."""
from dataclasses import dataclass
import struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_table_payload_spawn_oracle import Oracle as PartialWordOracle
from tools.tests.game_seeded_sprite_oracle import Oracle as SignedCopyOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read

ENTRY,COUNT,COPY=0x15188E48,0x1502DB20,0x10023A10
RECORD,OWNER,OTHER,SOURCE,OTHER_SOURCE=0x30000,0x50000,0x51000,0x70000,0x71000
BUFFERS=(0x100000,0x200000)
FLAG,TABLE,JUMP,REGISTRY=0x800BE9C0,0x800C4ED0,0x80096DF8,0x8008D580
CAPACITY=65536
SPECIAL={59,117,130,136,144,150,152,156,157,159,160,177,178,180}
u32=lambda n:n&0xFFFFFFFF

@dataclass(frozen=True)
class Case:
 snapshots:int=3
 matrices:int=1
 page:int=0
 filled:int=0
 type:int=59
 mutation:int=0
 missing:int=0
 alias:int=0
 phase:int=0
 residue:int=0
 source_residue:int=0
 seed:int=0

def symbols():return dict(D_800BE9C0=FLAG,func_1502DB20=COUNT,bcopy=COPY)
def pattern(c,bank,offset):return(offset*13+bank*29+c.seed*7+89)&255
def source_pointer(c):return 0 if c.missing else BUFFERS[0]+(0 if c.alias==1 else 192)if c.alias else SOURCE+c.source_residue
def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;m={STACK+i:(i*17+165)&255 for i in range(-2048,1024)}
 for p,n in((RECORD,32),(OWNER,512),(OTHER,512),(SOURCE,256),(OTHER_SOURCE,256)):
  m.update({p+i:(i*13+c.seed*7+89)&255 for i in range(n)})
 m[RECORD+1]=c.snapshots;m[RECORD+2]=c.filled;m[OWNER+4]=c.type;m[OTHER+4]=(c.type+17)&255
 put(m,RECORD+8,BUFFERS[0]+c.residue);put(m,RECORD+16,OWNER);put(m,OWNER+0x1D4,source_pointer(c));put(m,OTHER+0x1D4,OTHER_SOURCE+c.source_residue)
 m[s['D_800BE9C0']]=c.page
 for t in range(256):put(m,TABLE+2*t,1+(4 if t in SPECIAL else 0),2)
 put(m,TABLE+2*c.type,c.matrices+(4 if c.type in SPECIAL else 0),2)
 for bank,base in enumerate(BUFFERS):
  regions=[(0,384)]
  for page in{c.page,c.page^1}:
   start=page*c.snapshots*c.matrices*64;regions.append((start,(c.snapshots+1)*c.matrices*64+64))
  for start,n in regions:
   for i in range(max(-c.residue,start-16),start+n+16):m[base+c.residue+i]=pattern(c,bank,c.residue+i)
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def count_value(m,t):return u32(read(m,TABLE+2*t,2)-(4 if t in SPECIAL else 0))
def count_effect(m,c,s):
 if c.mutation&1:
  m[s['D_800BE9C0']]^=1;m[RECORD+1]^=1;m[RECORD+2]=c.snapshots;put(m,RECORD+8,BUFFERS[1]+c.residue);put(m,RECORD+16,OTHER)
def copy_effect(m,c,s,ordinal):
 if ordinal!=1:return
 if c.mutation&2:
  m[s['D_800BE9C0']]^=1;m[RECORD+1]^=1;m[RECORD+2]=c.snapshots
  put(m,RECORD+8,(BUFFERS[0]if read(m,RECORD+8)==BUFFERS[1]+c.residue else BUFFERS[1])+c.residue);put(m,RECORD+16,OWNER if read(m,RECORD+16)==OTHER else OTHER)
 if c.mutation&4:m[RECORD+2]=254

def reference(initial,c=Case(),s=None):
 s=symbols()if s is None else s;m=dict(initial);calls=[];snapshots=[];owner=read(m,RECORD+16);kind=m[RECORD+1];t=m[owner+4]
 calls.append((s['func_1502DB20'],(t,)));matrices=count_value(m,t);count_effect(m,c,s);page=m[s['D_800BE9C0']];span=u32(matrices*kind);current=u32(page*span);other=u32((page^1)*span)
 for index in range(1,kind+1):
  if index==kind:
   owner=read(m,RECORD+16);source=read(m,owner+0x1D4)
   if not source:m[RECORD+2]=0;return m,calls,snapshots
  else:source=u32(read(m,RECORD+8)+u32(index*matrices+other)*64)
  destination=u32(read(m,RECORD+8)+u32((index-1)*matrices+current)*64);length=u32(matrices<<6);assert length<=128
  a=(source,destination,length);calls.append((s['bcopy'],a));packet=data(m,source,length);snapshots.append(packet)
  for i,b in enumerate(packet):m[u32(destination+i)]=b
  copy_effect(m,c,s,index)
 filled=m[RECORD+2];live=m[RECORD+1]
 if filled!=live:m[RECORD+2]=(filled+1)&255
 return m,calls,snapshots

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=symbols()if s is None else s;self.copy_snapshots=[];self.ordinal=0
  super().__init__(words,memory,c,entry=entry,arguments=(RECORD,),connected=connected)
 def execute(self,w):
  if w>>26 in(34,38,42,46):return PartialWordOracle.execute(self,w)
  if w>>26==0 and w&63==32:return SignedCopyOracle.execute(self,w)
  return super().execute(w)
 def record_call(self,t):
  sizes={self.s['func_1502DB20']:1,self.s['bcopy']:3,ENTRY:1,0x15188F84:1};assert t in sizes,('Unbounded cache update provider',hex(t));a=tuple(self.arguments(sizes[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.s['bcopy']:
   assert a[2]<=128;self.copy_snapshots.append(data(self.memory,a[0],a[2]));self.ordinal+=1
 def hook(self,t):
  a=self.calls[-1][1];c=self.c;s=self.s;value=0xDEADBEEF
  if t==s['func_1502DB20']:value=count_value(self.memory,a[0]);count_effect(self.memory,c,s)
  elif t==s['bcopy']:
   packet=data(self.memory,a[0],a[2])
   for i,b in enumerate(packet):self.memory[u32(a[1]+i)]=b
   copy_effect(self.memory,c,s,self.ordinal);value=a[1]
  else:assert t==0x15188F84
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.copy_snapshots,m.current_pc,m.delay_of,m.all_accesses)
def observable(m,raw_fault=False):
 # The raw last-slot buffer load is word40; the fitted schedule uses word42.
 # This is a closed fault-PC correspondence, not literal raw PC equality.
 pc=m.root_entry+42*4 if raw_fault and m.current_pc==m.root_entry+40*4 else m.current_pc
 return(m.memory,m.r[16:24],m.r[28:32],m.f[20:],m.calls,m.events,m.trace,m.copy_snapshots,pc,m.delay_of,m.all_accesses)
def helpers(rom,count=True,copy=True):
 code={}
 for enabled,e,p,n in((count,COUNT,0x5AFD0,25),(copy,COPY,0x23A10,196)):
  if enabled:code.update(zip(range(e,e+4*n,4),struct.unpack_from('>%dI'%n,rom,p)))
 return code
