"""Instruction-driven seed and initial normalization; texture/geometry stay open."""
from copy import deepcopy
from pathlib import Path
import json
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests import game_side_ring_renderer_1519fe6c_opening_proof as opening
from tools.tests import game_side_ring_renderer_1519fe6c_setup_proof as setup
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms

class State(opening.State):
 def __init__(self,side):
  base=opening.initial(side,'seed');self.__dict__.update(base.__dict__)
  self.r=[('DEAD',side,'seed',i) if e.tagged(v,'DEAD') else v for i,v in enumerate(self.r)]
  self.f=[('DEAD_FP',side,'seed',i) if e.tagged(v,'DEAD_FP') else v for i,v in enumerate(self.f)]
  self.r[2]=('OUTPUT_AFTER_SETUP',);self.r[16]=('STACK',-95)
  self.store(('STACK',-8),4,('PACKET',))
  if side=='retail':self.store(('STACK',-12),4,('RECORDS',))
  self.private_writes=[];self.fp=[];self.fp_condition=None
 def load(self,address,size,pool):
  if e.tagged(address,'STACK'):assert all(address[1]+i in self.mem for i in range(size)),('uninitialized seed private read',self.side,address,size)
  if address==g.S['D_800A8D00']:
   assert size==4;return 0x38D1B717
  return super().load(address,size,pool)

class Program(setup.Program):
 def __init__(self,words,terms):super().__init__(words);self.terms=terms
 def step(self,s,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==4:s.f[w>>11&31]=s.r[w>>16&31]
  elif op==17 and fmt==16:
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31
   if fn==6:s.f[fd]=s.f[fs]
   else:
    assert fn in (0,1,2,3,4,5,7,13,50,60),('unsupported seed FP',hex(w))
    args=(s.f[fs],s.f[ft]) if fn in(0,1,2,3,50,60) else (s.f[fs],)
    observation=(fn,args,s.fcsr);s.fp.append(observation);s.trace.append(('FP',observation))
    value=self.terms.term('FP_VALUE',*observation);s.fcsr=self.terms.term('FP_STATUS',*observation)
    if fn in(50,60):s.fp_condition=value
    else:s.f[fd]=value
  else:super().step(s,w)
 def paths(self,start,stops,initial):
  states=[(start,initial)];answers={};work=0
  while states:
   pc,s=states.pop();work+=1;s.steps+=1
   assert work<20000 and s.steps<500,('unbounded seed proof',start,len(answers),hex(pc))
   if s.steps>1 and pc in stops:
    key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)));assert key not in answers,('duplicate seed path',key);answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31;floating=op==17 and rs==8
   if floating or op in (1,4,5,6,7,20,21,22,23):
    if floating:
     assert rt in(0,1,2,3);condition=s.fp_condition;assert condition is not None
     if not rt&1:condition=e.negate(condition)
     likely=bool(rt&2)
    elif op==1:
     assert rt in(0,1,2,3);condition=e.pred('SLT',s.r[rs],0)
     if rt in(1,3):condition=e.negate(condition)
     likely=rt in(2,3)
    else:
     if op in(4,5,20,21):condition=e.pred('EQ',s.r[rs],s.r[rt])
     else:assert rt==0;condition=e.pred('SLT',0,s.r[rs])
     if op in(5,21,6,22):condition=e.negate(condition)
     likely=op>=20
    for taken in e.choices(s,condition):
     n=deepcopy(s);e.assume(n,condition,taken)
     if taken or not likely:self.step(n,self.instruction(pc+4))
     dest=pc+4+4*e.signed((w&65535)|(-65536 if w&32768 else 0)) if taken else pc+8
     states.append((dest,n))
   else:
    assert op!=3 and not(op==0 and w&63==8),('unexpected seed call/return',hex(pc))
    self.step(s,w);states.append((pc+4,s))
  return answers

def trace(s):
 # This complete cut is read-only public memory with no provider calls.
 # All bytes are mapped ordinary RAM and stable for the cut. Moving a read
 # across an FP instruction cannot mutate RAM/FCSR, fault, or create MMIO
 # effects. Keep every address/width/multiplicity, and keep FP/FCSR order
 # exactly; raw access timing or exception-register/PC identity is not claimed.
 assert all(event[0] in ('READ','FP') for event in s.trace),('seed public mutation',s.trace)
 return sorted((event for event in s.trace if event[0]=='READ'),key=repr)+[event for event in s.trace if event[0]=='FP']

def relation(s):
 opening.saved(s)
 width=-40 if s.side=='raw' else -76
 allowed=set(range(-36,-12,4))|{width}
 assert all(size==4 and off in allowed for off,size in s.private_writes),('seed private write escape',s.side,s.private_writes)
 assert s.r[19 if s.side=='raw'else 18]==36
 byte=lambda v:e.bitop('AND',v,255)
 live=(s.r[16],s.r[17],s.r[7 if s.side=='raw'else 8],s.r[2],byte(s.r[5]),byte(s.r[11]),s.r[4 if s.side=='raw'else 10],s.r[9 if s.side=='raw'else 7],tuple(s.load(('STACK',n),4,b'') for n in range(-36,-12,4)),s.load(('STACK',width),4,b''),tuple(s.f[i] for i in(2,6,12,14,16,18,20,22)),tuple(s.f[24:]),s.load(('STACK',-4),4,b''),s.load(('STACK',-8),4,b''),s.r[18] if s.side=='raw'else s.r[12])
 return trace(s),s.fp,s.fcsr,live

def prove(raw,retail):
 terms=Terms();results={}
 for side,words,start,stop in(('raw',raw,0x274,0x430),('retail',retail,0x270,0x42C)):
  results[side]=Program(words,terms).paths(start,{stop:'texture'},State(side))
 a,b=results['raw'],results['retail']
 assert a.keys()==b.keys(),('seed path predicates',len(a),len(b),next(iter(a.keys()-b.keys()),None),next(iter(b.keys()-a.keys()),None))
 for key in a:
  left,right=relation(a[key]),relation(b[key])
  if left!=right:
   mismatch=next((i for i,(x,y) in enumerate(zip(left[0],right[0])) if x!=y),None)
   raise AssertionError(('seed transfer',key,'event',mismatch,left[0][mismatch] if mismatch is not None else left,right[0][mismatch] if mismatch is not None else right))
 return dict(symbolic_paths=len(a),seed_and_initial_epsilon_normalization=True,complete_read_only_seed_access_multiset=True,mapped_stable_ordinary_reads_may_cross_FP=True,arbitrary_FP_words_and_ordered_FCSR=True,FP_traps_not_assumed_disabled=True,raw_memory_access_timing_and_fault_PC_claimed=False,retail_alpha_compared_at_byte_consumer=True,private_previous_width_homes=dict(raw=-40,retail=-76),texture_proved=False,whole_function=False,c_match_credit=0)

def main():
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 image=(g.R/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(image,g.S['D_800A8D00'],4);assert image[at:at+4]==bytes.fromhex('38d1b717')
 p=g.programs();raw,retail=p['candidate'],p['retail'];report=prove(raw,retail);controls=[]
 alternative=raw[:]
 for pc in range(0x274,0x430,4):
  w=alternative[pc//4];op,fn,fmt=w>>26,w&63,w>>21&31
  if op==0:fields=(16,11) if fn in(0,2,3) else (21,16,11) if fn in(33,35,36,37,42,43) else (11,) if fn in(16,18) else (21,16) if fn==25 else ()
  elif op==17:fields=(16,) if fmt in(0,4) else ()
  elif op in(49,57,1):fields=(21,)
  elif op==15:fields=(16,)
  else:fields=(21,16)
  for shift in fields:
   reg=w>>shift&31
   if reg in(14,15):w=(w&~(31<<shift))|((29-reg)<<shift)
  alternative[pc//4]=w
 assert alternative!=raw and prove(alternative,retail)==report
 wide=raw[:]
 for pc in(0x2F0,0x3E8):
  w=wide[pc//4];assert w>>26==12 and w&65535==255
  wide[pc//4]=((w>>21&31)<<21)|((w>>16&31)<<11)|37
 assert wide!=raw and prove(wide,retail)==report
 report['independent_scratch_allocation_positive_control']=True
 report['deferred_alpha_byte_narrowing_positive_control']=True
 for name,pc,change in(
  ('attached-position-component',0x2B4,lambda w:w+4),
  ('record-height-component',0x388,lambda w:w-4),
  ('seed-index-wrap',0x2A0,lambda w:w-1),
  ('signed-previous-tag',0x2DC,lambda w:w^(4<<26)),
  ('previous-alpha-bit',0x2F0,lambda w:w^0x80),
  ('current-alpha-bit',0x3E8,lambda w:w^0x80),
  ('absolute-dx',0x3BC,lambda w:w^2),
  ('epsilon-comparison',0x3C8,lambda w:w^14),
  ('previous-width-home',0x2D0,lambda w:w+4)):
  wrong=raw[:];wrong[pc//4]=change(wrong[pc//4]);assert wrong!=raw
  try:prove(wrong,retail)
  except AssertionError as error:
   reason=str(error);assert not any(x in reason for x in('unsupported','unbounded seed proof','escaped code')),('invalid seed control',name,reason)
   controls.append(dict(name=name,rejected=reason[:180]))
  else:raise AssertionError(('ineffective seed control',name))
 wrong=raw[:];wrong[0x3BC//4],wrong[0x3C0//4]=wrong[0x3C0//4],wrong[0x3BC//4]
 try:prove(wrong,retail)
 except AssertionError as error:
  reason=str(error);assert not any(x in reason for x in('unsupported','unbounded seed proof','escaped code')),reason
  controls.append(dict(name='independent-FP-operation-order',rejected=reason[:180]))
 else:raise AssertionError('ineffective FP order control')
 report['effective_controls']=controls;out=g.O;(out/'seed-proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
