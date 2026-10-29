"""Channel command memory/call reference and bounded count/apply providers."""
from dataclasses import dataclass
import itertools
from tools.experiments import game_actor_channel_command_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.game_animation_timeline_oracle import signed
ACTOR=0x20000
@dataclass(frozen=True)
class Case:
 channel:int=0
 duration:int=0
 count:int=1
 null:bool=False
 mode:int=0
 phase:int=0
 seed:int=0
 alias:int=0
 owner:int=ACTOR

def actor(c):return 0 if c.null else c.owner

def mode_address(c,global_address=source.MODE):return (global_address,c.owner+0x70,c.owner+0x1fc)[c.alias]

def fixture(c=Case(),global_address=source.MODE):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-2048,1024)}
 m.update({c.owner+i:(i*13+c.seed)&255 for i in range(-32,0x360)})
 a=mode_address(c,global_address)
 for i in range(4):m[a+i]=0x5a+i
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}

def count_effect(m,c,a,g):
 if c.mode&1:put(m,g,0x12345678)
 if c.mode&2:put(m,a+0x72,0xa5a5,2);m[a+0x1ff]=0xc7

def apply_effect(m,c,a,b,d,g):
 if c.mode&4:put(m,g,0x76543210)
 if c.mode&8:put(m,a+0x72,0x4567,2);m[a+0x1ff]=0x9a

def reference(initial,c=Case(),global_address=source.MODE,count_target=source.COUNT,apply_target=source.APPLY):
 m=dict(initial);calls=[];a=actor(c);g=mode_address(c,global_address);b=c.channel&0xffffffff;d=c.duration&0xffffffff
 if a:
  calls.append((count_target,(a,)));count_effect(m,c,a,g)
  if signed(c.count)>0:
   if b==0:put(m,g,0);put(m,a+0x72,20,2);calls.append((apply_target,(a,0,10)));apply_effect(m,c,a,0,10,g)
   else:
    put(m,a+0x72,0xfffe,2)
    if b==1:put(m,g,2)
    else:
     if d:
      if signed(d)>20:d=20
      if signed(d)<=0:d=1
     calls.append((apply_target,(a,b,d)));apply_effect(m,c,a,b,d,g)
  else:
   put(m,g,int(b!=0))
   if b==0:m[a+0x1ff]=0
 return m,calls

class ChannelOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,count_target=source.COUNT,apply_target=source.APPLY,global_address=source.MODE,connected=None,arguments=None):
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(actor(c),c.channel,c.duration)if arguments is None else arguments,connected=connected)
  self.case,self.count_target,self.apply_target,self.global_address=c,count_target,apply_target,global_address;self.trace=[]
 def get(self,a,n):
  v=super().get(a,n)
  if self.own_instruction:self.trace.append(('R',a,n,v))
  return v
 def put(self,a,v,n):
  super().put(a,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',a,n,v&((1<<(n*8))-1)))
 def record_call(self,target):
  assert target in(self.count_target,self.apply_target),hex(target)
  args=tuple(self.arguments(1 if target==self.count_target else 3));self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  args=self.calls[-1][1];c=self.case;g=mode_address(c,self.global_address)
  if target==self.count_target:count_effect(self.memory,c,args[0],g);value=c.count&0xffffffff
  else:apply_effect(self.memory,c,*args,g);value=0x76543210
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.r[2]=value;self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011

def corpus():
 values=(0,1,2,19,20,21,255,0x7fffffff,0x80000000,0xffffffff)
 for channel,duration,count,null,phase in itertools.product(values,values,(0,1,0x7fffffff,0x80000000,0xffffffff),(False,True),(0,8)):
  yield Case(channel,duration,count,null,mode=(channel+duration)&15,phase=phase,seed=duration&255)
 for b in range(256):
  for field in('channel','duration'):
   for count in(0,1):yield Case(**{field:b},count=count,mode=b&15,seed=b)
 for alias,channel,duration,count,mode in itertools.product((1,2),(0,1,2),(0,20,21,0xffffffff),(0,1),range(16)):
  yield Case(channel,duration,count,mode=mode,alias=alias)

READ,INDEX,BASE=0x100126E8,0x800D18D0,0x800CC2D0
IDENT,LOOKUP,ANIMS,SUBMIT,TICK=0x150849A0,0x1507E908,0x1507E9F8,0x150302F0,0x1507E5C8
TABLE,ARCHIVE,DEFINITION,ANIM=0x800D1C90,0x30000,0x34000,0x35000
class ParentOracle(ChannelOracle):
 def __init__(self,parent,words,memory,c,packets):
  super().__init__(parent,memory,c,entry=source.PARENT,connected=dict(zip(range(source.ENTRY,source.ENTRY+204,4),words)),arguments=(0x12345678,));self.packets=list(packets);self.packet_index=0;self.child_arguments=[]
 def record_call(self,target):
  if target in(READ,source.ENTRY):
   args=tuple(self.arguments(2 if target==READ else 3));self.calls.append((target,args));self.events.append(('CALL',target,args))
   if target==source.ENTRY:self.child_arguments.append(args)
  else:super().record_call(target)
 def hook(self,target):
  if target!=READ:return super().hook(target)
  args=self.calls[-1][1];assert args==(STACK+self.case.phase-0x100,256),args
  if self.packet_index<len(self.packets):
   for i,v in enumerate(self.packets[self.packet_index]):self.put(args[0]+i,v,1)
   self.packet_index+=1;value=1
  else:value=0
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.r[2]=value


class Helpers(ChannelOracle):
 def __init__(self,words,memory,c,identity,animation,connected):
  super().__init__(words,memory,c,connected=connected);self.identity,self.animation=identity,animation
 def record_call(self,target):
  counts={source.COUNT:1,source.APPLY:3,IDENT:1,LOOKUP:2,ANIMS:2,SUBMIT:2,TICK:2};assert target in counts,hex(target)
  args=tuple(self.arguments(counts[target]));self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target not in(source.COUNT,source.APPLY)
  args=self.calls[-1][1]
  if target==IDENT:value=self.identity
  elif target==LOOKUP:value=DEFINITION
  elif target==ANIMS:value=ANIM if self.animation else 0
  elif target==TICK:self.memory[args[0]+0x6c]=args[1]&255;value=0x76543210
  elif target==SUBMIT:self.memory[args[0]+0x6d]=args[1]&255;value=0x76543210
  else:raise AssertionError(target)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.r[2]=value;self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011

def helper_reference(initial,c,identity,animation):
 m=dict(initial);calls=[];a=actor(c);b=c.channel&0xffffffff;d=c.duration&0xffffffff
 def call(t,*args):calls.append((t,tuple(v&0xffffffff for v in args)))
 def count():
  call(source.COUNT,a);ident=m[a+4]
  if ident!=150:call(IDENT,a);ident=identity
  if ident==255:return 0
  ptr=read(m,TABLE+4*ident)
  return read(m,ptr-4)//10 if ptr else 0
 def apply(b,d):
  call(source.APPLY,a,b,d);n=count()
  if signed(b)>=n:return
  call(LOOKUP,a,m[a+0x6f]);definition=DEFINITION
  if m[definition+4]:
   call(ANIMS,a,0)
   if animation:call(SUBMIT,a,m[ANIM+m[definition+4]-1]);m[a+0x6d]=m[ANIM+m[definition+4]-1]
  m[a+0x6f]=b&255;call(TICK,a,d);m[a+0x6c]=d&255
  if d:m[a+0x135]=d&255
  else:call(LOOKUP,a,b);m[a+0x135]=m[definition+3]
 if signed(count())>0:
  if b==0:put(m,source.MODE,0);put(m,a+0x72,20,2);apply(0,10)
  else:
   put(m,a+0x72,0xfffe,2)
   if b==1:put(m,source.MODE,2)
   else:
    if d:
     if signed(d)>20:d=20
     if signed(d)<=0:d=1
    apply(b,d)
 else:
  put(m,source.MODE,int(b!=0))
  if b==0:m[a+0x1ff]=0
 return m,calls
