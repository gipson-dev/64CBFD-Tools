"""Private whole-iteration transfer with two ordered multiply projections.

Not an installed normalizer. The two commuted multiplies are changed only in
this diagnostic input. All remaining scheduling, register, conditional-byte
and private-memory differences must be proved from the actual instructions.
"""
from tools.experiments import game_region_emitter_151a5660_recovery as source
from collections import Counter
from copy import deepcopy
from pathlib import Path
import importlib.util,json,struct,sys
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
O=source.OUT;R=source.ROOT;ENTRY=source.ENTRY
from tools.tests import game_region_emitter_151a5660_prefix_proof as opening
RNG,REAL,TRIG,HEIGHT,SUBMIT=0x150ADA20,0x150ADA68,0x151423D8,0x15046C80,0x15149550
class State(opening.State):
 def __init__(self,side):
  super().__init__(side);self.exposed_packet=True;self.exposed_query=False;self.exact_conversions=Counter()
def signed_interval(v):
 if isinstance(v,int):return ((v^0x80000000)-0x80000000,)*2
 if e.tagged(v,'SIGN16'):return -32768,32767
 if e.tagged(v,'LINEAR'):
  low=high=(v[1]^0x80000000)-0x80000000
  for term,k in v[2]:
   bound=signed_interval(term)
   if bound is None or k not in(1,0xffffffff):return None
   a,b=bound
   if k==1:low+=a;high+=b
   else:low-=b;high-=a
  if -0x80000000<=low<=high<0x80000000:return low,high
 return None
class Program(opening.Program):
 def step(self,s,w):
  op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  interval=signed_interval(s.f[rd])if op==17 and rs==20 and fn==32 else None
  if interval is not None and -(1<<24)<=interval[0]<=interval[1]<=1<<24:
   # Every represented signed integer is exact in binary32 under all rounding
   # modes; CVT.S.W raises no inexact/overflow/underflow/invalid exception.
   # Keep the complete per-epoch operand multiset, while allowing these pure
   # register conversions to commute. Fault/trap-state parity is not claimed.
   value=s.f[rd];s.exact_conversions[s.epoch,value]+=1;s.f[sa]=self.terms.term('EXACT_INTEGER_FLOAT',value)
  elif op==17 and rs==2:
   assert rd==31;s.r[rt]=s.fcsr;s.trace.append(('CFC1',s.fcsr))
  elif op==17 and rs==6:
   assert rd==31;s.trace.append(('CTC1',s.r[rt]));s.fcsr=s.r[rt]
  elif op==17 and rs==16 and fn==36:
   observation=(rs,fn,(s.f[rd],),s.fcsr);s.trace.append(('FP',observation))
   s.f[sa]=self.terms.term('FP_VALUE',*observation);s.fcsr=self.terms.term('FP_STATUS',*observation)
  elif op==0 and fn==27:
   a,b=s.r[rs],s.r[rt];s.divisors.add(b);e.assume(s,e.pred('EQ',b,0),False)
   s.hi=('UREM',a,b);s.lo=('UDIV',a,b)
  else:super().step(s,w)
 def call(self,s,target):
  assert target in(RNG,REAL,TRIG,HEIGHT,SUBMIT),hex(target)
  count={RNG:0,REAL:0,TRIG:1,HEIGHT:4,SUBMIT:6}[target]
  args=tuple(s.r[4:4+min(count,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,count-4)))
  assert s.r[29]==('STACK',-264)
  observed=()
  if target==HEIGHT:
   assert args[0]==('STACK',-156)and args[1]==0 and args[3]==e.add(('OWNER',),112),('height ABI',args)
   observed=tuple(s.load(('STACK',off),1)for off in range(-156,-144));s.exposed_query=True
  elif target==SUBMIT:
   assert args[0]==('STACK',-76)and args[1:4]==(10,0,0),('submit ABI',args)
   observed=tuple(s.load(('STACK',off),1)for off in range(-76,-4))
  else:
   for v in args:e.plain(v)
  ordinal=sum(s.calls.values());s.calls[target]+=1
  s.trace.append(('CALL',target,args,observed,s.fcsr));s.trace.append(('PRIVATE_FRAME',s.frame()));s.epoch+=1
  for begin,end,active in((-76,-4,s.exposed_packet),(-156,-144,s.exposed_query)):
   if active:
    for off in range(begin,end):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for i in range(max(4,count)):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  s.r[2]=('RESULT',target,ordinal)
  if target==HEIGHT:s.r[2]=e.bitop('AND',s.r[2],1) # verified complete original return chain
  if target in(REAL,TRIG):s.f[0]=('RESULT_FP',target,ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)
 def paths(self,start,stops,initial):
  active=[(start,initial)];answers={};work=0
  while active:
   pc,s=active.pop();work+=1;s.steps+=1;assert work<200000 and s.steps<1700,('unbounded transfer',work,hex(pc))
   if s.steps>1 and pc in stops:
    key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)));assert key not in answers,('duplicate path',key)
    answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31
   if op in(1,4,5,6,7,20,21,22,23)or op==17 and rs==8:
    if op==17:
     p=s.condition;assert p is not None;likely=bool(rt&2);p=p if rt&1 else e.negate(p)
    elif op==1:
     assert rt in(0,1,2,3);p=e.pred('SLT',s.r[rs],0);p=e.negate(p)if rt&1 else p;likely=bool(rt&2)
    else:
     p=g.predicate('EQ',s.r[rs],s.r[rt])if op in(4,5,20,21)else g.predicate('SLT',0,s.r[rs]);likely=op>=20
     if op in(5,21,6,22):p=e.negate(p)
    for take in e.choices(s,p):
     n=deepcopy(s);e.assume(n,p,take)
     if take or not likely:self.step(n,self.instruction(pc+4))
     active.append((pc+4+4*(((w&65535)^32768)-32768)if take else pc+8,n))
   elif op==3:
    s.r[31]=self.entry+pc+8;self.step(s,self.instruction(pc+4));self.call(s,((self.entry+pc+4)&0xf0000000)|((w&0x3ffffff)<<2));active.append((pc+8,s))
   elif op==0 and w&63==8:
    assert s.r[rs]==('RETURN',);self.step(s,self.instruction(pc+4));active.append((-4,s))
   elif op==0 and w&63==13:raise AssertionError(('BREAK in defined transfer domain',hex(pc)))
   else:self.step(s,w);active.append((pc+4,s))
  return answers
def initial(side,p):
 s=State(side)
 for w in p.words[:11]:p.step(s,w)
 for off in range(-264,0):s.mem.setdefault(off,('LOOP_PRIVATE_BYTE',off))
 for reg in(1,3,*range(4,16),17,24,25,31):s.r[reg]=('DEAD_LOOP_GPR',reg)
 for reg in range(20,28):s.f[reg]=('DEAD_LOOP_FP',reg)
 s.r[16]=e.add(('OWNER',),40);s.r[18]=('OWNER',);s.r[2]=s.load(e.add(('OWNER',),40),4)
 s.f[28]=0x3F800000;s.trace=[];s.read_set=Counter();return s
def relation(s,end):
 if end=='return':
  assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
  assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))
  assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
 else:
  assert s.r[29]==('STACK',-264)and s.r[16]==e.add(('OWNER',),40)and s.r[18]==('OWNER',)and s.f[28]==0x3F800000
  assert s.r[2]==s.load(e.add(('OWNER',),40),4),('loop source reload',s.side,s.r[2])
  for reg,at in ((16,-192),(17,-188),(18,-184)):
   assert s.load(('STACK',at),4)==('ENTRY',reg),('inductive saved GPR',reg)
  assert s.load(('STACK',-180),4)==('RETURN',)
  for reg in range(20,30):assert s.load(('STACK',-232+4*(reg-20)),4)==('ENTRY_FP',reg),('inductive saved FP',reg)
 return s.trace,s.read_set,s.fcsr,s.frame(),s.divisors,s.exact_conversions
def prove(raw,retail):
 terms=Terms();programs={side:Program(words,terms)for side,words in [('raw',raw),('retail',retail)]};values={}
 for side,p in programs.items():
  states=p.paths(0x10C,{0x10C:'loop',-4:'return'},initial(side,p));values[side]={key:relation(s,key[0])for key,s in states.items()}
 assert values['raw'].keys()==values['retail'].keys(),('iteration predicates',len(values['raw']),len(values['retail']),repr(next(iter(values['raw'].keys()-values['retail'].keys()),None))[:3000],repr(next(iter(values['retail'].keys()-values['raw'].keys()),None))[:3000])
 for key,left in values['raw'].items():
  right=values['retail'][key]
  if left!=right:
   part=next(i for i,(a,b)in enumerate(zip(left,right))if a!=b)
   if part==0:
    at=next((i for i,(a,b)in enumerate(zip(left[0],right[0]))if a!=b),None)
    raise AssertionError(('iteration event',key[0],at,repr(left[0][at]if at is not None else left[0])[:2500],repr(right[0][at]if at is not None else right[0])[:2500]))
   raise AssertionError(('iteration part',key[0],part,repr(left[part])[:2500],repr(right[part])[:2500]))
 return dict(paths=len(values['raw']),coverage={side:dict(visited_words=len(p.seen),unvisited_offsets=[hex(off)for off in range(0x10C,0x64C,4)if off not in p.seen])for side,p in programs.items()},ordered_effectful_FP_and_FCSR=True,exact_bounded_integer_conversions_compared_by_epoch_multiset=True,full_private_frame_at_providers_and_exit=True,all_public_aliases=True,retained_packet_and_query_mutable_by_providers=True,normal_nonzero_unsigned_division=True,whole_iteration=True)
def main():
 assert json.loads((O/'height-return-range.json').read_text())['byte_narrowing_lossless']
 label='qualified';dest=O/('iteration-proof-'+label+'-inductive.json');assert not dest.exists()
 raw,refs=payload(O/(label+'.o'),'func_151A5660');symbols={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())}
 actual=bound_blob(raw,refs,symbols);unprojected=actual[:];retail=list(struct.unpack('>403I',(O/'retail.bin').read_bytes()));guards=[]
 for off in(0x264,0x298):
  old,new=actual[off//4],retail[off//4]
  assert old>>26==new>>26==17 and old&63==new&63==2 and old>>21&31==new>>21&31==16
  assert old>>6&31==new>>6&31 and old>>11&31==new>>16&31 and old>>16&31==new>>11&31
  guards.append(dict(offset=hex(off),expected=hex(old),replacement=hex(new)));actual[off//4]=new
 report=prove(actual,retail);controls=[]
 variants=[('unprojected-ordered-multiplies',unprojected)]
 for name,off,old,new in [('outer-fallback-coordinate',0x4B8,0xE7B400C0,0xE7B400C4),('height-byte-mask',0x498,0x304F00FF,0x304F0000),('loop-subtract',0x604,0x461C3481,0x461C3480),('lifetime-divisor',0x544,0x27190001,0x27190002)]:
  bad=actual[:];assert bad[off//4]==old,(name,hex(bad[off//4]),hex(old));bad[off//4]=new;variants.append((name,bad))
 for name,bad in variants:
  try:prove(bad,retail)
  except(AssertionError,ValueError):controls.append(name)
  else:raise AssertionError(('ineffective iteration control',name))
 def rename(w):
  op,fn,fmt=w>>26,w&63,w>>21&31
  if op==0:fields=(16,11)if fn in(0,2,3)else(21,)if fn==8 else(11,)if fn in(16,18)else(21,16)if fn in(24,25,26,27)else(21,16,11)
  elif op in(2,3):fields=()
  elif op==17:fields=(16,)if fmt in(0,2,4,6)else()
  elif op in(1,6,7,22,23,49,53,57,61):fields=(21,)
  elif op==15:fields=(16,)
  else:fields=(21,16)
  for shift in fields:
   reg=w>>shift&31
   if reg in(24,25):w=(w&~(31<<shift))|((49-reg)<<shift)
  return w
 alternate=prove([rename(w)for w in actual],retail)
 assert alternate['paths']==report['paths']
 report.update(two_ordered_multiply_projections=guards,effective_controls=controls,positive_T8_T9_reallocation_paths=alternate['paths'],source_installed=source.installed(),c_match_credit=0)
 dest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
