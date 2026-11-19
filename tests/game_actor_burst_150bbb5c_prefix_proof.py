"""Locate the first strict FP/packet divergence before the first sprite call."""
from pathlib import Path
from copy import deepcopy
import json
from tools.tests import game_growth_curve_151a1fb4_proof as base
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests.game_actor_burst_150bbb5c_oracle import COLOR,RNG,SINE
from tools.experiments import game_actor_burst_150bbb5c_ordered as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
e=base.e;P=source.OUT

class State(base.State):
 def __init__(self,side):
  super().__init__(side);self.mem={i:('PRIVATE_BYTE',i)for i in range(-624,0)}
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   at=address[1];assert at%size==0 and -624<=at and at+size<=0,('stack read',at,size)
   return base.join([self.mem[i]for i in range(at,at+size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   at=address[1];assert at%size==0 and -624<=at and at+size<=0,('stack write',at,size)
   for i in range(size):self.mem[at+i]=base.byte(value,8*(size-i-1))
  else:super().store(address,size,value)

class Program(base.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',source.ENTRY);self.terms=terms;self.seen=set()
 def paths(self,start,stops,initial):
  states=[(start,initial)];answers={};work=0
  while states:
   pc,s=states.pop();work+=1;s.steps+=1
   assert work<100000 and s.steps<1500,('unbounded prefix',start,work,pc)
   if s.steps>1 and pc in stops:
    key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)))
    assert key not in answers,('duplicate prefix path',key)
    answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31
   delay=lambda state:self.step(state,self.instruction(pc+4))
   if op in(1,4,5,6,7,20,21,22,23):
    if op==1:
     assert rt in(0,1,2,3),('unsupported REGIMM branch',rt)
     value=s.r[rs]
     # A word masked below bit31 is nonnegative in the signed comparison.
     nonnegative=e.tagged(value,'AND')and isinstance(value[2],int)and value[2]<=0x7FFFFFFF
     condition=False if nonnegative else e.pred('SLT',value,0)
     if rt&1:condition=e.negate(condition)
     likely=bool(rt&2)
    else:
     condition=base.predicate('EQ',s.r[rs],s.r[rt])if op in(4,5,20,21)else base.predicate('SLT',0,s.r[rs])
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
  assert target in(RNG,SINE,COLOR),hex(target)
  n={RNG:0,SINE:1,COLOR:5}[target]
  args=tuple(s.r[4:4+min(4,n)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,n-4)))
  packet=()
  if target==COLOR:
   assert args[0]==('STACK',-296),args
   packet=tuple(s.mem[i]for i in range(-296,-128))
  s.trace.append(('CALL',target,args,packet,s.fcsr))
  ordinal=sum(s.calls.values());s.calls[target]+=1;s.epoch+=1
  for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
  for i in range(max(4,n)):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  s.r[2]=('RESULT',target,ordinal)
  if target==SINE:s.f[0]=('RESULT_FP',target,ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal)
  s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)

def run(raw_path=None,label='strict-prefix'):
 terms=Terms();rows={};coverage={};jal=0x0C000000|((COLOR>>2)&0x3FFFFFF)
 for side,name in (('raw','owner.o'),('retail','original.o')):
  path=raw_path if side=='raw' and raw_path is not None else source.OUT/name
  words=bound_blob(*payload(path,source.NAME),source.lookup())
  at=next(i*4 for i,w in enumerate(words) if w==jal);program=Program(words,terms)
  rows[side]=program.paths(0,{-4:'return',at+8:'after-color'},State(side));coverage[side]=len(program.seen)
 a,b=rows['raw'],rows['retail'];assert a.keys()==b.keys(),('prefix path predicates differ',len(a),len(b))
 differences=[]
 for key in a:
  left,right=a[key],b[key]
  assert left.read_set==right.read_set,('public prefix reads',key,left.read_set,right.read_set)
  if key[0]=='return':
   assert left.r[2]==right.r[2],('prefix returned result',left.r[2],right.r[2])
   assert left.r[29]==right.r[29]==('STACK',0),('prefix returned stack',left.r[29],right.r[29])
   for state in(left,right):
    assert state.r[31]==('RETURN',)
    assert all(state.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))
    assert state.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
  if left.trace!=right.trace:
   i=next(i for i,(x,y)in enumerate(zip(left.trace,right.trace)) if x!=y)
   differences.append(dict(endpoint=key[0],trace_index=i,raw=repr(left.trace[i])[:1000],retail=repr(right.trace[i])[:1000]))
 reverse={value:key for key,value in terms.values.items()}
 report=dict(strict_prefix_equal=not differences,paths=len(a),covered_words=coverage,
    first_differences=differences,raw_normalizer_derived=False,source_installed=False,c_match_credit=0)
 (P/(label+'-report.json')).write_text(json.dumps(report,indent=2)+'\n')
 (P/(label+'-terms.txt')).write_text('\n'.join(repr(key)+' = '+repr(value)for key,value in reverse.items())+'\n')
 print(json.dumps(report),flush=True)
 return report
