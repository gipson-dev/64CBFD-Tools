import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_segment_binding_150c8600_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x150C8600;HELPER=0x1510D0EC;CURSOR=0x30000;A=0x50000;B=0x60000;TABLE=0x80088810;GROUP0=0x80090230;GROUP1=0x80090244;RECORDS=0x800BE4E0
regions=((STACK-1024,STACK+512),(CURSOR,CURSOR+0x100),(A,A+0x80),(B,B+0x80),(TABLE,TABLE+8),(GROUP0,GROUP0+20),(GROUP1,GROUP1+20),(RECORDS,RECORDS+4))
assert all(b<=c or d<=a for i,(a,b) in enumerate(regions) for c,d in regions[i+1:])
@dataclass(frozen=True)
class Case:
 choice:int;pattern:int;switch:int;swap_tables:int;phase:int=0;seed:int=0
def cases():return [Case(*v) for v in itertools.product((-32768,-257,-256,-1,0,255,256,1024,1279,1280,32767),range(4),(-1,0,5),(0,1))]
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,512)}
 for base,n in ((CURSOR,0x100),(A,0x80),(B,0x80),(TABLE,8),(GROUP0,20),(GROUP1,20),(RECORDS,4)):m.update({base+i:(i*13+11)&255 for i in range(n)})
 put(m,TABLE,GROUP0);put(m,TABLE+4,GROUP1);put(m,RECORDS,A)
 for i in range(5):put(m,GROUP0+4*i,0x100+i);put(m,GROUP1+4*i,0x200+i)
 for base,shift in ((A,0),(B,1)):
  for i in range(10):
   m[base+10*i]=(0,1,2,255)[(i+c.pattern+shift)%4];put(m,base+10*i+4,c.choice,2)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+512}
def value(resource,i):return 0xa0000000|((resource&0xffff)<<4)|(i&15)
def mutate(m,c,i):
 if i==c.switch:put(m,RECORDS,B)
 if i==0 and c.swap_tables:put(m,TABLE,GROUP1);put(m,TABLE+4,GROUP0)
def reference(c):
 m=fixture(c);calls=[];groups=(read(m,TABLE),read(m,TABLE+4))
 for i in range(10):
  entry=read(m,RECORDS)+10*i;v=read(m,entry+4,2);v=(v^0x8000)-0x8000;choice=max(0,min(v>>8,4));group=m[entry]
  if group>=2:m[entry]=0;entry=read(m,RECORDS)+10*i;group=m[entry]
  resource=read(m,groups[group]+4*choice);calls.append((resource,3,0));mutate(m,c,i);put(m,CURSOR+8*i,0xdb060000+4*(i+1));put(m,CURSOR+8*i+4,value(resource,i))
 return public(m),calls,CURSOR+80
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(CURSOR,));self.before=self.r[:];self.before_f=self.f[:];self.normalized=[]
 def record_call(self,t):
  assert t==HELPER,hex(t);a=tuple(self.arguments(4));self.calls.append((t,a));self.normalized.append((a[0],a[2],a[3]));assert STACK-1024<=a[1]<STACK+512
 def hook(self,t):
  a=self.calls[-1][1];i=len(self.calls)-1;self.put(a[1],0x12340000+i,4);mutate(self.memory,self.case,i)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value(a[0],i)
def main():
 data,fs,rs=parse_object(out/'independent-selected.o');a,n=fs['func_150C8600']['value'],fs['func_150C8600']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>76I',(root/'conker/conker.us.bin').read_bytes(),0xF5AB0);seen=set()
 for c in cases():
  expected,calls,answer=reference(c)
  for ws in (retail,candidate):
   m=Oracle(ws,c);m.run();actual=public(m.memory);assert actual==expected,(c,[(hex(k),expected.get(k),actual.get(k)) for k in expected if expected.get(k)!=actual.get(k)][:10]);assert m.normalized==calls and m.r[2]==answer,(c,m.normalized,calls,m.r[2]);assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];seen.update(m.visits)
 report=dict(cases=len(cases()),retail_words_visited=sum(ENTRY+4*i in seen for i in range(76)),helper='modeled with record and table-pointer mutations',valid_disjoint_records_and_output=True,source_installed=False);(out/'guest_150C8600_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
