import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_motion_ring_integrator_151cd674_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x151CD674;OWNER=0x30000;RECORDS=0x50000;LIMIT=0x70000;STEP=0x800BE9A4;ACCEL=0x800AAFC0;HALF=0x800AAFC4
s8=lambda x:((x&255)^128)-128
bits=lambda x:struct.unpack('>I',struct.pack('>f',x))[0]
real=lambda x:struct.unpack('>f',struct.pack('>I',x&0xffffffff))[0]
f32=lambda x:real(bits(x))
@dataclass(frozen=True)
class Case:
 cap:int;current:int;end:int;count:int;flags:int;step:float;position:float;velocity:float;threshold:float=0.;accel:float=-.25;half:float=-.125;phase:int=0;seed:int=0
def cases():
 cs=[]
 for cap in (1,2,4,7):
  for current,end,count,flags,step,position,velocity in itertools.product((0,cap-1),(0,cap-1),(0,1,cap),(0,8),(-1.,0.,1.),(-5.,0.,15.),(-2.,2.)):
   cs.append(Case(cap,current,end,count,flags,step,position,velocity))
 for cap,step,position,velocity,threshold,accel,half in itertools.product((2,7),(.5,2.),(-1.,1.),(0.,1.),(-10.,10.),(-.5,.5),(-.25,.25)):
  cs.append(Case(cap,0,cap-1,cap,0,step,position,velocity,threshold,accel,half))
 return cs
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-256,512)};m.update({OWNER+i:(i*19+37)&255 for i in range(0xA0)});m.update({RECORDS+i:(i*13+11)&255 for i in range(224)});m.update({LIMIT+i:(i*7+9)&255 for i in range(80)})
 m[OWNER+0x25]=c.cap;m[OWNER+0x2c]=c.count&255;m[OWNER+0x2d]=c.current;m[OWNER+0x2e]=c.end;put(m,OWNER+0x1e,c.flags,2);put(m,OWNER+0x94,RECORDS);put(m,OWNER+0x98,LIMIT)
 for p,v in ((STEP,c.step),(ACCEL,c.accel),(HALF,c.half),(LIMIT+0x44,c.threshold)):put(m,p,bits(v))
 for i in range(c.cap):put(m,RECORDS+28*i+4,bits(c.position+i));put(m,RECORDS+28*i+12,bits(c.velocity))
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-256<=a<STACK+512}
def reference(c):
 m=fixture(c);count=c.count;current=c.current;index=c.end
 if count<2 and c.flags&8:return public(m),0
 while index!=current:
  index-=1
  if index<0:index=c.cap-1
  p=RECORDS+index*28;old=real(read(m,p+4));vel=real(read(m,p+12));step=real(read(m,STEP));a=real(read(m,ACCEL));h=real(read(m,HALF));pos=f32(old+f32(f32(vel*step)+f32(h*f32(step*step))));vel=f32(vel+f32(a*step));put(m,p+4,bits(pos));put(m,p+12,bits(vel))
  threshold=real(read(m,LIMIT+0x44))
  if pos<threshold:
   while index!=current:
    current=s8(current+1)
    if current==c.cap:current=0
    count=s8(count-1);m[OWNER+0x2d]=current&255;m[OWNER+0x2c]=count&255
   put(m,RECORDS+current*28+4,bits(threshold))
 for i in range(12):m[OWNER+0x54+i]=m[OWNER+0x10+i]
 return public(m),1
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(OWNER,));self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):raise AssertionError(('unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('unexpected helper',hex(t)))
def main():
 data,fs,rs=parse_object(out/'independent-selected.o');a,n=fs['func_151CD674']['value'],fs['func_151CD674']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>82I',(root/'conker/conker.us.bin').read_bytes(),0x1FAB24);seen=set();count=0
 for c in cases():
  expected,answer=reference(c);models=[Oracle(ws,c)for ws in(retail,candidate)]
  for label,m in zip(('retail','candidate'),models):
   m.run();actual=public(m.memory);assert actual==expected,(c,label,'memory',[(hex(k),expected.get(k),actual.get(k))for k in expected if expected.get(k)!=actual.get(k)][:12]);assert m.r[2]==answer,(c,label,'return');assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
  seen.update(models[0].visits);count+=1
 report=dict(cases=count,retail_words_visited=sum(ENTRY+4*i in seen for i in range(82)),valid_finite_disjoint_ring_storage=True,source_installed=False);(out/'guest_151CD674_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
