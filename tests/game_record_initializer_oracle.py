"""Independent record initializer model and bounded original loader providers."""
from dataclasses import dataclass,replace
from tools.experiments import game_record_initializer_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
BLOCK,MARK=0x30000,0x50000
LOOKUP,ALLOC,RELOC=0x1502AC88,0x1502B350,0x1502B4A8
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 index:int=0
 current:int=0
 load_mode:int=0
 resource_mode:int=0
 answer:int=1
 phase:int=0
 seed:int=0
 missing:int=-1
 block_zero:bool=False

def symbols():return dict(D_800DDE80=source.TABLE,D_800DDF68=source.FLAG,D_800DDF78=source.VIEWS,func_1502B6BC=source.LOAD,func_1510CE60=source.RESOURCE)
def row(c,s):return u32(s['D_800DDE80']+u32(c.index)*20)
def answer(c,s):return 0 if c.answer==0 else BLOCK if c.answer==1 else u32(row(c,s)+4*(c.answer-2))
def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;r=row(c,s);m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,768)}
 for base,length in((s['D_800DDE80'],220),(r,64),(BLOCK,64),(MARK,16),(s['D_800DDF68'],11),(u32(s['D_800DDF68']+c.index),1),(s['D_800DDF78'],44),(u32(s['D_800DDF78']+c.index*4),4)):
  for i in range(length):m[u32(base+i)]=(i*29+c.seed+0xA5)&255
 for i in range(16):put(m,u32(r+i*4),u32(0x12340000+c.seed*101+i*17));put(m,BLOCK+i*4,u32(0x87650000+c.seed*103+i*19))
 put(m,r,c.current)
 for i in range(4):put(m,MARK+i*4,0)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+768}
def load_effect(m,c,s):
 r=row(c,s);p=answer(c,s)
 if c.load_mode&1:put(m,u32(r+12),0xFEDCBA98)
 if c.load_mode&2:put(m,r,0xDEADBEEF)
 if c.load_mode&4 and p:
  for j in(0,2,4,6):put(m,u32(p+4*j),0x10203040+j*0x1010101)
 put(m,MARK,u32(read(m,MARK)+1));return p
def observe(m,c,s):return(read(m,u32(s['D_800DDF78']+c.index*4)),m[u32(s['D_800DDF68']+c.index)],tuple(read(m,u32(row(c,s)+4*i))for i in range(5)))
def resource_effect(m,c,s,args):
 r=row(c,s)
 put(m,args[4],0x2468ACE0)
 if c.resource_mode&1:put(m,r,0x31415926)
 if c.resource_mode&2:put(m,u32(s['D_800DDF78']+c.index*4),0x27182818)
 if c.resource_mode&4:m[u32(s['D_800DDF68']+c.index)]=0x80
 put(m,MARK+4,u32(read(m,MARK+4)+1));return c.resource_mode&1

def reference(initial,c=Case(),s=None,original_loader=False,entered=None):
 s=symbols()if s is None else s;m=dict(initial);calls=[];observations=[];r=row(c,s);sp=STACK+c.phase-40 if entered is None else entered-40
 def call(target,args):args=tuple(map(u32,args));calls.append((target,args));return args
 def load():
  args=call(s['func_1502B6BC'],(0,0,0,2,9,c.index+0xAD))
  if not original_loader:return load_effect(m,c,s)
  psp=sp-80;desc=psp+56;size=psp+68;put(m,size,1);offset=0xAB1950
  for ordinal,component in enumerate(args[4:]):
   if read(m,size):
    call(LOOKUP,(offset,component,desc));put(m,desc,0xF0000000 if ordinal==c.missing else 0xA0000020);offset=u32(offset+(ordinal+1)*8)
   put(m,size,read(m,desc)&0xFFFFFFF)
  if not read(m,size):return 0
  call(ALLOC,(offset,read(m,desc),size));put(m,size,0 if c.block_zero else 32);p=load_effect(m,c,s)
  if p and read(m,size):call(RELOC,(p,0));put(m,MARK+8,u32(read(m,MARK+8)+1))
  return p
 if not read(m,r):
  p=load()
  if p:
   put(m,r,p);put(m,u32(r+4),read(m,p));put(m,u32(r+8),read(m,u32(p+8)));put(m,u32(r+12),read(m,u32(p+24)))
   resource=read(m,u32(p+16));put(m,u32(s['D_800DDF78']+c.index*4),resource);args=call(s['func_1510CE60'],(resource,0,1,62,u32(r+16)));observations.append(observe(m,c,s));resource_effect(m,c,s,args);m[u32(s['D_800DDF68']+c.index)]=1
 return m,calls,observations

class RecordOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=None,connected=None,s=None,arguments=None):
  self.record_symbols=symbols()if s is None else s;self.case=c;self.base_case=c;self.lookup_ordinal=0
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
  s=self.record_symbols;counts={source.ENTRY:1,s['func_1502B6BC']:6,s['func_1510CE60']:5,LOOKUP:3,ALLOC:3,RELOC:2};assert target in counts,('Unbounded provider',hex(target));args=self.arguments(counts[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==source.ENTRY:self.case=replace(self.base_case,index=args[0])
  if target==s['func_1502B6BC']:self.lookup_ordinal=0
  if target==s['func_1510CE60']:self.observations.append(observe(self.memory,self.case,s))
 def hook(self,target):
  c=self.case;s=self.record_symbols;args=self.calls[-1][1]
  if target==s['func_1502B6BC']:result=load_effect(self.memory,c,s)
  elif target==LOOKUP:
   put(self.memory,args[2],0xF0000000 if self.lookup_ordinal==c.missing else 0xA0000020);self.lookup_ordinal+=1;result=self.lookup_ordinal*8
  elif target==ALLOC:put(self.memory,args[2],0 if c.block_zero else 32);result=load_effect(self.memory,c,s)
  elif target==RELOC:put(self.memory,MARK+8,u32(read(self.memory,MARK+8)+1));result=3
  else:assert target==s['func_1510CE60'];result=resource_effect(self.memory,c,s,args)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(result)
