"""Private retail/raw/normalized packed-record execution, helper models."""
import itertools,json,struct,math
from dataclasses import dataclass
from tools.experiments import game_packed_motion_1516a648_match as p
from tools.experiments import game_packed_motion_1516a648_match as n
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
OBJ=0x30000;TICKS=0x800BE9E4;UPDATE=0x1516F864;HEIGHT=0x1510F8D8;CONTACT=0x1516F94C;MARK=0x70000
u32=lambda n:n&0xffffffff
s32=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
s16=lambda n:((n&0xffff)^0x8000)-0x8000
@dataclass(frozen=True)
class Case:
 state:int;alpha:int;ticks:int;y:int;velocity:int;answer:int;mutation:int;phase:int=0;seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 m.update({OBJ+i:(i*29+c.seed*11+0x5a)&255 for i in range(0x100)});m.update({MARK+i:0 for i in range(16)})
 put(m,TICKS,u32(c.ticks));put(m,OBJ+0xe,0xfffd,2);put(m,OBJ+0x10,c.y&65535,2);put(m,OBJ+0x12,0x0007,2);put(m,OBJ+0x18,c.velocity&65535,2);m[OBJ+0x1f]=c.alpha;m[OBJ+0x24]=c.state
 return m
def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+1024}
def signedword(m,a):return s16(read(m,a,2))
def effect(m,c,target):
 if target==UPDATE and c.mutation&1:put(m,OBJ+0xe,0xff80,2);put(m,OBJ+0x10,100,2);put(m,OBJ+0x12,222,2);put(m,OBJ+0x18,0xff85,2)
 if target==HEIGHT and c.mutation&2:put(m,OBJ+0x10,0xffc0,2);put(m,OBJ+0x18,0xff03,2)
 if target==CONTACT:put(m,MARK,0x13579bdf)
def reference(c,initial):
 m=dict(initial);calls=[];alpha=m[OBJ+0x1f];state=m[OBJ+0x24];ticks=read(m,TICKS)
 if state:
  if alpha!=255:
   alpha=s32(alpha+u32(ticks<<4));alpha=255 if alpha>=256 else alpha;m[OBJ+0x1f]=alpha&255;state=m[OBJ+0x24]
 elif alpha:
  alpha=s32(alpha-u32(ticks<<2));alpha=0 if alpha<0 else alpha;m[OBJ+0x1f]=alpha&255;state=m[OBJ+0x24]
 if not state and not alpha:return m,calls,1
 put(m,OBJ+0x18,(signedword(m,OBJ+0x18)-300)&65535,2);calls.append((UPDATE,(OBJ,)));effect(m,c,UPDATE)
 calls.append((HEIGHT,tuple(u32(signedword(m,OBJ+i))for i in(0xe,0x10,0x12))+(0,)));effect(m,c,HEIGHT);level=s32(c.answer+10);m[OBJ+0x2c]=(level>>8)&255;m[OBJ+0x2d]=level&255
 if signedword(m,OBJ+0x10)<level:
  put(m,OBJ+0x10,level&65535,2);speed=math.trunc(signedword(m,OBJ+0x18)*-0.5);put(m,OBJ+0x18,speed&65535,2);calls.append((CONTACT,(OBJ,230)));effect(m,c,CONTACT)
 return m,calls,0
class Oracle(FactoryOracle):
 def __init__(self,words,c,connected=None,memory=None):
  self.c=c;super().__init__(words,fixture(c)if memory is None else memory,c,entry=p.ENTRY,arguments=(OBJ,),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  counts={UPDATE:1,HEIGHT:4,CONTACT:2};assert t in counts,hex(t);self.calls.append((t,tuple(self.arguments(counts[t]))))
 def hook(self,t):
  effect(self.memory,self.c,t);value=u32(self.c.answer) if t==HEIGHT else 0xabcdef01
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def main():
 raw,refs=p.payload(p.out/"independent-selected.o");lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/"conker/build/conker.us.elf").read_bytes())};syms={n:lookup[n]for es in refs.values()for _,n in es};candidate=p.bound_blob(raw,refs,syms);normal,nrefs=n.normalize(raw,refs);normalized=p.bound_blob(normal,nrefs,syms);retail=struct.unpack_from(">73I",(p.root/"conker/conker.us.bin").read_bytes(),p.ROM);cases=[]
 for i,(state,alpha,ticks,answer,mutation)in enumerate(itertools.product((0,1,255),(0,1,254,255),(0,1,0xffffffff,0x40000000),(0xfffffff5,0,32767,0x7fffffff),(0,1,2,3))):
  y=(-32768,-1,0,32767)[i%4];velocity=(-32768,-301,-1,0,1,301,32767)[i%7];cases.append(Case(state,alpha,ticks,y,velocity,answer,mutation,(i&1)*8,i%3))
 for i,(state,alpha,ticks)in enumerate(itertools.product((0,1),range(256),(0,1,0xffffffff,64))):cases.append(Case(state,alpha,ticks,0,-301,0,0,(i&1)*8,i%3))
 visits=[set(),set(),set()]
 for c in cases:
  machines=[]
  for index,ws in enumerate((retail,candidate,normalized)):
   m=Oracle(ws,c);m.run();want,calls,value=reference(c,m.initial);assert public(m.memory)==public(want),(c,"public");assert m.calls==calls,(c,m.calls,calls);assert m.r[2]==value,(c,m.r[2],value);assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];visits[index].update(m.visits);machines.append(m)
  a,b,d=machines;assert(a.memory,a.r,a.f,a.calls,a.trace)==(d.memory,d.r,d.f,d.calls,d.trace),(c,"normalized state")
 report=dict(cases=len(cases),executions=3*len(cases),retail_words_visited=sum(p.ENTRY+4*i in visits[0]for i in range(73)),normalized_complete_state=True,helpers_modeled=True,invalid_float_hardware_not_qualified=True,source_installed=False,byte_exact=False);(p.out/"guest.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report),flush=True);return report
if __name__=="__main__":main()
