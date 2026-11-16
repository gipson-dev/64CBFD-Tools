"""Bounded setup transfer only: ordered FP/FCSR, live loop roles and private writes.

Ordinary mapped public reads commute only within intervals without a public
write. Private stack and the immutable epsilon word are disjoint from public
storage. This does not qualify entry, retirement calls, loop, tail or epilogue.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import json,re,struct,subprocess,sys
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_ring_emitter_151a37c0_screen as m
ENTRY=m.ENTRY

class State(e.State):
 def __init__(self,frame):
  super().__init__('common','setup');self.r[29]=('STACK',-frame);self.r[17]=('OWNER',);self.r[18]=('PAYLOAD',);self.r[22]=('ENTRIES',)
  self.mem={};self.fp=[];self.fp_condition=None;self.fcsr=('FCSR',);self.effects=[];self.private_writes=[]
 def load(self,address,size,pool):
  if address==0x800A8D58:return 0x38D1B717
  if e.tagged(address,'STACK'):
   assert size==4 and address[1]%4==0;return self.mem.get(address[1],('INITIAL_HOME',address[1]))
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   assert size==4 and address[1]%4==0;self.mem[address[1]]=value;self.private_writes.append((address[1],size));return
  super().store(address,size,value);self.effects.append(self.trace[-1])
class Program(e.Program):
 def __init__(self,words,terms,frame):
  super().__init__(words,b'',ENTRY);self.terms=terms;self.frame=frame
  rng=next(i*4 for i,w in enumerate(words) if w>>26==3 and ((w&0x3FFFFFF)<<2|0x10000000)==0x150ADA20)
  self.core=rng-0x48;self.epilogue=(len(words)-16)*4
 def step(self,s,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==4:s.f[w>>11&31]=s.r[w>>16&31]
  elif op==17 and fmt==16 and fn in(0,1,2,3,4,5,7,60):
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31;args=(s.f[fs],) if fn in(4,5,7) else(s.f[fs],s.f[ft]);event=(fn,args,s.fcsr);s.fp.append(event);s.effects.append(('FP',event))
   value=self.terms.term('FP_VALUE',*event);s.fcsr=self.terms.term('FP_STATUS',*event)
   if fn==60:s.fp_condition=value
   else:s.f[fd]=value
  else:super().step(s,w)
 def paths(self):
  active=[(0x154,State(self.frame))];answers={};work=0
  while active:
   pc,s=active.pop();work+=1;s.steps+=1;assert work<10000 and s.steps<220,(pc,work)
   if pc in(self.core,self.epilogue):
    label='loop' if pc==self.core else 'return';key=(label,tuple(sorted(s.facts.items(),key=repr)));assert key not in answers;answers[key]=s;continue
   w=self.instruction(pc);op,fmt,rt=w>>26,w>>21&31,w>>16&31
   if op==17 and fmt==8:
    condition=s.fp_condition;likely=bool(rt&2)
    if not rt&1:condition=e.negate(condition)
    for taken in e.choices(s,condition):
     n=deepcopy(s);e.assume(n,condition,taken)
     if taken or not likely:self.step(n,self.instruction(pc+4))
     active.append((pc+4+4*(((w&65535)^32768)-32768) if taken else pc+8,n))
   else:self.step(s,w);active.append((pc+4,s))
  return answers
def read_epochs(trace):
 groups=[];reads=Counter()
 for event in trace:
  if event[0]=='READ':reads[event]+=1
  else:groups.append((tuple(sorted(reads.items(),key=repr)),event));reads=Counter()
 groups.append(tuple(sorted(reads.items(),key=repr)));return groups
def relation(s,label):
 allowed={-24,-20,-16,-76,-144,-108,-104,-100,-140}
 assert all(size==4 and at in allowed for at,size in s.private_writes),('private-write escape',s.private_writes)
 assert s.r[29]==('STACK',-288) and s.r[17]==('OWNER',) and s.r[18]==('PAYLOAD',) and s.r[22]==('ENTRIES',)
 for i in range(21,32,2):assert s.f[i]==('ENTRY_FP',i),('saved odd FP register',i)
 if label=='return':
  assert s.r[2]==1,('return value',s.r[2]);return ()
 assert (s.r[19],s.r[20],s.r[21])==(24,255,('STACK',-108)),('live ring roles',s.r[19:22])
 assert {-108,-104,-100,-140}<=s.mem.keys(),('missing live setup home',sorted(s.mem))
 assert s.mem[-140]==e.add(('PAYLOAD',),52),('cached output pointer',s.mem.get(-140))
 return tuple(s.f[i] for i in(20,22,24,26,28,30,2,12)),tuple(s.mem[x] for x in(-108,-104,-100)),s.mem[-140],s.fcsr

def prove_words(words):
 truth=m.retail();frame=(-words[0])&65535;terms=Terms()
 a=Program(words,terms,frame).paths();b=Program(truth,terms,288).paths()
 assert a.keys()==b.keys(),('FP predicate paths',len(a),len(b),list(a.keys()-b.keys())[:1],list(b.keys()-a.keys())[:1])
 for key in a:
  x,y=a[key],b[key];assert x.fp==y.fp,('FP trace',key,x.fp,y.fp);assert x.effects==y.effects,('write/FP order',key,x.effects,y.effects)
  assert read_epochs(x.trace)==read_epochs(y.trace),('ordinary-read/write epochs',key,read_epochs(x.trace),read_epochs(y.trace))
  assert relation(x,key[0])==relation(y,key[0]),('live setup transfer',key,relation(x,key[0]),relation(y,key[0]))
 return dict(paths=len(a),ordered_FP_FCSR=True,ordinary_read_commutes_only_without_public_writes=True,live_loop_inputs=True,private_write_inventory=True,source_installed=False,c_match_credit=0)


def controls(words):
 controls=[]
 def reject(label,bad):
  try:prove_words(bad)
  except AssertionError as error:
   controls.append(dict(label=label,rejected=True,reason=str(error)[:200]));return
  raise AssertionError(('ineffective setup corruption',label))
 bad=words.copy();bad[0x164//4]^=1;reject('wrong-position-difference',bad)
 at=next(i for i,w in enumerate(words) if i*4>=0x154 and w>>26==17 and w>>21&31==16 and w&63==2 and w>>6&31==28)
 bad=words.copy();bad[at]^=2<<6;reject('lost-horizontal-step-liveout',bad)
 at=next(i for i,w in enumerate(words) if i*4>=0x154 and w==0xAEA10000)
 bad=words.copy();bad[at]+=4;reject('lost-copied-position-liveout',bad)
 at=next(i for i,w in enumerate(words) if i*4>=0x154 and w>>26==57 and w>>21&31==29)
 bad=words.copy();bad[at]=(bad[at]&0xFFFF0000)|0x50;reject('saved-frame-write',bad)
 renamed=words.copy();end=Program(words,Terms(),288).core
 swap=lambda n:24 if n==25 else 25 if n==24 else n
 for i in range(0x154//4,end//4):
  w=words[i];op,rs,rt,rd=w>>26,w>>21&31,w>>16&31,w>>11&31
  if op==17:
   if rs==4:w=(w&~(31<<16))|(swap(rt)<<16)
  elif op not in(2,3):
   w=(w&~(31<<21))|(swap(rs)<<21)
   if op not in(49,53,57,61):w=(w&~(31<<16))|(swap(rt)<<16)
   if op==0:w=(w&~(31<<11))|(swap(rd)<<11)
  renamed[i]=w
 assert renamed!=words;prove_words(renamed)
 return dict(effective_negatives=controls,temporary_GPR_renaming_accepted=True,whole_function_qualified=False,c_match_credit=0)
