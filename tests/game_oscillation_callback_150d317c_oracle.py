"""Bounded guest model of the direct oscillation callback and FCSR conversion."""
import itertools,json,math,struct
from dataclasses import dataclass
from tools.experiments import game_oscillation_callback_150d317c_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.tests.game_actor_intensity_byte_oracle import converted
from tools.experiments.game_actor_state_tick_integration import symbol_rows
ACTOR=0x30000;NORMAL=0x15144B68;SINE=0x15047D60;DT=0x800BE9A4
@dataclass(frozen=True)
class Case:
 timer:int=0x40400000
 rate:int=0x42C80000
 step:int=0x3F800000
 mutation:int=0
 phase:int=0
 fcsr:int=0
 seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-512,512)};m.update({ACTOR+i:(i*29+c.seed*11+90)&255 for i in range(0x160)})
 for off,val in ((0x110,0),(0x114,0),(0x118,bits(10.)),(0x11C,bits(-10.)),(0x120,bits(2.)),(0x124,bits(3.)),(0x128,bits(.25)),(0x12C,bits(.75)),(0x130,bits(.5)),(0x134,bits(-.25)),(0x138,c.timer),(0x13C,c.rate)):put(m,ACTOR+off,val)
 put(m,DT,c.step);return m
def op(a,b,kind):
 x,y=floating(a),floating(b);return bits(rounded(x+y if kind=='+' else x-y if kind=='-' else x*y))
def maybe(a,b):return a==b or (a&0x7F800000==0x7F800000 and a&0x7FFFFF and b&0x7F800000==0x7F800000 and b&0x7FFFFF)
def effect(m,c,stage):
 if c.mutation&1 and stage==0:put(m,ACTOR+0x12C,bits(1.25));put(m,DT,bits(.5))
 if c.mutation&2 and stage==2:put(m,ACTOR+0x120,bits(4.));put(m,ACTOR+0x12C,bits(1.5))
 if c.mutation&4 and stage==3:put(m,ACTOR+0x11C,bits(12.));put(m,ACTOR+0x138,bits(2.));put(m,DT,bits(.25))
RETURNS=(bits(.125),bits(.625),bits(.5),bits(-.25))
def reference(initial,c):
 m=dict(initial);calls=[]
 for phase,speed in ((0x128,0x130),(0x12C,0x134)):put(m,ACTOR+phase,op(read(m,ACTOR+phase),op(read(m,ACTOR+speed),read(m,DT),'*'),'+'))
 for stage,off in ((0,0x128),(1,0x12C)):
  calls.append((NORMAL,read(m,ACTOR+off)));effect(m,c,stage);put(m,ACTOR+off,RETURNS[stage])
 for stage,phase,amp,base,dest in ((2,0x128,0x120,0x118,0x110),(3,0x12C,0x124,0x11C,0x114)):
  calls.append((SINE,read(m,ACTOR+phase)));effect(m,c,stage);put(m,ACTOR+dest,op(op(RETURNS[stage],read(m,ACTOR+amp),'*'),read(m,ACTOR+base),'+'))
 timer=op(read(m,ACTOR+0x138),read(m,DT),'-');put(m,ACTOR+0x138,timer);product=op(read(m,ACTOR+0x13C),timer,'*');m[ACTOR+0x5C]=converted(floating(product));return m,calls,int(floating(timer)>0.)
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=p.ENTRY,connected=None):
  self.c=c;super().__init__(words,fixture(c),c,entry=entry,arguments=(ACTOR,),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.fcsr=c.fcsr
 def execute(self,w):
  op0,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op0==17 and rs in(2,6):
   assert rd==31
   if rs==2:self.r[rt]=self.fcsr
   else:self.fcsr=self.r[rt]
  elif op0==17 and rs==16 and fn==36:
   assert self.fcsr&3==1;value=floating(self.f[rd])
   if not math.isfinite(value)or not -(2**31)<=value<2**31:self.fcsr|=0x40;self.f[fd]=0x80000000
   else:self.f[fd]=math.trunc(value)&0xFFFFFFFF
  elif op0==17 and rs==16 and fn in(0,1,2,6,60):
   if fn==60:self.condition=floating(self.f[rd])<floating(self.f[rt])
   elif fn==6:self.f[fd]=self.f[rd]
   else:self.f[fd]=op(self.f[rd],self.f[rt],{0:'+',1:'-',2:'*'}[fn])
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  assert t in (NORMAL,SINE)and self.fcsr==self.c.fcsr;self.calls.append((t,self.f[12]))
 def hook(self,t):
  stage=len(self.calls)-1;assert t==(NORMAL if stage<2 else SINE);effect(self.memory,self.c,stage)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=RETURNS[stage];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');lookup={r[1]:r[2][1]for r in symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});truth=struct.unpack_from('>96I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM);assert tuple(words)==truth
 values=(0,0x80000000,bits(-1.),bits(.5),bits(1.),bits(255.),bits(65536.),0x4F000000,0x4F800000,0x7F800000,0xFF800000,0x7FC12345);cases=[]
 for i,(timer,rate,mutation,fcsr)in enumerate(itertools.product(values,(0,bits(1.),bits(2.),bits(-1.)),(0,1,2,4,7),(0,0xA5A50003))):cases.append(Case(timer=timer,rate=rate,mutation=mutation,phase=(i&1)*8,fcsr=fcsr,seed=i%5))
 visited=set()
 for c in cases:
  m=Oracle(words,c);m.run();want,calls,ret=reference(m.initial,c);actual={a:b for a,b in m.memory.items()if not STACK-512<=a<STACK+512};expected={a:b for a,b in want.items()if not STACK-512<=a<STACK+512}
  assert actual==expected,(c,'memory');assert len(m.calls)==4 and all(a[0]==b[0]and maybe(a[1],b[1])for a,b in zip(m.calls,calls)),(c,m.calls,calls);assert m.r[2]==ret and m.fcsr==c.fcsr and m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];visited.update(m.visits)
 r=dict(cases=len(cases),raw_equals_retail=True,visited_words=len(visited),missing=[i for i in range(96)if p.ENTRY+i*4 not in visited],FCSR_restored_bounded_nontrapping_model=True,hardware_FCSR_and_portable_invalid_C_cast_not_qualified=True,helpers_are_mutating_models=True,source_installed=False)
 (p.out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
