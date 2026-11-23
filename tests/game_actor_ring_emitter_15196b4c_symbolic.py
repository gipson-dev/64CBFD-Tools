"""Independent inductive instruction transfer, before any projection is used.

Domain: normal o32 execution, ordinary mapped nonvolatile public RAM, aligned
private frame disjoint from public objects, valid callback table selections.
Public aliases are not separated: every public store/provider ends the read
epoch. Providers may mutate public RAM and every previously exposed private
output range, preserve saved registers, and arbitrarily replace FCSR/volatiles.
No raw fault-prefix, MMIO, race or floating-trap register identity is claimed.

Single precision values keep exact operands and numeric controls. FCSR flags
are cumulative; cause is the last computational operation, and condition the
last comparison. Equal exception-event sets establish equal normal-completion
domains even with arbitrary enables. See the separately checked fcsr_lemma.py.
"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import json,struct,sys
from tools.experiments import game_actor_ring_emitter_15196b4c_match as packet
r=packet.ROOT;o=packet.OUT
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
ENTRY=0x15196b4c;TRANSFORM=0x15143134;FIRST=0x15198d88;SECOND=0x151990ac;RNG=0x150ada20
OWNER=('OWNER',);PAYLOAD=('PAYLOAD',);RECORDS=('RECORDS',);WORLD=('STACK',-20)
SAVES={**{off-288:('ENTRY',reg)for off,reg in((0x48,16),(0x4c,17),(0x50,18),(0x54,19),(0x58,20),(0x5c,21),(0x60,22))},0x64-288:('RETURN',),**{0x18+4*i-288:('ENTRY_FP',20+(i^1))for i in range(12)}}
LAYOUT={
 'raw':dict(point=0xd4,end=0xc8,pointptr=0x7c,endptr=0x74,time=('m',0x104),steps=(('f',28),('f',30),('m',0xf0),('m',0xec),('m',0xe8),('m',0xe4),('m',0x78),('m',0x70)),core=0x244,pre=6,epilogue=0x5cc),
 'retail':dict(point=0xd0,end=0xc4,pointptr=0x90,endptr=0x8c,time=('f',28),steps=(('f',30),('m',0x88),('m',0x84),('m',0x80),('m',0x7c),('m',0x78),('m',0x74),('m',0x70)),core=0x234,pre=8,epilogue=0x5bc)}
def home(s,offset):return s.mem[offset-288]
def role(s,where):return s.f[where[1]]if where[0]=='f'else home(s,where[1])
def setrole(s,where,value):
 if where[0]=='f':s.f[where[1]]=value
 else:s.mem[where[1]-288]=value

class State(e.State):
 def __deepcopy__(self,memo):
  memo[id(self.terms)]=self.terms
  answer=type(self).__new__(type(self));memo[id(self)]=answer
  answer.__dict__=deepcopy(self.__dict__,memo);return answer
 def __init__(self,side,phase,terms):
  super().__init__('common',phase);self.side=side;self.phase=phase;self.terms=terms
  self.r[29]=('STACK',0 if phase=='prefix'else -288);self.r[31]=('RETURN',)
  self.mem={}if phase=='prefix'else dict(SAVES)
  self.epoch=0;self.readset=set();self.readcounts=Counter();self.private_writes=[];self.exposed=set()
  self.fp_events=[];self.status_reset(('INITIAL',phase));self.r[16]=('ENTRY',16)
  if phase=='prefix':self.r[4]=OWNER;return
  self.r[16]=OWNER;self.r[17]=36;self.r[18]=PAYLOAD;self.r[19]=RECORDS;self.r[20]=WORLD;self.r[21]=255;self.r[22]=6
  layout=LAYOUT[side]
  for reg,name in((20,'ELAPSED'),(22,'SPEED'),(26,'SIZE')):self.f[reg]=(name,)
  self.f[24]=0x3f800000
  for key in('point','end'):
   for axis in range(3):self.mem[layout[key]+4*axis-288]=(key.upper(),axis)
  self.mem[layout['pointptr']-288]=e.add(PAYLOAD,32);self.mem[layout['endptr']-288]=e.add(PAYLOAD,44)
  setrole(self,layout['time'],('TIME_STEP',))
  for i,where in enumerate(layout['steps']):setrole(self,where,('STEP',i))
  for axis in range(3):self.mem[-20+4*axis]=('WORLD',axis)
  self.exposed.update((-20,-16,-12));self.f[layout['pre']]=self.load(e.add(PAYLOAD,0x7c),4,b'')
 def status_reset(self,tag):
  self.controls=('NUMERIC_CONTROLS',tag);self.flagbase=('FLAGS',tag);self.exceptions=set();self.last=('CAUSE',tag);self.fp_condition=('CONDITION',tag)
 def status(self):return(self.controls,self.flagbase,tuple(sorted(self.exceptions,key=repr)),self.last,self.fp_condition)
 def load(self,address,size,pool):
  if e.tagged(address,'STACK'):
   assert size==4 and address[1]%4==0 and -288<=address[1]<=-4,('private load extent',address,size)
   assert address[1]in self.mem,('uninitialized private load',self.side,self.phase,address)
   return self.mem[address[1]]
  e.plain(address);assert not e.has_tag(address,'DEAD');key=(self.epoch,address,size);self.readset.add(key);self.readcounts[key]+=1
  return self.terms.term('READ',*key)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   assert size==4 and address[1]%4==0 and -288<=address[1]<=-4,('private store extent',address,size)
   self.mem[address[1]]=value;self.private_writes.append((address[1],size));return
  e.plain(value);assert not e.has_tag(value,'DEAD')and not e.has_tag(value,'DEAD_FP');value=e.bitop('AND',value,(1<<(8*size))-1)
  self.trace.append(('WRITE',e.plain(address),size,value));self.epoch+=1

class Program(e.Program):
 def __init__(self,words,side,terms):super().__init__(words,b'',ENTRY);self.side=side;self.terms=terms;self.layout=LAYOUT[side]
 def step(self,s,w):
  op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
  if op==0 and fn==37 and ((rt==0 and e.tagged(s.r[rs],'STACK'))or(rs==0 and e.tagged(s.r[rt],'STACK'))):s.r[w>>11&31]=s.r[rs]if rt==0 else s.r[rt]
  elif op in(53,61):
   at=e.add(s.r[rs],((w&65535)^32768)-32768);assert e.tagged(at,'STACK')and at[1]%8==0
   if op==61:s.store(at,4,s.f[rt+1]);s.store(e.add(at,4),4,s.f[rt])
   else:s.f[rt+1]=s.load(at,4,b'');s.f[rt]=s.load(e.add(at,4),4,b'')
  elif op==17 and rs==4:s.f[w>>11&31]=s.r[rt]
  elif op==17 and rs==16:
   fs,fd=w>>11&31,w>>6&31
   assert fn in(0,1,2,3,6,60),('unsupported FP',hex(w))
   if fn==6:s.f[fd]=s.f[fs];return
   args=(s.f[fs],s.f[rt]);assert not e.has_tag(args,'DEAD_FP');event=(fn,args,s.controls)
   # Numeric controls do not depend on old flags/cause. No commutativity or
   # reassociation axiom is used, including for floating add/multiply.
   value=self.terms.term('FP_VALUE',*event);exception=self.terms.term('FP_EXCEPT',*event)
   s.fp_events.append(event);s.exceptions.add(exception);s.last=exception
   if fn==60:s.fp_condition=value
   else:s.f[fd]=value
  else:super().step(s,w)
 def call(self,s,target):
  assert s.r[29]==('STACK',-288)
  indirect=not isinstance(target,int)
  if indirect:n=1;assert e.tagged(target,'SCALE_TARGET'),target
  else:assert target in(TRANSFORM,FIRST,SECOND,RNG),('unknown provider',target);n=3 if target==TRANSFORM else 2 if target in(FIRST,SECOND)else 0
  args=tuple(s.r[4:4+n]);assert not any(e.has_tag(a,'DEAD')for a in args);ordinal=sum(s.calls.values());s.calls[target]+=1
  if indirect:assert args==(OWNER,)
  elif target==TRANSFORM:
   occurrence=s.calls[target]-1
   assert occurrence in(0,1)
   # All private storage exposed by this function is exactly the 12-byte
   # output at entry SP-20. Public point inputs/outputs remain arbitrary RAM.
   assert not any(e.has_tag(a,'STACK')for a in(args[0],args[2]))
   if occurrence==1:assert args[1]==WORLD;s.exposed.update((-20,-16,-12))
  elif target in(FIRST,SECOND):assert args==(OWNER,WORLD)
  for a in args:
   if e.has_tag(a,'STACK'):assert a==WORLD
  before=tuple((off,s.mem.get(off,('PRIVATE_ENTRY',off)))for off in sorted(s.exposed))
  s.trace.append(('CALL',target,args,before,s.status()));s.epoch+=1
  for off in s.exposed:s.mem[off]=('PROVIDER_PRIVATE',ordinal,off)
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for off in range(-288,-272,4):s.mem[off]=('CALL_HOME',ordinal,off)
  s.r[2]=('RESULT',ordinal);s.f[0]=('RESULT_FP',ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.status_reset(('CALL',ordinal))
 def paths(self,start,initial,loop_cut=True):
  active=[(start,initial)];answers={};work=0
  while active:
   pc,s=active.pop();work+=1;s.steps+=1
   assert work<40000 and s.steps<550,('unbounded proof',self.side,initial.phase,pc,work)
   stop='loop'if pc==self.layout['core']else'return'if pc==self.layout['epilogue']else'returned'if pc==-4 else None
   if s.steps>1 and stop is not None:
    key=(stop,tuple(sorted(s.facts.items(),key=repr)));assert key not in answers,('duplicate path',key)
    answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31;floating=op==17 and rs==8
   if floating or op in(4,5,20,21):
    condition=s.fp_condition if floating else e.pred('EQ',s.r[rs],s.r[rt]);likely=bool(rt&2)if floating else op in(20,21)
    if (floating and not rt&1)or op in(5,21):condition=e.negate(condition)
    assert not e.has_tag(condition,'DEAD')and not e.has_tag(condition,'DEAD_FP')
    for taken in e.choices(s,condition):
     n=deepcopy(s);e.assume(n,condition,taken)
     if taken or not likely:self.step(n,self.instruction(pc+4))
     active.append((pc+4+4*(((w&65535)^32768)-32768)if taken else pc+8,n))
   elif op==3 or(op==0 and w&63==9):
    target=((self.entry+pc+4)&0xf0000000)|((w&0x3ffffff)<<2)if op==3 else('SCALE_TARGET',s.r[rs])
    s.r[31]=self.entry+pc+8;self.step(s,self.instruction(pc+4));self.call(s,target);active.append((pc+8,s))
   elif op==0 and w&63==8:
    target=s.r[rs];self.step(s,self.instruction(pc+4));assert target==('RETURN',);active.append((-4,s))
   else:self.step(s,w);active.append((pc+4,s))
  return answers

def relation(s,label):
 layout=LAYOUT[s.side]
 assert all(s.mem.get(at)==v for at,v in SAVES.items()),('saved frame changed',s.side,s.phase)
 assert all(s.f[i]==('ENTRY_FP',i)for i in range(21,32,2)),('odd FPR lifetime',s.side,s.phase)
 assert s.r[29]==('STACK',-288)
 assert all(s.r[i]==('ENTRY',i)for i in(23,28,30)),('unspilled saved GPR',s.side,s.phase)
 # Function writes may materialize scalar/vector temporaries anywhere in its
 # unexposed local region, never in saved homes or the exposed output range.
 if s.phase!='prefix':assert all(at not in SAVES and at not in s.exposed for at,n in s.private_writes)
 if label=='return':assert s.r[2]in(0,1);live=(s.r[2],)
 else:
  assert s.r[16]==OWNER and s.r[17]==36 and s.r[20]==WORLD and s.r[21]==255 and s.r[22]==6
  live=(s.r[18],s.r[19],tuple(s.f[i]for i in(20,22,24,26)),role(s,layout['time']),tuple(role(s,v)for v in layout['steps']),tuple(home(s,layout[key]+4*axis)for key in('point','end')for axis in range(3)),home(s,layout['pointptr']),home(s,layout['endptr']),s.f[layout['pre']],tuple(s.mem[off]for off in(-20,-16,-12)))
 return s.trace,s.readset,s.status(),Counter(s.fp_events),live

def prove(raw,retail,verbose=True):
 assert len(raw)==387 and len(retail)==383
 assert raw[0]==retail[0]==0x27bdfee0 and raw[-17:]==retail[-17:]
 result={};duplicate_reads={}
 for phase in('prefix','loop'):
  terms=Terms();answers=[]
  for words,side in((raw,'raw'),(retail,'retail')):
   p=Program(words,side,terms);s=State(side,phase,terms)
   answers.append(p.paths(0 if phase=='prefix'else LAYOUT[side]['core'],s))
  a,b=answers
  assert a.keys()==b.keys(),('path predicates',phase,len(a),len(b),list(a.keys()-b.keys())[:1],list(b.keys()-a.keys())[:1])
  for key in a:
   x,y=relation(a[key],key[0]),relation(b[key],key[0])
   for index,name in enumerate(('public/provider effects','quiet read footprints','FCSR normal completion','FP operations','live storage relation')):
    assert x[index]==y[index],('transfer',phase,name,key,x[index],y[index])
  result[phase]=len(a);duplicate_reads[phase]=[max(sum(n-1 for n in s.readcounts.values())for s in v.values())for v in answers]
  if verbose:print(phase,len(a),'passed',flush=True)
 # Literal-identical complete epilogue is separately executed from arbitrary
 # return value and saved register homes, with no presumed register contents.
 terms=Terms();out=[]
 for words,side in((raw,'raw'),(retail,'retail')):
  s=State(side,'epilogue',terms);s.private_writes=[];s.r[2]=('RESULT',)
  answer=Program(words,side,terms).paths(LAYOUT[side]['epilogue'],s);assert len(answer)==1
  s=next(iter(answer.values()));assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
  assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))
  assert all(s.f[i]==('ENTRY_FP',i)for i in range(20,32))and s.r[2]==('RESULT',)
  assert not s.trace and not s.private_writes;out.append(s.status())
 assert out[0]==out[1]
 return dict(inductive_phase_paths=result,epilogue_words=17,duplicate_quiet_reads=duplicate_reads,whole_function_transfer=True,source_installed=packet.installed(),matching_credit=0)

def programs():
 answer=[]
 for name in('selected-final/candidate.o','original-target.o'):
  data,refs=payload(o/name,'func_15196B4C');answer.append(bound_blob(data,refs,S))
 return answer
def controls(raw,retail):
 rejected=[]
 def reject(label,words):
  try:prove(words,retail,False)
  except AssertionError as error:rejected.append(dict(label=label,reason=str(error)[:220]))
  else:raise AssertionError(('ineffective proof control',label))
 for label,at,mask in(
  ('matrix-null-gate',0x50,1<<26),('selector-byte',0x54,1),
  ('matrix-stride',0xa0,1<<6),('first-transform-input',0x98,4),
  ('second-transform-output',0xb0,4),('phase-rate',0xd0,4),
  ('inverse-operation',0x100,1),('quiet-duplicate-size-read',0x1e4,4),
  ('point-copy-axis',0x110,4),('world-end-axis',0x19c,4),
  ('first-child-accumulator',0x250,4),('second-child-threshold',0x288,1<<16),
  ('entry-stride',0x148,4),('signed-duration',0x380,4<<26),
  ('random-divisor',0x134,1),('count-increment',0x4c4,1),
  ('gravity-axis',0x418,4),('phase-decrement',0x564,1),
  ('interpolation-step',0x504,1<<16),('captured-final-pointer',0x588,4),
  ('speed-output',0x5c0,4),('saved-F20-restore',0x5d0,8)):
  words=raw.copy();words[at//4]^=mask;reject(label,words)
 # A nonretail allocation must pass without consulting projection rows.
 for label,gpr,fpr in(('GPR-nine-ten',True,False),('FPR-eight-ten',False,True)):
  words=[]
  swap=lambda v:(10 if v==9 else 9 if v==10 else v)if gpr else(10 if v==8 else 8 if v==10 else v)
  from tools.experiments.game_curve_emitter_151a11e4_match import fields as basefields
  for w in raw:
   fields=[(21,'g'),(16,'g')]if w>>26 in(20,21)else[(21,'g'),(11,'g')]if w>>26==0 and w&63==9 else basefields(w)
   for shift,kind in fields:
    if (gpr and kind=='g')or(fpr and kind=='f'):w=(w&~(31<<shift))|(swap(w>>shift&31)<<shift)
   words.append(w)
  assert words!=raw;prove(words,retail,False)
 # Two independent setup SUBs can exchange their arithmetic issue positions
 # while their materialized inputs remain ready and all consumers stay later.
 # Use the two difference operations immediately preceding the final step loop.
 # The full relation decides whether a scheduling control is admissible.
 accepted=[]
 for a in range(66,144):
  if raw[a]>>26!=17 or raw[a]&63!=1:continue
  for b in range(a+1,min(a+9,144)):
   if raw[b]>>26!=17 or raw[b]&63!=1:continue
   words=raw.copy();words[a],words[b]=words[b],words[a]
   try:prove(words,retail,False)
   except AssertionError:continue
   accepted.append([a,b]);break
  if accepted:break
 assert accepted,('no effective independent schedule control',)
 return dict(negative_controls=rejected,positive_controls=['GPR-nine-ten','FPR-eight-ten'],accepted_independent_FP_schedule=accepted,projection_used=False)

def proof():
 raw,retail=programs();q=prove(raw,retail);(o/'whole-proof.json').write_text(json.dumps(q,indent=2)+'\n')
 tests=controls(raw,retail);(o/'whole-proof-controls.json').write_text(json.dumps(tests,indent=2)+'\n');print(json.dumps(q),flush=True);return q
