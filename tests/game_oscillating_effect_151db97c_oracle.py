"""Modeled helper and mutation checks for the private oscillating-effect update."""
import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_oscillating_effect_151db97c_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x151DB97C;DAMP=0x15131918;SINE=0x151423D8;RECORD=0x30000;TICK=0x800BE9E4
@dataclass(frozen=True)
class Case:
 flags:int;mutation:int;tick:int;seed:int;phase:int=0
def cases():
 for i,(flags,mutation,tick,phase) in enumerate(itertools.product((0,1,2,3,0x80,0xff),range(8),(0,1,0xffffffff,0x7fffffff),(0,8))):
  yield Case(flags,mutation,tick,i%3,phase)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-512,512)}
 m.update({RECORD+i:(i*19+c.seed*11+37)&255 for i in range(0xc8)})
 put(m,TICK,c.tick);m[RECORD+0xa8]=c.flags;put(m,RECORD+0xac,bits(.75))
 for off,v in ((0xb0,0),(0xb1,127),(0xb2,255),(0xb3,1),(0xb4,2),(0xb5,255)):m[RECORD+off]=(v+c.seed)&255
 for off,v in ((0x4c,7.),(0x50,-9.),(0x54,12.),(0xb8,1.5),(0xbc,-2.25),(0xc0,.25)):
  put(m,RECORD+off,bits(v))
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def mutate_damp(m,c):
 if c.mutation&1:m[RECORD+0xa8]^=1
 if c.mutation&2:
  put(m,TICK,read(m,TICK)^0x80000001);m[RECORD+0xb1]^=0x80;put(m,RECORD+0xb8,bits(-2.5))
def mutate_sine(m,c,index):
 if c.mutation&4:
  m[RECORD+0xb1+(index%2)]^=0x40
  if index==2:put(m,RECORD+0xbc,bits(3.5))
def sine(arg):return bits(((arg&3)-2)*.25)
def reference(c,initial):
 m=dict(initial);calls=[]
 if m[RECORD+0xa8]&2:
  calls.append((DAMP,(RECORD+0x58,read(m,RECORD+0xac))));mutate_damp(m,c)
 if m[RECORD+0xa8]&1:
  for i in range(3):m[RECORD+0xb0+i]=(m[RECORD+0xb0+i]+m[RECORD+0xb3+i]*read(m,TICK))&255
  values=[]
  for i in range(3):
   arg=(m[RECORD+0xb0+i]-64)&255;calls.append((SINE,(arg,)));values.append(sine(arg));mutate_sine(m,c,i)
  for i in range(3):put(m,RECORD+0x4c+4*i,fp(read(m,RECORD+0xb8+4*i),values[i],'mul'))
 return m,calls,1
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(RECORD,0x89abcdef))
  self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  assert t in (DAMP,SINE),hex(t)
  a=tuple(self.arguments(2 if t==DAMP else 1));self.calls.append((t,a))
 def hook(self,t):
  if t==DAMP:mutate_damp(self.memory,self.case)
  else:
   arg=self.calls[-1][1][0]&255;index=sum(v[0]==SINE for v in self.calls)-1;mutate_sine(self.memory,self.case,index)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
  if t==SINE:self.f[0]=sine(arg)
def words(tag):
 data,fs,rs=parse_object(out/(tag+'.o'));a,n=fs['func_151DB97C']['value'],fs['func_151DB97C']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n}
 look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
 return bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es})
def main():
 candidate=words('independent-selected');retail=struct.unpack_from('>75I',(root/'conker/conker.us.bin').read_bytes(),0x208e2c);seen=set();count=0
 for c in cases():
  for ws in (retail,candidate):
   m=Oracle(ws,c);m.run();expected,calls,result=reference(c,m.initial)
   assert (public(m.memory),m.calls,m.r[2])==(public(expected),calls,result),(c,m.calls,calls,[(hex(k),v,public(m.memory).get(k))for k,v in public(expected).items()if public(m.memory).get(k)!=v][:8])
   assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
   if ws is retail:seen.update(m.visits)
  count+=1
 report=dict(cases=count,retail_words_visited=sum(ENTRY+4*i in seen for i in range(75)),helpers='modeled with mutations',valid_disjoint_record_only=True,source_installed=False)
 (out/'guest_151DB97C_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
