import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_sorted_record_insert_150241b4_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x150241B4;HELPER=0x15024130;TABLE=0x30000;COUNT=0x50000;MARK=0x70000;CAP=0x800C3C9A
@dataclass(frozen=True)
class Case:
 size:int;capacity:int;priority:int;tag:int=0x123456e1;parameter:int=0xabcd8001;context:int=0x13572468;pattern:int=0;mutate:int=0;phase:int=0;seed:int=0
def keys(c):return tuple(i*3-9 for i in range(10))if c.pattern==0 else ((0,)*10 if c.pattern==1 else (-4,-4,-1,-1,0,0,7,7,10,10))
def cases():
 return [Case(size,capacity,priority,pattern=pattern)for size,capacity,priority,pattern in itertools.product(range(9),(0,4,8,10),(-2147483648,-9,-6,-4,-1,0,7,20,2147483647),range(3))]+[Case(4,10,0,tag=tag,parameter=parameter,pattern=2)for tag,parameter in itertools.product((0,255,0x123456e1),(0,65535,0xabcd8001))]+[Case(size,size,priority,pattern=2,mutate=1)for size,priority in itertools.product((0,1,4,8),(-1,0))]
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-256,512)};m.update({TABLE+i:(i*19+37)&255 for i in range(120)});put(m,COUNT,c.size);put(m,CAP,c.capacity,2);put(m,MARK,0)
 for i in range(10):put(m,TABLE+12*i,0x12000000+i);put(m,TABLE+12*i+4,keys(c)[i]);m[TABLE+12*i+8]=(i*17+3)&255;m[TABLE+12*i+9]=0xA5;put(m,TABLE+12*i+10,0x8000+i,2)
 for i,v in enumerate((c.parameter,c.priority,c.context)):put(m,STACK+16+4*i,v)
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-256<=a<STACK+512}
def reference(c):
 m=fixture(c);calls=[]
 if c.size>=c.capacity:
  calls=[(HELPER,(c.size,c.context))];put(m,MARK,0x12345678)
  if c.mutate:put(m,TABLE+4,0x12345678);put(m,COUNT,99)
  put(m,COUNT,0)
 else:
  index=next((i for i in range(c.size)if keys(c)[i]>=c.priority),c.size)
  for i in range(c.size-1,index-1,-1):
   for j in range(12):m[TABLE+12*(i+1)+j]=m[TABLE+12*i+j]
  put(m,TABLE+12*index,0x89abcdef);put(m,TABLE+12*index+4,c.priority);m[TABLE+12*index+8]=c.tag&255;put(m,TABLE+12*index+10,c.parameter,2);put(m,COUNT,c.size+1)
 return public(m),calls
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(TABLE,COUNT,0x89abcdef,c.tag));self.before=self.r[:];self.before_f=self.f[:];self.count_address=COUNT
 def record_call(self,t):assert t==HELPER;self.calls.append((t,tuple(self.arguments(2))))
 def hook(self,t):
  assert t==HELPER;put(self.memory,MARK,0x12345678)
  if self.case.mutate:put(self.memory,TABLE+4,0x12345678);put(self.memory,self.count_address,99)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xdeadbeef
def main():
 data,fs,rs=parse_object(out/'independent-nounroll.o');a,n=fs['func_150241B4']['value'],fs['func_150241B4']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:(look[nm]if nm in look else int(nm[2:],16))for es in refs.values()for _,nm in es});retail=struct.unpack_from('>81I',(root/'conker/conker.us.bin').read_bytes(),0x51664);seen=set();count=0
 for c in cases():
  expected,calls=reference(c);models=[Oracle(ws,c)for ws in (retail,candidate)]
  for label,m in zip(('retail','candidate'),models):
   m.run();actual=public(m.memory);assert actual==expected,(c,label,'memory',[(hex(k),expected.get(k),actual.get(k))for k in expected if expected.get(k)!=actual.get(k)][:12]);assert m.calls==calls,(c,label,'calls',m.calls,calls);assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
  seen.update(models[0].visits);count+=1
 report=dict(cases=count,retail_words_visited=sum(ENTRY+4*i in seen for i in range(81)),valid_disjoint_sorted_storage=True,helper='modeled',return_register_unqualified=True,source_installed=False);(out/'guest_150241B4_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
