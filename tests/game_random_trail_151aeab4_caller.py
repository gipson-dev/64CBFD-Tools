"""Complete retail effect router, primary emitter and opaque alternate ABI."""
from dataclasses import replace
import itertools,json,struct
from tools.tests import game_random_trail_151aeab4_oracle as o
CALLER,ALTERNATE=0x151AE890,0x151AE984
LOW,HIGH=[o.SYMS[n]for n in('D_800A9D84','D_800A9D88')]
rom=(o.source.FROZEN/'conker/conker.us.bin').read_bytes();caller=list(struct.unpack_from('>61I',rom,CALLER-0x15000000+0x2D4B0))
def router_effect(m,c,ordinal):
 if c.mutation&1:
  for at,value in zip(o.GLOBALS,(.125+ordinal*.0625,2.+ordinal*.25,4.+ordinal*.5,1.+ordinal*.125)):o.put(m,at,o.o.bits(value))
 if c.mutation&2:m[o.POSITION+2]^=ordinal+1
 if c.mutation&4:m[o.ACTOR+0xC]^=0x5A
def alternate_effect(m,args):
 for j,value in enumerate((0xDA984,args[4],args[5],*args[1:4])):o.put(m,o.OUTPUT+96+j*4,value)

class Caller(o.Oracle):
 def __init__(self,words,m,c,route,gate,original=caller):
  args=(0,0,o.read(m,o.POSITION+8),o.o.bits(.5),o.o.bits(-.75),o.o.bits(1.25),o.ACTOR)
  super().__init__(original,m,c,entry=CALLER,arguments=args,connected={o.ENTRY+4*i:w for i,w in enumerate(words)})
  self.f[12],self.f[14]=o.read(m,o.POSITION),o.read(m,o.POSITION+4)
  self.route,self.gate,self.started=route,gate,False;self.router_calls=[];self.invocations=[];self.alternates=[]
 def record_call(self,target):
  if target==o.ENTRY:
   args=tuple(self.arguments(3));assert args==(self.r[29]+0x2C,int(0.<o.o.floating(self.gate)),self.memory[o.ACTOR+0xC]),('primary ABI',args)
   self.invocations.append((target,args));self.started=True
  elif target==ALTERNATE:self.alternates.append(tuple(self.arguments(6)))
  elif target==o.REAL and not self.started:self.router_calls.append(target)
  else:super().record_call(target)
 def hook(self,target):
  if self.started:return super().hook(target)
  args=self.alternates[-1]if target==ALTERNATE else()
  self.boundaries.append((target,args,tuple(self.get(self.r[29]+i,1)for i in range(72))))
  if target==ALTERNATE:alternate_effect(self.memory,self.alternates[-1]);value=0xABCD1234
  else:
   assert target==o.REAL and len(self.router_calls)<=2
   ordinal=len(self.router_calls)-1;router_effect(self.memory,self.case,ordinal);value=self.route if ordinal==0 else self.gate
  for i in range(6 if target==ALTERNATE else 4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF
  if target==o.REAL:self.f[0]=value
  else:self.r[2]=value

def one(words,c,route,gate,original=caller):
 initial=o.fixture(c);o.put(initial,LOW,o.o.bits(.0625));o.put(initial,HIGH,o.o.bits(.375))
 m=Caller(words,initial,c,route,gate,original).run();expected=dict(initial);home=o.o.STACK+c.phase;position=home-12
 for j in range(3):o.put(expected,position+j*4,o.read(initial,o.POSITION+j*4))
 needed=1 if o.o.floating(route)<.0625 else 2
 for ordinal in range(needed):router_effect(expected,c,ordinal)
 channel=expected[o.ACTOR+0xC];calls=[];packets=[];invocations=[];alternates=[]
 if needed==2:
  if o.o.floating(route)<.25:
   mode=int(0.<o.o.floating(gate));invocations=[(o.ENTRY,(position,mode,channel))]
   expected,calls,packets=o.reference(expected,c,position=position,mode=mode,channel=channel,target_home=home-56)
  else:
   args=(position,o.o.bits(.5),o.o.bits(-.75),o.o.bits(1.25),int(.375<o.o.floating(gate)),channel);alternates=[args];alternate_effect(expected,args)
 assert len(m.router_calls)==needed and m.invocations==invocations and m.alternates==alternates
 assert m.service.calls==calls and m.service.packets==packets
 assert o.o.public(m.memory)==o.o.public(expected),('router public',c,route,gate)
 assert tuple(m.r[16:24])+(m.r[28],m.r[29],m.r[30])==m.saved_g and tuple(m.f[20:])==m.saved_fp
 return m

def run(programs):
 seen={name:set()for name in programs};n=0;primary=0
 for seed,route,gate,mutation in itertools.product(range(4),(o.o.bits(0.),o.o.bits(.125),o.o.bits(.25),o.o.bits(.75),0x7FC00000),(o.o.bits(-1.),o.o.bits(0.),o.o.bits(1.),0x7FC00000),(0,3,12,15)):
  c=o.Case(seed=seed,azimuth=(0,127,128,255)[seed],pitch=seed*63,first=(0,40,41,0xFFFFFFFF)[seed],second=(0,100,101,0xFFFFFFFF)[seed],last=seed*5+4,channel=(0xABCD0000,0x12340001,0xFFFF0080,0xFFFFFFFF)[seed],mutation=mutation,pattern=seed,phase=(seed&1)*8)
  runs={name:one(words,c,route,gate)for name,words in programs.items()};a=runs['retail']
  for name,m in runs.items():seen[name].update(m.visits);assert o.o.public(m.memory)==o.o.public(a.memory)
  assert runs['derived'].memory==a.memory and runs['derived'].fp==a.fp and runs['derived'].boundaries==a.boundaries
  primary+=bool(a.invocations);n+=1
 bad=caller[:];index=bad.index(0x91C6000C);bad[index]=0x91C6000D
 try:one(programs['retail'],o.Case(),o.o.bits(.125),o.o.bits(1.),original=bad)
 except AssertionError as error:assert 'primary ABI'in str(error);control=str(error)
 else:raise AssertionError('wrong caller selector accepted')
 return dict(cases_per_stream=n,primary_emitter_cases_per_stream=primary,caller_words=61,caller_coverage={k:len({at for at in v if CALLER<=at<CALLER+244})for k,v in seen.items()},complete_derived_RAM_private_and_FP_equal=True,early_primary_and_alternate_paths=True,alternate_constructor_is_opaque=True,effective_control=control)
