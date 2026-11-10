"""Independent packed-coordinate, mode, float and reloaded path-publication contract."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_path_offset_15078544_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.experiments import game_path_offset_15078544_match as qualify
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=qualify.ENTRY;SYMS=qualify.SYMS;ACTOR=0x20000;ALT_ACTOR=0x21000;TABLE=0x60000;ALT_TABLE=0x61000;ROWS=(0x70000,0x72000,0x74000,0x76000)
ACTORS=0x800CC2D0;CALL_NAMES=('func_15048A40','func_150489B0','func_150484A0','sinf','cosf')
u32=lambda n:n&0xFFFFFFFF
byte=lambda n:((n&255)^128)-128
mul=lambda a,b:bits(floating(a)*floating(b))
add=lambda a,b:bits(floating(a)+floating(b))
sub=lambda a,b:bits(floating(a)-floating(b))
same=lambda a,b:a==b or math.isnan(floating(a))and math.isnan(floating(b))
def trunc(v):
 f=floating(v);return u32(math.trunc(f))if math.isfinite(f)and-2147483648<=f<2147483648 else 0x80000000
@dataclass(frozen=True)
class Case:
 command:int=0
 highx:int=0x81
 highz:int=0x7F
 packed:int=0x5A
 selected:int=1
 group:int=0
 heading:int=0xC1FF
 target:tuple=(0x43C80000,0xC1D40000,0xC4FA0000)
 current:tuple=(0x44034000,0x42C80000,0x44034000)
 returns:tuple=(0x3F000000,0x3F400000,0x3F200000)
 effects:int=0
 alias:int=0
 phase:int=0

def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base,n in((ACTOR,812),(ALT_ACTOR,812),(s['D_800CC2D0'],812*26),(TABLE,1024),(ALT_TABLE,1024),*((p,2080)for p in ROWS)):
  m.update({base+i:(i*29+0x59)&255 for i in range(-16,n+16)})
 # The current-actor global follows the 26-entry actor array. Its guard range
 # overlaps the array tail; preserve bytes already initialized for that owner.
 for name in('D_800D154C','D_800D1890','D_800D2104'):
  for i in range(-16,32):m.setdefault(s[name]+i,(i*13+0xA5)&255)
 for base,group in((ACTOR,c.group),(ALT_ACTOR,c.group^1)):
  m[base+546]=c.selected;m[base+319]=group
  for i,v in enumerate(c.current):put(m,base+20+i*4,v)
 target=s['D_800CC2D0']+c.selected*812
 for i,v in enumerate(c.target):put(m,target+20+i*4,v)
 put(m,target+122,c.heading,2);put(m,s['D_800D154C'],ACTOR);put(m,s['D_800D2104'],TABLE)
 for i in range(256):put(m,TABLE+i*4,ROWS[i&1]);put(m,ALT_TABLE+i*4,ROWS[2+(i&1)])
 for n,v in(('D_800D1890',c.command),('D_800D1891',c.highx),('D_800D1892',c.highz),('D_800D1893',c.packed)):m[s[n]]=v
 if c.alias:
  assert c.command==64 and c.highx==c.highz==c.packed==0
  if c.alias==1:destination=s['D_800D1890'];x,y=258.,-19.
  elif c.alias==2:destination=s['D_800D154C']+2;x,y=4096.,-19.
  elif c.alias==3:destination=s['D_800D2104'];x,y=6.,4096.
  else:assert c.alias==4;destination=STACK+c.phase-12;x,y=16256.,0.
  put(m,TABLE+c.group*4,destination-8);put(m,target+20,bits(x));put(m,target+24,bits(y));put(m,target+28,bits(7.))
 return m

def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+1024}
def snapshot(m):return tuple(sorted(public(m).items()))
def effect(m,c,stage,s=SYMS):
 if c.effects&1:put(m,s['D_800D154C'],ALT_ACTOR)
 if c.effects&2:m[s['D_800D1890']]=(65+stage*71)&255
 if c.effects&4:put(m,s['D_800D2104'],ALT_TABLE)
 if c.effects&8:
  target=s['D_800CC2D0']+c.selected*812
  for i in range(3):put(m,target+20+i*4,bits(9000.+stage+i))
  for base in(ACTOR,ALT_ACTOR):m[base+319]^=1;put(m,base+20,bits(-3.*stage))

def reference(initial,c=Case(),s=SYMS):
 m=dict(initial);cmd=m[s['D_800D1890']];actor=read(m,s['D_800D154C']);m[s['D_800D1890']]=cmd&63;target=s['D_800CC2D0']+m[actor+546]*812;packed=m[s['D_800D1893']]
 dx=bits(float(((byte(m[s['D_800D1891']])*16)|(packed>>4))*8));dz=bits(float(((byte(m[s['D_800D1892']])*16)|(packed&15))*8));y=read(m,target+24);x=read(m,target+20);z=read(m,target+28);mode=cmd>>6;calls=[];observations=[]
 def call(name,args,value):calls.append((s[name],args));observations.append(snapshot(m));effect(m,c,len(calls),s);return value
 if mode==0:
  heading=((read(m,target+122,2)>>8)-64)&255;sin=call('func_15048A40',(heading,),c.returns[0]);cos=call('func_150489B0',(heading,),c.returns[1]);actor=read(m,s['D_800D154C'])
 elif mode==1:sin=bits(0.);cos=bits(1.)
 else:
  angle=call('func_150484A0',(sub(read(m,actor+20),x),sub(read(m,actor+28),z)),c.returns[0]);sin=call('sinf',(angle,),c.returns[1]);cos=call('cosf',(angle,),c.returns[2]);actor=read(m,s['D_800D154C'])
 x=add(x,add(mul(dx,cos),mul(dz,sin)));delta=sub(mul(dz,cos),mul(dx,sin));writes=[]
 for field,value in((8,x),(10,y),(12,add(z,delta))):
  table=read(m,s['D_800D2104']);group=m[actor+319];row=read(m,table+group*4);index=m[s['D_800D1890']];p=row+index*8+field;v=trunc(value)&65535;put(m,p,v,2);writes.append((p,v));actor=read(m,s['D_800D154C'])
 return m,calls,observations,writes

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=());self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.observations=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==13:self.f[w>>6&31]=trunc(self.f[w>>11&31]);return
  return super().execute(w)
 def record_call(self,t):
  names={self.syms[n]:n for n in CALL_NAMES};assert t in names,hex(t);name=names[t];a=(self.r[4]&255,)if name.startswith('func_15048')and name!='func_150484A0'else(self.f[12],self.f[14])if name=='func_150484A0'else(self.f[12],);self.calls.append((t,a));self.observations.append(snapshot(self.memory));self.events.append(('CALL',t,a))
 def hook(self,t):
  stage=len(self.observations);effect(self.memory,self.case,stage,self.syms)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=self.case.returns[stage-1];self.hi,self.lo=0xA5000010,0xA5000011

def words(p,s=SYMS):return bound_blob(*qualify.payload(p),s)
def check(m,c=Case(),s=SYMS):
 want,calls,obs,writes=reference(m.initial,c,s);assert len(m.calls)==len(calls),('call count',c)
 for a,b in zip(m.calls,calls):assert a[0]==b[0]and len(a[1])==len(b[1])and all(same(x,y)for x,y in zip(a[1],b[1])),('ABI',a,b,c)
 assert m.observations==obs,('helper snapshots',c)
 assert public(m.memory)==public(want),('public',[(hex(p),v,want.get(p))for p,v in public(m.memory).items()if want.get(p)!=v][:8],c)
 actual=[(p,v)for mode,p,n,v in m.trace if mode=='W'and n==2 and not STACK-1024<=p<STACK+1024];assert actual==writes,('store addresses/order',actual,writes,c)
 assert all(m.memory[p]==v for p,v in m.initial.items()if STACK+c.phase<=p<STACK+c.phase+512),('caller storage',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]

def cases():
 result=[replace(Case(),command=n,highx=(n*37)&255,highz=(n*71)&255,packed=(n*23)&255,heading=n*257,selected=n%4,group=n&1,phase=(n&1)*8)for n in range(256)]
 for command,effects in itertools.product((3,65,133,197),range(16)):result.append(replace(Case(),command=command,effects=effects))
 for n in(0,0x80000000,0x3F800000,0xBF800000,0x7F800000,0xFF800000,0x7FC12345,0x4F000000):
  for axis in range(3):
   values=list(Case().target);values[axis]=n;result.append(replace(Case(),command=64,target=tuple(values)))
 for alias in(1,2,3):result.append(replace(Case(),command=64,highx=0,highz=0,packed=0,alias=alias))
 result.append(replace(Case(),selected=25,command=0xC1))
 return result

def main():
 paths={'raw':out/'selected.o','normalized':out/'qualified-padded/game_A28B0.c.o','retail':out/'retail-linked.o'};counts={};coverage={}
 for label,p in paths.items():
  seen=set()
  for c in cases():m=Oracle(words(p),fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  counts[label]=len(cases());coverage[label]=len(seen&set(range(ENTRY,ENTRY+(608 if label=='raw'else 600),4)))
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={n:(0x15300000+i*0x100 if n in CALL_NAMES else 0x80300000+low+i*0x10000)for i,n in enumerate(SYMS)}
  for mode in(0,1,2,3):
   c=replace(Case(),command=mode*64+3,effects=15,phase=(mode&1)*8);m=Oracle(words(paths['raw'],s),fixture(c,s),c,entry=ENTRY+0x4000,s=s);m.run();check(m,c,s);rebases+=1
 c=replace(Case(),command=64,highx=0,highz=0,packed=0,alias=4);events={}
 for label,p in paths.items():
  m=Oracle(words(p),fixture(c),c);m.run();events[label]=[(p,v)for mode,p,n,v in m.trace if mode=='W'and n==2]
 assert events['normalized']==events['retail']!=events['raw'],events
 report=dict(cases_per_body=counts,total=sum(counts.values()),coverage=coverage,independent_rebases=rebases,all_public_bytes=True,all_three_store_addresses_and_order=True,live_actor_command_table_reloads=True,signed_packed_coordinates=True,void_no_arguments=True,private_home_alias_profiles={'normalized_equals_retail':True,'raw_late_private_reload_differs':True},invalid_float_conversion_guest_only=True,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
