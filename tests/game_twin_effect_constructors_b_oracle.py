import itertools,json,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments import game_twin_effect_constructors_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x151B50F4;RANDF=0x150ADA68;RANDI=0x150ADA20;EMIT=0x151D9014;POSITION=0x30000;MARK=0x70000;CONST=0x800AA3E8
@dataclass(frozen=True)
class Case:
 vector:tuple;randoms:tuple;selector:int;answer:int;phase:int=0;seed:int=0
def cases():
 vectors=((0,0,0),(0x3f800000,0xc0200000,0x40400000),(0x80000000,0x3dcccccd,0xc2f60000),(0x3dcccccd,0x3e4ccccd,0x3e99999a),(0xc1200000,0x41200000,0x80000000),(0x3f000000,0xbf000000,0x3f800000))
 randoms=((0,bits(0.),0,0,bits(0.)),(1,bits(.5),30,100,bits(1.)),(2,bits(1.),31,101,bits(-.5)),(0xffffffff,bits(-.25),0xffffffff,0x80000000,bits(.25)),(3,bits(.125),15,44,bits(.75)),(4,bits(-1.),16,45,bits(-1.)),(5,bits(.75),255,89,bits(.125)),(6,bits(.25),0x80000000,0xffffffff,bits(-.125)))
 base=[Case(*v) for v in itertools.product(vectors,randoms,(0,1,255,0x1234),(0,0x34560))]
 return base+[replace(c,phase=8) for c in base[::12]]
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,512)}
 for base,n in ((POSITION,16),(MARK,4),(CONST,16)):m.update({base+i:(i*13+11)&255 for i in range(n)})
 for i,v in enumerate((0x3e051eb9,0x3fd9999a,0x3e010625,0xbf33b646) if c.phase else (0x3dd2f1ab,0x3f000000,0x3f1a1cad,0xbf85c290)):put(m,CONST+4*i,v)
 put(m,MARK,0);return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+512}
def reference(c):
 m=fixture(c);variant,f1,i1,i2,f2=c.randoms
 velocity=tuple(fp(v^0x80000000,read(m,CONST),'mul') for v in c.vector)
 first=fp(fp(f1,read(m,CONST+8),'mul'),read(m,CONST+12),'add')
 second=fp(fp(f2,bits(202.),'mul'),bits(142.),'add')
 args=(POSITION,0,0,first,(i1&15)+10,i2%45+137,second,variant&1,read(m,CONST+4),read(m,CONST+4),0,0,1,0,c.selector&255,1)
 put(m,MARK,0x13579bdf);return public(m),velocity,args,c.answer
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(POSITION,*c.vector,c.selector));self.before=self.r[:];self.before_f=self.f[:];self.observed=None
 def execute(self,w):
  op,fmt,fs,fd,fn=w>>26,(w>>21)&31,(w>>11)&31,(w>>6)&31,w&63
  if op==17 and fmt==16 and fn==7:self.f[fd]=self.f[fs]^0x80000000
  else:super().execute(w)
 def record_call(self,t):
  assert t in (RANDF,RANDI,EMIT),hex(t)
  if t==EMIT:
   a=tuple(self.arguments(16));assert STACK-1024<=a[1]<STACK
   velocity=tuple(read(self.memory,a[1]+4*i) for i in range(3));self.observed=(velocity,(a[0],0,*a[2:]))
  self.calls.append(t)
 def hook(self,t):
  index=len(self.calls)
  if t==EMIT:put(self.memory,MARK,0x13579bdf)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
  if t==RANDF:self.f[0]=self.case.randoms[1 if index==2 else 4]
  elif t==RANDI:self.r[2]=self.case.randoms[0 if index==1 else 2 if index==3 else 3]
  else:self.r[2]=self.case.answer
def main():
 data,fs,rs=parse_object(out/'variant_151B50F4.o');a,n=fs['func_151B50F4']['value'],fs['func_151B50F4']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n}
 look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es})
 retail=struct.unpack_from('>82I',(root/'conker/conker.us.bin').read_bytes(),0x1E25A4);seen=set()
 for c in cases():
  expected,velocity,args,answer=reference(c)
  for ws in (retail,candidate):
   m=Oracle(ws,c);m.run();assert (public(m.memory),m.observed,m.r[2])==(expected,(velocity,args),answer),(c,m.observed,(velocity,args),hex(m.r[2]))
   assert m.calls==[RANDI,RANDF,RANDI,RANDI,RANDF,EMIT]
   assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
   if ws is retail:seen.update(m.visits)
 report=dict(cases=len(cases()),retail_words_visited=sum(ENTRY+4*i in seen for i in range(82)),helpers='modeled',source_installed=False)
 (out/'guest_151B50F4_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
