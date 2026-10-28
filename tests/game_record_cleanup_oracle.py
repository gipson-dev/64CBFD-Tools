"""Independent record cleanup model with shared row/view aliases and resource-list execution."""
from dataclasses import dataclass,replace
from tools.experiments import game_record_cleanup_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
BLOCK,RESOURCE_BLOCK,SHARED,MARK,DECREMENT=0x30000,0x31000,0x32000,0x50000,0x1510D694
u32=lambda n:n&0xFFFFFFFF
s16=lambda n:(n&65535)-65536 if n&32768 else n&65535
@dataclass(frozen=True)
class Case:
 index:int=9
 asset:int=BLOCK
 resource:int=RESOURCE_BLOCK
 shared:int=SHARED
 flag8:int=254
 flag9:int=254
 resource_mode:int=0
 free_mode:int=0
 count:int=3
 phase:int=0
 seed:int=0

def symbols():return dict(D_800DDE80=source.TABLE,D_800DDF70=source.FLAG+8,D_800DDF71=source.FLAG+9,D_800DDF20=source.TABLE+160,D_800DDF98=source.VIEWS+32,D_800DDF78=source.VIEWS,func_1510D630=source.RESOURCE,func_10004074=source.FREE)
def row(index,s):return u32(s['D_800DDE80']+u32(index)*20)
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+768}
def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,768)}
 for base,length in((s['D_800DDE80'],220),(row(c.index,s),20),(s['D_800DDF70']-8,11),(s['D_800DDF78'],44),(u32(s['D_800DDF78']+c.index*4),4),(RESOURCE_BLOCK,32),(MARK,16)):
  for i in range(length):m[u32(base+i)]=(i*29+c.seed+0xA5)&255
 for i in range(11):put(m,row(i,s),0);put(m,row(i,s)+16,0)
 put(m,s['D_800DDF20'],c.shared);put(m,row(c.index,s),c.asset);put(m,row(c.index,s)+16,c.resource)
 m[s['D_800DDF70']]=c.flag8&255;m[s['D_800DDF71']]=c.flag9&255
 put(m,RESOURCE_BLOCK,c.count&65535,2)
 for j in range(1,16):put(m,RESOURCE_BLOCK+2*j,((0,1,32767,32768,65535)[j%5]),2)
 return m

def resource_effect(m,c,s):
 a=row(c.index,s);put(m,u32(a+16),0xDEAD1234)
 if c.resource_mode&1:put(m,a,0)
 if c.resource_mode&2:put(m,a,0x34567890)
 if c.resource_mode&4:m[s['D_800DDF70']]=m[s['D_800DDF71']]=254;put(m,s['D_800DDF20'],0x45678900)

def free_effect(m,c,s):
 if c.free_mode&1:put(m,row(c.index,s),0xCAFEBABE);put(m,u32(s['D_800DDF78']+c.index*4),0xFEEDFACE)
 if c.free_mode&2:put(m,s['D_800DDF20'],0xDEADBEEF);put(m,s['D_800DDF98'],0x01234567)

def reference(initial,c=Case(),s=None,original_resource=False):
 s=symbols()if s is None else s;m=dict(initial);calls=[];a=row(c.index,s)
 def call(target,args):calls.append((target,tuple(map(u32,args))))
 p=read(m,u32(a+16))
 if p:
  call(s['func_1510D630'],(p,))
  if original_resource:
   count=s16(read(m,p,2))
   for j in range(max(count,0)):
    call(DECREMENT,(s16(read(m,u32(p+2+j*2),2)),));resource_effect(m,c,s)
   call(s['func_10004074'],(p,));free_effect(m,c,s)
  else:resource_effect(m,c,s)
  put(m,u32(a+16),0)
 if c.index==8:
  if m[s['D_800DDF71']]!=254:return m,calls
 elif c.index==9 and m[s['D_800DDF70']]==254:
  p=read(m,s['D_800DDF20'])
  if p:call(s['func_10004074'],(p,));free_effect(m,c,s);put(m,s['D_800DDF20'],0);put(m,s['D_800DDF98'],0)
 p=read(m,a)
 if p:call(s['func_10004074'],(p,));free_effect(m,c,s);put(m,a,0);put(m,u32(s['D_800DDF78']+c.index*4),0)
 return m,calls

class CleanupOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=None,connected=None,s=None,arguments=None):
  self.syms=symbols()if s is None else s;self.case=c
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
 def execute(self,word):
  if word>>26==0x20:
   base=word>>21&31;target=word>>16&31;displacement=s16(word);value=self.get(u32(self.r[base]+displacement),1);self.r[target]=u32(value-256 if value&128 else value)
  else:super().execute(word)
 def record_call(self,target):
  s=self.syms;assert target in(source.ENTRY,s['func_1510D630'],s['func_10004074'],DECREMENT),('Unbounded cleanup provider',hex(target));args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==source.ENTRY:self.case=replace(self.case,index=args[0])
 def hook(self,target):
  if target in(self.syms['func_1510D630'],DECREMENT):resource_effect(self.memory,self.case,self.syms)
  else:assert target==self.syms['func_10004074'];free_effect(self.memory,self.case,self.syms)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xABCDEF01
