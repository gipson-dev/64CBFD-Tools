"""Independent float-pair model, aliases and rounded IEEE-single operations."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-paired-float-approach-1505A250-match'
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x1505A250;OUTPUT=0x30000;TIMESTEP=0x800D1550
floating=lambda b:struct.unpack('>f',struct.pack('>I',b&0xFFFFFFFF))[0]
def bits(f):
 try:return struct.unpack('>I',struct.pack('>f',f))[0]
 except OverflowError:return 0xFF800000 if f<0 else 0x7F800000
def rounded(f):return floating(bits(f))
def canonical(b):return 0x7FC00000 if b&0x7F800000==0x7F800000 and b&0x7FFFFF else b
def divide(a,b):
 if math.isnan(a)or math.isnan(b):return math.nan
 if b==0.0:return math.nan if a==0.0 else math.copysign(math.inf,math.copysign(1.,a)*math.copysign(1.,b))
 return rounded(a/b)
@dataclass(frozen=True)
class Case:
 target_x:int=0
 target_z:int=0
 x:int=0x41A00000
 z:int=0xC1200000
 rate:int=0x3F000000
 timestep:int=0x3F800000
 alias:int=0
 phase:int=0
 seed:int=0
def pointers(c,s=TIMESTEP):
 home=STACK+c.phase
 return [(OUTPUT+8,OUTPUT+12),(OUTPUT+8,OUTPUT+8),(s,OUTPUT+12),(OUTPUT+8,s),(home+8,OUTPUT+12),(OUTPUT+8,home+8),(home+8,home+8)][c.alias]
def fixture(c,s=TIMESTEP):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-256,512)};m.update({OUTPUT+i:(i*29+c.seed*11+90)&255 for i in range(32)})
 put(m,OUTPUT+8,c.x);put(m,OUTPUT+12,c.z);put(m,s,c.timestep);put(m,s+4,0x2468ACE0);put(m,STACK+c.phase+16,pointers(c,s)[1]);return m
def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+512}
def reference(initial,c,s=TIMESTEP,addresses=None):
 m=dict(initial);home=STACK+c.phase;px,pz=pointers(c,s)if addresses is None else addresses;put(m,home+8,c.rate)
 oldx=floating(read(m,px));oldz=floating(read(m,pz));tx=floating(c.target_x);tz=floating(c.target_z);dx=rounded(tx-oldx);dz=rounded(tz-oldz)
 if dx==0.0 and dz==0.0:return m,False
 distance=rounded(math.sqrt(rounded(rounded(dx*dx)+rounded(dz*dz))));rate=rounded(floating(c.rate)*floating(read(m,s)));put(m,home+8,bits(rate))
 steps=[floating(bits(rounded(divide(d,distance)*rate))&0x7FFFFFFF)for d in(dx,dz)]
 for i,(pointer,delta,target,step)in enumerate(zip((px,pz),(dx,dz),(tx,tz),steps)):
  previous=oldx if i==0 else floating(read(m,pointer))
  if delta>=0.0:
   value=rounded(previous+step)
   if value>target:value=target
  else:
   value=rounded(previous-step)
   if value<target:value=target
  put(m,pointer,bits(value))
 return m,True
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY,s=TIMESTEP,connected=None):
  self.c=c;self.step_symbol=s;px,pz=pointers(c,s)
  super().__init__(words,memory,c,entry=entry,arguments=(0x87654321,0x76543210,c.rate,px,pz),connected=connected)
  self.f[12]=c.target_x;self.f[14]=c.target_z;self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2,3,4,5,6,7,50,60,62):
   a,b=floating(self.f[fs]),floating(self.f[ft])
   if fn==0:self.f[fd]=bits(rounded(a+b))
   elif fn==1:self.f[fd]=bits(rounded(a-b))
   elif fn==2:self.f[fd]=bits(rounded(a*b))
   elif fn==3:self.f[fd]=bits(divide(a,b))
   elif fn==4:self.f[fd]=bits(math.sqrt(a)if a>=0.0 else math.nan)
   elif fn==5:self.f[fd]=self.f[fs]&0x7FFFFFFF
   elif fn==6:self.f[fd]=self.f[fs]
   elif fn==7:self.f[fd]=self.f[fs]^0x80000000
   elif fn==50:self.condition=a==b
   elif fn==60:self.condition=a<b
   else:self.condition=a<=b
  else:super().execute(w)
 def record_call(self,t):raise AssertionError(('Leaf made a call',hex(t)))
 def hook(self,t):raise AssertionError(('Leaf used a helper',hex(t)))
def words(path,s=TIMESTEP):
 text,fs,rs=parse_object(path);a,n=fs['func_1505A250']['value'],fs['func_1505A250']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};assert set(n for vs in refs.values()for _,n in vs)<={'D_800D1550'};return bound_blob(text[a:a+n],refs,{'D_800D1550':s})
def check(m,c,s=TIMESTEP):
 expected,active=reference(m.initial,c,s);px,pz=pointers(c,s);changed=set()
 for address in(px,pz):
  assert canonical(read(m.memory,address))==canonical(read(expected,address)),('float-output',c,hex(address),hex(read(m.memory,address)),hex(read(expected,address)))
  changed.update(range(address,address+4))
 assert all(m.memory[a]==v for a,v in public(expected).items()if a not in changed),('public-bytes',c)
 assert canonical(read(m.memory,STACK+c.phase+8))==canonical(read(expected,STACK+c.phase+8)),('rate-home',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],('saved-ABI',c)
 assert not m.calls
def cases():
 cs=[]
 for x,z,tx,tz,rate,alias in itertools.product((-20.,-1.,0.,1.,20.),(-20.,-1.,0.,1.,20.),(-1.,0.,1.),(-1.,0.,1.),(0.5,100.),(0,1)):
  cs.append(Case(x=bits(x),z=bits(z),target_x=bits(tx),target_z=bits(tz),rate=bits(rate),alias=alias))
 patterns=(0,0x80000000,1,0x80000001,0x007FFFFF,0x807FFFFF,0x00800000,0x80800000,0x3F000000,0xBF000000,0x3F800000,0xBF800000,0x41200000,0xC1200000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0xFFC12345)
 for field,value,alias in itertools.product(('target_x','target_z','x','z','rate','timestep'),patterns,range(4)):cs.append(replace(Case(alias=alias),**{field:value}))
 for x,z,rate in itertools.product((1,0x007FFFFF,0x00800000,0x3F800000,0x7F7FFFFF),(0,1,0x80000001),(0,1,0x3F800000,0x7F800000)):cs.append(Case(x=x,z=z,rate=rate))
 for alias,rate,timestep in itertools.product((4,5,6),(0,0x3F000000,0xBF800000,0x7F800000),(0,0x3F800000,0x40000000)):cs.append(Case(alias=alias,rate=rate,timestep=timestep))
 for value in(0x3EFFFFFF,0x3F000000,0x3F000001):cs.append(Case(x=0,z=0,target_x=0x3F000000,target_z=0,rate=value))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]
def main():
 cs=cases();original=struct.unpack_from('>86I',(root/'conker/conker.us.bin').read_bytes(),0x87700);raw=words(out/'selected.o');assert list(original)==raw
 seen=set();pairs=0
 for c in cs:
  a=Oracle(raw,fixture(c),c);b=Oracle(original,fixture(c),c)
  for m in(a,b):m.run();check(m,c);seen.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+344)
  assert(a.memory,a.r,a.f,a.trace)==(b.memory,b.r,b.f,b.trace),('complete-machine',c);pairs+=1
 report=dict(cases=len(cs),executions=2*len(cs),coverage=len(seen),missing=[i for i in range(86)if i not in seen],complete_machine_and_trace_pairs=pairs,output_and_timestep_aliases=True,physical_parameter_home_aliases_guest_only=True,NaNs_compared_by_class_in_reference=True,FCSR_or_hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
