"""Inductive ramp regions; immutable code, mapped public data and private o32 frame.

The untouched prefix/suffix preserve every instruction and edge, modulo an
unsigned ADDU commute and symmetric equality operands. Four independently
executed ramp regions cover both loops without an iteration bound. Fresh
symbolic public reads and ordered writes admit public aliases. Raw/private
fault-state equality is a separate normalized guest gate.
"""
from pathlib import Path
from copy import deepcopy
import json,struct,sys
from tools.experiments import game_actor_effect_update_15196748_match as p
r=p.ROOT;o=p.OUT
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_actor_effect_update_15196748_normalizer import position
ENTRY=0x15196748
class State(e.State):
 def __init__(self,side,phase):
  super().__init__(side,phase);self.r[16]=('OWNER',);self.r[7]=('PAYLOAD',);self.r[10]=('RECORDS',);self.r[9]=36;self.r[29]=('STACK',-56);self.r[31]=('RETURN',)
  self.f=[('FPR',i)for i in range(32)];self.hi=('HI',);self.lo=('LO',);self.mem={}
  if phase=='entry':self.r[2]=('HEAD',)
  elif phase=='forward':self.r[17]=('CURSOR',);self.r[4]=('REMAINING',);self.r[5 if side=='raw'else 3]=('RAMP',)
  elif phase=='gate':self.r[24]=('SECOND_FLAG',)
  elif phase=='backward':self.r[17]=('CURSOR',);self.r[4]=('REMAINING',);self.r[5]=('REVERSE_RAMP',)
class Program(e.Program):
 def __init__(self,words):super().__init__(words,b'',ENTRY)
 def paths(self,start,stops,initial):
  active=[(start,initial)];answers={};work=0
  while active:
   pc,s=active.pop();s.steps+=1;work+=1;assert work<5000 and s.steps<150,('proof bound',pc)
   if s.steps>1 and pc in stops:
    key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)));assert key not in answers,('duplicate path',key);answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31
   if op in(1,4,5,6,7,20,21,22,23):
    if op in(4,5,20,21):condition=e.pred('EQ',s.r[rs],s.r[rt])
    elif op==1:assert rt==1;condition=e.negate(e.pred('SLT',s.r[rs],0))
    else:assert rt==0;condition=e.pred('SLT',0,s.r[rs])
    if op in(5,21,6,22):condition=e.negate(condition)
    for taken in e.choices(s,condition):
     n=deepcopy(s);e.assume(n,condition,taken)
     if taken or op<20:self.step(n,self.instruction(pc+4))
     target=pc+4+4*(((w&65535)^32768)-32768)if taken else pc+8;active.append((target,n))
   else:self.step(s,w);active.append((pc+4,s))
  return answers
def relation(s,side,end):
 common=(s.trace,s.r[16],s.r[7],s.r[10],s.r[9],s.r[29],s.r[31],tuple(s.f),s.fcsr,s.hi,s.lo)
 live=(s.r[17],s.r[4],s.r[5 if side=='raw'else 3])if end=='forward'else(s.r[24],)if end=='gate'else(s.r[17],s.r[4],s.r[5])if end=='backward'else(s.r[2],)
 return common,live
def reads_writes(w):
 op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
 if not w:return set(),set()
 if op==0:
  if fn in(8,9):return{rs},{31}if fn==9 else set()
  if fn in(0,2,3):return{rt},{rd}
  if fn in(16,18):return set(),{rd}
  if fn in(25,27):return{rs,rt},set()
  if fn in(33,35,37,42):return{rs,rt},{rd}
  raise AssertionError(('R decode',hex(w)))
 if op in(32,33,35,36,37):return{rs},{rt}
 if op in(40,41,43):return{rs,rt},set()
 if op in(49,57):return{rs},set()
 if op==15:return set(),{rt}
 if op in(9,10,12):return{rs},{rt}
 if op in(4,5,20,21):return{rs,rt},set()
 if op in(1,6,7,22,23):return{rs},set()
 if op==3:return set(),{31}
 if op==17:assert rs==4;return{rt},set()
 raise AssertionError(('decode',hex(w)))
def dead_after(words,start):
 arities={84:2,198:1,211:1,224:1}if len(words)==256 else{84:2,199:1,212:1,225:1};volatile={1,2,3,*range(4,16),24,25,31};todo=[(start,frozenset((3,4,5,11,12,13,14,15,24,25)))];seen=set();checks=0
 def step(i,live):
  nonlocal checks
  uses,defs=reads_writes(words[i]);assert not uses&live,('unpassed role read',i,uses&live);checks+=1;return live-defs
 while todo:
  pc,live=todo.pop()
  if not live or(pc,live)in seen:continue
  seen.add((pc,live));assert 0<=pc<len(words);w=words[pc];op=w>>26;live=step(pc,live)
  if op==3 or(op==0 and w&63==9):
   live=step(pc+1,live);assert not live&set(range(4,4+arities[pc]));todo.append((pc+2,frozenset(live)))
  elif op in(1,4,5,6,7,20,21,22,23):
   live=step(pc+1,live);target=pc+1+(((w&65535)^32768)-32768);todo.extend(((target,frozenset(live)),(pc+2,frozenset(live))))
  elif op==0 and w&63==8:
   live=step(pc+1,live);assert not live&{2,*range(16,24),28,29,30,31}
  else:todo.append((pc+1,frozenset(live)))
 return checks
def proof(write=True,words=None):
 if words is None:
  S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};words=[bound_blob(*payload(o/path,'func_15196748'),S)for path in('selected-final/candidate.o','original-target.o')]
 a,b=words;assert len(a)==256 and len(b)==257;regions=set(range(126,182));identity=[]
 for i,w in enumerate(a):
  if i in regions:continue
  j=position(i);want=b[j]
  if i in(36,111):
   rs,rt=w>>21&31,w>>16&31;w=(w&~((31<<21)|(31<<16)))|(rt<<21)|(rs<<16)
  if w>>26 in(1,4,5,6,7,20,21,22,23):
   target=i+1+(((w&65535)^32768)-32768);w=(w&0xffff0000)|((position(target)-j-1)&65535)
  assert w==want,('outside ramp region',i,j,hex(w),hex(want));identity.append(i)
 assert a[36]&63==33 and a[111]>>26==21
 counts={}
 for phase,start,stops in(('entry',126,{133:'forward',155:'gate'}),('forward',133,{133:'forward',155:'gate'}),('gate',155,{165:'backward',190:'callbacks'}),('backward',165,{165:'backward',190:'callbacks'})):
  left=Program(a).paths(start*4,{i*4:v for i,v in stops.items()},State('raw',phase));right=Program(b).paths(position(start)*4,{position(i)*4:v for i,v in stops.items()},State('retail',phase));assert left.keys()==right.keys(),('path conditions',phase,left.keys()-right.keys(),right.keys()-left.keys())
  for key in left:
   x=relation(left[key],'raw',key[0]);y=relation(right[key],'retail',key[0]);assert x==y,('region transfer',phase,key,x,y)
  counts[phase]=len(left)
 dead=[dead_after(a,190),dead_after(b,191)];q=dict(source_words_covered=256,retail_words_covered=257,literal_or_commutative_outside_region_words=len(identity),inductive_paths=counts,post_region_dead_role_checks=dead,ordered_public_reads_writes_equal=True,branch_likely_and_flag_test_clone_proved=True,loop_iterations_unbounded=True,FP_prefix_suffix_operations_and_FCSR_unchanged=True,source_installed=p.installed(),matching_credit=0,limits='Ordinary mapped public memory and disjoint valid o32 private frame. Callback arities are separately audited. Unrecovered provider bodies and raw fault-state equality are not inferred.')
 if write:(o/'symbolic.json').write_text(json.dumps(q,indent=2)+'\n')
 return q
def controls(raw,retail):
 from tools.tests.game_actor_effect_update_15196748_normalizer import rename
 expected=proof(False,[raw,retail]);positives=[]
 for lo,hi,pair,label in((132,155,{11:13,13:11},'forward allocation'),(166,183,{12:14,14:12},'backward allocation')):
  changed=retail[:]
  for i in range(lo,hi):changed[i]=rename(changed[i],pair)
  assert changed!=retail and proof(False,[raw,changed])==expected;positives.append(label)
 changed=retail[:];assert changed[130]>>26==20;changed[130]=(changed[130]&0x03ffffff)|(4<<26);assert proof(False,[raw,changed])==expected;positives.append('unobserved eager flag test')
 edits=[(126,lambda w:w+1,'flags field'),(129,lambda w:w^3,'first flag bit'),(131,lambda w:(9<<26)|((w>>11&31)<<16)|1,'initial mark'),(132,lambda w:w+2,'forward count field'),(134,lambda w:w-1,'forward count decrement'),(140,lambda w:w-1,'forward destination'),(141,lambda w:w+2,'forward step field'),(142,lambda w:w-1,'capacity field'),(144,lambda w:w&~128,'forward byte wrap'),(145,lambda w:(w&0x03ffffff)|(4<<26),'capacity branch'),(154,lambda w:w^12,'second flag bit'),(159,lambda w:w-2,'backward count field'),(166,lambda w:w-1,'backward count decrement'),(168,lambda w:w-1,'backward cursor decrement'),(172,lambda w:w-1,'backward mark field'),(175,lambda w:w-(1<<6),'backward scale shift'),(176,lambda w:w-1,'backward destination'),(177,lambda w:w-2,'backward step field'),(179,lambda w:w&~128,'backward byte wrap')];failures=[]
 for side,base in enumerate((raw,retail)):
  for index,change,label in edits:
   at=index if side==0 else position(index);bad=base[:];bad[at]=change(bad[at]);assert bad!=base;pair=[raw,retail];pair[side]=bad
   try:proof(False,pair)
   except AssertionError as error:
    reason=str(error);assert reason and not any(x in reason for x in('unsupported','decode','proof bound','escaped code','duplicate path')),(label,reason);failures.append(dict(side=side,word=at,operation=label,reason=reason[:120]))
   else:raise AssertionError(('ineffective semantic control',side,index,label))
 bad=retail[:];bad[131]^=12
 try:proof(False,[raw,bad])
 except AssertionError as error:assert 'region transfer'in str(error);failures.append(dict(side=1,word=131,operation='cloned flag bit',reason=str(error)[:120]))
 else:raise AssertionError('Ineffective clone mutation')
 return dict(independent_positive_controls=positives,effective_semantic_controls=failures)
