"""Bounded instruction/model comparison for a private effect-timing callback."""
import itertools,json,math,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_timed_effect_callback_150e4cbc_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x150E4CBC;RECORD=0x30000;TICK=0x800BE9E4
signed=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
signed16=lambda n:((n&0xffff)^0x8000)-0x8000
def divzero(a,b):return (abs(a)//b)*(-1 if a<0 else 1)
@dataclass(frozen=True)
class Case:
 age:int;strength:int;base:int;tick:int;intensity:int;seed:int=0;phase:int=0
def cases():
 ages=(-0x80000000,-1,0,8,9,10,608,609,610,0x7fffffff)
 strengths=(-32768,-1,0,32767)
 ticks=(-0x80000000,-1,0,1,0x7fffffff)
 for i,(age,strength,tick,intensity) in enumerate(itertools.product(ages,strengths,ticks,(0,128,255))):
  yield Case(age,strength,(-32768,-1,0,32767)[i%4],tick,intensity,i%3,(i%2)*8)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-256,512)}
 m.update({RECORD+i:(i*19+c.seed*11+37)&255 for i in range(0xc0)})
 put(m,TICK,c.tick)
 for off,value,size in ((0x90,c.age,4),(0x94,c.base,2),(0x96,c.strength,2),(0x98,12345,2),(0xa2,-123,2),(0xa4,456,2),(0xb4,c.intensity,1)):
  put(m,RECORD+off,value,size)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-256<=a<STACK+512}
def reference(c,initial):
 m=dict(initial);age=c.age
 if age<9:scale=divzero(signed(age*90),9)
 else:scale=90-divzero(signed(age*90-810),600)
 product=signed(scale*c.strength)
 amount=math.trunc(floating(bits(float(product)))*0.00390625)
 put(m,RECORD+0xa4,amount,2)
 if age>=9:
  step=signed(c.tick*17)
  if step<c.intensity:put(m,RECORD+0xb4,c.intensity-step,1)
  else:put(m,RECORD+0x98,-1,2)
 put(m,RECORD+0xa2,(c.base*14)>>8,2)
 if age>=609:put(m,RECORD+0x98,-1,2)
 put(m,RECORD+0x90,age+c.tick,4)
 return m
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(RECORD,))
  self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):raise AssertionError(('unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('unexpected helper',hex(t)))
def words(tag):
 data,fs,rs=parse_object(out/(tag+'.o'));a,n=fs['func_150E4CBC']['value'],fs['func_150E4CBC']['size']
 refs={i-a:v for i,v in rs.items()if a<=i<a+n}
 look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
 return bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es})
def main():
 candidate=words('independent-selected');retail=struct.unpack_from('>82I',(root/'conker/conker.us.bin').read_bytes(),0x11216c);seen=set();count=0
 for c in cases():
  for ws in (retail,candidate):
   m=Oracle(ws,c);m.run();expected=public(reference(c,m.initial))
   assert public(m.memory)==expected,(c,[(hex(k),v,public(m.memory).get(k))for k,v in expected.items()if public(m.memory).get(k)!=v][:10])
   assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
   if ws is retail:seen.update(m.visits)
  count+=1
 report=dict(cases=count,retail_words_visited=sum(ENTRY+4*i in seen for i in range(82)),memory_and_saved_abi_match=True,valid_disjoint_record_only=True,source_installed=False)
 (out/'guest_150E4CBC_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
