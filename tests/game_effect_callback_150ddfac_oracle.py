"""Bounded callback model for ordered RNG effects and the effect descriptor."""
import itertools,json,struct
from dataclasses import dataclass
from tools.experiments import game_effect_callback_150ddfac_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.experiments.game_actor_state_tick_integration import symbol_rows
ACTOR=0x30000;PAYLOAD=0x32000;ALT=0x33000;POSITIONS=0x34020;ALTPOS=0x35020;PARAM=0x36000;ALTPARAM=0x36100
RAND_FLOAT=0x150ADA68;RAND_INT=0x150ADA20;SUBMIT=0x1513C73C
@dataclass(frozen=True)
class Case:
 random_float:int=0x3F000000
 choice:int=0
 first:int=0x12345678
 second:int=0x22222222
 third:int=0x33333333
 index:int=0
 height:int=0x42C80000
 mutation:int=0
 phase:int=0
 seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-512,512)}
 for base,size in((ACTOR,0x120),(PAYLOAD,0x80),(ALT,0x80),(POSITIONS-20,80),(ALTPOS-20,80),(PARAM,16),(ALTPARAM,16)):m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(size)})
 put(m,ACTOR+0x98,PAYLOAD);put(m,ACTOR+0x94,POSITIONS);m[ACTOR+0x2D]=c.index&255;m[ACTOR+0x0C]=0xA1;m[ACTOR+1]=0xB2
 for i in(-1,0,1):put(m,POSITIONS+20*i,bits(10.+i));put(m,POSITIONS+20*i+8,bits(-20.-i))
 return m
def effect(m,c,stage):
 if c.mutation&1 and stage==0:put(m,ACTOR+0x98,ALT);put(m,ACTOR+0x94,ALTPOS)
 if c.mutation&2 and stage==3:m[ACTOR+0x2D]=255;put(m,POSITIONS-20,bits(42.));put(m,POSITIONS-12,bits(-17.))
 if c.mutation&4 and stage==4:put(m,STACK+c.phase+16,bits(6.));put(m,STACK+c.phase+20,ALTPARAM)
 if c.mutation&8 and stage==4:m[ACTOR+0x0C]=0xC3;m[ACTOR+1]=0xD4
def descriptor(c):return ((0,4,17),(4,2,100),(6,1,30 if c.choice&1 else 29),(8,4,0),(12,4,0),(16,1,255),(17,1,255),(18,1,0),(19,1,0),(20,1,0),(21,1,255),(24,4,0x30002))
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase;put(m,home+16,c.height);put(m,home+20,PARAM);effect(m,c,0);m[PAYLOAD+0x20]=4
 for stage in range(1,5):effect(m,c,stage)
 index=m[ACTOR+0x2D];index=index-256 if index&128 else index;pos=POSITIONS+20*index;radius=bits(rounded(rounded(floating(c.random_float)*70.)+10.))
 args=(5,0,read(m,home+20),read(m,pos),read(m,home+16),read(m,pos+8),radius,radius,c.first&255,(c.third&1)+(c.second&1),0,m[ACTOR+0x0C],m[ACTOR+1]);return m,args
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=p.ENTRY,connected=None):
  self.c=c;super().__init__(words,fixture(c),c,entry=entry,arguments=(ACTOR,bits(1.),bits(2.),bits(3.),c.height,PARAM),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.obs=[]
 def execute(self,w):
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and rs==16 and fn in(0,2):
   a,b=floating(self.f[rd]),floating(self.f[rt]);self.f[fd]=bits(rounded(a+b if fn==0 else a*b))
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  if t==RAND_FLOAT:self.calls.append((t,()))
  elif t==RAND_INT:self.calls.append((t,()))
  elif t==SUBMIT:
   args=tuple(self.arguments(14));ptr=args[0];self.obs=[(off,n,read(self.memory,ptr+off,n))for off,n,_ in descriptor(self.c)];self.calls.append((t,args))
  else:raise AssertionError(('Unexpected call',hex(t)))
 def hook(self,t):
  stage=len(self.calls)-1;c=self.c
  if stage<5:effect(self.memory,c,stage)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True
  if stage==0:self.f[0]=c.random_float
  elif stage<5:self.r[2]=(c.choice,c.first,c.second,c.third)[stage-1]
  else:self.r[2]=0x87654321
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');lookup={r[1]:r[2][1]for r in symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});truth=struct.unpack_from('>96I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM);assert tuple(words)==truth
 cases=[]
 for i,(choice,index,mutation,rng,parity)in enumerate(itertools.product((0,1,0xFFFF),(-1,0,1),(0,1,2,3,8,11),(0,bits(.5),bits(1.)),(0,1))):cases.append(Case(choice=choice,index=index,mutation=mutation,random_float=rng,second=parity,third=1-parity,phase=(i&1)*8,seed=i%5))
 cases += [Case(mutation=mode,phase=phase)for mode in(4,7,12,15)for phase in(0,8)]
 visits=set()
 for c in cases:
  m=Oracle(words,c);m.run();expected,args=reference(m.initial,c);public=lambda x:{a:v for a,v in x.items()if not STACK-512<=a<STACK+512};assert public(m.memory)==public(expected),(c,'public');assert [t for t,_ in m.calls]==[RAND_FLOAT,RAND_INT,RAND_INT,RAND_INT,RAND_INT,SUBMIT];assert m.calls[-1][1][1:]==args,(c,m.calls[-1],args);assert m.obs==list(descriptor(c)),(c,m.obs);assert m.r[2]==1 and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];visits.update(m.visits)
 r=dict(cases=len(cases),raw_equals_retail=True,visited_words=len(visits),missing=[i for i in range(96)if p.ENTRY+i*4 not in visits],ordered_random_calls=5,descriptor_defined_fields_checked=True,caller_home_mutation_guest_only=True,helpers_are_mutating_models=True,source_installed=False);(p.out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
