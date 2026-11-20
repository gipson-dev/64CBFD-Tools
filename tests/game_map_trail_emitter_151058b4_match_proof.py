"""Loop-inductive normal-execution relation, independent of the normalizer.

Ordinary nonfaulting public memory is stable within each quiet epoch. Every
call or public store advances that epoch, allowing arbitrary provider writes
and public aliases. All FP/FCSR operations stay ordered. Only the unused raw
frame gap is absent from the entry-byte relation; passed object bytes retain
literal physical homes. Providers cannot inspect PCs or unpassed locals.
"""
from pathlib import Path
from collections import Counter
import json
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
e=g.e
ENTRY=0x151058B4
REAL,INTEGER,CHECK,SAMPLE,DIRECTION,SPAWN=0x150ADA68,0x150ADA20,0x151464B8,0x151432BC,0x15143794,0x1515C2F0
LOOP=0x1A8
def canonical(offset,raw):
 if raw:
  if -128<=offset<-120:raise AssertionError(('source-only gap accessed',offset))
  if -248<=offset<-128:return offset+8
 return offset
class State(g.State):
 def __init__(self,raw):
  super().__init__('raw'if raw else'retail');self.raw=raw;self.frame_bytes=248 if raw else 240
  self.mem={off:('PRIVATE_ENTRY',off)for off in range(-240,24)};self.exposed=set();self.accessed=set()
 def address(self,v):return('STACK',canonical(v[1],self.raw))if e.tagged(v,'STACK')else v
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -self.frame_bytes<=off and off+size<=24,('private read bound',off,size)
   self.accessed.update(range(off,off+size));return g.join([self.mem[canonical(off+i,self.raw)]for i in range(size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -self.frame_bytes<=off and off+size<=24,('private write bound',off,size)
   self.accessed.update(range(off,off+size))
   for i in range(size):self.mem[canonical(off+i,self.raw)]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def frame(self):return tuple(self.mem[off]for off in range(-240,24))
class Program(g.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  n={REAL:0,INTEGER:0,CHECK:1,SAMPLE:5,DIRECTION:4,SPAWN:6}[target]
  assert s.r[29]==('STACK',-s.frame_bytes)
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,n-4)))
  passed=tuple(s.address(a)for a in args);ordinal=sum(s.calls.values());s.calls[target]+=1;observed=()
  if target==SAMPLE:
   e.plain(passed[0]);assert passed[1:]==tuple(('STACK',i)for i in(-36,-28,-100,-104))
   for start in(-36,-28,-100,-104):s.exposed.update(range(start,start+4))
  elif target==DIRECTION:
   assert passed[3]==('STACK',-92);s.exposed.update(range(-92,-80))
  elif target==SPAWN:
   assert passed[:4]==(('STACK',-36),0,('STACK',-96),0)
   observed=(tuple(s.mem[i]for i in range(-36,-12)),tuple(s.mem[i]for i in range(-96,-36)))
   s.exposed.update(range(-96,-12))
  s.trace.append(('CALL',target,passed,observed,s.fcsr));s.trace.append(('FRAME',s.frame()));s.epoch+=1
  for off in s.exposed:s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for i in range(max(4,n)):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  s.r[2]=('RESULT',target,ordinal)
  if target==REAL:s.f[0]=('FLOAT_RESULT',ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)
def initial(raw,phase,program):
 s=State(raw)
 if phase=='prefix':return s
 for word in program.words[:18]:program.step(s,word)
 side='raw'if raw else'retail'
 for reg in(1,2,3,*range(4,28),30,31):s.r[reg]=('DEAD_ITERATION_GPR',side,reg)
 for reg in range(32):s.f[reg]=('DEAD_ITERATION_FP',side,reg)
 s.r[19]=('RECORD',);s.r[20]=e.add(('RECORD',),40);s.r[21]=101
 for reg,off in((18,-36),(22,-28),(23,-100),(30,-104)):s.r[reg]=('STACK',off)
 s.f[20]=('ITERATION_REMAINING',);s.f[22]=0x3F800000;s.f[24]=('CACHED_SCALE',);s.f[26]=('CACHED_BASE',);s.f[28]=0x41A00000;s.f[30]=0x41F00000
 for off in range(-104,-12):s.mem[off]=('ITERATION_PRIVATE_BYTE',off)
 s.exposed=set(range(-104,-12));s.trace=[];s.read_set=Counter();s.facts={};s.fcsr=('ITERATION_FCSR',);s.epoch=0
 return s
def observe(s,end):
 if end=='return':
  assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
  assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
  live=()
 else:
  assert s.r[29]==('STACK',-s.frame_bytes)
  assert(s.r[19],s.r[20],s.r[21])==(('RECORD',),e.add(('RECORD',),40),101)
  assert tuple(s.r[i]for i in(18,22,23,30))==tuple(('STACK',off)for off in(-36,-28,-100,-104))
  assert s.f[22]==0x3F800000 and s.f[28]==0x41A00000 and s.f[30]==0x41F00000
  assert s.r[28]==('ENTRY',28)
  for reg,off in[(i,0x50+4*(i-16))for i in range(16,24)]+[(30,0x70),(31,0x74)]:
   assert s.load(e.add(s.r[29],off),4)==(('RETURN',)if reg==31 else('ENTRY',reg)),('saved GPR',reg)
  for reg in range(20,32):assert s.load(e.add(s.r[29],0x20+4*(reg-20)),4)==('ENTRY_FP',reg),('saved FPR',reg)
  live=(s.f[20],s.f[24],s.f[26])
 assert not s.raw or not set(range(-128,-120))&s.accessed
 return(s.trace,s.read_set,s.divisors,s.fcsr,s.frame(),live)
def prove(raw,retail):
 assert len(raw)==len(retail)==197
 assert raw[0x1C4//4]==retail[0x1C4//4]==0x0007000D,('dead BREAK changed',)
 terms=Terms();programs=[Program(raw,terms),Program(retail,terms)];report={}
 for phase in('prefix','loop'):
  answers=[];steps=[]
  for side,p in enumerate(programs):
   paths=p.paths(0 if phase=='prefix'else LOOP,{LOOP:'loop',-4:'return'},initial(side==0,phase,p))
   answers.append({key:observe(s,key[0])for key,s in paths.items()});steps.append(max(s.steps for s in paths.values()))
  a,b=answers;assert a.keys()==b.keys(),('path predicates',phase,len(a),len(b))
  for key,x in a.items():
   y=b[key]
   if x!=y:
    part=next(i for i,(left,right)in enumerate(zip(x,y))if left!=right)
    if part==0:
     at=next((i for i,(left,right)in enumerate(zip(x[0],y[0]))if left!=right),None)
     raise AssertionError(('transfer trace',phase,key,at,repr(x[0][at]if at is not None else x[0])[:2200],repr(y[0][at]if at is not None else y[0])[:2200]))
    if part==4:
     at=next(i for i,(left,right)in enumerate(zip(x[part],y[part]))if left!=right);raise AssertionError(('private byte',phase,at-240,x[part][at],y[part][at]))
    raise AssertionError(('transfer part',phase,part,repr(x[part])[:1800],repr(y[part])[:1800]))
  report[phase]=dict(paths=len(a),max_steps=steps)
 for p in programs:assert p.seen==set(range(0,788,4))-{0x1C4},('instruction coverage',len(p.seen),sorted(set(range(0,788,4))-p.seen))
 return dict(phases=report,visited_words=[len(p.seen)for p in programs],private_incoming_bytes=264,source_gap_bytes=8,source_gap_accesses=0,full_header_bytes=24,full_packet_bytes=60,passed_physical_homes_identical=True,all_FP_and_FCSR_operations_ordered=True,ordinary_public_reads_stable_per_quiet_epoch=True,arbitrary_public_and_retained_private_provider_mutations=True,normal_execution_only=True,raw_fault_or_hardware_acceptance_not_claimed=True)

def negative_controls(raw,retail):
 """Mutate live semantics, ABI custody and the frame correspondence separately."""
 controls=[]
 def reject(label,bad):
  try:prove(bad,retail)
  except(AssertionError,ValueError,KeyError)as error:
   message=str(error).lower()
   assert not any(v in message for v in('unsupported','unbounded','out of range')),(label,error)
   controls.append(dict(label=label,reason=repr(error.args)[:400]))
  else:raise AssertionError(('ineffective proof control',label))
 def word(label,value,mask):
  bad=raw[:];at=bad.index(value);bad[at]^=mask;reject(label,bad)
 word('frame-size',0x27BDFF08,8)
 word('saved-return-home',0xAFBF0074,4)
 word('duration-divisor',0x2401001F,1)
 word('byte-modulus',0x24150065,1)
 word('signed-source-height',0x87190002,0x10000000)
 word('channel-source',0x9268000C,1)
 word('direction-radius-FP-order',0x461C0482,0x001CE000)
 word('loop-decrement',0x4616A501,0x00000800)
 word('dead-BREAK',0x0007000D,0x00010000)
 at=next(i for i,w in enumerate(raw)if w>>26==9 and w>>21&31==29 and w>>16&31==7)
 for label,off in(('direction-private-home',0x98),('source-gap-access',0x78)):
  bad=raw[:];bad[at]=(bad[at]&0xFFFF0000)|off;reject(label,bad)
 bad=raw[:];bad[0]=retail[0];bad[-1]=retail[-1];reject('frame-only-without-local-operands',bad)
 bad=raw[:];bad[0xB4//4],bad[0x17C//4]=bad[0x17C//4],bad[0xB4//4];reject('partial-initializer-permutation',bad)
 return dict(effective_negatives=len(controls),controls=controls)
