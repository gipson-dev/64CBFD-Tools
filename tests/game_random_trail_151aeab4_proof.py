"""Full trail-emitter relation, opaque providers and exposed velocity bytes."""
from pathlib import Path
import json,struct
from tools.tests import game_strip_follow_151ae3a8_proof as base
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests.game_strip_update_151ad174_proof import alternate
from tools.tests import game_random_trail_151aeab4_oracle as oracle
e,g=base.e,base.g
FRAME=152
class State(base.State):
 def __init__(self):
  super().__init__();self.phase='random-trail';self.mem={i:('PRIVATE_ENTRY',i)for i in range(-FRAME,16)}
  self.r[4],self.r[5],self.r[6]=('POSITION',),('MODE_WORD',),('CHANNEL_WORD',)
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   at=address[1];assert size in(1,2,4)and -FRAME<=at and at+size<=16 and at%size==0,('private read',at,size)
   return base.base.word_roundtrip(g.join([self.mem[at+i]for i in range(size)]))
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   at=address[1];assert size in(1,2,4)and -FRAME<=at and at+size<=16 and at%size==0,('private write',at,size)
   for i in range(size):self.mem[at+i]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def frame(self):return tuple(self.mem[i]for i in range(-FRAME,16))

class Program(base.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',oracle.ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  assert target in oracle.COUNTS,('unknown provider',hex(target));count=oracle.COUNTS[target]
  args=tuple(s.r[4:4+min(count,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,count-4)))
  ordinal=sum(s.calls.values());s.calls[target]+=1
  s.trace.extend((('CALL',target,args,s.fcsr),('CALL_PRIVATE',s.frame()),('CALL_PUBLIC',tuple(sorted(s.public.items(),key=repr)))))
  if target==oracle.SUBMIT:
   assert args[1]==('STACK',-16),('exposed velocity address',args[1]);packet=tuple(s.load(e.add(args[1],i),1)for i in range(12));s.trace.append(('EXPOSED_VELOCITY',packet))
   for i in range(12):s.store(e.add(args[1],i),1,('SUBMIT_PACKET_BYTE',ordinal,i))
  s.epoch+=1
  for address in s.public:s.public[address]=('PROVIDER_BYTE',ordinal,address)
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for i in range(max(4,count)):s.store(e.add(s.r[29],i*4),4,('CALL_HOME',ordinal,i))
  if target in(oracle.REAL,oracle.TRIG):s.f[0]=('FP_RESULT',target,ordinal,args)
  else:s.r[2]=('WORD_RESULT',target,ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi,s.lo=('CALL_HI',ordinal),('CALL_LO',ordinal)
  s.fcsr,s.condition=('CALL_CSR',ordinal),('CALL_CONDITION',ordinal)

def prove(truth,candidate):
 terms=Terms();answers=[];coverage=[]
 for words in(truth,candidate):
  p=Program(words,terms);answers.append(p.paths(0,{-4:'return'},State()));coverage.append(len(p.seen))
 left,right=answers;assert left.keys()==right.keys()and len(left)==1,('paths',len(left),len(right))
 for key,a in left.items():
  b=right[key]
  for name,x,y in(('all168private',a.frame(),b.frame()),('ordered effects and FP',a.trace,b.trace),('public',a.public,b.public),('reads',a.read_set,b.read_set),('FP status',a.fcsr,b.fcsr),('FP condition',a.condition,b.condition)):
   if x!=y:
    at=next((i for i,(u,v)in enumerate(zip(x,y))if u!=v),None)if isinstance(x,(list,tuple))else None
    raise AssertionError((name,at,repr(x[at]if at is not None else x)[:650],repr(y[at]if at is not None else y)[:650]))
  for s in(a,b):
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',),('stack/RA restore',s.r[29],s.r[31])
   assert all(s.r[i]==('ENTRY_GPR',i)for i in(*range(16,24),28,30)),('saved GPR restore',)
   assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)],('saved FPR restore',)
 return dict(complete_paths=1,private_bytes=168,ordered_public_and_FP_status=True,all13_calls=True,all18_arguments=True,exposed_velocity_bytes=12,coverage=coverage,terms=len(terms.values))

def controls(truth,candidate):
 alt=[alternate(w)for w in candidate];assert alt!=candidate;positive=prove(truth,alt)
 changes=[('wrong-mode-byte',0x93A8009F,lambda w:(w&0xFFFF0000)|0x9C),('wrong-channel-byte',0x93AB00A3,lambda w:(w&0xFFFF0000)|0xA0),('wrong-first-sample-home',0xE7A0005C,lambda w:(w&0xFFFF0000)|0x58),('wrong-submitted-velocity',0x27A50088,lambda w:(w&0xFFFF0000)|0x84),('wrong-final-context',0x240C0001,lambda w:(w&0xFFFF0000)|0),('wrong-frame-restore',0x27BD0098,lambda w:(w&0xFFFF0000)|0x90)]
 rejected=[]
 for name,before,change in changes:
  assert candidate.count(before)==1,(name,hex(before),candidate.count(before));bad=candidate[:];index=bad.index(before);bad[index]=change(before)
  try:prove(truth,bad)
  except AssertionError as error:
   reason=str(error);assert reason and not any(s in reason for s in('unsupported','unbounded','escaped code')),reason;rejected.append(dict(name=name,index=index,rejection=reason[:240]))
  else:raise AssertionError(('ineffective control',name))
 return dict(independent_GPR_allocation_positive=positive,effective_negatives=rejected)
