"""Complete instruction relation for the recovered actor bound burst parent.

Normal mapped/aligned execution is assumed. Public memory is stable within a
quiet epoch and may change after each opaque provider. Passed private objects
are related by the explicit points-to map; providers cannot inspect physical
private address bits, implementation PCs, unpassed locals or undeclared register
inputs. All mapped bytes, ordered FP/FCSR operations, saved ABI and emitted V0
are related. Unmapped private reads, writes and passed pointers are rejected.
This does not normalize or install code or claim fault/interrupt/hardware parity.
"""
from pathlib import Path
from copy import deepcopy
import hashlib,json,struct
from tools.experiments import game_actor_bound_burst_150b7b40_screen as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
e=g.e;ENTRY=0x150B7B40
POSITION,SINE,TRANSFORM,BOUNDS,BURST=0x15142314,0x151423D8,0x15143134,0x1515C244,0x150B82D0
RADIAL,INIT,QUERY,RNG,FLOOR,REAL=0x150B85C0,0x1504715C,0x15046C80,0x150ADA20,0x1514C678,0x150ADA68
CHILD,SPRAY=0x15132A4C,0x15151A38
RETAIL={1:(-24,12),2:(-12,12),3:(-36,12),4:(-216,12),5:(-240,12),6:(-252,12),7:(-220,4),8:(-224,4),9:(-228,4),10:(-300,36),11:(-312,12),12:(-180,124),13:(-476,136)}
RAW={1:(-24,12),2:(-12,12),3:(-36,12),4:(-192,12),5:(-204,12),6:(-216,12),7:(-172,4),8:(-176,4),9:(-180,4),10:(-252,36),11:(-264,12),12:(-160,124),13:(-400,136)}
def homes(raw):
 pairs=[(-600 if raw else -616,-616,128),(-168 if raw else -204,-204,8),(0,0,16)]
 pairs += [(RAW[k][0]if raw else RETAIL[k][0],RETAIL[k][0],RETAIL[k][1])for k in RETAIL]
 result={}
 for physical,canonical,n in pairs:
  for i in range(n):assert physical+i not in result;result[physical+i]=canonical+i
 assert len(result)==544 and len(set(result.values()))==544;return result
class State(g.State):
 def __init__(self,raw,remap=True):
  super().__init__('common');self.raw=raw;self.frame_bytes=600 if raw else 616;self.homes=homes(raw and remap)
  self.mem={v:('PRIVATE_ENTRY',v)for v in self.homes.values()};self.exposed=set()
  self.r[4:7]=[('ACTOR',),('SLOT_WORD',),('CONTEXT_WORD',)]
 def address(self,value):
  if e.tagged(value,'STACK'):
   off=value[1];assert off in self.homes,('unmapped private pointer',off);return('STACK',self.homes[off])
  return value
 def value(self,v):
  if e.tagged(v,'STACK'):return self.address(v)
  return tuple(self.value(x)for x in v)if isinstance(v,tuple)else v
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0
   return g.join([self.mem[self.homes[off+i]]for i in range(size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0
   for i in range(size):self.mem[self.homes[off+i]]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def frame(self):return tuple((off,self.value(self.mem[off]))for off in sorted(self.mem))
class Program(g.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def step(self,s,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==16 and fn in(4,5,7,50):
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31;args=(s.f[fs],s.f[ft])if fn==50 else(s.f[fs],)
   observation=(fmt,fn,args,s.fcsr);s.trace.append(('FP',observation));value=self.terms.term('FP_VALUE',*observation);s.fcsr=self.terms.term('FP_STATUS',*observation)
   if fn==50:s.condition=value
   else:s.f[fd]=value
  else:super().step(s,w)
 def call(self,s,target):
  assert target in(POSITION,SINE,TRANSFORM,BOUNDS,BURST,RADIAL,INIT,QUERY,RNG,FLOOR,REAL,CHILD,SPRAY),('opening escaped target',hex(target))
  assert s.r[29]==('STACK',-s.frame_bytes)
  n={POSITION:3,SINE:1,TRANSFORM:3,BOUNDS:4,BURST:6,RADIAL:5,INIT:2,QUERY:4,RNG:0,FLOOR:12,REAL:0,CHILD:6,SPRAY:3}[target]
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-s.frame_bytes+16+4*i),4)for i in range(max(0,n-4)))
  if target==FLOOR:args=(s.f[12],s.f[14],*args[2:])
  passed=tuple(s.address(v)for v in args);ordinal=sum(s.calls.values());s.calls[target]+=1;new=[]
  if target==POSITION:
   k={4:1,5:2,0:3}[passed[1]];assert passed[2]==('STACK',RETAIL[k][0]);new=[k]
  elif target==TRANSFORM:
   k={0x8009FD30:4,0x8009FD3C:5,0x8009FD48:6}[passed[0]];assert passed[1]==('STACK',RETAIL[k][0]);new=[k]
  elif target==BOUNDS:
   assert passed[0]==('ACTOR',)
   for k,v in zip((4,8,7),passed[1:]):assert v==('STACK',RETAIL[k][0])
   new=[4,8,7]
  elif target==BURST:
   for k,v in zip((4,7,8,9),passed[:4]):assert v==('STACK',RETAIL[k][0])
   new=[4,7,8,9]
  elif target==RADIAL:
   for k,v in zip((4,7,8),passed[:3]):assert v==('STACK',RETAIL[k][0])
   new=[4,7,8]
  elif target==INIT:
   assert passed[0]==('STACK',RETAIL[10][0])and passed[1]==('ACTOR',);new=[10]
  elif target==QUERY:
   assert passed[0]==('STACK',RETAIL[11][0])and passed[3]==('STACK',RETAIL[10][0]);new=[11,10]
  elif target in(CHILD,SPRAY):
   k=12 if target==CHILD else 13;assert passed[0]==('STACK',RETAIL[k][0]);new=[k]
  s.exposed.update(new)
  observed=tuple((k,tuple(s.value(s.mem[RETAIL[k][0]+i])for i in range(RETAIL[k][1])))for k in new)
  s.trace.append(('CALL',target,passed,observed,s.fcsr));s.trace.append(('FRAME',s.frame()));s.epoch+=1
  for k in s.exposed:
   base,nbytes=RETAIL[k]
   for i in range(nbytes):s.mem[base+i]=('PROVIDER_BYTE',ordinal,base+i)
  for i in range(max(4,n)):s.store(('STACK',-s.frame_bytes+4*i),4,('CALL_HOME',ordinal,i))
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  s.r[2]=('RESULT',target,ordinal)
  if target in(SINE,REAL):s.f[0]=('RESULT_FP',target,ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)
 # Known choices can reuse their sole state; unknown branches remain copied.
 def paths(self,start,stops,initial):
  states=[(start,initial)];answers={};work=0
  while states:
   pc,s=states.pop();work+=1;s.steps+=1;assert work<1000000 and s.steps<1500,('unbounded proof',start,work,hex(pc))
   if s.steps>1 and pc in stops:
    key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)));assert key not in answers,('duplicate path',key);answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31;delay=lambda n:self.step(n,self.instruction(pc+4))
   if op in(4,5,6,7,20,21,22,23)or op==17 and rs==8:
    if op==17:p=s.condition;assert p is not None;likely=bool(rt&2);p=p if rt&1 else e.negate(p)
    else:
     p=g.predicate('EQ',s.r[rs],s.r[rt])if op in(4,5,20,21)else g.predicate('SLT',0,s.r[rs]);likely=op>=20
     if op in(5,21,6,22):p=e.negate(p)
    choices=e.choices(s,p)
    for take in choices:
     n=deepcopy(s) if len(choices)>1 else s;e.assume(n,p,take)
     if take or not likely:delay(n)
     dest=pc+4+4*(((w&65535)^32768)-32768)if take else pc+8;states.append((dest,n))
   elif op==3:
    s.r[31]=self.entry+pc+8;delay(s);self.call(s,((self.entry+pc+4)&0xf0000000)|((w&0x3ffffff)<<2));states.append((pc+8,s))
   elif op==0 and w&63==8:
    assert s.r[rs]==('RETURN',);delay(s);states.append((-4,s))
   elif op==0 and w&63==13:raise AssertionError(('normal-domain BREAK reached',hex(pc),s.facts))
   else:self.step(s,w);states.append((pc+4,s))
  return answers

def observe(s,end):
 if end=='return':
  assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
  assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
 else:
  assert s.r[29]==('STACK',-s.frame_bytes)and s.f[20]==0x3F800000
  if s.raw:assert s.f[22]==0
  # Check saved custody rather than dead current FP values. Remaining FP
  # lifetimes and the constant-zero source role must be proved in continuation.
  for reg in range(20,32):assert g.join([s.mem[-616+0x30+4*(reg-20)+j]for j in range(4)])==('ENTRY_FP',reg)
 live=(2,16,17,18,19,20,21,28,29,30,31)
 return(s.trace,s.read_set,s.divisors,s.frame(),s.fcsr,tuple((i,s.address(s.r[i]))for i in live),s.exposed)
def compare(aa,bb):
 assert aa.keys()==bb.keys(),('logical path keys differ',len(aa),len(bb))
 for key in aa:
  if aa[key]!=bb[key]:
   part=next(i for i,(x,y)in enumerate(zip(aa[key],bb[key]))if x!=y)
   raise AssertionError(('relation observation differs',part))
def run(words,israw,terms,remap=True,counts=False):
 program=Program(words,terms);paths=program.paths(0,{-4:'return'},State(israw,remap))
 if counts:
  assert len(paths)==257
  unseen=set(range(0,1936,4))-program.seen
  assert len(unseen)==1 and words[next(iter(unseen))//4]==0x3C013F80
  for state in paths.values():
   if sum(state.calls.values()):
    assert state.calls[CHILD]==state.calls[SPRAY]==2 and state.calls[REAL]==6 and state.calls[SINE]==10
    assert state.calls[RNG]==4+state.calls[FLOOR]and state.calls[BURST]==state.calls[RADIAL]==state.calls[INIT]==state.calls[QUERY]==1
 answers={key:observe(s,key[0])for key,s in paths.items()}
 return answers,dict(raw=israw,paths=len(paths),words_visited=len(program.seen),maximum_path_steps=max(s.steps for s in paths.values()))
def main():
 source.check_inputs();raw,refs=payload(source.OUT/'captured-model.o','func_150B7B40');pin=source.PIN['variants']['captured-model'];assert hashlib.sha256(raw).hexdigest()==pin['raw_sha256']
 assert refs=={int(k):[tuple(v)for v in rows]for k,rows in pin['refs'].items()}
 lookup={v[1]:v[2][1]for v in symbol_rows((source.FROZEN/'conker/build/conker.us.elf').read_bytes())}
 source_words=bound_blob(raw,refs,lookup);truth=(source.FROZEN/'conker/conker.us.bin').read_bytes()[0xE4FF0:0xE5780];retail=list(struct.unpack('>484I',truth));terms=Terms();answers=[];reports=[]
 for israw,words in((True,source_words),(False,retail)):
  answer,report=run(words,israw,terms,counts=True);answers.append(answer);reports.append(report)
 assert answers[0].keys()==answers[1].keys(),('path keys differ',len(answers[0]),len(answers[1]))
 for key in answers[0]:
  aa,bb=answers[0][key],answers[1][key]
  if aa!=bb:
   part=next(i for i,(x,y)in enumerate(zip(aa,bb))if x!=y)
   if part==0:
    at=next((i for i,(x,y)in enumerate(zip(aa[0],bb[0]))if x!=y),None)
    raise AssertionError(('trace mismatch',key,at,repr(aa[0][at])[:1400]if at is not None else len(aa[0]),repr(bb[0][at])[:1400]if at is not None else len(bb[0])))
   raise AssertionError(('observation part',part,repr(aa[part])[:1200],repr(bb[part])[:1200]))
 controls=[]
 def reject(label,words,remap=True):
  try:bad,_=run(words,True,terms,remap);compare(bad,answers[1])
  except(AssertionError,KeyError,ValueError)as error:
   reason=str(error);assert not any(v in reason for v in('unsupported','unbounded proof','opening escaped target')),(label,reason)
   controls.append(dict(label=label,rejected=True,reason=reason[:180]));print(json.dumps(controls[-1]),flush=True)
  else:raise AssertionError(('ineffective relation negative',label))
 reject('disabled-private-home-map',source_words,False)
 def word_change(label,predicate,mask):
  at=[i for i,w in enumerate(source_words)if predicate(w)];assert len(at)==1,(label,at)
  bad=source_words[:];bad[at[0]]^=mask;reject(label,bad)
 word_change('frame-size',lambda w:w==0x27BDFDA8,8)
 word_change('slot-width',lambda w:w==0x30B500FF,128)
 word_change('first-output-home',lambda w:w==0x27A60240,4)
 at=[i for i,w in enumerate(source_words)if w>>26==17 and w>>21&31==16 and w&63==3];assert len(at)==2
 bad=source_words[:];i=at[0];w=bad[i];bad[i]=(w&~(31<<16|31<<11))|((w>>11&31)<<16)|((w>>16&31)<<11);reject('ratio-operand-order',bad)
 word_change('cached-zero-role',lambda w:w==0x4480B000,4<<16)
 word_change('child-duration',lambda w:w>>26==9 and w>>21&31==0 and w&65535==300,1)
 word_change('spray-resource',lambda w:w>>26==15 and w&65535==0x22,1)
 word_change('loop-trip-count',lambda w:w==0x2A410002,3)
 word_change('saved-return-home',lambda w:w==0xAFBF007C,4)
 assert len(controls)==10
 report=dict(passes=True,complete_relation_passes=True,streams=reports,canonical_private_and_incoming_bytes=544,unmapped_accesses_rejected=True,exact_two_trip_counts_verified=True,effective_negatives=controls,normalization_and_adoption_pending=True,c_match_credit=0)
 (source.OUT/'complete-relation-report.json').write_text(json.dumps(report,indent=2)+'\n');source.check_inputs();print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
