"""Owner phase and sine scale, live post-call reloads and forwarded result."""
from dataclasses import dataclass
import struct
from tools.experiments import game_owner_sine_scale_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
OWNER,ALT_OWNER,ALT_STATE=0x200000,0x210000,0x220000
SINE,FINISH,TABLE,WINDOW,END=0x15047D60,0x15133894,0x800898B0,0x15132244,0x15132278
u32=lambda x:x&0xFFFFFFFF
def add(a,b):return bits(floating(a)+floating(b))
def mul(a,b):return bits(floating(a)*floating(b))
@dataclass(frozen=True)
class Case:
 angle:int=0x3F800000
 tick:int=0x3F800000
 base:int=0x40000000
 sample:int=0x3F400000
 result:int=1
 phase:int=0
 mode:int=0
 seed:int=0
 owner:int=OWNER
def symbols():return dict(D_800AA454=0x800AA454,D_800AA458=0x800AA458,D_800AA45C=0x800AA45C,D_800BE9A4=0x800BE9A4,sinf=SINE,func_15133894=FINISH)
def public(m):return{p:v for p,v in m.items()if not STACK-2048<=p<STACK+2304}
def fixture(c=Case(),s=None):
 s=s or symbols();m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,2304)}
 for base in(OWNER,ALT_OWNER,ALT_STATE,c.owner):
  for i in range(0x200):m.setdefault(base+i,(i*13+c.seed+0xA5)&255)
 for base in(c.owner+0x170,ALT_STATE):put(m,base,c.angle);put(m,base+4,c.base)
 for name,value in(('D_800AA454',0x40C90FDB),('D_800AA458',0x3F0E5605),('D_800AA45C',0x3D79DB24),('D_800BE9A4',c.tick)):put(m,s[name],value)
 for i in range(100):m[TABLE+i]=0
 put(m,TABLE+24,source.ENTRY)
 return m
def effect(m,c,s,home,ordinal):
 if ordinal==0:
  if c.mode&1:put(m,c.owner+0x174,0xC0300000);put(m,s['D_800AA45C'],0x3E000001)
  if c.mode&2:put(m,home,ALT_OWNER);put(m,home-16,ALT_STATE)
 elif c.mode&4:put(m,c.owner+0x170,0xC0A00000);put(m,s['D_800BE9A4'],0x3F000000)
def observe(m,c):return(read(m,c.owner+0x170),read(m,c.owner+0x174),read(m,c.owner+0x18),read(m,c.owner+0x1C))
def reference(initial,c=Case(),s=None,home=None):
 s=s or symbols();home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];snapshots=[];state=c.owner+0x170;period=read(m,s['D_800AA454'])
 put(m,state,add(read(m,state),mul(read(m,s['D_800AA458']),read(m,s['D_800BE9A4']))))
 steps=0
 while floating(read(m,state))>floating(period):
  put(m,state,bits(floating(read(m,state))-floating(period)));steps+=1;assert steps<100
 put(m,home,c.owner);put(m,home-16,state)
 calls.append((s['sinf'],(read(m,state),)));snapshots.append(observe(m,c));effect(m,c,s,home,0)
 state=read(m,home-16);owner=read(m,home);base=read(m,state+4);scale=read(m,s['D_800AA45C']);value=add(base,mul(c.sample,mul(scale,base)))
 put(m,owner+0x1C,value);put(m,owner+0x18,value)
 calls.append((s['func_15133894'],(owner,)));snapshots.append(observe(m,c));effect(m,c,s,home,1)
 return m,calls,u32(c.result),snapshots
class SineScaleOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None):
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=s or symbols(),connected=connected,arguments=(c.owner,))
  self.snapshots=[];self.ordinal=0
 def record_call(self,target):
  if target==source.ENTRY:self.target_home=self.r[29];args=(self.r[4],)
  elif target==self.syms['sinf']:args=(self.f[12],);self.snapshots.append(observe(self.memory,self.case))
  else:assert target==self.syms['func_15133894'];args=(self.r[4],);self.snapshots.append(observe(self.memory,self.case))
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target==(self.syms['sinf']if self.ordinal==0 else self.syms['func_15133894'])and self.ordinal<2
  effect(self.memory,self.case,self.syms,self.target_home,self.ordinal)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  if self.ordinal==0:self.f[0]=self.case.sample
  else:self.r[2]=u32(self.case.result)
  self.ordinal+=1
def caller_machine(rom,words,c=Case(),selector=6,gate=0):
 initial=fixture(c);initial[c.owner+0x71]=selector
 connected=dict(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));connected[END]=0
 m=SineScaleOracle(struct.unpack_from('>13I',rom,0x15F6F4),initial,c,entry=WINDOW,connected=connected)
 m.r[16]=c.owner;m.r[5]=gate;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
 return m,initial
def full_state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace,m.snapshots)

# Connected helper qualification. Geometry and the selected event callback are
# explicit ABI boundaries; the three literal helper bodies execute normally.
import math
from dataclasses import replace
from tools.tests import test_game_trig_match as trig
MOVE,GEOMETRY,EVENT,EVENT_TABLE,ATTACHED=0x151337C0,0x15046C80,0x150B89E0,0x80089934,0x230000
HELPERS=((SINE,0x75210,104),(FINISH,0x160D44,80),(MOVE,0x160C70,53))
@dataclass(frozen=True)
class ConnectedCase(Case):
 velocity:int=0xC0000000
 flags:int=1
 selector:int=1
 geometry:int=1
 attachment:int=-1
 event_result:int=0
def helper_code(rom):
 code={}
 for entry,pos,n in HELPERS:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,pos)))
 return code
def connected_fixture(c=ConnectedCase()):
 assert c.mode==0;m=fixture(c)
 for a,v in trig.GLOBALS.items():put(m,a,v)
 for off,v in ((0x10,2.),(0x20,.25),(0x24,.5),(0x28,.75),(0x38,1.),(0x3C,10.),(0x40,3.),(0x44,.25),(0x4C,-.5),(0x50,1.),(0x54,-1.),(0x58,2.),(0x5C,0.)):
  put(m,c.owner+off,bits(v))
 put(m,c.owner+0x48,c.velocity);put(m,c.owner+0x60,c.flags);m[c.owner+0x73]=c.selector
 put(m,c.owner+0x130,0 if c.attachment<0 else ATTACHED)
 m.update({ATTACHED+i:0 for i in range(0x80)})
 if c.attachment>=0:m[ATTACHED+0x4F]=c.attachment
 for i in range(8):m[EVENT_TABLE+i]=0
 put(m,EVENT_TABLE+4,EVENT)
 return m
def connected_reference(initial,c=ConnectedCase()):
 phase=add(read(initial,c.owner+0x170),mul(read(initial,symbols()['D_800AA458']),read(initial,symbols()['D_800BE9A4'])))
 period=read(initial,symbols()['D_800AA454'])
 while floating(phase)>floating(period):phase=bits(floating(phase)-floating(period))
 m,calls,_,snapshots=reference(initial,replace(c,sample=trig.reference(phase)))
 p=c.owner;dt=read(m,symbols()['D_800BE9A4']);xyz=[read(m,p+x)for x in(0x38,0x3C,0x40)]
 calls.append((MOVE,(p,)))
 put(m,p+0x38,add(xyz[0],mul(read(m,p+0x44),dt)))
 velocity=read(m,p+0x48);acc=read(m,p+0x5C)
 delta=add(mul(velocity,dt),mul(mul(mul(acc,dt),dt),bits(.5)))
 put(m,p+0x3C,add(xyz[1],delta));put(m,p+0x40,add(xyz[2],mul(read(m,p+0x4C),dt)))
 put(m,p+0x48,add(velocity,mul(acc,dt)))
 for dst,speed in((0x20,0x50),(0x24,0x54),(0x28,0x58)):put(m,p+dst,add(read(m,p+dst),mul(read(m,p+speed),dt)))
 result=1;packets=[]
 if c.flags&1 and c.selector and floating(read(m,p+0x3C))<floating(xyz[1]):
  packet=(read(m,p+0x38),add(read(m,p+0x10),xyz[1]),read(m,p+0x40));packets.append(packet)
  bottom=bits(floating(read(m,p+0x3C))-floating(read(m,p+0x10)))
  # GEOMETRY's first argument is the helper's private three-float packet.
  calls.append((GEOMETRY,(STACK+c.phase-40-80+0x34,0,bottom,p+0x110)))
  put(m,p+0x110,bits(7.5))
  if c.geometry and not(c.attachment>=0 and c.attachment&0x60==0x40):
   args=(p,*xyz,read(m,p+0x110),p+0x114);calls.append((EVENT,args));m[p+0x115]^=0x55
   result=((c.event_result&255)^128)-128
 return m,calls,u32(result),snapshots,packets
class ConnectedOracle(SineScaleOracle):
 def __init__(self,words,memory,c,rom):
  super().__init__(words,memory,c,connected=helper_code(rom));self.geometry_packets=[]
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==0 and fn==3:self.r[rd]=((self.r[rt]&0x7FFFFFFF)-(self.r[rt]&0x80000000))>>fd&0xFFFFFFFF
  elif op==17 and rs==16 and fn==13:self.f[fd]=math.trunc(floating(self.f[rd]))&0xFFFFFFFF
  elif op==17 and rs==16 and fn==7:self.f[fd]=self.f[rd]^0x80000000
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  if t in(source.ENTRY,SINE,FINISH):return super().record_call(t)
  count={MOVE:1,GEOMETRY:4,EVENT:6}[t];a=tuple(map(u32,self.arguments(count)));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==GEOMETRY:self.geometry_packets.append(tuple(read(self.memory,a[0]+4*i)for i in range(3)))
 def hook(self,t):
  c=self.case;a=self.calls[-1][1]
  if t==GEOMETRY:put(self.memory,a[3],bits(7.5));result=c.geometry
  else:assert t==EVENT;self.memory[c.owner+0x115]^=0x55;result=c.event_result
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(result)
