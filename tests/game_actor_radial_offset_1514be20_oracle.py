import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_actor_radial_offset_1514be20_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x1514BE20;ACTOR=0x30000;HELPER=0x15145128
@dataclass(frozen=True)
class Case:
 x:float;y:float;z:float;f:float;outcome:int;phase:int=0;seed:int=0
def bits(v):return struct.unpack('>I',struct.pack('>f',v))[0]
def real(v):return struct.unpack('>f',struct.pack('>I',v))[0]
def f32(v):return real(bits(v))
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-512,512)};m.update({ACTOR+i:(i*19+37)&255 for i in range(0x180)})
 for off,val in ((0x34,c.x),(0x38,c.y),(0x3c,c.z),(0x40,c.x+20),(0x44,c.y-30),(0x48,c.z+40),(0x15c,c.f)):put(m,ACTOR+off,bits(val))
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def reference(c):
 m=fixture(c)
 origin=[real(read(m,ACTOR+0x34+4*i)) for i in range(3)]
 current=[real(read(m,ACTOR+0x40+4*i)) for i in range(3)]
 target=[origin[0],f32(origin[1]+100.),origin[2]]
 fraction=real(read(m,ACTOR+0x15c))
 interpolated=[f32(current[i]+f32(f32(target[i]-current[i])*fraction)) for i in range(3)]
 sample=tuple(bits(f32(interpolated[i]-origin[i])) for i in range(3))
 if c.outcome:
  for i,v in enumerate((.5,-.25,.75)):put(m,ACTOR+0x40+4*i,bits(f32(origin[i]+f32(v*100.))))
 else:
  for i in range(3):put(m,ACTOR+0x40+4*i,read(m,ACTOR+0x34+4*i))
 return sample,public(m)
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(ACTOR,));self.before=self.r[:];self.before_f=self.f[:];self.sample=None
 def record_call(self,t):
  assert t==HELPER; a=tuple(self.arguments(4));assert a[0]==a[1];self.sample=tuple(read(self.memory,a[0]+i*4)for i in range(3));self.calls.append((t,a))
 def hook(self,t):
  assert t==HELPER;a=self.calls[-1][1]
  if self.case.outcome:
   for i,v in enumerate((0.5,-0.25,0.75)):self.put(a[1]+i*4,bits(v),4)
   self.put(a[2],bits(100),4);self.put(a[3],bits(.01),4)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=self.case.outcome
def main():
 text,fs,rs=parse_object(out/'independent-selected.o');a,n=fs['func_1514BE20']['value'],fs['func_1514BE20']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n}
 look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es})
 retail=struct.unpack_from('>76I',(root/'conker/conker.us.bin').read_bytes(),0x1792D0);count=0;seen=set()
 for x,y,z,f,outcome in itertools.product((-100.,0.,200.),(-100.,0.,200.),(-100.,0.,200.),(0.,.5,1.,2.),(0,1)):
  c=Case(x,y,z,f,outcome);machines=[Oracle(ws,c) for ws in (retail,candidate)]
  for m in machines:m.run();assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
  sample,expected=reference(c);a,b=machines
  for m in machines:
   assert m.sample==sample,(c,'input',m.sample,sample)
   assert public(m.memory)==expected,(c,'memory')
   assert m.r[2]==c.outcome,(c,'return')
  seen.update(a.visits);count+=1
 report=dict(cases=count,retail_words_visited=sum(ENTRY+4*i in seen for i in range(76)),helper='controlled modeled outcomes; not original body',valid_actor_layout=True,source_installed=False)
 (out/'guest_1514BE20_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
