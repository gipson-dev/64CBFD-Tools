"""Independent complete strip-constructor reference; disjoint mapped fixtures."""
from pathlib import Path
from dataclasses import dataclass,asdict
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_strip_constructor_151acbd4_private_recovery as source
R,P,ENTRY=source.ROOT,source.OUT,source.ENTRY
RECORD,DESC,POINTS,VERTICES,MARK=0x30000,0x50000,0x60000,0x80000,0x70000
TABLE,CATEGORY=0x80090B60,0x800BE9F0
SYMS={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())}
CREATE,ALLOC,COPY=SYMS['func_15167A68'],SYMS['allocate_memory'],SYMS['memcpy'];COUNTS={CREATE:6,ALLOC:4,COPY:3}
u32=lambda n:n&0xffffffff
signed=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
@dataclass(frozen=True)
class Case:
 seed:int=0;outcome:int=1;category:int=0;mutation:int=0;phase:int=0;extra:int=0;coords:int=0;scale:int=0
COORDS=((-12.75,70.5,-45.25,-120.75),(0.,0.,0.,0.),(2147483520.,-2147483648.,-2147483648.,2147483520.),(-2147483648.,2147483520.,2147483520.,-2147483648.),(16777216.,16777218.,-16777218.,-16777216.))
SCALES=(0x3f800000,0x00000000,0x80000000,0x7fc00123,0x7f800000,0xff800000,0x3e800000)
REGIONS=((RECORD,88),(DESC,36),(POINTS,480),(VERTICES,2560),(TABLE,768),(CATEGORY,4),(MARK,4))
def cases():
 for seed,outcome in itertools.product(range(256),(0,1)):
  yield Case(seed,outcome,(0,11,44,57)[seed%4],seed%32,(seed&1)*8,(0,-1,0x7fffffff,-0x80000000)[seed%4],seed%5,seed%7)
 for category,mutation,phase,coords,scale in itertools.product((0,11,44,57),(0,1,2,4,8,16,31),(0,8),(0,2,3),(0,1,3)):
  yield Case(7,1,category,mutation,phase,-1,coords,scale)
def fixture(c):
 assert all(not(STACK-4096<at+n and at<STACK+1024)for at,n in REGIONS)
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-4096,1024)}
 for at,n in REGIONS:m.update({at+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for off,v in zip((4,8,12,20),COORDS[c.coords]):put(m,DESC+off,bits(v))
 put(m,DESC+28,SCALES[c.scale]);m[DESC]=c.seed;put(m,CATEGORY,c.category)
 for i in range(64):put(m,TABLE+12*i+6,(0,1,63,256,65535)[(i+c.seed)%5],2);put(m,TABLE+12*i+8,(0,1,16,1024,65535)[(i+c.seed)%5],2)
 return m
class Service:
 def __init__(self,m,c):self.m=m;self.c=c;self.calls=[];self.allocations=0
 def invoke(self,t,args):
  m,c=self.m,self.c;n=len(self.calls);self.calls.append((t,tuple(args)))
  if t==COPY:
   assert args==(RECORD+16,DESC,36)
   for i in range(36):m[RECORD+16+i]=m[DESC+i]
   return RECORD+16
  if t==CREATE:
   if c.mutation&1:
    for off,v in zip((4,8,12,20),(31.75,-100.25,20.5,300.75)):put(m,DESC+off,bits(v))
    put(m,DESC+28,bits(2.5))
   if c.mutation&16:put(m,CATEGORY,57)
   answer=RECORD if c.outcome else 0
  else:
   assert t==ALLOC and args in((480,1,0,0),(2560,1,2,0))
   if self.allocations==0:
    if c.mutation&2:
     for off,v in zip((20,24,28,36),(-13.75,34.25,23.5,-41.25)):put(m,RECORD+off,bits(v))
     put(m,RECORD+44,bits(4.0))
    answer=POINTS
   else:
    if c.mutation&4:m[RECORD+66]=7;put(m,RECORD+60,bits(99.5))
    if c.mutation&8:
     for texture in(54,55):put(m,TABLE+12*texture+6,127,2);put(m,TABLE+12*texture+8,513,2)
    if c.mutation&16:put(m,CATEGORY,11 if c.seed&1 else 57)
    answer=VERTICES
   self.allocations+=1
  put(m,MARK,u32(0x13579bdf+n*0x10203+t));return answer
def reference(initial,c):
 m=dict(initial);s=Service(m,c);category=read(m,CATEGORY)
 record=s.invoke(CREATE,(78 if category==44 else 47,0,u32(c.extra+88),1,255,1))
 if not record:return m,s.calls,0
 s.invoke(COPY,(record+16,DESC,36));put(m,record+52,fp(bits(1.),read(m,record+44),'div','left'));put(m,record+68,0);put(m,record+82,0,2)
 points=s.invoke(ALLOC,(480,1,0,0))
 x,y,endY,z=(int(floating(read(m,record+off)))for off in(20,24,36,28));put(m,record+56,points);m[record+66]=20;delta=signed(y-endY)
 for i in range(20):
  product=signed(delta*i);q=abs(product)//19*(-1 if product<0 else 1);interp=signed(q+endY)
  for off,value in((0,bits(float(x))),(4,bits(float(interp))),(8,bits(float(z))),(12,0),(16,0),(20,0)):put(m,read(m,record+56)+24*i+off,value)
 put(m,record+60,fp(bits(float(delta)),bits(19.),'div','left'));vertices=s.invoke(ALLOC,(2560,1,2,0));put(m,record+72,vertices)
 texture,shift=(55,4)if read(m,CATEGORY)==11 else(54,5);put(m,record+64,texture,2)
 red,green,blue=(88,75,44)if read(m,CATEGORY)==57 else(255,255,255)
 step=read(m,TABLE+12*read(m,record+64,2)+6,2)>>2;height=read(m,TABLE+12*read(m,record+64,2)+8,2)-1
 u=(0x2000,(256+step)<<5,(256+step*2)<<5,(256+step*3)<<5)
 for bank,i,corner in itertools.product(range(2),range(20),range(4)):
  index=bank*80+i*4+corner
  for off,value,size in((6,0,2),(8,u[corner],2),(10,(256+i*height)<<shift,2),(12,red,1),(13,green,1),(14,blue,1),(15,255,1)):put(m,read(m,record+72)+index*16+off,value,size)
 put(m,record+76,0);return m,s.calls,record
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c):
  super().__init__(words,initial,c,entry=ENTRY,s={},arguments=(DESC,u32(c.extra)));self.service=Service(self.memory,c);self.saved=tuple(self.r[16:24]);self.saved_more=(self.r[28],self.r[30],self.r[29]);self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(0,1,2,3):self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul','div')[w&63],'left');return
  return super().execute(w)
 def record_call(self,t):assert t in COUNTS,hex(t);self.pending=t,tuple(self.arguments(COUNTS[t]))
 def hook(self,t):
  target,args=self.pending;assert target==t;answer=self.service.invoke(t,args)
  for i in range(max(4,COUNTS[t])):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xdeadbeef;self.r[2]=answer
def public(m):return{p:v for p,v in m.items()if not STACK-4096<=p<STACK+1024}
def verify(words,c):
 initial=fixture(c);expected,calls,result=reference(initial,c);m=Oracle(words,initial,c).run()
 assert public(m.memory)==public(expected),('public',asdict(c),next(((hex(p),v,expected.get(p))for p,v in public(m.memory).items()if v!=expected.get(p)),None))
 assert m.service.calls==calls and m.r[2]==result,('calls/return',asdict(c),m.service.calls,calls,m.r[2],result)
 assert tuple(m.r[16:24])==m.saved and(m.r[28],m.r[30],m.r[29])==m.saved_more and tuple(m.f[20:])==m.saved_fp
 return m
def programs():
 result={'retail':list(struct.unpack('>360I',(P/'retail.bin').read_bytes()))}
 for label in('v2','v7'):
  b,r=payload(P/(label+'.o'),'func_151ACBD4');result[label]=bound_blob(b,r,SYMS)
 return result
def main():
 code=programs();seen={k:set()for k in code};n=0
 for c in cases():
  for label,words in code.items():seen[label].update(verify(words,c).visits)
  n+=1
  if n%256==0:print(json.dumps(dict(cases=n)),flush=True)
 report=dict(cases_per_stream=n,streams=list(code),words_visited={k:len(v)for k,v in seen.items()},unvisited={label:[hex(i*4)for i in range(len(words))if ENTRY+4*i not in seen[label]]for label,words in code.items()},public_disjoint_from_stack=True,all_initialized_public_bytes_compared=True,source_installed=False,c_match_credit=0)
 (P/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
