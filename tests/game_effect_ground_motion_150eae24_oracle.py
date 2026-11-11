import itertools,json,math,struct
from dataclasses import dataclass
from tools.experiments import game_effect_ground_motion_150eae24_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
ACTOR=0x30000;OUT1=0x50000;OUT2=0x51000;DELTA=0x800BE9A4;HELPER=0x15046C80
f=lambda x:floating(x);b=lambda x:bits(rounded(x));add=lambda x,y:b(f(x)+f(y));sub=lambda x,y:b(f(x)-f(y));mul=lambda x,y:b(f(x)*f(y))
@dataclass(frozen=True)
class Case:
 x:int;z:int;dx:int;dz:int;height:int;query:int;remaining:int;dt:int;answer:int;mutation:int;phase:int=0;seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 for base,size in ((ACTOR,160),(OUT1,64),(OUT2,64)):
  m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(size)})
 put(m,ACTOR+0x14,OUT1)
 for off,v in zip((0x18,0x1c,0x20,0x24,0x28,0x2c,0x30),(c.x,c.z,c.dx,c.dz,c.height,c.query,c.remaining)):put(m,ACTOR+off,v)
 put(m,DELTA,c.dt);return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+1024}
def ref(c,initial):
 m=dict(initial);x=add(c.x,mul(c.dx,c.dt));z=add(c.z,mul(c.dz,c.dt));put(m,ACTOR+0x18,x);put(m,ACTOR+0x1c,z);put(m,OUT1+0x0e,math.trunc(f(x))&65535,2);put(m,OUT1+0x12,math.trunc(f(z))&65535,2)
 if c.mutation:put(m,ACTOR+0x14,OUT2);put(m,ACTOR+0x28,b(-11.5));put(m,DELTA,b(.25))
 put(m,ACTOR+0x34,b(19.75));addr=read(m,ACTOR+0x14);height=read(m,ACTOR+0x34) if c.answer else read(m,ACTOR+0x28);put(m,addr+0x10,math.trunc(f(height))&65535,2);remaining=sub(c.remaining,read(m,DELTA));put(m,ACTOR+0x30,remaining);return m,int(not(f(remaining)<=0.0)),(x,c.height,z)
class Oracle(FactoryOracle):
 def __init__(self,words,c,connected=None,memory=None,entry=p.ENTRY):
  self.c=c;super().__init__(words,fixture(c) if memory is None else memory,c,entry=entry,arguments=(ACTOR,),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.points=[]
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and rs==16 and fn==13:
   value=f(self.f[rd]);assert math.isfinite(value) and -2147483648.0<=value<2147483648.0;self.f[fd]=math.trunc(value)&0xffffffff;self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  assert t==HELPER,hex(t);a=tuple(self.arguments(4));self.calls.append((t,a));self.points.append(tuple(read(self.memory,a[0]+4*i) for i in range(3)))
 def hook(self,t):
  assert t==HELPER;args=self.calls[-1][1];assert args[1:]==(0,self.c.query,ACTOR+0x34)
  if self.c.mutation:put(self.memory,ACTOR+0x14,OUT2);put(self.memory,ACTOR+0x28,b(-11.5));put(self.memory,DELTA,b(.25))
  put(self.memory,ACTOR+0x34,b(19.75))
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=self.c.answer
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');lookup={v[1]:v[2][1] for v in p.symbol_rows((p.out/'frozen/conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{n:lookup[n] for es in refs.values() for _,n in es});truth=struct.unpack_from('>75I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM);assert tuple(words)==truth[:74] and truth[74]==0
 samples=[(1.25,-2.75,.5,-1.5,8.5,-2.25,2,.5),(-5.75,6.5,-2,.5,-8.5,4,.25,.5),(0.,0.,0.,0.,-1.,1.,0.,1.),(123.75,-110.25,3.,-2.,5.,-10.,-.5,.25)]
 cases=[Case(*(b(v) for v in values),answer,mutation,phase,i%3) for i,(values,answer,mutation,phase) in enumerate(itertools.product(samples,(0,1),(0,1),(0,8)))];visited=set()
 for c in cases:
  m=Oracle(words,c);m.run();want,result,point=ref(c,m.initial);assert public(m.memory)==public(want),(c,'memory');assert m.r[2]==result,(c,m.r[2],result);assert len(m.calls)==1 and m.points==[point],(c,m.points,point);assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];visited.update(m.visits)
 report=dict(cases=len(cases),retail_body_words_visited=sum(p.ENTRY+4*i in visited for i in range(74)),retail_equals_compiled=True,finite_float_only=True,global_and_output_pointer_mutations=True,ground_helper_modeled=True,source_installed=False);(p.out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
