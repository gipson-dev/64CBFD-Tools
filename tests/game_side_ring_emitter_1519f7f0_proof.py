"""Inductive five-phase proof and effective controls for the emitter.

Contract: mapped/aligned ordinary memory; immutable code/literal storage;
disjoint private stack; o32 providers preserve saved registers and cannot
inspect code/return PCs or unpassed locals. Public reads/aliases, provider
mutations and initial/callback FCSR are arbitrary. Ordered FP opcode, operands
and status transfer are compared as uninterpreted operations, jointly with
public writes/calls. Only three explicitly checked ordinary-memory commutes
are admitted. This does not claim raw fault-register/PC equality or defined C
semantics for the retained uninitialized inverse/transition bytes.

Cuts: entry -> movement/transition/return; movement -> one emission/return;
emission -> tail; tail -> next emission/return; identical epilogue. Protected
frame write inventories preserve every unpassed live slot and saved register.
The emission backedge is inductive, without an iteration-count bound.
"""
import json
from pathlib import Path
from tools.tests import game_side_ring_emitter_1519f7f0_prefix_proof as prefix
from tools.tests import game_side_ring_emitter_1519f7f0_transition_proof as transition
from tools.tests import game_side_ring_emitter_1519f7f0_prelude_proof as prelude
from tools.tests import game_side_ring_emitter_1519f7f0_core_proof as core
from tools.tests import game_side_ring_emitter_1519f7f0_tail_proof as tail

def rename(words,start,end,pair):
 result=words[:]
 for i in range(start//4,end//4):
  w=result[i];op=w>>26
  fields=(21,16,11) if op==0 else (21,) if op in (49,53,57,61) else (16,) if op==15 else () if op in (3,17) else (21,16)
  if op==17 and w>>21&31 in (0,4):fields=(16,)
  for shift in fields:
   reg=w>>shift&31
   if reg in pair:w=(w&~(31<<shift))|((sum(pair)-reg)<<shift)
  result[i]=w
 assert result!=words
 return result

def swap_fp(w):
 fs,ft=w>>11&31,w>>16&31
 return (w&~((31<<11)|(31<<16)))|(fs<<16)|(ft<<11)

def qualify(raw,retail):
 reports={}
 for name,engine,start,end,pair,tests in (
  ('prefix',prefix,0,0x110,(8,9),(
   ('active-field',0x44,lambda w:w+4),('identity-byte',0x60,lambda w:w-1),
   ('seed-y',0xC4,lambda w:w+4),('flag-mask',0xD8,lambda w:w^12),
   ('query-mode-byte',0xF4,lambda w:w-1),('annulled-query-delay',0x108,lambda w:(w&0x3FFFFFF)|(5<<26)))),
  ('transition',transition,0x110,0x19C,(14,15),(
   ('owner-reload-field',0x118,lambda w:w+4),('mode-byte-home',0x158,lambda w:w+1),
   ('copy-size',0x170,lambda w:w^1),('second-output',0x18C,lambda w:w+4),('factory-class',0x148,lambda w:w+1))),
  ('prelude',prelude,0x1A0,0x3F4,(13,14),(
   ('ordered-dy-operands',0x1D4,swap_fp),('epsilon-literal',0x1A4,lambda w:w+4),
   ('inverse-home',0x250,lambda w:w-4),('smoothing-cursor',0x348,lambda w:w-1),('step-x-home',0x3BC,lambda w:w-4))),
  ('core',core,0x3F4,0x558,(10,11),(
   ('nonzero-divisor',0x458,lambda w:w-1),('post-rng-counter',0x450,lambda w:w+2),
   ('motion-fp-operands',0x490,swap_fp),('floor-bottom-operands',0x52C,swap_fp),('floor-query-point',0x524,lambda w:w+4))),
  ('tail',tail,0x558,0x648,(14,15),(
   ('tail-counter-byte',0x56C,lambda w:w-1),('capacity-wrap',0x564,lambda w:w+1),
   ('phase-decrement-operands',0x604,swap_fp),('step-x-home',0x5C4,lambda w:w-4),('final-position-store',0x634,lambda w:w+4)))
 ):
  expected=engine.prove(raw,retail)
  assert engine.prove(rename(raw,start,end,pair),retail)==expected,(name,'allocation positive control')
  results=[]
  for label,pc,change in tests:
   wrong=raw[:];wrong[pc//4]=change(wrong[pc//4]);assert wrong!=raw
   try:engine.prove(wrong,retail)
   except AssertionError as error:
    reason=str(error)
    assert reason and not any(x in reason for x in ('unsupported','escaped code','unbounded proof','proof bound')),(name,label,'invalid control',reason[:200])
    results.append(dict(name=label,offset=hex(pc),rejection=reason[:180]))
   else:raise AssertionError((name,label,'ineffective control'))
  reports[name]=dict(independent_GPR_allocation_positive_control=True,controls=results)
  print(name,len(results),'semantic controls passed',flush=True)
 return reports

def prove(raw,retail):
 reports={}
 for name,engine in (('prefix',prefix),('transition',transition),('prelude',prelude),('core',core),('tail',tail)):
  reports[name]=engine.prove(raw,retail)
 assert raw[0x648//4:]==retail[0x648//4:] and len(raw)==len(retail)==415
 return dict(phases=reports,epilogue_identical=True,whole_CFG_phase_relation=True,ordered_FP_and_FCSR=True,
             private_exposed_homes_preserved=True,initialized_inverse_not_assumed=True,
             source_C_undefined_states_not_qualified=True)

def main():
 from tools.experiments import game_side_ring_emitter_1519f7f0_match as source
 p=source.programs();report=prove(p['candidate'],p['retail']);report['controls']=qualify(p['candidate'],p['retail'])
 (source.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
