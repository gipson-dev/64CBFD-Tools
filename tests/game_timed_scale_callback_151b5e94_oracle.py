"""Timed sound/scale callback: live reloads, return ABI and literal helper paths."""
from dataclasses import dataclass
import math,struct
from tools.experiments import game_timed_scale_callback_151b5e94_match as source
from tools.tests import game_owner_sine_scale_oracle as base
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
STACK,OWNER,ALT_STATE=base.STACK,base.OWNER,base.ALT_STATE
SINE,FINISH,SOUND,INNER,TABLE,WINDOW,END=base.SINE,base.FINISH,0x10010F88,0x10010E78,base.TABLE,base.WINDOW,base.END
CONSTANTS={'D_800AA434':0x3F80418A,'D_800AA438':0x41EF3333,'D_800AA43C':0x41490FDB,'D_800AA440':0x3D4CCCCD}
u32=base.u32;add=base.add;mul=base.mul;public=base.public
half=lambda v:((v&65535)^32768)-32768

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
 sound_phase:int=0x41A00000
 coordinates:tuple=(0x3FA00000,0xC0300000,0x46FFFF80)

def symbols():return {**{n:int(n.split('_')[1],16)for n in CONSTANTS},'D_800BE9A4':0x800BE9A4,'sinf':SINE,'func_15133894':FINISH,'func_10010F88':SOUND}

def initialize_globals(m,c,s):
 for name,value in CONSTANTS.items():put(m,s[name],value)
 put(m,s['D_800BE9A4'],c.tick)

def fixture(c=Case(),s=None):
 s=s or symbols();m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,2304)}
 for p in(OWNER,base.ALT_OWNER,ALT_STATE,c.owner):
  for i in range(0x200):m.setdefault(p+i,(i*13+c.seed+0xA5)&255)
 for p in(c.owner+0x170,ALT_STATE):put(m,p,c.angle);put(m,p+4,c.base)
 for i,v in enumerate(c.coordinates):put(m,c.owner+0x38+4*i,v)
 initialize_globals(m,c,s)
 for i in range(100):m[TABLE+i]=0
 put(m,TABLE+20,source.ENTRY)
 return m

def observe(m,c):return tuple(read(m,c.owner+i)for i in(0x170,0x174,0x18,0x1C))

def effect(m,c,s,home,target):
 if target==s['func_10010F88']:
  if c.mode&4:put(m,c.owner+0x170,c.sound_phase);put(m,c.owner+0x174,0x40400000)
  if c.mode&16:put(m,c.owner+0x3C,0xC2DE0000)
  if c.mode&64:put(m,s['D_800AA43C'],0x3F000000)
 elif target==s['sinf']:
  if c.mode&1:put(m,c.owner+0x174,0xC0300000);put(m,s['D_800AA440'],0x3E000001)
  if c.mode&2:put(m,home-16,ALT_STATE)
  if c.mode&32:put(m,home,base.ALT_OWNER);put(m,c.owner+0x170,0x40C00000)
 elif target==s['func_15133894']:
  if c.mode&8:put(m,c.owner+0x170,0xC0A00000);put(m,s['D_800BE9A4'],0x3F000000)
 else:raise AssertionError(hex(target))

def sound_arguments(m,c):
 xyz=tuple(u32(math.trunc(floating(read(m,c.owner+x))))for x in(0x38,0x3C,0x40))
 return (0x502,24000,0,0,0xFFFFFFFF,*xyz,100,500)

def reference(initial,c=Case(),s=None,home=None):
 s=s or symbols();home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];snapshots=[];state=c.owner+0x170
 value=add(read(m,state),mul(read(m,s['D_800AA434']),read(m,s['D_800BE9A4'])));put(m,state,value)
 if floating(value)>floating(read(m,s['D_800AA438'])):
  put(m,state,0);calls.append((s['func_10010F88'],sound_arguments(m,c)));snapshots.append(observe(m,c));effect(m,c,s,home,s['func_10010F88'])
 if floating(read(m,state))<floating(read(m,s['D_800AA43C'])):
  put(m,home-16,state);calls.append((s['sinf'],(read(m,state),)));snapshots.append(observe(m,c));effect(m,c,s,home,s['sinf'])
  state=read(m,home-16);b=read(m,state+4);v=add(b,mul(c.sample,mul(read(m,s['D_800AA440']),b)))
 else:v=read(m,state+4)
 put(m,c.owner+0x1C,v);put(m,c.owner+0x18,v)
 calls.append((s['func_15133894'],(c.owner,)));snapshots.append(observe(m,c));effect(m,c,s,home,s['func_15133894'])
 return m,calls,u32(c.result),snapshots

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None):
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=s or symbols(),connected=connected,arguments=(c.owner,));self.snapshots=[]
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==0 and fn==3:self.r[rd]=((self.r[rt]&0x7FFFFFFF)-(self.r[rt]&0x80000000))>>fd&0xFFFFFFFF
  elif op==17 and rs==16 and fn==13:self.f[fd]=math.trunc(floating(self.f[rd]))&0xFFFFFFFF
  elif op==17 and rs==16 and fn==7:self.f[fd]=self.f[rd]^0x80000000
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  if t==source.ENTRY:self.target_home=self.r[29];args=(self.r[4],)
  elif t==self.syms['sinf']:args=(self.f[12],);self.snapshots.append(observe(self.memory,self.case))
  elif t in(self.syms['func_10010F88'],self.syms['func_15133894']):args=tuple(map(u32,self.arguments(10 if t==self.syms['func_10010F88']else 1)));self.snapshots.append(observe(self.memory,self.case))
  else:raise AssertionError(hex(t))
  self.calls.append((t,args));self.events.append(('CALL',t,args))
 def clobber(self,result):
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(result)
 def hook(self,t):
  effect(self.memory,self.case,self.syms,self.target_home,t);self.clobber(self.case.result if t==self.syms['func_15133894']else 0xA55A)
  if t==self.syms['sinf']:self.f[0]=self.case.sample

def caller_machine(rom,words,c=Case(),selector=5,gate=0):
 initial=fixture(c);initial[c.owner+0x71]=selector
 code=dict(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));code[END]=0
 m=Oracle(struct.unpack_from('>13I',rom,0x15F6F4),initial,c,entry=WINDOW,connected=code)
 m.r[16]=c.owner;m.r[5]=gate;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
 return m,initial

def full_state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace,m.snapshots)

@dataclass(frozen=True)
class ConnectedCase(Case):
 velocity:int=0xC0000000
 flags:int=1
 selector:int=1
 geometry:int=1
 attachment:int=-1
 event_result:int=0

HELPERS=(*base.HELPERS,(SOUND,0x10F88,29))

def helper_code(rom):
 code={}
 for entry,pos,n in HELPERS:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,pos)))
 return code

def connected_fixture(c=ConnectedCase()):
 m=base.connected_fixture(c);initialize_globals(m,c,symbols());put(m,TABLE+20,source.ENTRY)
 return m

def connected_reference(initial,c=ConnectedCase()):
 assert c.mode==0
 angle=add(read(initial,c.owner+0x170),mul(read(initial,symbols()['D_800AA434']),read(initial,symbols()['D_800BE9A4'])))
 if floating(angle)>floating(read(initial,symbols()['D_800AA438'])):angle=0
 from dataclasses import replace
 m,calls,_,snapshots=reference(initial,replace(c,sample=base.trig.reference(angle)if floating(angle)<floating(read(initial,symbols()['D_800AA43C']))else c.sample))
 if calls[0][0]==SOUND:
  wire=calls[0][1];typed=(0,wire[0],wire[1],wire[2],wire[3],wire[4],*(u32(half(v))for v in wire[5:]))
  calls.insert(1,(INNER,typed))
 p=c.owner;dt=read(m,symbols()['D_800BE9A4']);xyz=[read(m,p+x)for x in(0x38,0x3C,0x40)];calls.append((base.MOVE,(p,)))
 put(m,p+0x38,add(xyz[0],mul(read(m,p+0x44),dt)))
 velocity=read(m,p+0x48);acc=read(m,p+0x5C);delta=add(mul(velocity,dt),mul(mul(mul(acc,dt),dt),bits(.5)))
 put(m,p+0x3C,add(xyz[1],delta));put(m,p+0x40,add(xyz[2],mul(read(m,p+0x4C),dt)));put(m,p+0x48,add(velocity,mul(acc,dt)))
 for dst,speed in((0x20,0x50),(0x24,0x54),(0x28,0x58)):put(m,p+dst,add(read(m,p+dst),mul(read(m,p+speed),dt)))
 result=1;packets=[]
 if c.flags&1 and c.selector and floating(read(m,p+0x3C))<floating(xyz[1]):
  packet=(read(m,p+0x38),add(read(m,p+0x10),xyz[1]),read(m,p+0x40));packets.append(packet)
  bottom=bits(floating(read(m,p+0x3C))-floating(read(m,p+0x10)))
  calls.append((base.GEOMETRY,(STACK+c.phase-72-80+0x34,0,bottom,p+0x110)));put(m,p+0x110,bits(7.5))
  if c.geometry and not(c.attachment>=0 and c.attachment&0x60==0x40):
   calls.append((base.EVENT,(p,*xyz,read(m,p+0x110),p+0x114)));m[p+0x115]^=0x55;result=((c.event_result&255)^128)-128
 return m,calls,u32(result),snapshots,packets

class ConnectedOracle(Oracle):
 def __init__(self,words,memory,c,rom):super().__init__(words,memory,c,connected=helper_code(rom));self.geometry_packets=[]
 def record_call(self,t):
  if t in(source.ENTRY,SINE,FINISH,SOUND):return super().record_call(t)
  count={base.MOVE:1,base.GEOMETRY:4,base.EVENT:6,INNER:11}[t];args=tuple(map(u32,self.arguments(count)));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==base.GEOMETRY:self.geometry_packets.append(tuple(read(self.memory,args[0]+4*i)for i in range(3)))
 def hook(self,t):
  c=self.case;a=self.calls[-1][1]
  if t==INNER:value=0xA55A
  elif t==base.GEOMETRY:put(self.memory,a[3],bits(7.5));value=c.geometry
  else:assert t==base.EVENT;self.memory[c.owner+0x115]^=0x55;value=c.event_result
  self.clobber(value)
