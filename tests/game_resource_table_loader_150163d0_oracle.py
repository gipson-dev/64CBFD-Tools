import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_resource_table_loader_150163d0_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x150163D0;BASE=0x30000;GLOBAL=0x800D18B0;HELPER=0x1502B7F0
@dataclass(frozen=True)
class Case:
 count:int;outcome:int;resource:int;phase:int=0;seed:int=0
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-512,512)};m.update({BASE+i:(i*19+37)&255 for i in range(256)});put(m,GLOBAL,0x12345678)
 for i in range(c.count):put(m,BASE+8*i,0x80+7*i);put(m,BASE+8*i+4,0xDEADBEEF-i)
 put(m,BASE+8*c.count,0);return m
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def reference(c):
 m=fixture(c);put(m,GLOBAL,BASE)
 if 0<c.outcome<0x80000000:
  for i in range(c.count):put(m,BASE+8*i,BASE+0x80+7*i)
 else:put(m,GLOBAL,0)
 return public(m)
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(c.resource,));self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  assert t==HELPER;args=tuple(self.arguments(5));assert args==(GLOBAL,3,12,self.case.resource,9),(self.case,args);self.calls.append((t,args))
 def hook(self,t):
  assert t==HELPER;self.put(GLOBAL,BASE,4)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=self.case.outcome
def main():
 tag='independent-selected'
 text,fs,rs=parse_object(out/(tag+'.o'));a,n=fs['func_150163D0']['value'],fs['func_150163D0']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};ws=bound_blob(text[a:a+n],refs,{nm:look.get(nm,int(nm[2:],16)if nm.startswith('D_')else 0)for es in refs.values()for _,nm in es});retail=struct.unpack_from('>76I',(root/'conker/conker.us.bin').read_bytes(),0x43880)
 count=0;seen=set()
 for n,outcome,resource in itertools.product(range(13),(0,1,0x7fffffff,0x80000000,0xffffffff),(0,1,0x12345678)):
  c=Case(n,outcome,resource);machines=[Oracle(code,c)for code in (retail,ws)]
  for m in machines:m.run();assert public(m.memory)==reference(c),(c,'memory');assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
  seen.update(machines[0].visits);count+=1
 report=dict(variant=tag,cases=count,retail_words_visited=sum(ENTRY+4*i in seen for i in range(76)),loader='controlled modeled outcomes',return_register_unqualified=True,source_installed=False)
 (out/('guest_'+tag+'_screen.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
