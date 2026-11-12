import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_record_tail_release_15114b94_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x15114B94;RELEASE=0x1516972C;COUNT=0x800DBEF0;BASE=0x800DBEF4;RESERVED=0x800DBF98;A=0x50000;B=0x60000;CHILD=0x70000;MARK=0x80000
regions=((STACK-1024,STACK+512),(A,A+0x700),(B,B+0x700),(CHILD,CHILD+0x100),(MARK,MARK+4),(COUNT,COUNT+8),(RESERVED,RESERVED+4))
assert all(b<=c or d<=a for i,(a,b) in enumerate(regions) for c,d in regions[i+1:])
@dataclass(frozen=True)
class Case:
 count:int;index:int;mask:int;reserved:int;child:int;mutate:int;phase:int=0;seed:int=0
def cases():return [Case(*v) for v in itertools.product((0,1,4,8),(0,2,7,8,0xffffffff),(0,0xff,0xaa),(0,1,9),(0,1),(0,1,2))]
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,512)}
 for base,n in ((A,0x700),(B,0x700),(CHILD,0x100),(MARK,4),(COUNT,8),(RESERVED,4)):m.update({base+i:(i*13+11)&255 for i in range(n)})
 put(m,COUNT,c.count);put(m,BASE,A);put(m,RESERVED,c.reserved);put(m,MARK,0)
 for base,shift in ((A,0),(B,1)):
  for i in range(10):
   p=base+i*0xa0;m[p+0x70]=(0x40 if (i+shift)%2 else 0x20)|(8 if c.mask&(1<<i) else 0);put(m,p+0x94,CHILD+4*i if c.child else 0)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+512}
def mutate(m,c):
 put(m,MARK,0x13579bdf)
 if c.mutate:
  put(m,BASE,B);m[B+c.index*0xa0+0x70]^=0x40
  if c.mutate==2:put(m,COUNT,max(0,c.count-1));put(m,RESERVED,2)
def reference(c):
 m=fixture(c);calls=[];count=read(m,COUNT)
 if c.index<count:
  offset=c.index*0xa0;record=read(m,BASE)+offset;child=read(m,record+0x94)
  if child:calls.append((RELEASE,(child,)));mutate(m,c);put(m,read(m,BASE)+offset+0x94,0)
  record=read(m,BASE)+offset;m[record+0x70]|=8;m[read(m,BASE)+offset+0x6e]=1;count=read(m,COUNT)
 boundary=(count-read(m,RESERVED))&0xffffffff
 while count and m[read(m,BASE)+(count-1)*0xa0+0x70]&8:
  if count-1>=boundary and read(m,RESERVED):put(m,RESERVED,read(m,RESERVED)-1)
  else:boundary=(boundary-1)&0xffffffff
  count-=1;put(m,COUNT,count)
 return public(m),calls
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(c.index,));self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):assert t==RELEASE;self.calls.append((t,tuple(self.arguments(1))))
 def hook(self,t):
  mutate(self.memory,self.case)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def main():
 data,fs,rs=parse_object(out/'independent-selected.o');a,n=fs['func_15114B94']['value'],fs['func_15114B94']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>76I',(root/'conker/conker.us.bin').read_bytes(),0x142044);seen=set()
 for c in cases():
  expected,calls=reference(c)
  for ws in (retail,candidate):
   m=Oracle(ws,c);m.run();actual=public(m.memory);assert actual==expected,(c,[(hex(k),expected.get(k),actual.get(k)) for k in expected if expected.get(k)!=actual.get(k)][:10]);assert m.calls==calls,(c,m.calls,calls);assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];seen.update(m.visits)
 report=dict(cases=len(cases()),retail_words_visited=sum(ENTRY+4*i in seen for i in range(76)),helper='modeled with table and count mutations',valid_disjoint_records=True,return_register_unqualified=True,source_installed=False);(out/'guest_15114B94_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
