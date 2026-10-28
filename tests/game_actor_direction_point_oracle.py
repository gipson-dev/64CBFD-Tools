"""Actor-relative point construction with ordered stack/record aliases and callers."""
from dataclasses import dataclass
from tools.experiments import game_actor_direction_point_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
MASK=0xFFFFFFFF
ACTOR,ALT,POINT,OUT,ALT_OUT,OWNER,LINK,CHANGED,RESULT,DATA,BYTES=(0x200000+i*0x10000 for i in range(11))
TRIG_TABLE,FRACTIONS=0x8009A220,0x800A2420
FRACTION,RAY,FACTORY,COPY=0x15107AE0,0x15081690,0x15105CE0,0x10022EC0
SYMBOLS=dict(func_1515C244=source.ORIGIN,func_15143794=source.DIRECTION)
sign=lambda v:((v&65535)^32768)-32768
mul=lambda a,b:bits(floating(a)*floating(b))
add=lambda a,b:bits(floating(a)+floating(b))
sub=lambda a,b:bits(floating(a)-floating(b))
POINTS=((0,0x80000000,0x3F800000),(0x3FA00000,0xC1900000,0x42C80000),(1,0x80000001,0x00800000),(0x7F800000,0xFF800000,0x7FC12345))
@dataclass(frozen=True)
class Case:
 yaw:int=0x1234FFFF
 pitch:int=0x56788000
 optional:bool=True
 mode:int=0
 origin:tuple=POINTS[1]
 direction:tuple=POINTS[0]
 radius:int=0x3FC00000
 scale:int=0x3F400000
 phase:int=0
 actor:int=ACTOR
 point:int=POINT
 output:int=OUT
 actor_id:int=0
 actor_radius:int=7
 height:int=-3
 ray_hit:bool=True
 allocated:bool=True

def fixture(c=Case()):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,2048)}
 for base in(c.actor,ALT,c.point,c.output,ALT_OUT,OWNER,LINK,CHANGED,RESULT,DATA,BYTES):
  for i in range(-16,848):m[(base+i)&MASK]=(i*13+0x59)&255
 for base in(c.actor,ALT):
  m[base+4]=c.actor_id;put(m,base+0xF0,c.scale);put(m,base+0xE4,c.actor_radius&65535,2);put(m,base+0xE6,13,2);put(m,base+0xE8,c.height&65535,2)
  for i,v in enumerate(c.origin):put(m,base+20+4*i,v)
 put(m,ALT+0xF0,bits(-1.5));put(m,STACK+c.phase+16,c.output if c.optional else 0)
 return m

def origin_effect(m,c,sp,args):
 for i,v in enumerate(c.origin):put(m,args[1]+4*i,v)
 put(m,args[2],c.radius);put(m,args[3],bits(-99.5))
 if c.mode&1:put(m,sp,ALT)
 if c.mode&2:put(m,sp+4,0xDEAD8001);put(m,sp+8,0x1234FFFF)
 if c.mode&4:put(m,c.actor+240,bits(-2.5))

def direction_effect(m,c,sp,args):
 for i,v in enumerate(c.direction):put(m,args[3]+4*i,v)
 if c.mode&8:put(m,sp,ALT)
 if c.mode&16:
  for i,v in enumerate((bits(17.5),bits(-9.0),bits(3.5))):put(m,sp-12+4*i,v)
 if c.mode&32:put(m,sp+16,ALT_OUT)

def clobber_arguments(m,sp):
 for i in range(4):put(m,sp-56+i*4,0xB5000000+i)

def finish(m,sp,point):
 actor=read(m,sp);y=read(m,point+4);out=read(m,sp+16);scale=read(m,actor+240);x=read(m,point)
 put(m,point+4,mul(y,scale));origin_x=read(m,sp-12);y=read(m,point+4);x=add(x,origin_x);z=read(m,point+8)
 put(m,point,x);put(m,point+4,add(y,read(m,sp-8)));put(m,point+8,add(z,read(m,sp-4)))
 if out:
  for i in range(3):put(m,out+4*i,read(m,sp-12+4*i))
 return out

def reference(initial,c=Case(),symbols=SYMBOLS):
 m=dict(initial);sp=STACK+c.phase;put(m,sp,c.actor);put(m,sp+4,c.yaw&MASK);put(m,sp+8,c.pitch&MASK)
 first=(c.actor,sp-12,sp-16,sp-20);calls=[(symbols['func_1515C244'],first)];origin_effect(m,c,sp,first);clobber_arguments(m,sp)
 second=(sign(read(m,sp+6,2))&MASK,sign(read(m,sp+10,2))&MASK,read(m,sp-16),c.point);calls.append((symbols['func_15143794'],second));direction_effect(m,c,sp,second);clobber_arguments(m,sp)
 out=finish(m,sp,c.point);return m,calls,out

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}

def vector(m,p):return tuple(read(m,p+4*i)for i in range(3))
def trig(m,angle):
 angle&=255;index=64-(angle&63)if angle&64 else angle&63;value=read(m,TRIG_TABLE+4*index)
 return value if angle&192 in(0,192)else value^0x80000000

def actual_reference(initial,c=Case()):
 m=dict(initial);base=c.actor;origin=vector(m,base+20);radius=bits(float(sign(read(m,base+0xE4,2))))if m[base+4]<0xBB else bits(1.0)
 if m[base+4]<0xBB:origin=(origin[0],add(origin[1],bits(float(sign(read(m,base+0xE8,2))))),origin[2])
 temp=mul(radius,trig(m,c.pitch));direction=(mul(temp,trig(m,c.yaw-64)),mul(radius^0x80000000,trig(m,c.pitch-64)),mul(temp,trig(m,c.yaw)))
 point=(add(direction[0],origin[0]),add(mul(direction[1],read(m,base+240)),origin[1]),add(direction[2],origin[2]))
 for i,v in enumerate(point):put(m,c.point+4*i,v)
 if c.optional:
  for i,v in enumerate(origin):put(m,c.output+4*i,v)
 return m,point,origin

class DirectionOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),symbols=SYMBOLS,entry=source.ENTRY,connected=None,arguments=None):
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.actor,c.yaw&MASK,c.pitch&MASK,c.point,c.output if c.optional else 0)if arguments is None else arguments,connected=connected)
  self.case,self.symbols=c,symbols;self.child_sp=STACK+c.phase;self.trace=[];self.target_entries=[];self.ray_packets=[];self.factory_packets=[];self.copy_packets=[]
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
 def execute(self,word):
  op,rs,rt,fn=word>>26,(word>>21)&31,(word>>16)&31,word&63
  if op==17 and rs==16 and fn==7:self.f[(word>>6)&31]=self.f[(word>>11)&31]^0x80000000;return
  if op not in(34,38,42,46):return super().execute(word)
  self.own_instruction=True;self.dispatched_word=word
  try:
   at=(self.r[rs]+sign(word))&MASK;k=at&3;n=4-k if op in(34,42)else k+1
   if op==34:self.r[rt]=(self.get(at,n)<<((4-n)*8))|(self.r[rt]&((1<<((4-n)*8))-1))
   elif op==38:self.r[rt]=(self.r[rt]&~((1<<(n*8))-1))|self.get(at-n+1,n)
   elif op==42:self.put(at,self.r[rt]>>((4-n)*8),n)
   else:self.put(at-n+1,self.r[rt]&((1<<(n*8))-1),n)
   self.r[0]=0
  finally:self.own_instruction=False
 def record_call(self,target):
  sizes={source.ENTRY:5,self.symbols['func_1515C244']:4,self.symbols['func_15143794']:4,source.TRIG:1,FRACTION:4,RAY:15,FACTORY:4,COPY:3};assert target in sizes,hex(target);args=self.arguments(sizes[target])
  if target==source.ENTRY:self.child_sp=self.r[29];self.target_entries.append(args)
  if target==RAY:self.ray_packets.append(args)
  if target==FACTORY:self.factory_packets.append(bytes(self.memory[args[0]+i]for i in range(80)))
  if target==COPY:self.copy_packets.append(bytes(self.memory[args[1]+i]for i in range(args[2])))
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  c=self.case;args=self.calls[-1][1];result=0
  if target==self.symbols['func_1515C244']:origin_effect(self.memory,c,self.child_sp,args)
  elif target==self.symbols['func_15143794']:direction_effect(self.memory,c,self.child_sp,args)
  elif target==RAY:
   self.memory[args[7]+0x59]=int(c.ray_hit)
   for i,v in enumerate((bits(9.5),bits(-7.0),bits(2.0))):put(self.memory,args[7]+8+4*i,v)
  elif target==FACTORY:result=RESULT if c.allocated else 0;put(self.memory,RESULT+0x60,DATA)
  else:raise AssertionError(('unbounded helper',hex(target)))
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.r[2]=0xA5000010,0xA5000011,result
