"""Independent bounded floating-point callback model."""
import itertools,json,struct
from dataclasses import dataclass
from tools.experiments import game_actor_position_pair_15195528_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
SOURCE=0x30000;ACTOR=0x32000;SCALE=0x800A8708;RAND=0x150ADA68;TRIG=0x1514373C;SUBMIT=0x15137610
f=lambda x:floating(x);b=lambda x:bits(rounded(x));add=lambda a,c:b(f(a)+f(c));sub=lambda a,c:b(f(a)-f(c));mul=lambda a,c:b(f(a)*f(c))
@dataclass(frozen=True)
class Case:
 source:int=1;actor:int=1;yaw:int=0;actor_yaw:int=0;scale:int=0;sin:int=0;cos:int=0;random:int=0;mutation:int=0;phase:int=0;seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 for base in (SOURCE,ACTOR):m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(256)})
 put(m,SOURCE+0x40,c.yaw);put(m,ACTOR+0x40,c.actor_yaw);put(m,SCALE,c.scale)
 for off,v in zip((0x14,0x18,0x1c),(bits(10.5),bits(-2.25),bits(100.0))):put(m,ACTOR+off,v)
 return m
def public(m):return{k:v for k,v in m.items()if not STACK-1024<=k<STACK+1024}
def mutate(m,c):
 if c.mutation:
  for off,v in zip((0x14,0x18,0x1c),(bits(-7.0),bits(12.0),bits(0.5))):put(m,ACTOR+off,v)
def reference(c,initial):
 m=dict(initial);yaw=read(m,(SOURCE if c.source == 1 else ACTOR)+0x40);angle=mul(sub(yaw,bits(90.0)),c.scale);mutate(m,c)
 x=mul(c.sin,bits(20.0));z=mul(c.cos,bits(20.0));px,py,pz=[read(m,ACTOR+o)for o in (0x14,0x18,0x1c)];up=add(py,bits(50.0));start=(add(px,x),up,add(pz,z));end=(sub(px,x),up,sub(pz,z));direction=(c.sin,bits(0.0),c.cos);return m,angle,start,end,direction
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  self.c=c;super().__init__(words,fixture(c),c,entry=p.ENTRY,arguments=(SOURCE if c.source == 1 else ACTOR if c.source == 2 else 0,ACTOR if c.actor else 0,0x12345678));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.observation=None
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and rs==16 and fn in (0,1,2):
   x,y=f(self.f[rd]),f(self.f[rt]);self.f[fd]=b(x+y if fn==0 else x-y if fn==1 else x*y)
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  if t==RAND:self.calls.append((t,()))
  elif t==TRIG:
   a=tuple(self.arguments(4));assert a[3]==a[2]+8 and STACK-1024<=a[2]<STACK;self.calls.append((t,(self.f[12],self.f[14])))
  elif t==SUBMIT:
   a=tuple(self.arguments(6));self.calls.append((t,(a[0],a[4],a[5])));self.observation=tuple(tuple(read(self.memory,a[j]+i*4)for i in range(3))for j in (1,2,3))
  else:raise AssertionError(hex(t))
 def hook(self,t):
  if t==TRIG:
   a=self.arguments(4);self.put(a[2],self.c.sin,4);self.put(a[3],self.c.cos,4);mutate(self.memory,self.c)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
  if t==RAND:self.f[0]=self.c.random

def main():
 raw,refs=p.payload(p.out/'independent-selected.o');lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});truth=struct.unpack('>74I',(p.out/'original-function.bin').read_bytes());assert tuple(words)==truth
 cases=[]
 for i,(source,yaw,scale,trig,mutation)in enumerate(itertools.product((0,1,2),(bits(0.),bits(45.),bits(180.)),(bits(0.5),bits(1.0),bits(0.017453292)),((bits(.25),bits(-.75)),(bits(-1.),bits(.5))),(0,1))):cases.append(Case(source,1,yaw,bits(-30.),scale,*trig,bits(.25),mutation,8*(i&1),i%3))
 visits=set()
 for c in cases:
  m=Oracle(words,c);m.run();want,angle,start,end,direction=reference(c,m.initial);assert public(m.memory)==public(want),(c,'memory');assert m.calls==[(TRIG,(angle,bits(1.))),(SUBMIT,(ACTOR,255,1))],(c,m.calls,angle);assert m.observation==(start,end,direction),(c,m.observation,start,end,direction);assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];visits.update(m.visits)
 c=Case(0,0,bits(0.),bits(0.),bits(.5),bits(.25),bits(.75),bits(.25),0,0,0);m=Oracle(words,c)
 try:m.run()
 except AssertionError as e:assert e.args[0]==('unmapped read',0x14,4),e
 else:raise AssertionError('Expected unmapped actor read')
 assert m.calls==[(RAND,()),(TRIG,(mul(mul(c.random,bits(360.0)),c.scale),bits(1.)))];visits.update(m.visits)
 result=dict(cases=len(cases),null_actor_fault_cases=1,words_visited=sum(p.ENTRY+4*i in visits for i in range(74)),retail_equals_compiled=True,helpers_modeled=True,finite_nearest_rounding_only=True,source_installed=False);(p.out/'guest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
