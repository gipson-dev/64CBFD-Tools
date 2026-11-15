"""Bounded original/raw execution, random sequencing and complete effect packet."""
from dataclasses import dataclass,replace
import itertools,json
from tools.experiments import game_randomized_dispatch_150c2898_recovery as s
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
RANDF,RANDI,EMIT,OWNER,MARK,CONST=0x150ada68,0x150ada20,0x151d9014,0x30040,0x70000,0x800a0288
@dataclass(frozen=True)
class Case:
 position:tuple=(0x3f800000,0xc0200000,0x40400000)
 vector:tuple=(0x3f000000,0xbf800000,0x40000000)
 randoms:tuple=(0x3f000000,0x3e800000,0xffffffff,0x80000000,0x3f400000)
 mode:int=0x87
 selector:int=0xfe
 mutation:int=0
 phase:int=0
 seed:int=0
 rule:str='left'

def cases():
 positions=((0,0,0),(bits(1.),bits(-2.5),bits(3.)),(0x80000000,bits(32767.),bits(-32768.)))
 vectors=((0,0x80000000,0),(bits(.5),bits(-1.),bits(2.)),(bits(-100.),bits(.001),bits(1e5)))
 randoms=((bits(0.),bits(0.),0,0,bits(0.)),(bits(1.),bits(1.),15,100,bits(1.)),(bits(.25),bits(.5),16,101,bits(.75)),(bits(-.5),bits(.125),0xffffffff,0x80000000,bits(-.25)))
 for i,(p,v,r,ids,mutation,phase) in enumerate(itertools.product(positions,vectors,randoms,((0,0),(255,128)),(0,1),(0,8))):
  yield Case(p,v,r,*ids,mutation,phase,i)
 for n in range(128):yield Case(randoms=(bits(.375),bits(.625),n,n*101+(n%101),bits(.875)),seed=n,mutation=n&1,phase=(n&1)*8)

def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-256,768)}
 for base,n in ((OWNER-32,128),(MARK,32),(CONST,12)):m.update({base+i:(i*13+c.seed*11+0x53)&255 for i in range(n)})
 m[OWNER+12]=c.mode;m[OWNER+1]=c.selector
 for i,v in enumerate((c.vector[1],c.vector[2],OWNER)):put(m,STACK+c.phase+16+4*i,v)
 for i,v in enumerate((0x3dcccccd,0x3f19999a,0xbf400000)):put(m,CONST+4*i,v)
 return m

def effect(m,c,ordinal):
 put(m,MARK,(0x13579bdf+ordinal*0x10203)&0xffffffff)
 if c.mutation:
  m[OWNER+12]^=0x55;m[OWNER+1]^=0xa3
  for i,v in enumerate((0x3e800000,0x3f400000,0xbe800000)):
   put(m,CONST+4*i,v if ordinal%2 else (0x3dcccccd,0x3f19999a,0xbf400000)[i])

def public(m,phase=0):return {a:v for a,v in m.items() if not STACK+phase-120<=a<STACK+phase}

def reference(initial,c):
 m=dict(initial);home=STACK+c.phase
 put(m,home+8,c.position[2]);put(m,home+12,c.vector[0])
 op=lambda a,b,k:fp(a,b,k,c.rule)
 effect(m,c,0)
 speed=op(op(op(c.randoms[0],bits(112.),'mul'),bits(247.),'add'),read(m,CONST),'mul')
 velocity=tuple(op(v^0x80000000,speed,'mul') for v in c.vector)
 for i in range(1,5):effect(m,c,i)
 first=op(op(c.randoms[1],read(m,CONST+4),'mul'),read(m,CONST+8),'add')
 second=op(op(c.randoms[4],bits(119.),'mul'),bits(129.),'add')
 args=(0,0,6,first,(c.randoms[2]&15)+25,c.randoms[3]%101+155,second,0,bits(1.),bits(1.),1,0,1,0,m[OWNER+12],m[OWNER+1])
 effect(m,c,5)
 return public(m,c.phase),(c.position,velocity,args)

class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=s.ENTRY,connected=None):
  super().__init__(words,initial,c,entry=entry,arguments=(*c.position,*c.vector,OWNER),connected=connected)
  self.f[12:15:2]=[c.position[0],c.position[1]];self.before_f=self.f[:];self.observed=None
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in (0,1,2):
   self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul')[w&63],self.case.rule)
  elif w>>26==17 and w>>21&31==16 and w&63==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
  else:super().execute(w)
 def record_call(self,t):
  assert t in (RANDF,RANDI,EMIT),hex(t)
  if t==EMIT:
   a=tuple(self.arguments(16));assert a[:2]==(self.r[29]+108,self.r[29]+96)
   pos=tuple(read(self.memory,a[0]+4*i) for i in range(3));vel=tuple(read(self.memory,a[1]+4*i) for i in range(3))
   self.observed=(pos,vel,(0,0,*a[2:]))
  self.calls.append(t)
 def hook(self,t):
  index=len(self.calls)-1;effect(self.memory,self.case,index)
  for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
  if t==RANDF:self.f[0]=self.case.randoms[{0:0,1:1,4:4}[index]]
  elif t==RANDI:self.r[2]=self.case.randoms[index]
  else:self.r[2]=0x34560

def verify(m,initial,c):
 want,observed=reference(initial,c)
 assert public(m.memory,c.phase)==want and m.observed==observed,(c,m.observed,observed)
 assert m.calls==[RANDF,RANDF,RANDI,RANDI,RANDF,EMIT]
 assert m.r[16:24]==m.before[16:24] and m.r[28:31]==m.before[28:31] and m.f[20:]==m.before_f[20:]

def state(m):return m.r,m.f,m.hi,m.lo,m.memory,m.trace,m.calls,m.observed,m.current_pc,m.delay_of

def main():
 programs=s.programs();seen=set();count=0
 for c in cases():
  initial=fixture(c);states=[]
  for words in programs:
   m=Oracle(words,initial,c);m.run();verify(m,initial,c);states.append(state(m));seen.update(m.visits)
  assert states[0]==states[1];count+=1
 assert len(seen)==86
 exceptional=0
 for v,slot,rule in itertools.product((0,0x80000000,1,0x7f7fffff,0x7f800000,0xff800000,0x7f800001,0x7fc30002),range(5),('left','right')):
  r=list(Case().randoms);r[(0,1,4,0,1)[slot]]=v;c=Case(randoms=tuple(r),vector=(v,bits(-1.),bits(.5)),rule=rule);initial=fixture(c)
  for words in programs:m=Oracle(words,initial,c);m.run();verify(m,initial,c)
  exceptional+=1
 prefixes=0
 for c in (Case(),Case(mutation=1,phase=8)):
  initial=fixture(c);m=Oracle(programs[0],initial,c);m.run()
  for cut in range(m.all_accesses):
   states=[]
   for words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut failed to fire')
    states.append(state(m))
   assert states[0]==states[1];prefixes+=1
 controls=0
 for old,new in ((0x24060006,0x24060005),(0x31cf000f,0x31cf0007),(0x904c000c,0x904c000b),(0x24010065,0x24010064)):
  words=programs[0][:];assert words.count(old)==1;words[words.index(old)]=new;c=Case();initial=fixture(c)
  try:m=Oracle(words,initial,c);m.run();verify(m,initial,c)
  except AssertionError:controls+=1
  else:raise AssertionError('Ineffective instruction control')
 report=dict(finite_cases=count,exceptional_modeled_cases=exceptional,streams=2,all_words_visited=86,full_state_access_prefixes=prefixes,instruction_controls=controls,helpers_modeled=True,hardware_fcsr_not_claimed=True)
 (s.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
