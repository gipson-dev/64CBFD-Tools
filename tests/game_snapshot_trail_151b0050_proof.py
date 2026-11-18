"""Full trail-emitter relation, opaque providers and exposed velocity bytes."""
from pathlib import Path
import json,struct
from tools.tests import game_strip_follow_151ae3a8_proof as base
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests.game_strip_update_151ad174_proof import alternate
from tools.tests import game_snapshot_trail_151b0050_oracle as oracle
e,g=base.e,base.g
FRAME=128
class State(base.State):
 def __init__(self):
  super().__init__();self.phase='radial-trail';self.mem={i:('PRIVATE_ENTRY',i)for i in range(-FRAME,60)}
  self.r[4],self.r[5],self.r[6],self.r[7]=('KIND_WORD',),('INDEX_WORD',),('X_WORD',),('Y_WORD',)
  self.source_layout=False
 def canonical(self,address):
  if not self.source_layout or not e.tagged(address,'STACK'):return address
  offset=address[1]+FRAME
  if 0x50<=offset<0x68:return('STACK',address[1]+(16 if offset<0x58 else -8))
  return address
 def load(self,address,size,pool=b''):
  address=self.canonical(address)
  if e.tagged(address,'STACK'):
   at=address[1];assert size in(1,2,4)and -FRAME<=at and at+size<=60 and at%size==0,('private read',at,size)
   return base.base.word_roundtrip(g.join([self.mem[at+i]for i in range(size)]))
  return super().load(address,size,pool)
 def store(self,address,size,value):
  address=self.canonical(address)
  if e.tagged(address,'STACK'):
   at=address[1];assert size in(1,2,4)and -FRAME<=at and at+size<=60 and at%size==0,('private write',at,size)
   for i in range(size):self.mem[at+i]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def frame(self):return tuple(self.mem[i]for i in range(-FRAME,60))

class Program(base.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',oracle.ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  assert target in oracle.COUNTS,('unknown provider',hex(target));count=oracle.COUNTS[target]
  args=tuple(s.r[4:4+min(count,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,count-4)))
  ordinal=sum(s.calls.values());s.calls[target]+=1
  s.trace.extend((('CALL',target,args,s.fcsr),('CALL_PRIVATE',s.frame()),('CALL_PUBLIC',tuple(sorted(s.public.items(),key=repr)))))
  if target==oracle.DIRECTION:
   assert args[3]==('STACK',-24)
   for i in range(12):s.store(e.add(args[3],i),1,('DIRECTION_BYTE',ordinal,i))
  if target==oracle.SUBMIT:
   assert args[:2]==(('STACK',-12),('STACK',-24)),('exposed vector addresses',args[:2])
   for label,pointer in zip(('POSITION','DIRECTION'),args[:2]):
    packet=tuple(s.load(e.add(pointer,i),1)for i in range(12));s.trace.append(('EXPOSED_'+label,packet))
    for i in range(12):s.store(e.add(pointer,i),1,('SUBMIT_'+label+'_BYTE',ordinal,i))
  s.epoch+=1
  for address in s.public:s.public[address]=('PROVIDER_BYTE',ordinal,address)
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for i in range(max(4,count)):s.store(e.add(s.r[29],i*4),4,('CALL_HOME',ordinal,i))
  if target==oracle.REAL:s.f[0]=('FP_RESULT',target,ordinal,args)
  else:s.r[2]=('WORD_RESULT',target,ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi,s.lo=('CALL_HI',ordinal),('CALL_LO',ordinal)
  s.fcsr,s.condition=('CALL_CSR',ordinal),('CALL_CONDITION',ordinal)

def prove(truth,candidate,source_layout=False):
 terms=Terms();answers=[];coverage=[]
 for index,words in enumerate((truth,candidate)):
  state=State();state.source_layout=bool(index and source_layout)
  p=Program(words,terms);answers.append(p.paths(0,{-4:'return'},state));coverage.append(len(p.seen))
 left,right=answers;assert left.keys()==right.keys()and len(left)==1,('paths',len(left),len(right))
 for key,a in left.items():
  b=right[key]
  for name,x,y in(('all188canonical_private',a.frame(),b.frame()),('ordered effects and FP',a.trace,b.trace),('public',a.public,b.public),('reads',a.read_set,b.read_set),('FP status',a.fcsr,b.fcsr),('FP condition',a.condition,b.condition)):
   if x!=y:
    at=next((i for i,(u,v)in enumerate(zip(x,y))if u!=v),None)if isinstance(x,(list,tuple))else None
    raise AssertionError((name,at,repr(x[at]if at is not None else x)[:650],repr(y[at]if at is not None else y)[:650]))
  for s in(a,b):
   assert s.calls=={oracle.REAL:3,oracle.RNG:3,oracle.DIRECTION:1,oracle.SUBMIT:1}
   assert s.r[2]==1
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',),('stack/RA restore',s.r[29],s.r[31])
   assert all(s.r[i]==('ENTRY_GPR',i)for i in(*range(16,24),28,30)),('saved GPR restore',)
   assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)],('saved FPR restore',)
 return dict(complete_paths=1,private_bytes=188,ordered_public_and_FP_status=True,all8_calls=True,all18_arguments=True,exposed_position_and_direction_bytes=24,coverage=coverage,terms=len(terms.values))



def controls(truth,candidate):
 alt=[alternate(w)for w in candidate];assert alt!=candidate;positive=prove(truth,alt)
 changes=[('wrong-heading-half',0x87A400A6,lambda w:(w&0xFFFF0000)|0xA4),('wrong-first-capture',0xE7A00050,lambda w:(w&0xFFFF0000)|0x54),('wrong-position-snapshot',0xE7AC0074,lambda w:(w&0xFFFF0000)|0x70),('wrong-submitted-position',0x27A40074,lambda w:(w&0xFFFF0000)|0x70),('wrong-frame-restore',0x27BD0080,lambda w:(w&0xFFFF0000)|0x78)]
 rejected=[]
 for name,before,change in changes:
  assert candidate.count(before)==1,(name,hex(before),candidate.count(before));bad=candidate[:];index=bad.index(before);bad[index]=change(before)
  try:prove(truth,bad)
  except AssertionError as error:
   reason=str(error);assert reason and not any(s in reason for s in('unsupported','unbounded','escaped code')),reason;rejected.append(dict(name=name,index=index,rejection=reason[:240]))
  else:raise AssertionError(('ineffective control',name))
 return dict(independent_GPR_allocation_positive=positive,effective_negatives=rejected)



def derive(words):return oracle.derive(words)

def main(raw,truth):
 derived=derive(raw);assert derived==truth
 report=dict(raw_capture_relation=prove(truth,raw,True),derived_relation=prove(truth,derived),controls=controls(truth,derived),c_match_credit=0)
 (oracle.p/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
