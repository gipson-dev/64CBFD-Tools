"""Scene reset, original transition command and bounded callback/integrity routes."""
from dataclasses import dataclass
import struct
from tools.experiments import game_scene_state_reset_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

TRANSITION,PREPARE,CHECK,SELECT,PLATFORM=0x1501C730,0x1501C53C,0x151E7EF8,0x151E7E9C,0x10017870
REGISTER,REGISTER_END,DISPATCH=0x151E0248,0x151E03F8,0x151E5014
SLOT,OBJECT,SETUP=0x800E0A88,0x50000,0x150076BC
CODE_START,CODE_END,SP_LOAD=0x151DDC20,0x151DE7D4,0x10003330
HELPERS=((TRANSITION,0x49BE0,74),(CHECK,0x2153A8,26),(SELECT,0x21534C,23))
FIELDS=(('D_80087260',1),('D_80087270',8),('D_8008FD8C',1),('D_8008FD90',1),
 ('D_8008FD94',4),('D_8008FDBC',2),('D_800BE618',1),('D_800D23A8',1),
 ('D_800E0B94',1),('D_800D2E40',1),('D_800BE3DF',1),('D_800BE3E0',1),
 ('D_800E0B99',1),('D_800E0BB1',1),('D_800E9D00',4))
u32=lambda n:n&0xFFFFFFFF
signed8=lambda n:((n&255)^128)-128
@dataclass(frozen=True)
class Case:
 flags:int=0
 scene:int=0x80
 channel:int=0xFE
 effect:int=0
 phase:int=0
 seed:int=0
 selector:int=2
 checksum_good:bool=True

def symbols():
 s={n:int(n[2:],16)for n,_ in FIELDS}
 s.update(func_1501C730=TRANSITION,func_151E7EF8=CHECK);return s
def public(m):return {p:v for p,v in m.items()if not STACK-4096<=p<STACK+1024}
def observation(m,s):return tuple(bytes(m[s[n]+i]for i in range(w))for n,w in FIELDS)
def fixture(c=Case(),s=None,rom=None):
 s=s or symbols();m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-4096,1024)}
 for n,w in FIELDS:
  for i in range(-4,w+4):m[s[n]+i]=(s[n]+i*13+c.seed+0x5A)&255
 put(m,s['D_800E9D00'],c.flags);put(m,s['D_800BE3DF'],c.scene,1);put(m,s['D_800BE3E0'],c.channel,1)
 if rom is not None:
  for a,n in((0x800D2132,2),(0x800BEA00,8),(0x800BE9F4,4),(0x800DD2C0,1),(0x800BE615,1),(0x800E0BE9,1),(SP_LOAD,4)):
   for i in range(-4,n+4):m[a+i]=(a+i*7+c.seed+0xA5)&255
  for i,b in enumerate(rom[0x23B460:0x23B47C]):m[0x800969A0+i]=b
  for i,b in enumerate(rom[CODE_START-0x15000000+0x2D4B0:CODE_END-0x15000000+0x2D4B0]):m[CODE_START+i]=b
  checksum=sum(read(m,p)for p in range(CODE_START,CODE_END,4))&0xFFFFFFFF
  assert checksum==0xBFC924E3,'Original integrity bytes changed'
  if not c.checksum_good:put(m,CODE_START,read(m,CODE_START)^1)
  put(m,0x800E0BE9,c.selector,1);put(m,SP_LOAD,struct.unpack_from('>I',rom,0x3330)[0])
 return m
def effect(m,c,s,final=False):
 if final:
  if c.effect&4:
   m[s['D_800E0B99']]^=2;m[s['D_800E0BB1']]^=4
 elif c.effect&1:
  m[s['D_80087260']]^=1;m[s['D_8008FD94']+1]=0x55
  m[s['D_800E0B99']]=0xAB;m[s['D_800E0BB1']]=0xCD
 if not final and c.effect&2:
  m[s['D_800BE3DF']]^=0xFF;m[s['D_800BE3E0']]^=0xFF
def reference(initial,c=Case(),s=None,connected=False):
 s=s or symbols();m=dict(initial);obs=[];calls=[]
 m[s['D_80087260']]=0x33 if read(m,s['D_800E9D00'])&0x200 else 3
 for name in('D_80087270','D_800D23A8','D_800E0B94','D_800D2E40'):m[s[name]]=0
 for name in('D_8008FD8C','D_8008FD90','D_8008FD94','D_800BE618'):m[s[name]]=1
 put(m,s['D_8008FDBC'],0,2)
 args=(6,u32(signed8(m[s['D_800BE3DF']])),m[s['D_800BE3E0']],0,1)
 calls.append((s['func_1501C730'],args));obs.append(observation(m,s));effect(m,c,s)
 if connected:
  calls.append((PREPARE,()));put(m,0x800D2132,0,2)
  put(m,0x800BEA00,args[4]);put(m,0x800BEA04,args[3]);put(m,0x800BE9F4,args[1])
  put(m,0x800DD2C0,args[2],1);put(m,0x800BE615,2,1)
 m[s['D_800E0B99']]=1;m[s['D_800E0BB1']]=1
 calls.append((s['func_151E7EF8'],()));obs.append(observation(m,s))
 if connected:
  calls.append((SELECT,()));mode=signed8(m[0x800E0BE9]);calls.append((PLATFORM,(1 if mode==2 else 2 if mode==0 else 4,)))
 effect(m,c,s,True)
 if connected and sum(read(m,p)for p in range(CODE_START,CODE_END,4))&0xFFFFFFFF!=0xBFC924E3:put(m,SP_LOAD,0)
 return m,calls,obs
class ResetOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None):
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=s or symbols(),connected=connected,arguments=(0x12345678,0xDEADBEEF,0x80000001,0xFFFFFFFF))
  self.snapshots=[]
 def record_call(self,t):
  counts={source.ENTRY:0,self.syms['func_1501C730']:5,self.syms['func_151E7EF8']:0,PREPARE:0,SELECT:0,PLATFORM:1,SETUP:1,source.ENTRY+0x100:0}
  assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t in(self.syms['func_1501C730'],self.syms['func_151E7EF8']):self.snapshots.append(observation(self.memory,self.syms))
 def hook(self,t):
  if t in(self.syms['func_1501C730'],PREPARE):effect(self.memory,self.case,self.syms)
  elif t in(self.syms['func_151E7EF8'],PLATFORM):effect(self.memory,self.case,self.syms,True)
  else:assert t in(SETUP,source.ENTRY+0x100),hex(t)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0x87654321
def helper_code(rom,transition_only=False):
 result={}
 for entry,off,n in HELPERS[:1]if transition_only else HELPERS:result.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,off)))
 return result
def register_machine(rom,c=Case(),flags=16,wrong=False):
 initial=fixture(c);home=STACK+c.phase
 for base,n in((OBJECT,0x200),(SLOT-8,32),(0x8008FD74,4),(0x8008FDA8,4),(0x800BE3DC,2),(0x80082BC0,1),(0x8008FDD4,4)):
  for i in range(n):initial[base+i]=0xA5
 put(initial,0x8008FDD4,OBJECT);put(initial,OBJECT+0x20,flags,2);put(initial,home+0x54,0x123400E1);put(initial,home+0x28,OBJECT+0x100);put(initial,OBJECT+0x10E,0x80,1)
 body=list(struct.unpack_from('>30I',rom,REGISTER-0x15000000+0x2D4B0))
 if wrong:
  assert body[7]==0x31F80010;body[7]=0x31F80020
 m=ResetOracle(body,initial,c,entry=REGISTER);m.code=WindowCode(m.code,m);m.code.ends=(0x151E03F4,REGISTER_END)
 return m,initial
def dispatcher_machine(rom,words,c=Case(),connected=False,wrong=False):
 initial=fixture(c,rom=rom if connected else None);put(initial,SLOT,source.ENTRY+(0x100 if wrong else 0))
 code=helper_code(rom)if connected else{};code.update(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words))
 m=ResetOracle(struct.unpack_from('>8I',rom,DISPATCH-0x15000000+0x2D4B0),initial,c,entry=DISPATCH,connected=code)
 m.r[29]-=24;put(m.memory,STACK+c.phase-4,m.r[31]);return m,initial
