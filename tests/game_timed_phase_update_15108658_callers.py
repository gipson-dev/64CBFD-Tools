"""One bounded original callback window, real prologue, separate epilogue.

Only contracted ABI state is compared across different raw register allocation.
The full parent, cleanup dispatch and nonfinite FP are not qualified here.
"""
from pathlib import Path
from dataclasses import replace
import hashlib,itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_timed_phase_update_15108658_match as p
from tools.tests import game_timed_phase_update_15108658_guest as g
o=p.OUT
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
PARENT,WINDOW,END,EPILOGUE=0x151303ec,0x15130a0c,0x15130a50,0x15130a8c
TABLE_BYTES=(Path.cwd()/'conker/conker.us.bin').read_bytes()[0x22e220:0x22e2c0]
class Tracked(WindowCode):
 def __getitem__(self,pc):
  w=super().__getitem__(pc)
  if PARENT<=pc<=0x15130a98:self.owner.executed_parent.add(pc)
  return w
class Connected(g.Machine):
 def __init__(self,leaf,c,parent,selector,gate,change=None):
  super().__init__(leaf,c);self.parent_frame=g.STACK+c.phase-88;self.selector=selector;self.gate=gate;self.child_arguments=[];self.child_expected=None;self.child_fcsr=None;self.executed_parent=set()
  self.code.update(parent)
  if change:self.code[change[0]]=change[1]
  self.code=Tracked(self.code,self);self.entry=PARENT;self.code.ends=(PARENT+8,)
  self.memory[g.POINT+0x72]=selector&255
  for i,b in enumerate(TABLE_BYTES):self.memory[0x80089760+i]=b
  try:self.run();raise AssertionError('Missing original prologue boundary')
  except WindowBoundary:pass
  assert self.r[29]==self.parent_frame and g.read(self.memory,self.parent_frame+20)==self.before[31]
  self.entry=WINDOW;self.code.ends=(END,);self.r[7]=gate
 def record_call(self,t):
  if t!=g.ENTRY:return super().record_call(t)
  args=tuple(self.arguments(2));self.child_arguments.append(args);self.child_initial=dict(self.memory);self.child_fcsr=self.fcsr;self.child_expected=g.reference(self.memory,replace(self.c,fcsr=self.fcsr))
 def finish(self):
  try:self.run();raise AssertionError('Missing original caller boundary')
  except WindowBoundary:pass
  self.window_registers=self.r[:];self.window_memory=dict(self.memory);self.window_fcsr=self.fcsr
  self.entry=EPILOGUE;self.code.ends=();self.run();return self
def verify(m):
 expected_child=m.selector==24 and m.gate==0
 assert len(m.child_arguments)==int(expected_child)
 if expected_child:
  assert m.child_arguments==[(g.POINT,m.parent_frame+0x48)],'scratch pointer ABI'
  wanted,answer,calls,obs,fcsr=m.child_expected
  assert g.public(m.window_memory,m.c)==g.public(wanted,m.c),'public memory'
  assert m.calls==calls and m.observations==obs,'RNG contract'
  assert m.window_registers[2]==answer and m.window_registers[7]==int(answer==0),'zero return consumer'
  assert m.window_fcsr==fcsr,'FCSR'
 else:assert m.window_registers[7]==m.gate,'skip gate'
 assert m.window_registers[4]==g.POINT
 assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.saved_f
def main():
 full=(o/'baseline/conker/asm/15D730.s').read_text().split('glabel func_151303EC\n',1)[1].split('endlabel func_151303EC',1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',full);blob=bytes.fromhex(''.join(w for _,_,w in rows));rom=(Path.cwd()/'conker/conker.us.bin').read_bytes();assert len(rows)==428 and blob==rom[0x15d89c:0x15df4c]
 parent={int(va,16):int(w,16)for _,va,w in rows};programs=[g.bound_blob(*g.payload(o/(n+'.o'),'func_15108658'),g.symbols)for n in('original-target','selected-final/owner-candidate')];corpus=[(g.Case(remaining=v,cooldown=c,delta=.125,rng=r,mutation=mut,phase=phase,fcsr=rm),sel,gate)for v,c,r,mut,phase,rm,sel,gate in itertools.product((-1.,1.5,10.),(0.,2**-30,11.),(0.,.5),(0,1),(0,8),(0,3),(-1,24),(0,1))];seen=set();children=0
 for c,sel,gate in corpus:
  models=[]
  for ws in programs:
   m=Connected(ws,c,parent,sel,gate).finish();verify(m);models.append(m)
  a,b=models;assert a.memory==b.memory and a.calls==b.calls and a.observations==b.observations and a.window_fcsr==b.window_fcsr and a.child_arguments==b.child_arguments
  assert tuple(a.window_registers[i]for i in(2,4,7,29,31))==tuple(b.window_registers[i]for i in(2,4,7,29,31))
  seen.update(a.executed_parent);children+=len(a.child_arguments)
 controls=[]
 for name,at,word,c in [('scratch-storage',0x15130a30,0x27a5004c,g.Case()),('zero-return-consumer',0x15130a44,0x10400002,g.Case(remaining=-1.,cooldown=0.))]:
  m=Connected(programs[0],c,parent,24,0,(at,word)).finish()
  try:verify(m)
  except AssertionError:controls.append(dict(name=name,complete_window_and_separate_epilogue=True,rejected=True))
  else:raise AssertionError('Ineffective control')
 q=dict(cases_per_stream=len(corpus),streams=2,connected_children_per_stream=children,actual_parent_words_executed=len(seen),actual_parent_addresses=[hex(a)for a in sorted(seen)],original_two_word_prologue_and_separate_four_word_epilogue=True,bounded_window='15130A0C..15130A50',signed_selector_minus_one_and_A3_gates=True,callback_record_and_parentSP48_scratch_arguments=True,zero_return_A3_consumer=True,public_memory_and_private_frame_and_saved_registers_and_RNG_observations_equal=True,raw_caller_scratch_GPR_FPR_equality_not_claimed=True,complete_parent_and_cleanup_not_qualified=True,finite_traps_disabled_model_only=True,effective_controls=controls,source_installed=p.installed(),matching_credit=0,parent_matching_credit=0)
 (o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
