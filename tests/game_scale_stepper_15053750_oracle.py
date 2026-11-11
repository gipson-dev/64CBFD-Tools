"""Private finite-float guest screen; full qualification still follows baseline freeze."""
import itertools,json,struct
from dataclasses import dataclass
from tools.experiments import game_scale_stepper_15053750_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
ACTOR=0x30000;HELPER=0x15062bdc
f=lambda x:floating(x);b=lambda x:bits(rounded(x));add=lambda x,y:b(f(x)+f(y));sub=lambda x,y:b(f(x)-f(y));mul=lambda x,y:b(f(x)*f(y))
@dataclass(frozen=True)
class Case:
 x:int;y:int;tx:int;ty:int;step:int;mutation:int;phase:int=0;seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 m.update({ACTOR+i:(i*29+c.seed*11+0x5a)&255 for i in range(0x260)})
 for off,val in zip((0x14c,0x150,0x154,0x158,0x15c),(c.x,c.y,c.tx,c.ty,c.step)):put(m,ACTOR+off,val)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+1024}
def mutate(m,c,ordinal):
 if ordinal==0 and c.mutation:
  put(m,ACTOR+0x158,b(-2.0));put(m,ACTOR+0x15c,b(0.5))
def reference(c,initial):
 m=dict(initial);calls=[]
 for axis in (0,1):
  current=read(m,ACTOR+(0x14c if axis==0 else 0x150));target=read(m,ACTOR+(0x154 if axis==0 else 0x158));delta=sub(target,current)
  if f(delta)==0.0:continue
  step=read(m,ACTOR+0x15c)
  new=target if abs(f(delta))<f(step) else add(mul(b(-1.0 if f(delta)<0.0 else 1.0),step),current)
  x=new if axis==0 else read(m,ACTOR+0x14c);y=new if axis==1 else read(m,ACTOR+0x150)
  calls.append((HELPER,(ACTOR,x,y)));put(m,ACTOR+0x14c,x);put(m,ACTOR+0x150,y);mutate(m,c,len(calls)-1)
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,c,connected=None,memory=None):
  self.c=c;super().__init__(words,fixture(c) if memory is None else memory,c,entry=p.ENTRY,arguments=(ACTOR,),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and rs==16 and fn in (0,1,2):
   x,y=f(self.f[rd]),f(self.f[rt]);self.f[fd]=b(x+y if fn==0 else x-y if fn==1 else x*y)
  elif op==17 and rs==16 and fn==5:self.f[fd]=self.f[rd]&0x7fffffff
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  assert t==HELPER,hex(t);self.calls.append((t,tuple(self.arguments(3))))
 def hook(self,t):
  assert t==HELPER;_,x,y=self.calls[-1][1];put(self.memory,ACTOR+0x14c,x);put(self.memory,ACTOR+0x150,y);mutate(self.memory,self.c,len(self.calls)-1)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');lookup={v[1]:v[2][1] for v in p.symbol_rows((p.out/'frozen/conker/build/conker.us.elf').read_bytes())}
 words=p.bound_blob(raw,refs,{n:lookup[n] for es in refs.values() for _,n in es});truth=struct.unpack_from('>81I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM);assert tuple(words)==truth
 samples=[(0,0,0,0,1),(0,0,.5,.5,1),(0,0,2,-2,1),(1,1,-2,2,.5),(0,0,1,-1,1),(2,-1,2,1,.5),(1,1,-1,1,2),(0,1,0,-1,0),(0,0,2,-2,-1)]
 cases=[Case(*(b(v) for v in vals),mut,phase,i%3) for i,(vals,mut,phase) in enumerate(itertools.product(samples,(0,1),(0,8)))]
 visited=set()
 for c in cases:
  m=Oracle(words,c);m.run();want,calls=reference(c,m.initial)
  assert public(m.memory)==public(want),(c,'memory');assert m.calls==calls,(c,m.calls,calls)
  assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];visited.update(m.visits)
 result=dict(cases=len(cases),retail_words_visited=sum(p.ENTRY+4*i in visited for i in range(81)),unvisited=[hex(p.ENTRY+4*i) for i in range(81) if p.ENTRY+4*i not in visited],retail_equals_compiled=True,finite_nearest_only=True,helper_modeled=True,source_installed=False,byte_exact=False)
 (p.out/'guest-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
