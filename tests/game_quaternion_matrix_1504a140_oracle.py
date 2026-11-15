"""Scalar-first quaternion semantics, aliases and explicitly modeled IEEE rules."""
from dataclasses import dataclass
import itertools,json,math,struct
from tools.experiments import game_quaternion_matrix_1504a140_recovery as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

OUTPUT=0x30040
class AlignmentFault(Exception):pass
@dataclass(frozen=True)
class Case:
 q:tuple=(0x3f800000,0x3f000000,0xbf800000,0x40000000)
 alias:int=0
 phase:int=0
 rule:str='left'

def is_nan(n):return n&0x7f800000==0x7f800000 and n&0x7fffff!=0
def fp(a,b,op,rule='left'):
 if is_nan(a) or is_nan(b):
  chosen=(a if is_nan(a) else b) if rule=='left' else (b if is_nan(b) else a)
  return chosen|0x400000
 x,y=floating(a),floating(b)
 if op=='div':
  if not y:return 0x7fc00000 if not x else bits(math.copysign(math.inf,x*math.copysign(1.,y)))
  value=x/y
 else:value=x+y if op=='add' else x-y if op=='sub' else x*y
 return 0x7fc00000 if math.isnan(value) else bits(value)

def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-256,1024)}
 for base in (0x30000,0x40000):m.update({base+i:(i*13+base//256+0x53)&255 for i in range(256)})
 q=(0x40040,OUTPUT,OUTPUT+4,OUTPUT+32,OUTPUT-8,OUTPUT+48,OUTPUT+60)[c.alias]
 for i,v in enumerate(c.q):put(m,q+i*4,v)
 return m,(q,OUTPUT)

def public(m,phase=0):return{a:v for a,v in m.items() if not STACK+phase-72<=a<STACK+phase}

def reference(initial,args,rule='left'):
 m=dict(initial);q,out=args;w,x,y,z=[read(m,q+i*4) for i in range(4)]
 op=lambda a,b,k:fp(a,b,k,rule)
 mul=lambda a,b:op(a,b,'mul');add=lambda a,b:op(a,b,'add');sub=lambda a,b:op(a,b,'sub')
 scale=op(bits(2.),add(mul(z,z),add(add(mul(w,w),mul(x,x)),mul(y,y))),'div')
 sx,sy,sz=mul(x,scale),mul(y,scale),mul(z,scale)
 wx,wy,wz=mul(w,sx),mul(w,sy),mul(w,sz)
 xx,xy,xz=mul(x,sx),mul(x,sy),mul(x,sz);yy,yz,zz=mul(y,sy),mul(y,sz),mul(z,sz)
 values={0:sub(bits(1.),add(yy,zz)),1:add(xy,wz),2:sub(xz,wy),4:sub(xy,wz),5:sub(bits(1.),add(xx,zz)),6:add(yz,wx),8:add(xz,wy),9:sub(yz,wx),10:sub(bits(1.),add(xx,yy)),3:0,7:0,11:0,15:bits(1.)}
 for i,v in values.items():put(m,out+i*4,v)
 return m

class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,args,entry=source.ENTRY,connected=None):
  super().__init__(words,initial,c,entry=entry,arguments=args,connected=connected)
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in (0,1,2,3):
   self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul','div')[w&63],self.case.rule)
  else:super().execute(w)
 def get(self,address,size):
  if size in (4,8) and address%size:raise AlignmentFault
  return super().get(address,size)
 def put(self,address,value,size):
  if size in (4,8) and address%size:raise AlignmentFault
  return super().put(address,value,size)
 def record_call(self,t):raise AssertionError('Quaternion leaf has no calls')
 def hook(self,t):raise AssertionError('No external providers')

def finite_corpus():
 for vals,alias,phase in itertools.product(itertools.product((-2.,-.25,.5,1.),repeat=4),range(7),(0,8)):
  yield Case(tuple(bits(v) for v in vals),alias,phase)
 for i,alias,phase in itertools.product(range(4),range(7),(0,8)):
  yield Case(tuple(bits(1.) if k==i else 0 for k in range(4)),alias,phase)

def exceptional_corpus():
 for vals in itertools.product((0x3f800000,0x7fc00001,0x7fc30002),repeat=4):
  if not any(is_nan(v) for v in vals):continue
  for rule,alias in itertools.product(('left','right'),range(7)):yield Case(vals,alias,0,rule)
 specials=(0,0x80000000,1,0x80000001,0x007fffff,0x00800000,0x7f7fffff,0x7f800000,0xff800000,0x7f800001,0xff800002)
 for value,slot,rule in itertools.product(specials,range(4),('left','right')):
  vals=[0,0,0,0];vals[slot]=value;yield Case(tuple(vals),slot%7,8,rule)

def check(m,want,c):
 assert public(m.memory,c.phase)==public(want,c.phase),c
 assert not m.calls

def main():
 programs=source.programs();seen=[set() for _ in programs];counts=[]
 for corpus in (finite_corpus,exceptional_corpus):
  count=0
  for c in corpus():
   initial,args=fixture(c);want=reference(initial,args,c.rule)
   for i,(words,entry) in enumerate(programs):
    m=Oracle(words,initial,c,args,entry);m.run();check(m,want,c);seen[i].update(m.visits)
   count+=1
  counts.append(count)
 assert all(len(v)==89 for v in seen)
 prefixes=0
 for c in (Case(),Case(alias=1,phase=8),Case(q=(0,0,0,0)),Case(q=(0x7f800001,0x7fc30002,0,0),alias=6,rule='right')):
  initial,args=fixture(c);m=Oracle(programs[0][0],initial,c,args);m.run()
  for cut in range(m.all_accesses):
   states=[]
   for words,entry in programs:
    one=Oracle(words,initial,c,args,entry);one.cut=cut
    try:one.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    states.append((one.r,one.f,one.memory,one.trace,one.current_pc,one.delay_of))
   assert states[0]==states[1];prefixes+=1
 controls=0;truth=programs[0][0]
 for old,new in ((0x46085183,0x46085182),(0xe4aa0000,0xe4aa0004),(0x46062200,0x46062201)):
  assert truth.count(old)==1;bad=truth[:];bad[bad.index(old)]=new;c=Case();initial,args=fixture(c);m=Oracle(bad,initial,c,args);m.run()
  try:check(m,reference(initial,args),c)
  except AssertionError:controls+=1
  else:raise AssertionError('Ineffective instruction control')
 report=dict(finite_cases=counts[0],exceptional_cases=counts[1],streams=len(programs),all_words_visited=89,aliases=7,access_prefixes=prefixes,instruction_controls=controls,nan_rules=['left operand wins','right operand wins'],hardware_nan_fcsr_not_claimed=True,private=True)
 (source.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
