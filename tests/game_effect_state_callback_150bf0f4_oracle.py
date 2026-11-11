import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_effect_state_callback_150bf0f4_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
norm=p
from tools.experiments import game_effect_state_callback_150bf0f4_match as p
ENTRY=0x150BF0F4;RECORD=0x30000;TICK=0x800BE9E4
signed=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
signed16=lambda n:((n&0xffff)^0x8000)-0x8000
signed8=lambda n:((n&0xff)^0x80)-0x80
@dataclass(frozen=True)
class Case:
 active:int;value:int;target:int;tick:int;x:int;y:int;dx:int;dy:int;fadein:int;fadeout:int;phase_byte:int;seed:int=0;phase:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-256,512)}
 m.update({RECORD+i:(i*19+c.seed*11+37)&255 for i in range(80)});put(m,TICK,c.tick)
 for off,v in ((0x24,c.active),(0x1f,c.value),(0x26,c.target),(0x27,c.fadein),(0x2f,c.fadeout),(0x2d,c.dx),(0x2e,c.dy),(0x2c,c.phase_byte)):m[RECORD+off]=v&255
 put(m,RECORD+0x14,c.x,2);put(m,RECORD+0x16,c.y,2);return m
def public(m):return {a:v for a,v in m.items()if not STACK-256<=a<STACK+512}
def reference(c,initial):
 m=dict(initial);value=c.value
 if c.active:
  if value!=c.target:
   value=signed(value+c.tick*c.fadein)
   if value>c.target:value=c.target
   m[RECORD+0x1f]=value&255
 elif value:
  value=signed(value-c.tick*c.fadeout)
  if value<0:value=0
  m[RECORD+0x1f]=value&255
 if not c.active and not value:return m,1
 x=signed16(c.x+c.dx*c.tick);y=signed16(c.y+c.dy*c.tick);put(m,RECORD+0x14,x,2);put(m,RECORD+0x16,y,2)
 if x<=0:put(m,RECORD+0x16,0,2);put(m,RECORD+0x14,0,2);return m,1
 phase=signed(c.phase_byte+c.tick)
 if phase>=128:phase=127
 m[RECORD+0x2c]=phase&255;return m,0
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(RECORD,));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):raise AssertionError(('unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('unexpected helper',hex(t)))
def words(tag):
 text,fs,rs=parse_object(out/(tag+'.o'));a,n=fs['func_150BF0F4']['value'],fs['func_150BF0F4']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};return bound_blob(text[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es})
def cases():
 params=itertools.product((0,1),(0,1,7),(0,4,7),(0,1,4),(0,1,12),(-2,0,3))
 cs=[Case(active,val,target,tick,x,3,dx,-1,2,3,phase,i%3) for i,(active,val,target,tick,x,dx) in enumerate(params) for phase in (0,126)]
 for i,(tick,active,value,x,dx) in enumerate(itertools.product((-2147483648,-1,2147483647),(0,1),(0,255),(-32768,32767),(-128,127))):cs.append(Case(active,value,127,tick,x,-32768,dx,127,255,255,255,i%3))
 return cs
def main():
 candidate=words('independent-selected');retail=struct.unpack_from('>74I',(root/'conker/conker.us.bin').read_bytes(),0xEC5A4);raw,refs=p.payload(out/'independent-selected.o');fixed,fre=norm.normalize(raw,refs);lookup={v[1]:v[2][1]for v in symbol_rows((out/'frozen/conker/build/conker.us.elf').read_bytes())};fixed=bound_blob(fixed,fre,{nm:lookup[nm]for es in fre.values()for _,nm in es});assert tuple(fixed)==retail;seen=set();cs=cases()
 for c in cs:
  machines=[]
  for ws in(retail,candidate,fixed):
   m=Oracle(ws,c);m.run();expected,result=reference(c,m.initial);assert public(m.memory)==public(expected),(c,'memory');assert m.r[2]==result,(c,m.r[2],result);assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];machines.append(m)
  assert public(machines[0].memory)==public(machines[1].memory) and machines[0].r[2]==machines[1].r[2];assert (machines[0].memory,machines[0].r,machines[0].f,machines[0].trace)==(machines[2].memory,machines[2].r,machines[2].f,machines[2].trace);seen.update(machines[0].visits)
 report=dict(cases=len(cs),retail_words_visited=sum(ENTRY+4*i in seen for i in range(74)),memory_return_and_saved_abi_match=True,normalized_complete_state=True,valid_disjoint_record_only=True,source_installed=False)
 (out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
