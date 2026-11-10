"""Independent attached-effect model with live reloads and seeded guest padding."""
import itertools,json,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-next-151B4CD0-match'
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY,OWNER,ALT,OUTPUT=0x151B4CD0,0x30000,0x31000,0x50000
SELECT,NOTIFY,RNG,CREATE,COPY=0x15134070,0x1516962C,0x150ADA20,0x1513418C,0x10022EC0
PADDING=(9,10,11,17,18,19,46,47)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 owner:int=OWNER
 kind:int=1
 class_byte:int=1
 identity:int=0x87
 selector:int=0xA5A500E1
 category:int=0x87654321
 random:int=0xFFFFFFFF
 scale:int=0x3EE56042
 outcome:int=1
 mutation:int=0
 after:int=0
 alias:int=0
 phase:int=0
 seed:int=0
def symbols():return dict(D_800A3FE6=0x800A3FE6,D_800AA3D0=0x800AA3D0,func_15134070=SELECT,func_1516962C=NOTIFY,func_150ADA20=RNG,func_1513418C=CREATE,memcpy=COPY)
def slot(c,s=None):return u32((s or symbols())['D_800A3FE6']+u32(c.kind)*16)
def output(c,s=None):return(OUTPUT,OWNER,(s or symbols())['D_800A3FE6']-0x58,STACK+c.phase+4-0x58)[c.alias]if c.outcome else 0
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def fixture(c,s=None):
 s=s or symbols();m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,1024)}
 for a,n in((OWNER-16,0x350),(ALT-16,0x350),(OUTPUT-16,0xB0),(s['D_800A3FE6']-0x60,0x1A0)):m.update({a+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 for p in(OWNER,ALT):put(m,p,1);put(m,p+4,c.identity,1);put(m,p+0x3B,c.identity^(0x55 if p==ALT else 0),1);put(m,p+0x1D4,0);put(m,p+0x74,15,1)
 put(m,slot(c,s),c.class_byte,1);put(m,s['D_800AA3D0'],c.scale);return m
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def effect(m,c,s,t,home):
 if t==s['func_15134070']:
  if c.mutation&1:put(m,slot(c,s),c.after,1);put(m,OWNER+0x3B,c.identity^0x33,1)
  if c.mutation&16:put(m,home,ALT)
 if t==s['func_1516962C']:
  p=read(m,home)
  if c.mutation&2:put(m,p+0x3B,read(m,p+0x3B,1)^0x66,1);put(m,s['D_800AA3D0'],0x7FC12345)
  if c.mutation&32:put(m,home,ALT);put(m,home+4,0x12340080);put(m,home+8,0x80000000)
 if t==s['func_150ADA20']and c.mutation&4:put(m,slot(c,s),c.after,1);put(m,s['D_800AA3D0'],0x40000000);put(m,read(m,home)+0x3B,0xEE,1)
 if t==s['func_1513418C']and c.mutation&8:put(m,home-56,c.after^1,1)
def reference(initial,c,s=None):
 s=s or symbols();m=dict(initial);home=STACK+c.phase;packet=home-52;payload=home-56;calls=[];packets=[];copies=[]
 put(m,home+4,c.selector);put(m,home+8,c.category)
 if not c.owner:return m,calls,0,packets,copies
 put(m,home,c.owner);calls.append((s['func_15134070'],(c.owner,)));effect(m,c,s,s['func_15134070'],home);put(m,home-60,c.kind)
 if u32(c.kind)==99:return m,calls,0,packets,copies
 if read(m,slot(c,s),1)==2:return m,calls,0,packets,copies
 owner=read(m,home);calls.append((s['func_1516962C'],(40,owner,22)));effect(m,c,s,s['func_1516962C'],home);owner=read(m,home)
 put(m,packet,0);put(m,packet+4,0);put(m,packet+8,read(m,owner+0x3B,1),1);put(m,packet+12,owner);put(m,packet+16,2,1)
 for at,v in((20,0),(24,0xC1D80000),(28,0x41800000),(32,0x41700000),(36,read(m,s['D_800AA3D0']))):put(m,packet+at,v)
 put(m,packet+42,6,1);calls.append((s['func_150ADA20'],()));effect(m,c,s,s['func_150ADA20'],home);put(m,packet+40,u32(c.random)%21+40,2)
 for at,v in((43,8),(44,255),(45,7)):put(m,packet+at,v,1)
 put(m,payload,int(read(m,slot(c,s),1)==1),1);packets.append(data(m,packet,48));selector=read(m,home+7,1);category=read(m,home+8);calls.append((s['func_1513418C'],(packet,1,selector,category)));effect(m,c,s,s['func_1513418C'],home);answer=output(c,s)
 if answer:
  calls.append((s['memcpy'],(u32(answer+0x58),payload,1)));copy=data(m,payload,1);copies.append(copy);put(m,u32(answer+0x58),copy[0],1)
 return m,calls,answer,packets,copies
class Oracle(FactoryOracle):
 def __init__(self,ws,memory,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=s or symbols();super().__init__(ws,memory,c,entry=entry,arguments=(c.owner,c.selector,c.category),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.packets=[];self.copies=[]
 def record_call(self,t):
  counts={self.s['func_15134070']:1,self.s['func_1516962C']:3,self.s['func_150ADA20']:0,self.s['func_1513418C']:4,self.s['memcpy']:3,ENTRY:3};assert t in counts,hex(t);args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==self.s['func_1513418C']:self.packets.append(data(self.memory,args[0],48))
  if t==self.s['memcpy']:self.copies.append(data(self.memory,args[1],args[2]))
 def hook(self,t):
  effect(self.memory,self.c,self.s,t,STACK+self.c.phase);value={self.s['func_15134070']:u32(self.c.kind),self.s['func_150ADA20']:u32(self.c.random),self.s['func_1513418C']:output(self.c,self.s)}.get(t,0x87654321)
  if t==self.s['memcpy']:
   a=self.calls[-1][1];chunk=data(self.memory,a[1],a[2])
   for i,b in enumerate(chunk):put(self.memory,u32(a[0]+i),b,1)
   value=a[0]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True;self.r[2]=value
def words(path,s=None):
 text,fs,rs=parse_object(path);a,n=fs['func_151B4CD0']['value'],fs['func_151B4CD0']['size'];return bound_blob(text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s or symbols())
def check(m,c,s=None):
 expected,calls,answer,packets,copies=reference(m.initial,c,s);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory)==public(expected),(c,'public');assert m.r[2]==answer,(c,'return');assert m.packets==packets,(c,'packets',m.packets,packets);assert m.copies==copies,(c,'copy');assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],(c,'ABI')
def run(ws,c,s=None):
 m=Oracle(ws,fixture(c,s),c,s=s);m.run();check(m,c,s);return m
def cases():
 cs=[Case(kind=k,class_byte=cl,outcome=o,mutation=mu,after=after)for k,cl,o,mu,after in itertools.product((0,1,19,99),(0,1,2,255),(0,1),(0,1,2,4,8,15),(0,1,2))]
 for v in(0,1,20,21,40,41,0x7FFFFFFF,0x80000000,0xFFFFFFFF):cs.append(Case(random=v))
 for v in(0,0x80000000,1,0x7F800000,0xFF800000,0x7FA12345,0x7FC12345,0xFFFFFFFF):cs.append(Case(scale=v))
 for v in(0,127,128,255,256,0x80000000,0xFFFFFFFF):cs.append(Case(selector=v,category=v))
 for mu,alias in itertools.product((0,15,16,32,63),range(4)):cs.append(Case(mutation=mu,alias=alias))
 cs.extend(Case(owner=0,selector=v,category=v)for v in(0,0xFFFFFFFF))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]
def main():
 cs=cases();truth=struct.unpack_from('>95I',(root/'conker/conker.us.bin').read_bytes(),0x1E2180);raw=words(out/'selected.o');assert raw==list(truth);seen=set()
 for c in cs:
  a,b=[run(ws,c)for ws in(raw,truth)];assert(a.memory,a.r,a.f,a.trace,a.calls,a.packets,a.copies)==(b.memory,b.r,b.f,b.trace,b.calls,b.packets,b.copies),(c,'machine');seen.update((pc-ENTRY)//4 for pc in a.visits if ENTRY<=pc<ENTRY+380)
 report=dict(cases=len(cs),executions=2*len(cs),coverage=len(seen),missing=[i for i in range(95)if i not in seen],complete_machine_and_trace_pairs=len(cs),all_48_packet_bytes_guest_checked=True,padding=PADDING,parameter_homes_and_private_payload_mutations_guest_only=True,FCSR_or_hardware_qualified=False);(out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
