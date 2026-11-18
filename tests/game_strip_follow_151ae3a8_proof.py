"""Complete ordered/private sampled-position relation with opaque providers."""
from pathlib import Path
from collections import Counter
import json,struct
from tools.tests import game_strip_attach_151ae0e4_proof as base
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests.game_strip_update_151ad174_proof import alternate
from tools.tests import game_strip_follow_151ae3a8_oracle as oracle
e,g=base.e,base.g
FRAME=120
class State(base.State):
 def __init__(self):
  g.State.__init__(self,'common');self.side='common';self.phase='sample-position'
  self.mem={i:('PRIVATE_ENTRY',i)for i in range(-FRAME,16)};self.public={};self.read_set=Counter();self.epoch=0;self.trace=[]
  self.r=[0]+[('ENTRY_GPR',i)for i in range(1,32)]
  self.r[4],self.r[29],self.r[31]=('INPUT',),('STACK',0),('RETURN',)
  self.f=[('ENTRY_FP',i)for i in range(32)];self.fcsr=('ENTRY_CSR',);self.condition=('ENTRY_CONDITION',)
 def load(self,address,size,pool=b''):
  assert size in(1,2,4)
  if e.tagged(address,'STACK'):
   at=address[1];assert -FRAME<=at and at+size<=16 and at%size==0,('private read',at,size)
   return base.word_roundtrip(g.join([self.mem[at+i]for i in range(size)]))
  value=g.join([self.public.get(e.add(address,i),('MEMORY_BYTE',self.epoch,e.add(address,i)))for i in range(size)])
  self.read_set[address,size,value]+=1;return value
 def store(self,address,size,value):
  assert size in(1,2,4)
  if e.tagged(address,'STACK'):
   at=address[1];assert -FRAME<=at and at+size<=16 and at%size==0,('private write',at,size)
   for i in range(size):self.mem[at+i]=g.byte(value,8*(size-i-1))
  else:
   self.trace.append(('WRITE',address,size,value))
   for i in range(size):self.public[e.add(address,i)]=g.byte(value,8*(size-i-1))
 def frame(self):return tuple(self.mem[i]for i in range(-FRAME,16))

class Program(base.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',oracle.ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  assert target in(oracle.HEADING,oracle.TRIG),('unknown provider',hex(target))
  ordinal=sum(s.calls.values());s.calls[target]+=1;args=(s.r[4],)
  assert (ordinal==0)==(target==oracle.HEADING)
  s.trace.extend((('CALL',target,args,s.fcsr),('CALL_PRIVATE',s.frame()),('CALL_PUBLIC',tuple(sorted(s.public.items(),key=repr)))))
  s.epoch+=1
  for address in s.public:s.public[address]=('PROVIDER_BYTE',ordinal,address)
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for i in range(4):s.store(e.add(s.r[29],i*4),4,('CALL_HOME',ordinal,i))
  if target==oracle.HEADING:s.r[2]=('HEADING_RESULT',)
  else:s.f[0]=('TRIG_RESULT',ordinal,args[0])
  s.r[31]=('CALL_RETURN',ordinal);s.hi,s.lo=('CALL_HI',ordinal),('CALL_LO',ordinal)
  s.fcsr,s.condition=('CALL_CSR',ordinal),('CALL_CONDITION',ordinal)

def prove(truth,candidate):
 terms=Terms();answers=[];coverage=[]
 for words in(truth,candidate):
  p=Program(words,terms);answers.append(p.paths(0,{-4:'return'},State()));coverage.append(len(p.seen))
 left,right=answers;assert left.keys()==right.keys()and len(left)==1,('paths',len(left),len(right))
 for key,a in left.items():
  b=right[key]
  for name,x,y in(('all136private',a.frame(),b.frame()),('ordered public and FP',a.trace,b.trace),('public',a.public,b.public),('reads',a.read_set,b.read_set),('FP status',a.fcsr,b.fcsr),('FP condition',a.condition,b.condition)):
   if x!=y:
    at=next((i for i,(u,v)in enumerate(zip(x,y))if u!=v),None)if isinstance(x,(list,tuple))else None
    raise AssertionError((name,at,repr(x[at]if at is not None else x)[:650],repr(y[at]if at is not None else y)[:650]))
  for s in(a,b):
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',),('stack/RA restore',s.r[29],s.r[31])
   assert all(s.r[i]==('ENTRY_GPR',i)for i in(*range(16,24),28,30)),('saved GPR restore',)
   assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)],('saved FPR restore',)
 return dict(complete_paths=1,private_bytes=136,ordered_public_and_FP_status=True,public_reload_epochs=True,all_three_provider_calls=True,coverage=coverage,terms=len(terms.values))

def controls(truth,candidate):
 alt=[alternate(w)for w in candidate];assert alt!=candidate;positive=prove(truth,alt)
 specifications=[('missing-incoming-home',0xAFA40078,0),('wrong-actor-capture-home',0xAFA40050,0xAFA40054),('wrong-side-result-home',0xE7A00044,0xE7A00040),('wrong-old-Y-home',0xE7A40070,0xE7A4006C),('wrong-first-point-home',0xE7A80024,0xE7A80030),('wrong-new-Y-home',0xE7A80064,0xE7A80068),('wrong-next-Z-load',0xC7A60020,0xC7A60024),('wrong-frame-restore',0x27BD0078,0x27BD0070)]
 rejected=[]
 for name,before,after in specifications:
  assert candidate.count(before)==1,(name,hex(before),candidate.count(before));bad=candidate[:];index=bad.index(before);bad[index]=after
  try:prove(truth,bad)
  except AssertionError as error:
   reason=str(error);assert reason and not any(s in reason for s in('unsupported','unbounded','escaped code')),reason
   rejected.append(dict(name=name,index=index,rejection=reason[:240]))
  else:raise AssertionError(('ineffective control',name))
 return dict(independent_GPR_allocation_positive=positive,effective_negatives=rejected)
