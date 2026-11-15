"""Private finite-domain semantics; physical frame and word matching remain open."""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_radial_effect_150c29f0_recovery as s
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
RANDF,RANDI,TRIG,EMIT=0x150ada68,0x150ada20,0x151423d8,0x15149550
OWNER,CONST,TABLE,MARK=0x30040,0x800a02a0,0x8009a220,0x70000
PARENT,PARENT_ROM=0x15149264,0x176714
@dataclass(frozen=True)
class Case:
 randoms:tuple=(0x12340080,0x3f000000,0xffffffff,0x3e800000,0x3f400000,0x80000000)
 position:tuple=(0x3f800000,0xc0200000,0x40800000,0x40400000)
 mode:int=0x87
 selector:int=0xfe
 mutation:int=0
 phase:int=0
 seed:int=0

def cases():
 for angle,pattern in itertools.product(range(256),(0,1)):
  randoms=(angle|(0xffff0000 if pattern else 0),bits(.5 if pattern else 0.),0x80000000+angle if pattern else angle,bits(1. if pattern else .25),bits(-.5 if pattern else .75),0xffffffff-angle if pattern else angle)
  position=tuple(bits(v) for v in ((-100.,32767.,-2.,-32768.) if pattern else (1.,-2.5,4.,3.)))
  yield Case(randoms,position,(0,255)[pattern],(128,0)[pattern],angle&1,pattern*8,angle)

@lru_cache(maxsize=1)
def rom():return (s.ROOT/'conker/conker.us.bin').read_bytes()
def quarter():return struct.unpack_from('>65I',rom(),0x23ece0)
def trig(angle):
 angle&=255;index=64-(angle&63) if angle&64 else angle&63
 return quarter()[index] ^ (0 if angle&192 in (0,192) else 0x80000000)

def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,1024)}
 for base,n in ((OWNER-32,128),(CONST,32),(TABLE,260),(MARK,32)):m.update({base+i:(i*13+c.seed*11+0x53)&255 for i in range(n)})
 m[OWNER+12]=c.mode;m[OWNER+1]=c.selector;m[OWNER+13]=0;m[OWNER+16]=5;m[OWNER+17]=255
 put(m,OWNER+14,0xff81,2)
 for i,v in enumerate(c.position):put(m,OWNER+40+4*i,v)
 for i,v in enumerate((.1,.2,.3,.4,.5,.6,.7,.8)):put(m,CONST+4*i,bits(v))
 for i,v in enumerate(quarter()):put(m,TABLE+4*i,v)
 put(m,STACK+c.phase,OWNER)
 return m

def effect(m,c,ordinal):
 put(m,MARK,(0x13579bdf+ordinal*0x10203)&0xffffffff)
 if c.mutation:
  m[OWNER+12]^=0x55;m[OWNER+1]^=0xa3
  for i in range(4):put(m,OWNER+40+4*i,bits((i+1)*(.5 if ordinal&1 else -1.)))
  for i in range(8):put(m,CONST+4*i,bits((i+1)*(.125 if ordinal&1 else -.25)))

def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+1024}
def packet_bytes(m,p):return bytes(m[p+i] if not 0x35<=i<0x38 else 0 for i in range(72))

def reference(initial,c):
 m=dict(initial);packet={i:0 for i in range(72)};r0,rf0,r1,rf1,rf2,r2=c.randoms
 mul=lambda a,b:fp(a,b,'mul');add=lambda a,b:fp(a,b,'add')
 effect(m,c,0);angle=r0&255;xdir,zdir=trig(angle-64),trig(angle)
 effect(m,c,3);radius=mul(rf0,read(m,OWNER+48))
 effect(m,c,4)
 x=add(read(m,OWNER+40),mul(radius,xdir));y=read(m,OWNER+52);z=add(read(m,OWNER+44),mul(radius,zdir))
 for off,v in ((0,x),(4,y),(8,z),(0x38,0),(0x3c,read(m,CONST+8)),(0x40,read(m,CONST)),(0x44,read(m,CONST+4))):put(packet,off,v)
 effect(m,c,5);first=add(mul(rf1,bits(.5)),bits(1.))
 effect(m,c,6);second=add(mul(rf2,bits(.5)),bits(1.))
 for off,n,scale in ((0xc,3,first),(0x14,4,first),(0x10,5,second),(0x18,6,second),(0x1c,7,second)):put(packet,off,mul(read(m,CONST+4*n),scale))
 for off,v in ((0x20,0x6231),(0x22,0x1a4d),(0x24,r1%201+100),(0x2a,1)):put(packet,off,v,2)
 for off,v in ((0x29,255),(0x2c,255),(0x2d,255),(0x2f,1),(0x34,15)):packet[off]=v
 args=(0,10,1,0,m[OWNER+12],m[OWNER+1]);observation=(packet_bytes(packet,0),args)
 effect(m,c,7);effect(m,c,8);put(m,OWNER+14,r2%51+25,2)
 calls=[(RANDI,()),(TRIG,((angle-64)&255,)),(TRIG,(angle,)),(RANDF,()),(RANDI,()),(RANDF,()),(RANDF,()),(EMIT,args),(RANDI,())]
 return public(m),calls,observation

def helper_code():
 words=struct.unpack_from('>27I',rom(),0x16f888)
 return dict(zip(range(TRIG,TRIG+108,4),words))

class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=s.ENTRY,connected=None):
  code=helper_code();code.update(connected or {})
  super().__init__(words,initial,c,entry=entry,arguments=(OWNER,),connected=code)
  self.before_f=self.f[:];self.observed=None;self.target_entries=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in (0,1,2):self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul')[w&63])
  elif w>>26==17 and w>>21&31==16 and w&63==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
  else:super().execute(w)
 def record_call(self,t):
  if t==s.ENTRY:
   assert self.r[4]==OWNER;self.target_entries.append(t);return
  assert t in (RANDF,RANDI,TRIG,EMIT),hex(t)
  if t==TRIG:a=(self.r[4]&255,)
  elif t==EMIT:
   raw=tuple(self.arguments(6));assert self.r[29]<=raw[0]<STACK and raw[0]+72<=STACK+self.case.phase
   a=(0,*raw[1:]);self.observed=(packet_bytes(self.memory,raw[0]),a)
  else:a=()
  self.calls.append((t,a))
 def hook(self,t):
  assert t!=TRIG,'Trig must execute original instructions'
  ordinal=len(self.calls)-1;effect(self.memory,self.case,ordinal)
  for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
  if t==RANDI:self.r[2]=self.case.randoms[{0:0,4:2,8:5}[ordinal]]
  elif t==RANDF:self.f[0]=self.case.randoms[{3:1,5:3,6:4}[ordinal]]
  else:self.r[2]=0x34560

def verify(m,initial,c):
 want,calls,observation=reference(initial,c)
 assert public(m.memory)==want and m.calls==calls and m.observed==observation,(c,m.calls,calls,m.observed,observation)
 assert m.r[16:24]==m.before[16:24] and m.r[28:31]==m.before[28:31] and m.f[20:]==m.before_f[20:]

def main():
 programs=s.programs();seen=[set(),set()];n=0
 for c in cases():
  initial=fixture(c)
  for i,words in enumerate(programs):m=Oracle(words,initial,c);m.run();verify(m,initial,c);seen[i].update(m.visits)
  n+=1
 target_seen=[len(v&set(range(s.ENTRY,s.ENTRY+len(words)*4,4))) for v,words in zip(seen,programs)]
 assert target_seen==[132,129]
 assert all(set(helper_code())<=v for v in seen)
 controls=0
 for old,new in ((0x240100c9,0x240100c8),(0x24010033,0x24010032),(0x2405000a,0x24050009),(0x904f000c,0x904f000b)):
  words=programs[0][:];assert words.count(old)==1;words[words.index(old)]=new;c=Case();initial=fixture(c)
  try:m=Oracle(words,initial,c);m.run();verify(m,initial,c)
  except AssertionError:controls+=1
  else:raise AssertionError('Ineffective control')
 # The emitted radius multiply reverses its two inputs. Do not let finite
 # commutativity hide the unresolved ordered NaN behavior in this private C.
 r=list(Case().randoms);r[1]=0x7fc00001;p=list(Case().position);p[2]=0x7fc30002
 c=Case(randoms=tuple(r),position=tuple(p));observations=[]
 for words in programs:
  m=Oracle(words,fixture(c),c);m.run();observations.append(m.observed[0])
 assert observations[0]!=observations[1]
 boundary=dict(rule='explicit left NaN wins model',retail_x=observations[0][:4].hex(),raw_x=observations[1][:4].hex(),retail_z=observations[0][8:12].hex(),raw_z=observations[1][8:12].hex(),hardware_nan_rule_not_claimed=True,open=True)
 (s.OUT/'exceptional-boundary.json').write_text(json.dumps(boundary,indent=2)+'\n')
 report=dict(finite_cases=n,streams=2,target_words_visited=target_seen,trig_words_visited=27,packet_defined_bytes=69,packet_padding_bytes_uncredited=3,instruction_controls=controls,physical_frame_equivalence=False,ordered_nan_operand_boundary_open=True,private_uninstalled=True,exceptional_fp_fcsr_not_claimed=True)
 (s.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
