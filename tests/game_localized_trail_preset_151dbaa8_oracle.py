import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_localized_trail_preset_151dbaa8_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x151DBAA8;HELPER=0x15153F18;POINT=0x30000;MARK=0x50000;CONST=0x800AB4C0
regions=((STACK-1024,STACK+512),(POINT,POINT+16),(MARK,MARK+4),(CONST,CONST+16))
assert all(b<=c or d<=a for i,(a,b) in enumerate(regions) for c,d in regions[i+1:])
@dataclass(frozen=True)
class Case:
 point:tuple;count:int;selector:int;mode:int;request:int;mutate:int;phase:int=0;seed:int=0
def cases():return [Case(*v) for v in itertools.product(((0,0,0),(0x3f800000,0xc0200000,0x40400000),(0x7fc01234,0x80000000,0x7f800000)),(-65537,-32768,-1,0,1,32767,65535),(0,0x80,0x1ff),(0,255,0x12345678),(0,0xffffffff,0x12345678),(0,1))]
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,512)}
 for base,n in ((POINT,16),(MARK,4),(CONST,16)):m.update({base+i:(i*13+11)&255 for i in range(n)})
 for i,v in enumerate(c.point):put(m,POINT+4*i,v)
 for i,v in enumerate((0x403c28f5,0x3f1ced92,0x3f1a5e36,0x41233333)):put(m,CONST+4*i,v)
 put(m,MARK,0);return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+512}
def mutate(m,c):
 put(m,MARK,0x13579bdf)
 if c.mutate:put(m,POINT,0xdeadbeef);put(m,CONST,0x12345678)
def reference(c):
 m=fixture(c);values={0:(2,0),2:(2,255),4:(2,0xffc0),6:(2,46),8:(4,c.point[0]),12:(4,c.point[1]),16:(4,c.point[2]),20:(4,0x40b00000),24:(4,read(m,CONST)),28:(4,read(m,CONST+4)),32:(4,read(m,CONST+8)),36:(4,0x41200000),40:(4,read(m,CONST+12)),44:(2,c.count&0xffff),46:(2,0),48:(2,3),50:(2,2),52:(2,30),54:(2,30),56:(2,155),58:(2,100),60:(1,c.selector&255),64:(4,0x3f000000),68:(2,16),70:(2,15),72:(4,0)}
 mutate(m,c);return public(m),values,(0,c.mode&255,c.request&0xffffffff)
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(POINT,c.count,c.selector,c.mode,c.request));self.before=self.r[:];self.before_f=self.f[:];self.packet=None;self.call_args=None
 def record_call(self,t):
  assert t==HELPER,hex(t);a=tuple(self.arguments(5));assert a[1]==a[0]+8 and STACK-1024<=a[0]<STACK+512;self.call_args=(a[2],a[3],a[4]);self.packet={off:read(self.memory,a[0]+off,n) for off,(n,_) in reference(self.case)[1].items()};self.calls.append((t,a))
 def hook(self,t):
  mutate(self.memory,self.case)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def main():
 data,fs,rs=parse_object(out/'independent-selected.o');a,n=fs['func_151DBAA8']['value'],fs['func_151DBAA8']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>75I',(root/'conker/conker.us.bin').read_bytes(),0x208F58);seen=set()
 for c in cases():
  expected,values,args=reference(c)
  for ws in (retail,candidate):
   m=Oracle(ws,c);m.run();assert public(m.memory)==expected,(c,'memory');assert m.packet=={k:v for k,(_,v) in values.items()} and m.call_args==args and len(m.calls)==1,(c,m.packet,m.call_args,args);assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];seen.update(m.visits)
 report=dict(cases=len(cases()),retail_words_visited=sum(ENTRY+4*i in seen for i in range(75)),helper='modeled',initialized_packet_fields_only=True,return_register_unqualified=True,source_installed=False);(out/'guest_151DBAA8_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
