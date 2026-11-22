"""Ordered script operations, signed clamps, early exits and FP conversions."""
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
import itertools,json,math,struct,sys
from tools.experiments import game_view_light_script_150ecc70_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_interpolated_particle_emitter_150d1204_guest as fp
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY=0x150ECC70;QUERY=0x1509BE40;SUBMIT=0x1509BFB0;SMOOTH=0x150495B0
VIEW=0x30000;SIZE=0x9A0;GLOBALS=tuple(range(0x80088AD0,0x80088AF4,4))
bits,floating,u32=fp.bits,fp.floating,fp.u32
signed=lambda v:(u32(v)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 replies:tuple=(1,0,0,1)
 selector:int=7
 enabled:int=1
 parameter:int=0xFEDCBA98
 value:int=1001
 flags:int=0x13579BDF
 colors:tuple=(bits(63.75),bits(255.5),bits(256.25))
 current:tuple=(bits(10.),bits(30.),bits(90.))
 velocity:tuple=(bits(1.),bits(-2.),bits(3.))
 dt:int=bits(.125)
 mode:int=0
 phase:int=0
 fcsr:int=0
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)}
 m.update({VIEW+i:(i*19+0xA5)&255 for i in range(-16,SIZE+16)})
 put(m,VIEW+0x84,c.flags);put(m,VIEW+0x7B4,c.dt)
 for p,v in zip(GLOBALS,c.current+(bits(12.),bits(34.),bits(56.))+c.velocity):put(m,p,v)
 return m
def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+512}
def snapshot(m):return (read(m,VIEW+0x84),read(m,VIEW+0x134),read(m,VIEW+0x190),read(m,VIEW+0x7B4),*(read(m,p)for p in GLOBALS))
def conversion(w):
 value=floating(w)
 return u32(math.trunc(value))&255 if math.isfinite(value)and -1.<value<4294967296. else 255
def effect(m,c,t,args,ordinal):
 if t==QUERY:
  if c.mode&1 and ordinal==1:put(m,VIEW+0x84,read(m,VIEW+0x84)^0xF0F0FFFF)
  selector=args[1]
  if selector in(0x403B,0x4038,0x4039,0x403A):return u32(c.replies[(0x403B,0x4038,0x4039,0x403A).index(selector)])
  if selector==0x2007 and args[2]==0xB7:return u32(c.selector)
  if selector==0x4010:return u32(c.enabled)
  assert selector==u32(c.selector|0x2000) and args[2]in(0x9C,0x9A),args
  return u32(c.parameter if args[2]==0x9C else c.value)
 if t==SMOOTH:
  put(m,args[0],c.colors[ordinal-1]);put(m,args[2],bits(float(ordinal)))
  if c.mode&2:
   put(m,VIEW+0x7B4,bits(.25*ordinal))
   if ordinal==2:put(m,GLOBALS[0],bits(511.5))
  return 0xABCDEF00+ordinal
 assert t==SUBMIT
 if c.mode&4:
  put(m,VIEW+0x84,read(m,VIEW+0x84)^0x55AA00FF)
  for j,p in enumerate(GLOBALS[:3]):put(m,p,bits(17.25+ordinal*31+j))
 return 0x12340000+ordinal
def reference(initial,c,provider=None):
 m=dict(initial);calls=[];observations=[];counts={}
 def call(t,*args):
  args=tuple(map(u32,args));calls.append((t,args));observations.append(snapshot(m));counts[t]=counts.get(t,0)+1
  return effect(m,c,t,args,counts[t])if provider is None else provider(m,c,t,args,counts[t])
 if call(QUERY,1,0x403B,6,0x2000):
  for selector in(0x4031,0x4032,0x4033):call(SUBMIT,0,selector,1)
  put(m,VIEW+0x84,read(m,VIEW+0x84)|0x80021200)
  if call(QUERY,1,0x4038,6,0x2000):palette=(128.,255.,255.)
  elif call(QUERY,1,0x4039,6,0x2000):palette=(255.,128.,255.)
  elif call(QUERY,1,0x403A,6,0x2000):palette=(255.,255.,128.)
  else:palette=(255.,255.,255.)
  for p,v in zip(GLOBALS[3:6],palette):put(m,p,bits(v))
  selector=call(QUERY,0,0x2007,0xB7)|0x2000
  if not call(QUERY,1,0x4010,6,0x2000):
   put(m,VIEW+0x134,0);put(m,VIEW+0x190,0);return m,calls,observations
  assert selector!=0
  put(m,VIEW+0x134,1)
  call(SUBMIT,1,0x9000,0x17,call(QUERY,1,selector,0x9C,0x2000))
  value=signed(call(QUERY,1,selector,0x9A,0x2000))
  call(SUBMIT,2,0x9000,8,min(1190,max(900,value)),min(231,max(180,value>>1)))
  put(m,VIEW+0x190,bits(220.))
 else:
  for p in GLOBALS[3:6]:put(m,p,bits(255.))
  for selector in(0x4031,0x4032,0x4033):call(SUBMIT,0,selector,0)
  put(m,VIEW+0x84,read(m,VIEW+0x84)&0x7FFDEDFF);put(m,VIEW+0x84,read(m,VIEW+0x84)|8)
 for i in range(3):call(SMOOTH,GLOBALS[i],read(m,GLOBALS[3+i]),GLOBALS[6+i],bits(4.),bits(6.),read(m,VIEW+0x7B4))
 for i,selector in enumerate((0x30F3,0x30F4,0x30F5)):call(SUBMIT,1,selector,0x12,conversion(read(m,GLOBALS[i])))
 return m,calls,observations
class Oracle(fp.Oracle):
 def __init__(self,words,c,entry=ENTRY,connected=None,memory=None,arguments=None):
  self.c=c
  FactoryOracle.__init__(self,words,fixture(c)if memory is None else memory,c,entry=entry,arguments=(VIEW,)if arguments is None else arguments,connected=connected)
  self.initial=dict(self.memory);self.before_f=self.f[:];self.fcsr=c.fcsr;self.counts={};self.observations=[]
 def record_call(self,t):
  assert t in(QUERY,SUBMIT,SMOOTH,ENTRY),hex(t)
  n=6 if t==SMOOTH else 1 if t==ENTRY else 3+self.r[4]
  assert 0<=n<=11
  args=tuple(map(u32,self.arguments(n)))
  self.calls.append((t,args));self.events.append(('CALL',t,args));self.counts[t]=self.counts.get(t,0)+1;self.observations.append(snapshot(self.memory))
 def clobber(self,value):
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
 def hook(self,t):self.clobber(effect(self.memory,self.c,t,self.calls[-1][1],self.counts[t]))
@lru_cache(maxsize=1)
def streams():
 raw=json.loads((out/'ternary-order3/words.json').read_text());truth=list(struct.unpack_from('>341I',(root/'conker/conker.us.bin').read_bytes(),0x11A120))
 return raw,truth
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def observable(m):return public(m.memory),m.calls,m.observations,m.fcsr,m.r[16:24],m.r[28:],m.f[20:]
def check(ws,c):
 m=Oracle(ws,c).run();expected,calls,observations=reference(m.initial,c)
 assert m.calls==calls,(c,'calls',m.calls,calls)
 assert m.observations==observations,(c,'snapshots',m.observations,observations)
 assert public(m.memory)==public(expected),(c,'memory')
 assert m.fcsr==c.fcsr,(c,'FCSR',m.fcsr,c.fcsr)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 return m
def cases():
 replies=((0,1,1,1),(1,1,1,1),(1,0,1,1),(1,0,0,1),(1,0,0,0),(0xFFFFFFFF,0,0x80000000,0))
 yield from(Case(replies=q,enabled=e,mode=mode,phase=phase,fcsr=rm|sticky)for q,e,mode,phase,rm,sticky in itertools.product(replies,(0,1),(0,7),(0,8),range(4),(0,0x54)))
 values=(-2147483648,-1,0,1,359,360,361,462,463,464,465,899,900,901,1189,1190,1191,1192,2147483647)
 yield from(Case(value=v,selector=s,mode=mode,phase=phase)for v,s,mode,phase in itertools.product(values,(0,7,0xFFF),(0,7),(0,8)))
 colors=(0,0x80000000,bits(-.5),bits(-1.),bits(255.),bits(256.),bits(511.5),bits(2147483648.),bits(4294967040.),bits(4294967296.),0x7F800000,0xFF800000,0x7FC00001)
 yield from(Case(colors=(v,)*3,fcsr=rm|0x54)for v,rm in itertools.product(colors,range(4)))
def main():
 count=0;visits=[set(),set()]
 for c in cases():
  pair=[check(ws,c)for ws in streams()];assert observable(pair[0])==observable(pair[1])
  for i,m in enumerate(pair):visits[i].update(m.visits)
  count+=1
 r=dict(cases_per_stream=count,streams=2,body_words=341,frame=56,
  executed_words=[sum(ENTRY+4*i in v for i in range(341))for v in visits],
  unexecuted_indices=[[i for i in range(341)if ENTRY+4*i not in v]for v in visits],
  ABI_and_public_state_equal=True,all_four_rounding_modes=True,FCSR_restoration=True,
  invalid_float_conversions_guest_only=True,signed_clamp_boundaries=True,early_return_skips_smoothing=True,
  dynamic_zero_one_two_payload_counts=True,source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
