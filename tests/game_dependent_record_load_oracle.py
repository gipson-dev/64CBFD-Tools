"""Independent two-index loader model with original initializer/asset-loader contexts."""
from dataclasses import dataclass
from tools.experiments import game_dependent_record_load_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
BLOCK,IBLOCK,MARK,VIEWS=0x30000,0x31000,0x50000,0x800DDF78
LOOKUP,ALLOC,RELOC,RESOURCE,CONSUMER=0x1502AC88,0x1502B350,0x1502B4A8,0x1510CE60,0x15174FA4
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 required:int=7
 index:int=10
 required_live:int=0
 target_live:int=0
 init_mode:int=1
 load_mode:int=0
 answer:int=1
 phase:int=0
 seed:int=0
 init_answer:int=1
 missing:int=-1
 block_zero:bool=False

def symbols():return dict(D_800DDE80=source.TABLE,D_800DDF68=source.FLAG,func_15183ACC=source.INITIALIZE,func_1502B6BC=source.LOAD)
def row(index,s):return u32(s['D_800DDE80']+u32(index)*20)
def answer(c,s,initializing=False):
 mode=c.init_answer if initializing else c.answer
 return 0 if mode==0 else(IBLOCK if initializing else BLOCK)if mode==1 else u32(row(c.required if mode<5 else c.index,s)+4*((mode-2)%3))
def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;a=row(c.required,s);b=row(c.index,s);m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,768)}
 for base,length in((s['D_800DDE80'],220),(a,64),(b,64),(BLOCK,64),(IBLOCK,64),(MARK,20),(s['D_800DDF68'],11),(u32(s['D_800DDF68']+c.required),1),(u32(s['D_800DDF68']+c.index),1),(VIEWS,44),(u32(VIEWS+c.required*4),4)):
  for i in range(length):m[u32(base+i)]=(i*29+c.seed+0xA5)&255
 for i in range(16):
  for base,tag in((a,0x12340000),(b,0x23450000),(BLOCK,0x87650000),(IBLOCK,0x98760000)):put(m,u32(base+i*4),u32(tag+c.seed*103+i*19))
 put(m,a,c.required_live);put(m,b,c.target_live)
 for i in range(5):put(m,MARK+i*4,0)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+768}
def initialize_effect(m,c,s):
 a,b=row(c.required,s),row(c.index,s)
 if c.init_mode&1:put(m,a,0xF00D1234)
 if c.init_mode&2:put(m,b,0xABCD4321)
 if c.init_mode&4:put(m,b,0)
 put(m,MARK,u32(read(m,MARK)+1))
def load_effect(m,c,s,initializing=False):
 a,b=row(c.required,s),row(c.index,s);p=answer(c,s,initializing)
 if c.load_mode&1:put(m,b,0xDEADBEEF)
 if c.load_mode&2:put(m,a,0)
 if c.load_mode&4 and p:
  for j in(0,2,6):put(m,u32(p+4*j),0x10203040+j*0x1010101)
 put(m,MARK+4,u32(read(m,MARK+4)+1));return p
def resource_effect(m,c,s,args):
 put(m,args[4],0x2468ACE0)
 if c.init_mode&4:put(m,row(c.required,s),0)
 if c.init_mode&2:put(m,row(c.index,s),0xABCD4321)
 put(m,MARK+8,u32(read(m,MARK+8)+1))
def reference(initial,c=Case(),s=None,original_init=False,original_loader=False):
 s=symbols()if s is None else s;m=dict(initial);calls=[];a,b=row(c.required,s),row(c.index,s);sp=STACK+c.phase-40
 def call(target,args):args=tuple(map(u32,args));calls.append((target,args));return args
 def load(initializing,entered):
  index=c.required if initializing else c.index;args=call(s['func_1502B6BC'],(0,0,0,2,9,index+0xAD))
  if not original_loader:return load_effect(m,c,s,initializing)
  psp=entered-80;desc=psp+56;size=psp+68;put(m,size,1);offset=0xAB1950
  for ordinal,component in enumerate(args[4:]):
   if read(m,size):call(LOOKUP,(offset,component,desc));put(m,desc,0xF0000000 if ordinal==c.missing else 0xA0000020);offset=u32(offset+(ordinal+1)*8)
   put(m,size,read(m,desc)&0xFFFFFFF)
  if not read(m,size):return 0
  call(ALLOC,(offset,read(m,desc),size));put(m,size,0 if c.block_zero else 32);p=load_effect(m,c,s,initializing)
  if p and read(m,size):call(RELOC,(p,0));put(m,MARK+16,u32(read(m,MARK+16)+1))
  return p
 if not read(m,a):
  call(s['func_15183ACC'],(c.required,))
  if not original_init:initialize_effect(m,c,s)
  elif not read(m,a):
   p=load(True,sp-40)
   if p:
    put(m,a,p);put(m,u32(a+4),read(m,p));put(m,u32(a+8),read(m,u32(p+8)));put(m,u32(a+12),read(m,u32(p+24)))
    resource=read(m,u32(p+16));put(m,u32(VIEWS+c.required*4),resource);args=call(RESOURCE,(resource,0,1,62,u32(a+16)));resource_effect(m,c,s,args);m[u32(s['D_800DDF68']+c.required)]=1
 if read(m,a)and not read(m,b):
  p=load(False,sp)
  if p:
   put(m,b,p);put(m,u32(b+4),read(m,p));put(m,u32(b+8),read(m,u32(p+8)));last=read(m,u32(p+24));put(m,u32(b+16),0);put(m,u32(b+12),last);m[u32(s['D_800DDF68']+c.index)]=1
 return m,calls

class RecordOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=None,connected=None,s=None,arguments=None):
  self.record_symbols=symbols()if s is None else s;self.case=c;self.lookup_ordinal=0;self.pending_initializer_load=False;self.load_initializing=False
  super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=(u32(c.required),u32(c.index))if arguments is None else arguments,connected=connected)
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
  s=self.record_symbols;counts={source.ENTRY:2,s['func_15183ACC']:1,s['func_1502B6BC']:6,LOOKUP:3,ALLOC:3,RELOC:2,RESOURCE:5,CONSUMER:10};assert target in counts,('Unbounded provider',hex(target));args=self.arguments(counts[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==s['func_15183ACC']:self.pending_initializer_load=True
  if target==s['func_1502B6BC']:self.lookup_ordinal=0;self.load_initializing=self.pending_initializer_load;self.pending_initializer_load=False
 def hook(self,target):
  c=self.case;s=self.record_symbols;args=self.calls[-1][1];result=0xABCDEF01
  if target==s['func_15183ACC']:initialize_effect(self.memory,c,s);self.pending_initializer_load=False
  elif target==s['func_1502B6BC']:result=load_effect(self.memory,c,s,self.load_initializing)
  elif target==LOOKUP:
   put(self.memory,args[2],0xF0000000 if self.lookup_ordinal==c.missing else 0xA0000020);self.lookup_ordinal+=1;result=self.lookup_ordinal*8
  elif target==ALLOC:put(self.memory,args[2],0 if c.block_zero else 32);result=load_effect(self.memory,c,s,self.load_initializing)
  elif target==RELOC:put(self.memory,MARK+16,u32(read(self.memory,MARK+16)+1));result=3
  elif target==RESOURCE:resource_effect(self.memory,c,s,args)
  else:assert target==CONSUMER;put(self.memory,MARK+12,0x98765432)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(result)
