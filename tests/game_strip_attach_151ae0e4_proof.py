"""Private complete attachment relation; no production adoption credit."""
from pathlib import Path
from collections import Counter
import json,struct,sys
from tools.tests import game_strip_draw_151ad92c_entry_proof as opening
from tools.tests.game_strip_draw_151ad92c_suffix_proof import word_roundtrip
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests.game_strip_update_151ad174_proof import alternate
from tools.tests import game_strip_attach_151ae0e4_oracle as oracle

e,g=opening.e,opening.g
FRAME=56
class State(opening.State):
 def __init__(self):
  g.State.__init__(self,'common');self.side='common';self.phase='attachment'
  self.mem={i:('PRIVATE_ENTRY',i)for i in range(-FRAME,16)}
  self.public={};self.read_set=Counter();self.epoch=0;self.trace=[]
  self.r=[0]+[('ENTRY_GPR',i)for i in range(1,32)]
  self.r[4],self.r[5],self.r[29],self.r[31]=('ACTOR',),('KEY_WORD',),('STACK',0),('RETURN',)
  self.f=[('ENTRY_FP',i)for i in range(32)];self.fcsr=('ENTRY_CSR',);self.condition=('ENTRY_CONDITION',)
 def load(self,address,size,pool=b''):
  assert size in(1,2,4)
  if e.tagged(address,'STACK'):
   at=address[1];assert -FRAME<=at and at+size<=16 and at%size==0,('private read',at,size)
   return word_roundtrip(g.join([self.mem[at+i]for i in range(size)]))
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

class Program(opening.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',oracle.ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  assert target in(oracle.QUERY,oracle.PROJECT),('unexpected helper',hex(target))
  count=1 if target==oracle.QUERY else 5
  args=tuple(s.r[4:4+min(count,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,count-4)))
  ordinal=sum(s.calls.values());s.calls[target]+=1
  s.trace.extend((('CALL',target,args,s.fcsr),('CALL_PRIVATE',s.frame()),('CALL_PUBLIC',tuple(sorted(s.public.items(),key=repr)))))
  s.epoch+=1
  for address in s.public:s.public[address]=('PROVIDER_BYTE',ordinal,address)
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for i in range(max(4,count)):s.store(e.add(s.r[29],i*4),4,('CALL_HOME',ordinal,i))
  s.r[2],s.r[31]=('LOOKUP_RESULT',)if target==oracle.QUERY else('IGNORED_RESULT',),('CALL_RETURN',ordinal)
  s.hi,s.lo=('CALL_HI',ordinal),('CALL_LO',ordinal)
  s.fcsr,s.condition=('CALL_CSR',ordinal),('CALL_CONDITION',ordinal)

def prove(truth,candidate):
 terms=Terms();answers=[];coverage=[]
 for words in(truth,candidate):
  assert words[9:11]==[0x1000FFFF,0],('stationary lookup failure changed',words[9:11])
  program=Program(words,terms);answers.append(program.paths(0,{36:'spin',-4:'return'},State()));coverage.append(len(program.seen))
 left,right=answers
 assert left.keys()==right.keys(),('path predicates',len(left),len(right),next(iter(left.keys()-right.keys()),None))
 for key,a in left.items():
  b=right[key]
  for name,x,y in(('private72',a.frame(),b.frame()),('ordered public and FP',a.trace,b.trace),('public bytes',a.public,b.public),('stable public reads',a.read_set,b.read_set),('FP status',a.fcsr,b.fcsr),('FP condition',a.condition,b.condition)):
   if x!=y:
    at=next((i for i,(u,v)in enumerate(zip(x,y))if u!=v),None)if isinstance(x,(list,tuple))else None
    raise AssertionError((key[0],name,at,repr(x[at]if at is not None else x)[:450],repr(y[at]if at is not None else y)[:450]))
  if key[0]=='return':
   for s in(a,b):
    assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',),('stack/RA',s.r[29],s.r[31])
    assert all(s.r[i]==('ENTRY_GPR',i)for i in(*range(16,24),28,30)),('callee-saved GPR',)
    assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)],('callee-saved FP',)
  else:
   assert a.r[29]==b.r[29]==('STACK',-FRAME)
   assert tuple(e.choices(a,e.pred('EQ',('LOOKUP_RESULT',),0)))==(True,),('null spin predicate',a.facts)
 return dict(complete_paths=len(left),ends=dict(Counter(key[0]for key in left)),private_bytes=72,ordered_public_and_FP_status=True,public_reload_epochs=True,full_call_arguments=True,coverage=coverage,terms=len(terms.values))

def controls(truth,candidate):
 alt=[alternate(w)for w in candidate];assert alt!=candidate;positive=prove(truth,alt)
 specs=[('status-byte-width',11,lambda w:(w&0x03FFFFFF)|(32<<26)),
        ('wrong-five-argument-Z',27,lambda w:0xAFA00010),
        ('off-by-one-point-index',42,lambda w:(w&0xFFFF0000)|0xFFFE),
        ('wrong-point-stride',52,lambda w:(w&~(31<<6))|(2<<6)),
        ('wrong-attachment-state',85,lambda w:(w&0xFFFF0000)|0x13),
        ('wide-key-store',86,lambda w:(w&0x03FFFFFF)|(43<<26)),
        ('missing-fatal-spin',9,lambda w:0),
        ('wrong-frame-restore',93,lambda w:(w&0xFFFF0000)|0x30)]
 rejected=[]
 for name,index,change in specs:
  bad=candidate[:];before=bad[index];bad[index]=change(before);assert bad[index]!=before,(name,hex(before))
  try:prove(truth,bad)
  except AssertionError as error:
   reason=str(error);assert reason and not any(s in reason for s in('unsupported','unbounded','escaped code')),reason
   rejected.append(dict(name=name,index=index,original=hex(before),changed=hex(bad[index]),rejection=reason[:240]))
  else:raise AssertionError(('ineffective control',name,index,hex(before)))
 return dict(independent_GPR_allocation_positive=positive,effective_negatives=rejected)
