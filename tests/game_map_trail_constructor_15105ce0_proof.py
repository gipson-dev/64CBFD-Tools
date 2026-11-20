"""Independent complete finite-path constructor relation.

Contract: valid aligned memory and private stack disjoint from public objects.
Public reads are stable in a quiet epoch; any public write or ABI call starts
a new epoch. Providers may change all public memory, o32 caller registers,
FCSR, outgoing homes and retained descriptor bytes, while preserving saved
registers. They cannot inspect implementation PCs or unpassed local storage.
The divisor must be nonzero. This proves normal execution, not raw fault,
timing, hardware, gameplay or portable-C undefined-input equivalence.
"""
from collections import Counter
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests import game_map_trail_constructor_15105ce0_oracle as abi
e=g.e

class State(g.State):
 def __init__(self,side):
  super().__init__(side)
  self.mem={off:('PRIVATE_ENTRY',off)for off in range(-216,24)}
  self.exposed=set();self.accessed=set()
  self.r=[('INITIAL_GPR',i)for i in range(32)];self.r[0]=0
  self.r[4:8]=[('PACKET',),('EXTRA',),('PRIORITY_WORD',),('CONTEXT',)]
  self.r[29]=('STACK',0);self.r[31]=('RETURN',)
  for reg in (*range(16,24),28,30):self.r[reg]=('ENTRY',reg)
  self.f=[('INITIAL_FP',i)for i in range(32)]
  for reg in range(20,32):self.f[reg]=('ENTRY_FP',reg)
  self.fcsr=('ENTRY_FCSR',)
 def load(self,address,size,pool=b''):
  if not e.tagged(address,'STACK'):return super().load(address,size,pool)
  off=address[1]
  assert size in(1,2,4)and off%size==0 and -216<=off and off+size<=24,('private read bounds',off,size)
  self.accessed.update(range(off,off+size))
  return g.join([self.mem[off+i]for i in range(size)])
 def store(self,address,size,value):
  if not e.tagged(address,'STACK'):return super().store(address,size,value)
  off=address[1]
  assert size in(1,2,4)and off%size==0 and -216<=off and off+size<=24,('private write bounds',off,size)
  self.accessed.update(range(off,off+size))
  for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
 def frame(self):return tuple(self.mem[off]for off in range(-216,24))

class Program(g.Program):
 def __init__(self,words,terms):
  e.Program.__init__(self,words,b'',abi.ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  n=abi.COUNTS[target]
  assert s.r[29]==('STACK',-216)
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-200+4*i),4)for i in range(max(0,n-4)))
  ordinal=sum(s.calls.values());s.calls[target]+=1;observed=()
  if target==abi.CHILD:
   assert args[:4]==(('STACK',-128),0,0,0),('child pointer/ABI',args)
   observed=tuple(s.mem[off]for off in range(-128,-16))
   s.exposed.update(range(-128,-16))
  else:
   for arg in args:e.plain(arg)
  s.trace.append(('CALL',target,args,observed,s.fcsr))
  s.trace.append(('FRAME',s.frame()))
  s.epoch+=1
  for off in s.exposed:s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for i in range(max(4,n)):s.store(('STACK',-216+4*i),4,('CALL_HOME',ordinal,i))
  for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
  s.r[2]=('RESULT',target,ordinal)
  s.r[31]=('CALL_RETURN',ordinal)
  s.lo,s.hi,s.fcsr=('CALL_LO',ordinal),('CALL_HI',ordinal),('CALL_FCSR',ordinal)
  s.condition=('CALL_CONDITION',ordinal)

def observe(s):
 assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
 assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))
 assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
 return s.trace,s.read_set,s.divisors,s.fcsr,s.frame(),s.r[2]

def prove(raw,retail):
 assert len(raw)==233 and len(retail)==235
 assert raw[0]==retail[0]==0x27BDFF28
 terms=Terms();programs=[Program(raw,terms),Program(retail,terms)];answers=[]
 for side,p in enumerate(programs):
  paths=p.paths(0,{-4:'return'},State('raw'if side==0 else'retail'))
  answers.append({key:observe(s)for key,s in paths.items()})
 a,b=answers
 assert a.keys()==b.keys(),('path predicates',len(a),len(b))
 for key,x in a.items():
  y=b[key]
  if x==y:continue
  part=next(i for i,(u,v)in enumerate(zip(x,y))if u!=v)
  if part==0:
   for at,(u,v)in enumerate(zip(x[0],y[0])):
    if u!=v:raise AssertionError(('trace',at,repr(u)[:1800],repr(v)[:1800]))
  raise AssertionError(('transfer part',part,repr(x[part])[:2000],repr(y[part])[:2000]))
 coverage=[]
 for p in programs:
  expected={i*4 for i,w in enumerate(p.words)if w!=0x0007000D}
  assert p.seen==expected,('instruction coverage',len(p.seen),len(expected),sorted(expected-p.seen),sorted(p.seen-expected))
  coverage.append(len(p.seen))
 return dict(symbolic_paths=len(a),visited_words=coverage,ordered_public_writes_and_ABI_calls=True,
             full_112_descriptor_bytes=True,full_240_private_frame_bytes=True,ordered_FP_and_FCSR=True,
             quiet_epoch_reads_stable=True,arbitrary_public_and_retained_descriptor_mutations=True,
             saved_ABI_restored=True,nonzero_divisor_normal_execution_only=True,
             raw_fault_register_or_hardware_claim=False)


def negative_controls(raw,retail):
 controls=[]
 def reject(label,bad):
  try:prove(bad,retail)
  except(AssertionError,ValueError,KeyError)as error:
   assert not any(s in str(error).lower()for s in('unsupported','unbounded','out of range')),(label,error)
   controls.append(dict(label=label,reason=repr(error.args)[:240]))
  else:raise AssertionError(('ineffective semantic control',label))
 def word(label,value,mask):
  bad=list(raw);at=bad.index(value);bad[at]^=mask;reject(label,bad)
 word('frame-size',0x27BDFF28,8)
 word('return-home',0xAFBF0044,4)
 word('priority-width',0x30D700FF,128)
 word('allocation-kind',0x24040040,1)
 word('point-buffer-size',0x26310018,12)
 word('packet-copy-width',0x24060050,4)
 word('unsigned-duration',0x004F001B,1)
 word('timer-destination',0xA6480068,2)
 word('descriptor-lifetime',0x240F012C,1)
 word('second-endpoint',0x24020003,1)
 word('second-random-flag',0x24020080,64)
 word('descriptor-physical-home',0x27B50058,4)
 word('loop-bound',0x28610002,1)
 word('saved-register-restore',0x8FB00020,4)
 return dict(effective_semantic_controls=len(controls),controls=controls)
