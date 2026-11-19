"""Instruction-driven ordered first-factory relation and explicit full-trace diagnostic.

Contract: mapped/aligned code and ordinary public memory, private frame disjoint
from public memory and literals, o32 providers preserving saved registers. Helpers
can mutate public memory/FCSR and every previously passed private range at later
calls; they cannot inspect unpassed locals, implementation code or return PCs.
Read multisets are compared only inside quiet epochs. Full private-frame, fault,
interrupt, portable-undefined-input and gameplay equivalence are not claimed.
The full trace deliberately reports its remaining trail mismatch rather than
normalizing it. Only the first factory boundary has a positive relation here.
"""
from pathlib import Path
from copy import deepcopy
import json
from tools.tests import game_actor_burst_150bbb5c_prefix_proof as prefix
from tools.tests import game_actor_burst_150bbb5c_oracle as g
from tools.experiments import game_actor_burst_150bbb5c_factory as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
o=source.OUT
e=prefix.e

def interval(value):
 if isinstance(value,int):
  n=((value&0xffffffff)^0x80000000)-0x80000000;return n,n
 if e.tagged(value,'AND')and isinstance(value[2],int)and 0<=value[2]<=0x7fffffff:return 0,value[2]
 if e.tagged(value,'LINEAR'):
  low=high=((value[1]&0xffffffff)^0x80000000)-0x80000000
  for term,coefficient in value[2]:
   bounds=interval(term)
   if bounds is None:return None
   c=((coefficient&0xffffffff)^0x80000000)-0x80000000
   a,b=(c*bounds[0],c*bounds[1]);low+=min(a,b);high+=max(a,b)
  if -0x80000000<=low<=high<=0x7fffffff:return low,high
 return None

def less(a,b):
 x,y=interval(a),interval(b)
 if x is not None and y is not None:
  if x[1]<y[0]:return True
  if x[0]>=y[1]:return False
 return e.pred('SLT',a,b)

class Program(prefix.Program):
 def __init__(self,words,terms,count_pair=None):
  super().__init__(words,terms);self.count_pair=count_pair
 def instruction(self,pc):
  self.current_pc=pc;return super().instruction(pc)
 def step(self,s,w):
  count=len(s.trace)
  if self.count_pair is not None and w>>26==12 and w&65535==3:
   value=s.r[w>>21&31]
   if value in(('RESULT',g.RNG,0),('RESULT',g.RNG,1)):
    s.r[w>>16&31]=self.count_pair[value[2]];s.r[0]=0;return
  # Keep NEG.S as an ordered opaque FP/status event, rather than assuming
  # a bit-level identity for all possible NaN and status inputs.
  if w>>26==17 and w>>21&31==16 and w&63==7:
   observation=(16,7,(s.f[w>>11&31],),s.fcsr)
   s.trace.append(('FP',observation));s.f[w>>6&31]=self.terms.term('FP_VALUE',*observation)
   s.fcsr=self.terms.term('FP_STATUS',*observation)
  else:super().step(s,w)
  for event in s.trace[count:]:s.locations.append((self.current_pc,hex(w)))
 def paths(self,start,stops,initial):
  initial.locations=[]
  states=[(start,initial)];answers={};work=0
  while states:
   pc,s=states.pop();work+=1;s.steps+=1
   assert work<100000 and s.steps<20000,('unbounded relation',start,work,pc)
   if s.steps>1 and pc in stops:
    key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)))
    assert key not in answers,('duplicate relation path',key)
    answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31
   delay=lambda state:self.step(state,self.instruction(pc+4))
   if op in(1,4,5,6,7,20,21,22,23):
    if op==1:
     assert rt in(0,1,2,3),('unsupported REGIMM branch',rt)
     condition=less(s.r[rs],0)
     if rt&1:condition=e.negate(condition)
     likely=bool(rt&2)
    else:
     condition=prefix.base.predicate('EQ',s.r[rs],s.r[rt])if op in(4,5,20,21)else less(0,s.r[rs])
     if op in(5,21,6,22):condition=e.negate(condition)
     likely=op>=20
    for take in e.choices(s,condition):
     n=deepcopy(s);e.assume(n,condition,take)
     if take or not likely:delay(n)
     states.append((pc+4+4*(((w&65535)^32768)-32768)if take else pc+8,n))
   elif op==3:
    s.r[31]=self.entry+pc+8;delay(s)
    self.call(s,((self.entry+pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2));states.append((pc+8,s))
   elif op==0 and w&63==8:
    assert s.r[rs]==('RETURN',);delay(s);states.append((-4,s))
   else:self.step(s,w);states.append((pc+4,s))
  return answers
 def call(self,s,target):
  count=len(s.trace)
  assert target in g.COUNTS,hex(target)
  n=g.COUNTS[target]
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,n-4)))
  packet=()
  if target in(g.COLOR,g.SPRITE,g.FACTORY):
   size=124 if target==g.FACTORY else 168
   address=args[0];assert e.tagged(address,'STACK'),args
   packet=tuple(s.mem[i]for i in range(address[1],address[1]+size))
  if target==g.TRAIL:
   assert all(e.tagged(address,'STACK')for address in args[:2]),args
   packet=tuple(tuple(s.mem[i]for i in range(address[1],address[1]+12))for address in args[:2])
  s.trace.append(('CALL',target,args,packet,s.fcsr))
  ordinal=sum(s.calls.values());s.calls[target]+=1;s.epoch+=1
  if not hasattr(s,'exposed'):s.exposed={}
  if target in(g.COLOR,g.SPRITE,g.FACTORY):
   address=args[0][1];size=124 if target==g.FACTORY else 168
   for i in range(size):s.exposed[address+i]=('descriptor'if target==g.FACTORY else'sprite',i)
  if target==g.TRAIL:
   for address,tag in zip(args[:2],('position','velocity')):
    for i in range(12):s.exposed[address[1]+i]=(tag,i)
  for offset,identity in s.exposed.items():s.mem[offset]=('PROVIDER_BYTE',ordinal,*identity)
  for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
  for i in range(max(4,n)):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  s.r[2]=('RESULT',target,ordinal)
  if target in(g.SINE,g.REAL):s.f[0]=('RESULT_FP',target,ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal)
  s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)
  for event in s.trace[count:]:s.locations.append((self.current_pc,'call'))

def run(raw_path=None,label='first-factory',target=g.FACTORY,count_pair=None):
 terms=Terms();rows={};coverage={}
 for side,name in(('raw','owner.o'),('retail','original.o')):
  path=raw_path if side=='raw'and raw_path is not None else o/name
  words=bound_blob(*payload(path,source.NAME),source.lookup())
  stops={-4:'return'}
  if target is not None:
   jal=0x0C000000|((target>>2)&0x3FFFFFF)
   at=next(i*4 for i,w in enumerate(words)if w==jal);stops[at+8]='after-target'
  program=Program(words,terms,count_pair)
  rows[side]=program.paths(0,stops,prefix.State(side))
  coverage[side]=len(program.seen)
 a,b=rows['raw'],rows['retail'];assert a.keys()==b.keys(),('factory path predicates differ',len(a),len(b))
 differences=[]
 for key in a:
  left,right=a[key],b[key]
  assert left.read_set==right.read_set,('public factory reads',key,left.read_set,right.read_set)
  if key[0]=='return':
   if not left.trace and not right.trace:assert left.r[2]==right.r[2],('factory returned result',left.r[2],right.r[2])
   for state in(left,right):
    assert state.r[29]==('STACK',0)and state.r[31]==('RETURN',)
    assert all(state.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))
    assert state.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
  if left.trace!=right.trace:
   for i in range(max(len(left.trace),len(right.trace))):
    x=left.trace[i]if i<len(left.trace)else None;y=right.trace[i]if i<len(right.trace)else None
    if x!=y:
     differences.append(dict(endpoint=key[0],event=i,raw=repr(x),retail=repr(y),raw_location=left.locations[i],retail_location=right.locations[i]));break
 report=dict(strict_factory_equal=not differences,paths=len(a),covered_words=coverage,first_differences=differences,source_installed=False,c_match_credit=0)
 (o/(label+'-report.json')).write_text(json.dumps(report,indent=2)+'\n')
 (o/(label+'-terms.txt')).write_text('\n'.join(repr(v)+' = '+repr(k)for k,v in terms.values.items())+'\n')
 traces={side:[dict(event=i,location=state.locations[i],value=repr(value))for i,value in enumerate(state.trace)]for side,states in rows.items()for state in [max(states.values(),key=lambda state:len(state.trace))]}
 (o/(label+'-traces.json')).write_text(json.dumps(traces,indent=2)+'\n')
 print(json.dumps(dict(report,first_differences=[dict(d,raw=d['raw'][:500],retail=d['retail'][:500])for d in differences])),flush=True)
 return report
