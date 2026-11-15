"""Ordered symbolic FP setup and smoothing for the literal-pool C candidate."""
from copy import deepcopy
from pathlib import Path
import json
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests import game_side_ring_emitter_1519f7f0_oracle as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

class State(e.State):
 def __init__(self,side):
  super().__init__('common','prelude');self.side=side;self.r[29]=('STACK',-280);self.mem={-8:('ENTRIES',)};self.effects=[];self.private_writes=[]
  self.r[16]=e.add(('EFFECT',),16);self.r[17]=('EFFECT',);self.r[19]=('PAYLOAD',);self.r[20]=('ACTOR',)
  self.f[4]=('ACTOR_X',);self.fcsr=('LIVE_FCSR',);self.fp=[];self.fp_condition=None
 def load(self,address,size,pool):
  if not e.tagged(address,'STACK'):return super().load(address,size,pool)
  assert size==4 and address[1]%4==0
  return self.mem.get(address[1],('PRIVATE_ENTRY_WORD',address[1]))
 def store(self,address,size,value):
  if not e.tagged(address,'STACK'):
   super().store(address,size,value);self.effects.append(self.trace[-1]);return
  assert size==4 and address[1]%4==0;self.mem[address[1]]=value;self.private_writes.append((address[1],size))

class Program(e.Program):
 def __init__(self,words,terms,side):super().__init__(words,b'',g.ENTRY);self.terms=terms;self.side=side
 def step(self,s,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==4:s.f[w>>11&31]=s.r[w>>16&31]
  elif op==17 and fmt==16 and fn in (0,1,2,3,4,5,7,60):
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31;args=(s.f[fs],) if fn in (4,5,7) else(s.f[fs],s.f[ft]);event=(fn,args,s.fcsr);s.fp.append(event);s.effects.append(('FP',event))
   value=self.terms.term('FP_VALUE',*event);s.fcsr=self.terms.term('FP_STATUS',*event)
   if fn==60:s.fp_condition=value
   else:s.f[fd]=value
  else:super().step(s,w)
 def paths(self):
  states=[(0x1A0,State(self.side))];answers={};work=0
  while states:
   pc,s=states.pop();work+=1;s.steps+=1;assert work<30000 and s.steps<250,('prelude proof bound',pc)
   if pc in (0x3F4,0x648):
    key=('loop' if pc==0x3F4 else 'return',tuple(sorted(s.facts.items(),key=repr)));assert key not in answers;answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31;floating=op==17 and rs==8
   if floating or op in (1,4,5,20,21):
    if floating:condition=s.fp_condition;likely=bool(rt&2);invert=not rt&1
    elif op==1:
     assert rt in (1,3);condition=e.negate(e.pred('SLT',s.r[rs],0));likely=rt==3;invert=False
    else:condition=e.pred('EQ',s.r[rs],s.r[rt]);likely=op in(20,21);invert=op in(5,21)
    if invert:condition=e.negate(condition)
    for taken in e.choices(s,condition):
     n=deepcopy(s);e.assume(n,condition,taken)
     if taken or not likely:self.step(n,self.instruction(pc+4))
     dest=pc+4+4*(((w&65535)^32768)-32768) if taken else pc+8;states.append((dest,n))
   else:self.step(s,w);states.append((pc+4,s))
  return answers

def relation(s,label):
 permitted={-36,-80,-76,-72,-64,-112,-108,-8}
 permitted.update(x-280 for x in ((0x80,0x74,0x70,0x6C,0x68) if s.side=='raw' else (0x84,0x7C,0x78,0x74,0x70)))
 assert all(size==4 and off in permitted for off,size in s.private_writes),('prelude private write escape',s.private_writes)
 assert s.r[29]==('STACK',-280) and s.r[17]==('EFFECT',) and s.r[19]==('PAYLOAD',) and s.r[20]==('ACTOR',)
 live=()
 if label=='loop':
  homes=(0x74,0x70,0x6C,0x68) if s.side=='raw' else (0x7C,0x78,0x74,0x70)
  assert all(x-280 in s.mem for x in homes),('missing step home',homes)
  steps=tuple(s.mem[x-280] for x in homes)
  assert s.r[3]==36 and s.r[7]==('ENTRIES',) and s.r[12 if s.side=='raw' else 11]==('STACK',-112)
  live=(tuple(s.f[i] for i in (20,22,24,26,28)),steps,tuple(s.mem[x] for x in(-80,-76,-72,-64,-112,-108)),
        s.mem[(0x80 if s.side=='raw' else 0x84)-280],s.r[3],s.r[7],s.lo,s.r[1],s.r[8 if s.side=='raw' else 25])
 else:assert s.r[2]==1
 return s.effects,s.trace,s.fp,s.fcsr,live
def prove(raw,retail):
 terms=Terms();a=Program(raw,terms,'raw').paths();b=Program(retail,terms,'retail').paths()
 assert a.keys()==b.keys(),('prelude predicates',len(a),len(b),list(a.keys()-b.keys())[:1],list(b.keys()-a.keys())[:1])
 for key in a:
  x,y=relation(a[key],key[0]),relation(b[key],key[0]);assert x==y,('prelude transfer',key,x,y)
 return dict(symbolic_paths=len(a),ordered_FP_and_FCSR=True,arbitrary_initial_FCSR=True,arbitrary_public_reads=True,
             uninitialized_inverse_word_preserved=True,private_spill_relation=True,smoothing_indices=True,whole_function=False)
