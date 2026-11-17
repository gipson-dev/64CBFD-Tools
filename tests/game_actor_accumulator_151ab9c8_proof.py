"""Instruction-driven normal-execution relation; raw private layout is explicit.

The candidate's exposed arrays, surface and flag sit four bytes above retail.
Unpassed private homes are implementation storage, not observable C output.
No code words, FP operands or public accesses are projected by this proof.
"""
from pathlib import Path
from collections import Counter
import json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_actor_accumulator_151ab9c8_recovery as source
R,P,ENTRY=source.ROOT,source.OUT,source.ENTRY
e=g.e
RNG,REAL,ANGLE,HEIGHT,EMIT=0x150ADA20,0x150ADA68,0x151423D8,0x1504715C,0x151D9014
REGIONS={'velocity':(-68,12),'position':(-56,12),'surface':(-44,36)}
class State(g.State):
 def __init__(self,side):
  super().__init__(side);self.shift=4 if side=='raw'else 0
  self.mem={off:('PRIVATE_BYTE',off)for off in range(-280,16)};self.exposed=set();self.r[4]=('RECORD',)
  for name,(off,size)in REGIONS.items():
   for i in range(size):self.mem[off+self.shift+i]=('REGION_BYTE',name,i)
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -280<=off and off+size<=16,('private load',off,size)
   return g.join([self.mem[off+i]for i in range(size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -280<=off and off+size<=16,('private store',off,size)
   for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def canonical(self,v):
  if e.tagged(v,'STACK'):
   for name,(off,size)in REGIONS.items():
    if v[1]==off+self.shift:return('REGION',name)
   raise AssertionError(('unrecognized exposed pointer',v))
  return v
 def region(self,name):
  off,size=REGIONS[name];return tuple(self.mem[off+self.shift+i]for i in range(size))
class Program(g.Program):
 def __init__(self,words,terms,side):
  e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set();self.side=side
  self.cut=next(i*4 for i,w in enumerate(words)if w>>26==3 and (0x10000000|((w&0x3ffffff)<<2))==RNG)
 def step(self,s,w):
  op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==32:
   v=s.load(e.add(s.r[rs],((w&65535)^32768)-32768),1)
   s.r[rt]=((v^128)-128)&e.U32 if isinstance(v,int)else('SIGN8',v)
  elif op==17 and rs==16 and fn==7:
   observation=(rs,fn,(s.f[rd],),s.fcsr);s.trace.append(('FP',observation))
   s.f[sa]=self.terms.term('FP_VALUE',*observation);s.fcsr=self.terms.term('FP_STATUS',*observation)
  else:super().step(s,w)
 def call(self,s,target):
  count={RNG:0,REAL:0,ANGLE:1,HEIGHT:2,EMIT:16}[target]
  args=tuple(s.r[4:4+min(count,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,count-4)))
  observed=()
  if target==HEIGHT:
   assert s.canonical(args[0])==('REGION','surface');s.exposed.add('surface')
  elif target==EMIT:
   assert (s.canonical(args[0]),s.canonical(args[1]),s.canonical(args[11]))==(('REGION','position'),('REGION','velocity'),('REGION','surface'))
   observed=tuple((name,s.region(name))for name in('position','velocity','surface'));s.exposed.update(REGIONS)
  args=tuple(s.canonical(a)for a in args)
  s.trace.append(('CALL',target,args,observed,s.fcsr))
  ordinal=sum(s.calls.values());s.calls[target]+=1;s.epoch+=1
  for name in sorted(s.exposed):
   off,size=REGIONS[name]
   for i in range(size):s.mem[off+s.shift+i]=('PROVIDER_BYTE',ordinal,name,i)
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for i in range(max(4,count)):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  s.r[2]=('RESULT',target,ordinal)
  if target in(REAL,ANGLE):s.f[0]=('RESULT_FP',target,ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)
def initial(side,phase,p):
 s=State(side)
 if phase=='prefix':return s
 for w in p.words[:18]:p.step(s,w)
 for i in(1,2,3,*range(4,24),24,25,30,31):s.r[i]=('DEAD_LOOP_GPR',i)
 for i in range(32):s.f[i]=('DEAD_LOOP_FP',i)
 s.r[18 if side=='raw'else 17]=e.add(('RECORD',),40);s.r[19]=('RECORD',);s.r[20]=46;s.r[23]=26;s.r[30]=101
 if side=='raw':
  s.r[21]=0x800A9018;s.r[22]=0x800A901C;s.store(('STACK',-116),4,('STACK',-40))
 else:s.r[21]=('STACK',-56);s.r[22]=('STACK',-68)
 s.f[28]=0x3f800000;s.f[30]=0x41f00000;s.mem[-5+s.shift]=0;s.exposed=set(REGIONS)
 s.trace=[];s.read_set=Counter();s.facts={};return s
def relation(s,end):
 if end=='return':
  assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
  assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
 else:
  assert s.r[29]==('STACK',-280)and s.r[18 if s.side=='raw'else 17]==e.add(('RECORD',),40)and s.r[19]==('RECORD',),('loop roles',s.side)
  assert (s.r[20],s.r[23],s.r[30],s.f[28],s.f[30])==(46,26,101,0x3f800000,0x41f00000)
  if s.side=='raw':assert(s.r[21],s.r[22],s.load(('STACK',-116),4))==(0x800a9018,0x800a901c,('STACK',-40))
  else:assert(s.r[21],s.r[22])==(('STACK',-56),('STACK',-68))
  for reg,off in [(r,-160+4*(r-16))for r in range(16,24)]+[(30,-128)]:assert s.load(('STACK',off),4)==('ENTRY',reg)
  assert s.load(('STACK',-124),4)==('RETURN',)
  for reg in range(20,32):assert s.load(('STACK',-208+4*(reg-20)),4)==('ENTRY_FP',reg)
 return s.trace,s.read_set,s.fcsr,s.region('surface')if'surface'in s.exposed else(),s.mem[-5+s.shift],s.divisors
def prove(words,truth):
 terms=Terms();programs={side:Program(w,terms,side)for side,w in(('raw',words),('retail',truth))};report={}
 for phase in('prefix','loop'):
  result={}
  for side,p in programs.items():
   paths=p.paths(0 if phase=='prefix'else p.cut,{p.cut:'loop',-4:'return'},initial(side,phase,p))
   result[side]={key:relation(s,key[0])for key,s in paths.items()}
  assert result['raw'].keys()==result['retail'].keys(),('predicates',phase,len(result['raw']),len(result['retail']))
  for key,left in result['raw'].items():
   right=result['retail'][key]
   if left!=right:
    part=next(i for i,(a,b)in enumerate(zip(left,right))if a!=b)
    if part==0:
     at=next((i for i,(a,b)in enumerate(zip(left[0],right[0]))if a!=b),min(len(left[0]),len(right[0])))
     raise AssertionError(('trace',phase,key[0],at,repr(left[0][at:at+1])[:1800],repr(right[0][at:at+1])[:1800]))
    raise AssertionError(('part',phase,key[0],part,repr(left[part])[:1200],repr(right[part])[:1200]))
  report[phase]=len(result['raw'])
 return dict(paths=report,coverage={side:dict(visited_words=len(p.seen),unvisited_offsets=[hex(i*4)for i in range(len(p.words))if i*4 not in p.seen])for side,p in programs.items()},raw_stack_shift=4,unpassed_private_homes_compared=False,ordered_FP_and_FCSR=True,arbitrary_public_alias_epochs=True,retained_regions_mutable=True,source_installed=source.installed(),c_match_credit=0)
def main():
 label='v28';raw,refs=payload(P/(label+'.o'),'func_151AB9C8');syms={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(raw,refs,syms);truth=list(struct.unpack('>227I',(P/'retail.bin').read_bytes()))
 report=prove(words,truth);controls=[]
 for name,old,new in [('snapshot-u16-offset',0x94490084,0x94490082),('rate-base-reload',0xc6440010,0xc6440014),('selector-offset',0x92460018,0x92460004),('velocity-negation',0x46006487,0x46006486),('loop-subtraction',0x461c2481,0x461c2480)]:
  bad=words[:];assert bad.count(old)==1,(name,hex(old));bad[bad.index(old)]=new
  try:prove(bad,truth)
  except AssertionError as error:
   reason=str(error);assert not any(s in reason for s in('unsupported','unbounded proof','escaped code','unrecognized exposed')),('invalid control',name,reason)
   controls.append(dict(name=name,reason=reason[:250]))
  else:raise AssertionError(('ineffective control',name))
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
 positive=prove([rename(w)for w in words],truth);assert positive['paths']==report['paths']
 assert report['coverage']['raw']['unvisited_offsets']==['0x68','0x84','0x15c','0x2e4','0x2f8']
 assert report['coverage']['retail']['unvisited_offsets']==['0x68','0x84','0x14c','0x2f4','0x304']
 report.update(effective_controls=controls,positive_T8_T9_reallocation_paths=positive['paths'],unvisited_words_are_two_unreachable_duplicate_loads_and_three_nonzero_DIV_BREAKs=True,termination_claim=False)
 (P/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
