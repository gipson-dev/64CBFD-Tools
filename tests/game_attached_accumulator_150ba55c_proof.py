"""Complete private projection and an inductive finite-value emitter relation.

The larger source frame has sixteen explicitly untouched source-only bytes.
The source and retail PCs/physical stack addresses are not equated. Ordered
finite arithmetic observations are compared; NaN payloads and raw FCSR flags
are deliberately not abstracted into a claim of hardware status equivalence.
"""
from collections import Counter
import json
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments import game_attached_accumulator_150ba55c_recovery as source
from tools.tests import game_attached_accumulator_150ba55c_oracle as oracle
e=g.e
ENTRY=source.ENTRY
RNG,REAL,TRANSFORM,DIRECTION,SUBMIT=(oracle.RNG,oracle.REAL,oracle.TRANSFORM,oracle.DIRECTION,oracle.SUBMIT)
REGIONS=dict(origin=(-24,12),radius=(-28,4),height=(-32,4),acceleration=(-44,12),position=(-60,12),rotation=(-72,12),velocity=(-84,12))
RAW_ONLY=tuple(range(-100,-84))
def project(off):
 if -280<=off<-100:return off+16
 if -84<=off<-80:return off+80
 if -80<=off<0:return off-4
 if 0<=off<16:return off
 raise AssertionError(('unmapped source byte',off))
MAPPING={i:project(i)for i in range(-280,16)if i not in RAW_ONLY}
assert len(MAPPING)==len(set(MAPPING.values()))==280 and set(MAPPING.values())==set(range(-264,16))
class State(g.State):
 def __init__(self,side):
  super().__init__(side);self.side=side;self.frame_size=280 if side=='raw'else 264;self.shift=4 if side=='raw'else 0
  self.mem={off:('PRIVATE_BYTE',MAPPING[off]if side=='raw'and off not in RAW_ONLY else off)for off in range(-self.frame_size,16)}
  if side=='raw':
   for off in RAW_ONLY:self.mem[off]=('RAW_ONLY',off)
  self.exposed=set();self.r[4]=('RECORD',)
  for name,(off,size)in REGIONS.items():
   for i in range(size):self.mem[off+self.shift+i]=('REGION_BYTE',name,i)
 def canon(self,value):
  if e.tagged(value,'STACK'):
   off=value[1]
   if self.side=='raw':off=project(off)
   return('STACK',off)
  if isinstance(value,tuple):return tuple(self.canon(v)for v in value)
  return value
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -self.frame_size<=off and off+size<=16
   assert not(self.side=='raw'and any(i in RAW_ONLY for i in range(off,off+size))),('source-only access',off,size)
   return g.join([self.mem[off+i]for i in range(size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -self.frame_size<=off and off+size<=16
   assert not(self.side=='raw'and any(i in RAW_ONLY for i in range(off,off+size))),('source-only access',off,size)
   for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def frame(self):
  if self.side=='raw':
   assert all(self.mem[i]==('RAW_ONLY',i)for i in RAW_ONLY),('source-only changed',)
   rows={target:self.canon(self.mem[old])for old,target in MAPPING.items()}
  else:rows=self.mem
  return tuple(rows[i]for i in range(-264,16))
 def region(self,name):
  off,size=REGIONS[name];return tuple(self.mem[off+self.shift+i]for i in range(size))
class Program(g.Program):
 def __init__(self,words,terms,side,commute=True):
  e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set();self.side=side;self.commute=commute;self.commutations=set()
  self.cut=next(i*4 for i,w in enumerate(words)if w>>26==3 and (0x10000000|((w&0x3ffffff)<<2))==RNG)
 def step(self,s,w):
  op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and rs==16 and fn in(0,1,2,3,60):
   args=(s.f[rd],s.f[rt])
   if self.commute and fn in(0,2):
    ordered=tuple(sorted(args,key=repr))
    if args!=ordered:self.commutations.add((fn,args))
    args=ordered
   observation=(rs,fn,args,s.fcsr);s.trace.append(('FP',observation));value=self.terms.term('FP_VALUE',*observation)
   # This proof has a finite-value/opaque FP-control boundary, not FCSR flags.
   if fn==60:s.condition=value
   else:s.f[sa]=value
   return
  return super().step(s,w)
 def call(self,s,target):
  count=oracle.COUNTS[target];args=tuple(s.r[4:4+min(count,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,count-4)))
  names=();pointers=()
  if target==TRANSFORM:
   names=('origin','radius','height');pointers=args[1:]
  elif target==DIRECTION:names=('position',);pointers=args[3:]
  elif target==SUBMIT:names=('position','rotation','velocity','acceleration');pointers=tuple(args[i]for i in(0,1,3,4))
  for name,pointer in zip(names,pointers):assert s.canon(pointer)==('STACK',REGIONS[name][0]),('provider pointer',name,pointer)
  observed=tuple((name,s.region(name))for name in names)if target==SUBMIT else()
  s.trace.append(('CALL',target,tuple(s.canon(a)for a in args),observed,s.fcsr))
  s.trace.append(('PRIVATE_FRAME',s.frame()));ordinal=sum(s.calls.values());s.calls[target]+=1;s.epoch+=1;s.exposed.update(names)
  for name in sorted(s.exposed):
   off,size=REGIONS[name]
   for i in range(size):s.mem[off+s.shift+i]=('PROVIDER_BYTE',ordinal,name,i)
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for i in range(max(4,count)):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  s.r[2]=('RESULT',target,ordinal)
  if target==REAL:s.f[0]=('RESULT_FP',target,ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)
def initial(side,phase,p):
 s=State(side)
 if phase=='prefix':return s
 for w in p.words[:18]:p.step(s,w)
 for i in(1,2,3,*range(4,24),24,25,30,31):s.r[i]=('DEAD_LOOP_GPR',i)
 for i in range(32):s.f[i]=('DEAD_LOOP_FP',i)
 s.r[17]=e.add(('RECORD',),40);s.r[18]=('STACK',-56 if side=='raw'else -60);s.r[19]=('RECORD',);s.r[20]=('CACHED_ACTOR',);s.r[21]=('CACHED_HEADING',);s.r[22]=127;s.r[23]=31
 s.r[30]=0x8009fe40 if side=='raw'else('STACK',-72)
 s.f[24]=0x43b40000;s.f[28]=('CACHED_RANGE',)
 s.f[26 if side=='raw'else 30]=('CACHED_BASE',);s.f[30 if side=='raw'else 26]=0x3f800000
 # This scalar is retained across all providers but never exposed to them.
 s.store(('STACK',-44 if side=='raw'else -48),4,('CACHED_SIZE',))
 s.exposed=set(REGIONS);s.trace=[];s.read_set=Counter();s.facts={};return s
def relation(s,end):
 if end=='return':
  assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
  assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
 else:
  assert s.r[29]==('STACK',-280 if s.side=='raw'else -264)
  assert(s.r[17],s.r[18],s.r[19],s.r[22],s.r[23])==(e.add(('RECORD',),40),('STACK',-56 if s.side=='raw'else -60),('RECORD',),127,31)
  assert s.r[30]==(0x8009fe40 if s.side=='raw'else('STACK',-72))
  assert(s.f[24],s.f[30 if s.side=='raw'else 26])==(0x43b40000,0x3f800000)
 return s.trace,s.read_set,s.frame(),s.divisors,tuple(sorted(s.exposed)),s.r[20]if end!='return'else None,s.r[21]if end!='return'else None,s.f[26 if s.side=='raw'else 30]if end!='return'else None,s.f[28]if end!='return'else None
def prove(raw,retail,commute=True):
 terms=Terms();programs={side:Program(words,terms,side,commute)for side,words in(('raw',raw),('retail',retail))};counts={}
 for phase in('prefix','loop'):
  results={}
  for side,p in programs.items():
   paths=p.paths(0 if phase=='prefix'else p.cut,{p.cut:'loop',-4:'return'},initial(side,phase,p));results[side]={key:relation(value,key[0])for key,value in paths.items()}
  assert results['raw'].keys()==results['retail'].keys(),('predicate keys',phase)
  for key,a in results['raw'].items():
   b=results['retail'][key]
   if a!=b:
    part=next(i for i,(x,y)in enumerate(zip(a,b))if x!=y)
    if part==0:
     at=next((i for i,(x,y)in enumerate(zip(a[0],b[0]))if x!=y),min(len(a[0]),len(b[0])))
     raise AssertionError(('trace',phase,key[0],at,repr(a[0][at:at+1])[:1200],repr(b[0][at:at+1])[:1200]))
    raise AssertionError(('relation',phase,key[0],part,repr(a[part])[:1200],repr(b[part])[:1200]))
  counts[phase]=len(results['raw'])
 return dict(passes=True,paths=counts,mapped_bytes=len(MAPPING),source_only_untouched_bytes=len(RAW_ONLY),coverage={side:dict(visited_words=len(p.seen),unvisited_offsets=[hex(i*4)for i in range(len(p.words))if i*4 not in p.seen])for side,p in programs.items()},finite_commutative_values=commute,ordered_FP_values=True,raw_FCSR_flags_proved=False,termination_claim=False,source_installed=False,c_match_credit=0)
def run(state):
 raw,retail=state['raw_words'],state['retail_words'];report=prove(raw,retail);controls=[]
 for name,old,new in(('identity-offset',0x9298003b,0x9298003a),('ready-offset',0x8e8801d4,0x8e8801d0),('yaw-modulus',0x2416007f,0x2416007e),('accumulator-store',0xe6240008,0xe624000c),('acceleration-y-home',0xe7a800f4,0xe7a800f8)):
  assert raw.count(old)==(2 if name in('ready-offset','accumulator-store')else 1),(name,hex(old))
  bad=[new if w==old else w for w in raw]
  try:prove(bad,retail)
  except AssertionError as error:
   reason=str(error);assert not any(v in reason for v in('unsupported','unbounded proof','escaped code')),('invalid control',name,reason)
   controls.append(dict(name=name,reason=reason[:220]))
  else:raise AssertionError(('ineffective control',name))
 state_only=State('raw')
 try:state_only.store(('STACK',-96),4,0)
 except AssertionError as error:assert'source-only access'in str(error)
 else:raise AssertionError('ineffective source-only write control')
 try:prove(raw,retail,False)
 except AssertionError as error:strict_boundary=str(error)[:500]
 else:strict_boundary=None
 assert strict_boundary is not None
 report.update(effective_controls=controls,source_only_write_control=True,strict_operand_order_rejection=strict_boundary)
 (source.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
