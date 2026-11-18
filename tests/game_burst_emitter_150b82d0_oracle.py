"""Independent complete burst model, retaining all four escaped vector buffers."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments import game_burst_emitter_150b82d0_match as source
p=source.OUT;f=source.FROZEN;ENTRY,POOL=0x150B82D0,0x80400000
RNG,REAL,DIRECTION,SUBMIT=0x150ADA20,0x150ADA68,0x15143794,0x1518A3C0
INPUT,OUTPUT,MARK=0x30000,0x50000,0x70000
VECTOR_BASES=(-16,-28,-40,-52)
LITERALS=(0xC4C44000,0x45444000,0x3C23D70A,0x4498A000,0x44E1C000,0x3A83126F,0x441E4000,0x3F7149E8)
data=lambda m,a,n:bytes(m[a+i]for i in range(n))
public=lambda m:{a:b for a,b in m.items()if not STACK-4096<=a<STACK+1024}
mul=lambda a,b:bits(floating(a)*floating(b))
add=lambda a,b:bits(floating(a)+floating(b))
@dataclass(frozen=True)
class Case:
 initial:int=0;alias:int=0;mutation:int=0;success:int=1;phase:int=0;seed:int=0
def cases():
 for initial,alias,mutation,success in itertools.product((0,25,0xffffffff,0x80000000),range(4),range(4),(0,1)):
  seed=(initial+alias*11+mutation*17+success*23)&255
  yield Case(initial,alias,mutation,success,8*(seed&1),seed)
def args(c):return(INPUT,0,INPUT+4 if c.alias==2 else INPUT+0x100,INPUT+8 if c.alias==3 else INPUT+0x100 if c.alias==1 else INPUT+0x104,0xABCD00FF,0x87654321)
def fixture(c,raw=False):
 h=STACK+c.phase;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-4096,1024)}
 for a,n in((INPUT,0x120),(OUTPUT,32),(MARK,4)):m.update({a+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for i,v in enumerate((1.25,-2.5,3.75)):put(m,INPUT+4*i,bits(v))
 put(m,INPUT+0x100,bits(2.5));put(m,INPUT+0x104,bits(.75))
 pool=sections(p/'owner.o')['.rodata'][1];m.update({POOL+i:b for i,b in enumerate(pool)})
 for i,v in enumerate(LITERALS):put(m,0x8009FD68+4*i,v)
 for i,v in enumerate(args(c)[4:]):put(m,h+16+4*i,v)
 if raw:
  before=dict(m)
  for off in range(-52,0):m[h+off]=before[h+(off-4 if off>=-48 else off+48)]
 return m
class Service:
 def __init__(self,m,c,home=None,raw=False,arguments=None):
  self.m,self.c=m,c;self.home=STACK+c.phase if home is None else home;self.raw=raw;self.argv=args(c)if arguments is None else arguments
  self.calls=[];self.integers=self.reals=self.submits=0;self.retained={};self.last_result=0
 def vector(self,index):return self.home+VECTOR_BASES[index]+(4 if self.raw else 0)
 def vector_index(self,address):
  found=[i for i in range(4)if self.vector(i)==address];assert len(found)==1,('vector address',hex(address),self.home,self.raw);return found[0]
 def invoke(self,t,a):
  m,c=self.m,self.c;ordinal=len(self.calls);a=tuple(a);observed=b'';normalized=a
  if t==DIRECTION:
   index=self.vector_index(a[3]);assert index in(0,2);self.retained[index]=a[3];normalized=(*a[:3],('vector',index))
  elif t==SUBMIT:
   values=list(a)
   for at,index in((0,0),(1,1),(3,2),(4,3)):
    assert self.vector_index(a[at])==index;self.retained[index]=a[at];values[at]=('vector',index)
   normalized=tuple(values);observed=b''.join(data(m,self.vector(i),12)for i in range(4))
  self.calls.append((t,normalized,observed));put(m,MARK,(0x13579bdf+ordinal*0x10203+t)&0xffffffff)
  if c.mutation&1:
   center,radius,ratio=self.argv[0],self.argv[2],self.argv[3]
   for i in range(3):put(m,center+4*i,bits((ordinal%17)*.125+i))
   put(m,radius,bits((ordinal%7)*.25+.5));put(m,ratio,bits((ordinal%5)*.125+.25))
  if c.mutation&2:
   for index,address in sorted(self.retained.items()):
    for i in range(3):put(m,address+4*i,bits((ordinal%19)*.125+index+i*.25))
  if t==RNG:
   answer=c.initial if self.integers==0 else(c.seed*0x9e3779b9+self.integers*0x13579bdf)&0xffffffff;self.integers+=1;return answer
  if t==REAL:
   answer=bits(((c.seed+self.reals*7)%17)/16.);self.reals+=1;return answer
  if t==DIRECTION:
   q=((a[0]&255)+(a[1]&255)+((a[2]>>16)&255))&511
   for i in range(3):put(m,a[3]+4*i,bits((q+i*17)/128.))
   return 0xDEADBEEF
  assert t==SUBMIT;self.submits+=1;put(m,OUTPUT,0x98760000+self.submits);self.last_result=OUTPUT if c.success else 0;return self.last_result
def reference(initial,c,home=None,arguments=None):
 m=dict(initial);s=Service(m,c,home,arguments=arguments);argv=s.argv
 def call(t,a=()):return s.invoke(t,a)
 def vector(i):return s.vector(i)
 remaining=call(RNG)%26+35
 for _ in range(remaining):
  heading=call(RNG)&255;pitch=(call(RNG)%61-63)&0xffffffff
  call(DIRECTION,(heading,pitch,read(m,argv[2]),vector(0)))
  at=vector(0);y=mul(read(m,at+4),read(m,argv[3]));put(m,at+4,y)
  put(m,at,add(read(m,at),read(m,argv[0])));put(m,at+4,add(y,read(m,argv[0]+4)));put(m,at+8,add(read(m,at+8),read(m,argv[0]+8)))
  for i in range(3):put(m,vector(1)+4*i,mul(call(REAL),bits(360.)))
  magnitude=mul(add(mul(call(REAL),LITERALS[3]),LITERALS[4]),LITERALS[2]);call(DIRECTION,(heading,pitch,magnitude,vector(2)))
  value=mul(add(mul(call(REAL),LITERALS[1]),LITERALS[0]),LITERALS[2]);put(m,vector(3),value);put(m,vector(3)+4,0)
  value=mul(add(mul(call(REAL),LITERALS[1]),LITERALS[0]),LITERALS[2]);put(m,vector(3)+8,value)
  first=call(REAL);second=call(REAL);duration=call(RNG)%51+75
  size=mul(add(mul(first,bits(104.)),bits(78.)),LITERALS[5]);rate=mul(add(mul(second,LITERALS[6]),bits(-1064.)),LITERALS[5])
  call(SUBMIT,(vector(0),vector(1),size,vector(2),vector(3),rate,LITERALS[7],1,duration,0,0,255,1))
 return m,s,remaining
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,raw=False,entry=ENTRY,connected=None,arguments=None):
  super().__init__(words,initial,c,entry=entry,s={},arguments=args(c)if arguments is None else arguments,connected=connected)
  self.service=Service(self.memory,c,raw=raw);self.saved=tuple(self.r[16:24])+tuple(self.r[28:]);self.saved_fp=tuple(self.f[20:])
 def record_call(self,t):self.pending=t,tuple(self.arguments({RNG:0,REAL:0,DIRECTION:4,SUBMIT:13}[t]))
 def hook(self,t):
  answer=self.service.invoke(*self.pending)
  for i in range(13 if t==SUBMIT else 4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=answer&0xffffffff
  if t==REAL:self.f[0]=answer
def streams():
 from tools.tests.game_burst_emitter_150b82d0_proof import derive
 lookup={v[1]:v[2][1]for v in symbol_rows((f/'conker/build/conker.us.elf').read_bytes())};lookup['.rodata']=POOL
 raw=bound_blob(*payload(p/'owner.o','func_150B82D0'),lookup)
 return[('original',list(struct.unpack('>188I',(p/'retail.bin').read_bytes())),False),('raw',raw,True),('normalized',derive(raw),False)]
def main(programs=None):
 programs=streams()if programs is None else programs;reports=[]
 for label,words,raw in programs:
  count=0;seen=set();submits=0
  for c in cases():
   expected,s,trips=reference(fixture(c),c);m=Oracle(words,fixture(c,raw),c,raw).run()
   assert m.service.calls==s.calls,(label,c,'calls')
   assert public(m.memory)==public(expected),(label,c,'public')
   assert m.service.submits==trips and m.r[2]==s.last_result and m.service.integers==1+3*trips and m.service.reals==8*trips
   assert tuple(m.r[16:24])+tuple(m.r[28:])==m.saved and tuple(m.f[20:])==m.saved_fp
   seen.update(m.visits&set(range(ENTRY,ENTRY+752,4)));count+=1;submits+=trips
  assert seen==set(range(ENTRY,ENTRY+752,4))-{ENTRY+0xE4}
  row=dict(stream=label,cases=count,reachable_words=len(seen),retail_words=188,submissions=submits,all_four_vectors_and_13_arguments=True,saved_ABI=True,normal_execution_only=True);reports.append(row);print(json.dumps(row),flush=True)
 report=dict(passes=True,streams=reports,raw_private_entry_map_applied=True,direction_output_contract='writes three words without reading prior contents',hardware_FCSR_and_raw_fault_identity_unclaimed=True,c_match_credit=0);(p/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
