"""Independent slot-search model, float rounding, helper effects and guest ABI."""
import itertools,json,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-slot-sector-search-1505DDA8-match'
from tools.tests.game_paired_float_approach_1505a250_oracle import Oracle as FloatOracle,bits,floating,rounded,canonical
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x1505DDA8;HELPER=0x1505DF10;ACTOR=0x30000;MARK=0x70000;LIMIT=0x80082FA0;TABLE=0x800CC2D0
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
s8=lambda v:((v&255)^128)-128
def symbols():return dict(D_80082FA0=LIMIT,D_800CC2D0=TABLE,func_1505DF10=HELPER)
@dataclass(frozen=True)
class Case:
 limit:int=3
 pattern:int=0
 match:int=1
 heading:int=0
 angle:int=0
 width:int=512
 velocity:int=0x40000000
 scale:int=0x3F800000
 distance:int=0x3E800000
 miss:int=0x7F800000
 mutation:int=0
 new_limit:int=0
 alias:int=-1
 stop_after:int=0
 unused:int=0x123456E1
 phase:int=0
 seed:int=0
 state:int=1
def actor(c,s=None):return ACTOR if c.alias<0 else(s or symbols())['D_800CC2D0']+c.alias*812
def active(c,i):return(1 if c.pattern==0 else 0 if c.pattern==1 else i%2==0 if c.pattern==2 else i==c.match)
def fixture(c,s=None):
 s=s or symbols();m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)};a=actor(c,s)
 for address,n in((a,812),(MARK,32)):m.update({address+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 for i in range(256):put(m,s['D_800CC2D0']+i*812,c.state if active(c,i)else 0)
 put(m,a+0x3C,c.velocity);put(m,a+0x76,c.angle,2);put(m,s['D_80082FA0'],c.limit);put(m,MARK,0);return m
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
def effect(m,c,slot,outputs,s=None):
 s=s or symbols();a=actor(c,s);n=read(m,MARK)+1;put(m,MARK,n)
 put(m,outputs[0],c.heading,2);put(m,outputs[1],0xC1200000);put(m,outputs[2],0x3F000000)
 if c.mutation&1:put(m,a+0x76,read(m,a+0x76,2)^0x100,2)
 if c.mutation&2:put(m,a+0x3C,bits(8.))
 if c.mutation&4:put(m,s['D_80082FA0'],c.new_limit)
 if c.mutation&8:put(m,s['D_800CC2D0']+((slot+1)&255)*812,0)
 if c.mutation&16:
  for i in range(4):put(m,STACK+c.phase+4*i,0xABCDEF00+i)
 if c.stop_after and n>=c.stop_after:put(m,s['D_80082FA0'],-1)
 result=c.distance if slot==c.match or c.match==-2 else c.miss
 put(m,MARK+4,result);put(m,MARK+8,slot);return result
def reference(initial,c,s=None):
 s=s or symbols();m=dict(initial);a=actor(c,s);slot=0;calls=[];iterations=0
 while slot<=signed(read(m,s['D_80082FA0'])):
  iterations+=1;assert iterations<=600,('Unbounded reference fixture',c)
  if read(m,s['D_800CC2D0']+slot*812):
   radius=rounded(rounded(floating(read(m,a+0x3C))*floating(c.scale))*.5)
   outputs=(STACK+c.phase-4,STACK+c.phase-8,STACK+c.phase-12);result=effect(m,c,slot,outputs,s);calls.append(slot)
   if floating(result)<rounded(radius*radius):
    if(read(m,a+0x76,2)-c.heading+(c.width&65535)//2)&65535 < (c.width&65535):return m,calls,u32(s8(slot))
  slot=(slot+1)&255
 return m,calls,0xFFFFFFFF
class Oracle(FloatOracle):
 def __init__(self,ws,memory,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=s or symbols();FactoryOracle.__init__(self,ws,memory,c,entry=entry,arguments=(actor(c,self.s),c.unused,c.width,c.scale),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.raw_calls=[]
 def record_call(self,t):
  assert t==self.s['func_1505DF10'],hex(t);args=tuple(map(u32,self.arguments(6)));self.raw_calls.append((t,args));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  a=self.calls[-1][1];assert a[0]==actor(self.c,self.s)and a[1]<256 and a[5]==0,a
  value=effect(self.memory,self.c,a[1],(a[2],a[3],a[4]),self.s)
  for i in range(6):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.f[0]=value
def words(path,s=None):
 t,fs,rs=parse_object(path);a,n=fs['func_1505DDA8']['value'],fs['func_1505DDA8']['size'];return bound_blob(t[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s or symbols())
def check(m,c,s=None):
 s=s or symbols();expected,calls,result=reference(m.initial,c,s);assert [a[1]for _,a in m.calls]==calls,(c,'calls');assert public(m.memory)==public(expected),(c,'public');assert m.r[2]==result,(c,'return',hex(m.r[2]),hex(result));assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],(c,'saved-ABI')
 home=STACK+c.phase
 for _,a in m.calls:assert a==(actor(c,s),a[1],home-4,home-8,home-12,0),(c,'output-addresses',a)
 if not(c.mutation&16 and calls):assert read(m.memory,home+4)==c.unused and read(m.memory,home+8)==c.width,(c,'argument-homes')
def cases():
 cs=[Case(limit=n,pattern=p,match=k,width=w)for n,p,k,w in itertools.product((-1,0,1,3,25),range(4),(-1,0,1,3),(0,1,512,65535))]
 for w in(0,1,2,3,511,512,513,32767,32768,65535):
  for h,a in itertools.product((0,1,65535,w//2,(65536-w//2)&65535),(0,1,32768,65535)):cs.append(Case(width=w,heading=h,angle=a))
 patterns=(0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x3F000000,0xBF000000,0x3F800000,0xBF800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0xFFC12345)
 for field,v,mutation in itertools.product(('velocity','scale','distance'),patterns,(0,1,2,3)):cs.append(replace(Case(mutation=mutation),**{field:v}))
 for mutation,alias,k,n in itertools.product((0,1,2,4,8,16),(-1,0,3),(-1,0,1,3),(0,3)):cs.append(Case(mutation=mutation,alias=alias,match=k,limit=n,new_limit=4 if n==0 else 0))
 for n,k in itertools.product((127,128,254,255),(0,127,128,254,255)):
  if k<=n:cs.append(Case(limit=n,match=k,pattern=3))
 for n in(-2147483648,-2,2147483647):cs.append(Case(limit=n,match=0))
 cs.extend((Case(limit=255,match=-1,stop_after=260),Case(velocity=bits(1.),scale=bits(1.),distance=0x3E800000),Case(velocity=bits(1.),scale=bits(1.),distance=0x3E7FFFFF),Case(velocity=bits(1.),scale=bits(1.),distance=0x3E800001),Case(width=0x1234FFFF),Case(width=0xFFFF0000)))
 cs.extend(Case(state=v)for v in(0,2,0x7FFFFFFF,0x80000000,0xFFFFFFFF))
 cs.extend((Case(match=0,unused=0),Case(mutation=2,distance=bits(4.))))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]
def main():
 cs=cases();retail=struct.unpack_from('>90I',(root/'conker/conker.us.bin').read_bytes(),0x8B258);raw=words(out/'selected.o');assert list(retail)==raw;seen=set();pairs=0;calls=0
 for c in cs:
  models=[]
  for ws in(raw,retail):
   m=Oracle(ws,fixture(c),c);m.run();check(m,c);seen.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+360);models.append(m)
  a,b=models;assert(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls),(c,'complete-machine');pairs+=1;calls+=len(a.calls)
 result=dict(cases=len(cs),executions=2*len(cs),complete_machine_and_trace_pairs=pairs,coverage=len(seen),missing=[i for i in range(90)if i not in seen],helper_calls=calls,float_edges_and_typed_aliases=True,live_helper_mutations=True,u8_wrap_terminated_fixture=True,FCSR_or_hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
