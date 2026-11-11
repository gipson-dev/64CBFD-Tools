import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_effect_curve_callback_151a175c_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
norm=p
from tools.experiments import game_effect_curve_callback_151a175c_match as p
ENTRY=0x151A175C;RECORD=0x30000;TICK=0x800BE9E4
signed=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
signed16=lambda n:((n&0xffff)^0x8000)-0x8000
@dataclass(frozen=True)
class Case:
 age:int;t0:int;t1:int;t2:int;t3:int;t4:int;tick:int;seed:int=0;phase:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-256,512)};m.update({RECORD+i:(i*19+c.seed*11+37)&255 for i in range(128)});put(m,TICK,c.tick)
 for off,v in ((0x20,-1234),(0x22,2345),(0x24,-32768),(0x34,23),(0x36,42),(0x38,c.age)):put(m,RECORD+off,v,2)
 for off,v in ((0x2c,0x21),(0x2d,0x80),(0x2e,0xfe),(0x3f,55)):m[RECORD+off]=v
 curve=[-3,7,c.t0,4,-6,c.t1,c.t2,-2,3,-4,127,-1,128,c.t3,-6,c.t4,7]
 for i,v in enumerate(curve):put(m,RECORD+0x50+2*i,v,2)
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-256<=a<STACK+512}
def reference(c,initial):
 m=dict(initial);curve=[signed16(read(m,RECORD+0x50+2*i,2)) for i in range(17)];age=c.age
 if curve[2]<age:m[RECORD+0x3f]=((curve[1]-age)*curve[0])&255
 if curve[5]<age:
  v=(curve[4]-age)*curve[3];put(m,RECORD+0x36,v,2);put(m,RECORD+0x34,v,2)
 if curve[6]<age:
  initial_values=[(signed16(read(m,RECORD+off,2)),m[RECORD+frac])for off,frac in ((0x20,0x2c),(0x22,0x2e),(0x24,0x2d))]
  for i,(off,frac) in enumerate(((0x20,0x2c),(0x22,0x2e),(0x24,0x2d))):
   velocity=signed(((curve[7+i]&0xffffffff)<<8)|(curve[10+i]&0xffffffff));high,low=initial_values[i];value=signed(((high&0xffffffff)<<8)|low);value=signed(value+velocity*c.tick);put(m,RECORD+off,value>>8,2);m[RECORD+frac]=value&255
 if age<curve[13]:m[RECORD+0x3f]=(age*curve[14])&255
 if age<curve[15]:
  v=age*curve[16];put(m,RECORD+0x36,v,2);put(m,RECORD+0x34,v,2)
 return m
class Oracle(FactoryOracle):
 def __init__(self,ws,c):
  super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(RECORD,));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):raise AssertionError(('unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('unexpected helper',hex(t)))
def words(tag):
 text,fs,rs=parse_object(out/(tag+'.o'));a,n=fs['func_151A175C']['value'],fs['func_151A175C']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};return bound_blob(text[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es})
def cases():
 cs=[Case(age,*thresholds,tick,i%3)for i,(age,thresholds,tick)in enumerate(itertools.product((-1,0,1),itertools.product((-1,1),repeat=5),(-1,0,1,2147483647)))]
 for i,(age,tick)in enumerate(itertools.product((-32768,32767),(-2147483648,-1,1,2147483647))):cs.append(Case(age,-32768,32767,-32768,32767,-32768,tick,i%3))
 return cs
def main():
 candidate=words('independent-selected');retail=struct.unpack_from('>96I',(root/'conker/conker.us.bin').read_bytes(),0x1CEC0C);raw,refs=p.payload(out/'independent-selected.o');fixed,fre=norm.normalize(raw,refs);lookup={v[1]:v[2][1]for v in symbol_rows((out/'frozen/conker/build/conker.us.elf').read_bytes())};fixed=bound_blob(fixed,fre,{nm:lookup[nm]for es in fre.values()for _,nm in es});assert tuple(fixed)==retail;seen=set();cs=cases()
 for c in cs:
  machines=[]
  for ws in(retail,candidate,fixed):
   m=Oracle(ws,c);m.run();assert public(m.memory)==public(reference(c,m.initial)),(c,'memory');assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];machines.append(m)
  assert public(machines[0].memory)==public(machines[1].memory);assert (machines[0].memory,machines[0].r,machines[0].f,machines[0].trace)==(machines[2].memory,machines[2].r,machines[2].f,machines[2].trace);seen.update(machines[0].visits)
 report=dict(cases=len(cs),retail_words_visited=sum(ENTRY+4*i in seen for i in range(96)),memory_and_saved_abi_match=True,normalized_complete_state=True,valid_disjoint_record_only=True,source_installed=False)
 (out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
