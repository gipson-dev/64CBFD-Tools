"""Independent adjacent-record state model and bounded original helper services."""
from dataclasses import dataclass
from tools.experiments import game_adjacent_record_load_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
BLOCK,MARK,VIEWS=0x30000,0x50000,0x800DDF78
LOOKUP,ALLOC,RELOC,RESOURCE,CONSUMER=0x1502AC88,0x1502B350,0x1502B4A8,0x1510CE60,0x15175390
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 index:int=0
 current:int=0
 adjacent:int=0
 init_mode:int=0
 load_mode:int=0
 answer:int=1
 phase:int=0
 seed:int=0
 missing:int=-1
 block_zero:bool=False

def symbols():return dict(D_800DDE80=source.TABLE,D_800DDF69=source.FLAG,func_15183ACC=source.INITIALIZE,func_1502B6BC=source.LOAD)
def row(c,s):return u32(s['D_800DDE80']+u32(c.index)*20)
def answer(c,s):
 r=row(c,s)
 return 0 if c.answer==0 else BLOCK if c.answer==1 else u32(r+(20 if c.answer>=5 else 0)+4*((c.answer-2)%3))
def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;r=row(c,s);m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-1024,768)}
 for base,length in((r,64),(BLOCK,64),(MARK,16),(u32(s['D_800DDF69']+c.index)-1,2),(u32(VIEWS+c.index*4),4)):
  for i in range(length):m[u32(base+i)]=(i*29+c.seed+0xA5)&255
 for i in range(10):put(m,u32(r+i*4),u32(0x12340000+c.seed*101+i*17))
 for i in range(16):put(m,BLOCK+i*4,u32(0x87650000+c.seed*103+i*19))
 put(m,r,c.current);put(m,u32(r+20),c.adjacent);put(m,MARK,0);put(m,MARK+4,0);put(m,MARK+8,0);return m
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+768}
def load_effect(m,c,s):
 r=row(c,s);p=answer(c,s)
 if c.load_mode&1:put(m,u32(r+12),0xFEDCBA98)
 if c.load_mode&2:put(m,u32(r+20),0xDEADBEEF)
 if c.load_mode&4 and p:put(m,p,0x10203040);put(m,u32(p+8),0x50607080)
 put(m,MARK+4,u32(read(m,MARK+4)+1));return p
def initialize_effect(m,c,s):
 r=row(c,s)
 if c.init_mode in(1,3):put(m,u32(r+20),0)
 if c.init_mode==2:put(m,u32(r+20),0x77)
 if c.init_mode:put(m,u32(r+12),0x76543210)
 put(m,MARK,u32(read(m,MARK)+1))
def reference(initial,c=Case(),s=None,original_init=False,original_loader=False):
 s=symbols()if s is None else s;m=dict(initial);calls=[];r=row(c,s);sp=STACK+c.phase-40
 def call(target,args):args=tuple(map(u32,args));calls.append((target,args));return args
 def load(index,entered):
  args=call(s['func_1502B6BC'],(0,0,0,2,9,index))
  if not original_loader:return load_effect(m,c,s)
  psp=entered-80;desc=psp+56;size=psp+68;put(m,size,1);offset=0xAB1950
  for ordinal,component in enumerate(args[4:]):
   if read(m,size):
    call(LOOKUP,(offset,component,desc));put(m,desc,0xF0000000 if ordinal==c.missing else 0xA0000020);offset=u32(offset+(ordinal+1)*8)
   put(m,size,read(m,desc)&0xFFFFFFF)
  if not read(m,size):return 0
  call(ALLOC,(offset,read(m,desc),size));put(m,size,0 if c.block_zero else 32);p=load_effect(m,c,s)
  if p and read(m,size):call(RELOC,(p,0));put(m,MARK+8,u32(read(m,MARK+8)+1))
  return p
 def initialize():
  call(s['func_15183ACC'],(c.index,))
  if not original_init:initialize_effect(m,c,s);return
  if read(m,r):return
  p=load(u32(c.index+0xAD),sp-40)
  if p:
   put(m,r,p);put(m,u32(r+4),read(m,p));put(m,u32(r+8),read(m,u32(p+8)));put(m,u32(r+12),read(m,u32(p+24)))
   resource=read(m,u32(p+16));put(m,u32(VIEWS+c.index*4),resource);args=call(RESOURCE,(resource,0,1,62,u32(r+16)));put(m,args[4],0x2468ACE0);m[u32(s['D_800DDF69']-1+c.index)]=1
 if not read(m,r):initialize()
 if not read(m,u32(r+20)):
  p=load(u32(c.index+0xAE),sp)
  if p:
   put(m,u32(r+20),p);put(m,u32(r+24),read(m,p));a=read(m,u32(r+12));b=read(m,u32(p+8));put(m,u32(r+36),0);put(m,u32(r+32),a);put(m,u32(r+28),b);m[u32(s['D_800DDF69']+c.index)]=1
 return m,calls

class RecordOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=None,connected=None,s=None,arguments=None):
  self.record_symbols=symbols()if s is None else s;self.case=c;self.lookup_ordinal=0
  super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=(u32(c.index),)if arguments is None else arguments,connected=connected)
  self.trace=[];self.all_accesses=0;self.cut=None
 def access(self):
  if self.own_instruction:
   if self.all_accesses==self.cut:raise faults.AccessBoundary
   self.all_accesses+=1
 def get(self,address,size):
  v=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,v))
  return v
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
 def record_call(self,target):
  s=self.record_symbols;counts={source.ENTRY:1,s['func_15183ACC']:1,s['func_1502B6BC']:6,LOOKUP:3,ALLOC:3,RELOC:2,RESOURCE:5,CONSUMER:18};assert target in counts,('Unbounded provider',hex(target));args=self.arguments(counts[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==s['func_1502B6BC']:self.lookup_ordinal=0
 def hook(self,target):
  c=self.case;s=self.record_symbols;args=self.calls[-1][1];result=0xABCDEF01
  if target==s['func_15183ACC']:initialize_effect(self.memory,c,s)
  elif target==s['func_1502B6BC']:result=load_effect(self.memory,c,s)
  elif target==LOOKUP:
   put(self.memory,args[2],0xF0000000 if self.lookup_ordinal==c.missing else 0xA0000020);self.lookup_ordinal+=1;result=self.lookup_ordinal*8
  elif target==ALLOC:put(self.memory,args[2],0 if c.block_zero else 32);result=load_effect(self.memory,c,s)
  elif target==RELOC:put(self.memory,MARK+8,u32(read(self.memory,MARK+8)+1));result=3
  elif target==RESOURCE:put(self.memory,args[4],0x2468ACE0)
  else:assert target==CONSUMER;put(self.memory,MARK+12,0x98765432)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(result)
