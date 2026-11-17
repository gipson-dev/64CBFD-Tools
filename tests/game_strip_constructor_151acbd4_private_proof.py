"""Complete instruction-driven relation under fresh, disjoint allocator objects.

No public fault-order or overlapping allocator-object claim. Every initialized
public/private byte is observed at providers and return. Providers may replace
all public object bytes; caller register/FCSR clobbers remain arbitrary.
"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_strip_constructor_151acbd4_private_recovery as source
R,P,ENTRY=source.ROOT,source.OUT,source.ENTRY;e=g.e
SYMS={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())}
CREATE,ALLOC,COPY=SYMS['func_15167A68'],SYMS['allocate_memory'],SYMS['memcpy']
RECORD,DESC,POINTS,VERTICES=('RECORD',),('DESC',),('POINTS',),('VERTICES',)
CATEGORY,TABLE=0x800BE9F0,0x80090B60
REGIONS=((RECORD,88),(DESC,36),(POINTS,480),(VERTICES,2560),(TABLE,768),(CATEGORY,4))
def predicate(op,a,b):
 if op=='EQ'and((a in(RECORD,DESC,POINTS,VERTICES)and b==0)or(b in(RECORD,DESC,POINTS,VERTICES)and a==0)):return False
 return g.predicate(op,a,b)
class State(g.State):
 def __init__(self,side,outcome):
  super().__init__(side);self.outcome=outcome;self.r[4]=DESC;self.r[5]=('EXTRA',);self.mem={};self.public={}
  for off in range(-64,16):self.mem[off]=('PRIVATE_BYTE',off)
  self.allocations=0
 def load(self,at,size,pool=b''):
  assert size in(1,2,4)
  if e.tagged(at,'STACK'):
   off=at[1];assert off%size==0 and -64<=off and off+size<=16,('private load',off,size)
   return g.join([self.mem[off+i]for i in range(size)])
  value=g.join([self.public.get(e.add(at,i),('PUBLIC_BYTE',e.add(at,i)))for i in range(size)])
  self.read_set[at,size,value]+=1;return value
 def store(self,at,size,value):
  assert size in(1,2,4)
  if e.tagged(at,'STACK'):
   off=at[1];assert off%size==0 and -64<=off and off+size<=16,('private store',off,size)
   for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
  else:
   assert not e.has_tag(at,'STACK')and not e.has_tag(value,'STACK')
   for i in range(size):self.public[e.add(at,i)]=g.byte(value,8*(size-i-1))
 def frame(self):return tuple(self.mem[i]for i in range(-64,16))
 def objects(self):
  return tuple((root,tuple(self.public.get(e.add(root,i),('PUBLIC_BYTE',e.add(root,i)))for i in range(size)))for root,size in REGIONS)
class Program(g.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  count={CREATE:6,ALLOC:4,COPY:3}[target]
  args=tuple(s.r[4:4+min(count,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,count-4)))
  s.trace.append(('CALL',target,args,s.fcsr));s.trace.append(('PUBLIC',s.objects()));s.trace.append(('PRIVATE',s.frame()))
  ordinal=sum(s.calls.values());s.calls[target]+=1
  if target==COPY:
   assert args==(e.add(RECORD,16),DESC,36)
   for i in range(36):s.public[e.add(RECORD,16+i)]=s.load(e.add(DESC,i),1)
   answer=args[0]
  else:
   # These are the fresh allocator-owned objects and known static globals,
   # deliberately disjoint from each other and the caller's descriptor/frame.
   # Arbitrary provider byte updates preserve no assumed input constants.
   for root,size in REGIONS:
    for i in range(size):s.public[e.add(root,i)]=('PROVIDER_BYTE',ordinal,root,i)
   if target==CREATE:answer=RECORD if s.outcome else 0
   else:
    assert args in((480,1,0,0),(2560,1,2,0)),('allocator ABI',args)
    answer=POINTS if s.allocations==0 else VERTICES;s.allocations+=1
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for i in range(max(4,count)):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  s.r[2]=answer;s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)
 def paths(self,start,stops,initial):
  active=[(start,initial)];answers={};work=0
  while active:
   pc,s=active.pop();work+=1;s.steps+=1;assert work<1000000 and s.steps<20000,('unbounded proof',work,hex(pc))
   if s.steps>1 and pc in stops:
    key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)));assert key not in answers;answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31
   if op in(1,4,5,6,7,20,21,22,23)or op==17 and rs==8:
    if op==17:p=s.condition;assert p is not None;likely=bool(rt&2);p=p if rt&1 else e.negate(p)
    elif op==1:assert rt in(0,1,2,3);p=predicate('SLT',s.r[rs],0);p=e.negate(p)if rt&1 else p;likely=bool(rt&2)
    else:
     p=predicate('EQ',s.r[rs],s.r[rt])if op in(4,5,20,21)else predicate('SLT',0,s.r[rs]);likely=op>=20
     if op in(5,21,6,22):p=e.negate(p)
    for take in e.choices(s,p):
     n=deepcopy(s);e.assume(n,p,take)
     if take or not likely:self.step(n,self.instruction(pc+4))
     active.append((pc+4+4*(((w&65535)^32768)-32768)if take else pc+8,n))
   elif op==3:
    s.r[31]=ENTRY+pc+8;self.step(s,self.instruction(pc+4));self.call(s,((ENTRY+pc+4)&0xf0000000)|((w&0x3ffffff)<<2));active.append((pc+8,s))
   elif op==0 and w&63==8:
    assert s.r[rs]==('RETURN',);self.step(s,self.instruction(pc+4));active.append((-4,s))
   elif op==0 and w&63==13:raise AssertionError(('normal domain BREAK',hex(pc)))
   else:self.step(s,w);active.append((pc+4,s))
  return answers
def words(label):
 if label=='retail':return list(struct.unpack('>360I',(P/'retail.bin').read_bytes()))
 raw,refs=payload(P/(label+'.o'),'func_151ACBD4');return bound_blob(raw,refs,SYMS)
def run(code,side,terms,outcome,cut=None):
 p=Program(code,terms);stops={-4:'return'}
 if cut is not None:
  sites=[i*4 for i,w in enumerate(code)if w>>26==3];stops[sites[cut]]='before-call-'+str(cut)
 paths=p.paths(0,stops,State(side,outcome));result={}
 for key,s in paths.items():
  if key[0]=='return':
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
  result[key]=(s.trace,s.objects(),s.frame(),s.read_set,s.fcsr,s.r[2]if key[0]=='return'else None)
 return result,p.seen
def compare(label,cut=None,code=None):
 terms=Terms();fail=[];count=0;coverage={}
 for outcome in(0,1):
  a,seen=run(words(label)if code is None else code,'raw',terms,outcome,cut);b,original=run(words('retail'),'retail',terms,outcome,cut)
  assert a.keys()==b.keys(),('predicates',label,outcome,len(a),len(b));coverage[outcome]=(len(seen),len(original));count+=len(a)
  for key,left in a.items():
   right=b[key]
   if left!=right:
    part=next(i for i,(x,y)in enumerate(zip(left,right))if x!=y);detail=None
    if part==0:
     at=next((i for i,(x,y)in enumerate(zip(left[0],right[0]))if x!=y),min(len(left[0]),len(right[0])));detail=(at,repr(left[0][at:at+1])[:500],repr(right[0][at:at+1])[:500])
    fail.append(dict(outcome=outcome,end=key[0],part=part,detail=detail))
 return dict(label=label,cut=cut,paths=count,equal_paths=count-len(fail),coverage=coverage,failures=fail)
def main():
 raw=words('v7');opening=compare('v7',2);assert opening['paths']==opening['equal_paths']==4
 controls=[]
 for label,old,new in [('factory-size',0x26060058,0x26060054),('copied-length',0x24060024,0x24060020),('reciprocal-operation',0x46062203,0x46062202),('state-clear-offset',0xac600044,0xac600048)]:
  bad=raw[:];assert bad.count(old)==1,(label,hex(old));bad[bad.index(old)]=new
  try:r=compare(label,2,bad)
  except AssertionError as error:
   reason=str(error);assert not any(s in reason for s in('unsupported','unbounded proof','escaped code')),('invalid control',label,reason)
  else:assert r['equal_paths']<r['paths'],('ineffective control',label)
  controls.append(label)
 frontier=compare('v7',3);assert frontier['paths']==4 and frontier['equal_paths']==2
 assert all(row['part']==0 and row['detail'][0]==12 for row in frontier['failures'])
 adjusted=raw[:];moves=[]
 for a,b,wa,wb in((0xf0,0xfc,0x4600540d,0x4600320d),(0x100,0x10c,0x440d8000,0x44054000)):
  assert adjusted[a//4]==wa and adjusted[b//4]==wb
  adjusted[a//4],adjusted[b//4]=wb,wa;moves.extend([dict(offset=hex(a),expected=hex(wa),replacement=hex(wb)),dict(offset=hex(b),expected=hex(wb),replacement=hex(wa))])
 second=compare('four-word-schedule-diagnostic',3,adjusted);assert second['paths']==4 and second['equal_paths']==2
 assert all(row['part']==0 and row['detail'][0]==36 for row in second['failures'])
 report=dict(opening=opening,effective_opening_controls=controls,unadjusted_prefix_frontier=frontier,explicit_diagnostic_words=moves,next_spacing_conversion_frontier=second,
  whole_function_proved=False,all_private_bytes_compared_at_opening_providers=True,FP_status_boundary_open=True,fresh_disjoint_allocator_objects=True,source_installed=False,c_match_credit=0)
 (P/'prefix-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(opening_paths=4,opening_equal=4,effective_controls=4,whole_function_proved=False,c_match_credit=0)),flush=True)
if __name__=='__main__':main()
