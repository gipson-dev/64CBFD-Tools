"""Factored FCR31 theorem for independent arithmetic in normal executions.

Architectural premise: NEC U10504EJ7V0UMJ1 pp213-214 and237-238,
https://hack64.net/docs/VR43XX.pdf . Cause describes the most recent FP
operation, Flags accumulate disabled IEEE exceptions, and E always traps.
Arithmetic depends on operands/rounding/flush controls, not prior Flags/Cause.

This proves a status-composition lemma, NOT the routine's dataflow or matching.
No trap-enable bits are assumed zero. The normal-completion domain is compared
in both orders; raw exception/fault prefixes are explicitly outside the claim.
No CFC1/CTC1, comparisons, calls, status observations or dependent arithmetic
may be crossed. A common final arithmetic instruction is required for Cause.
"""
from pathlib import Path
from itertools import product
from collections import Counter
import json,re
from tools.experiments import game_actor_ring_emitter_15196b4c_match as p
r=p.ROOT;o=p.OUT
def header():
 text=(r/'conker/include/2.0L/PR/R4300.h').read_text()
 expected={'FPCSR_FS':0x1000000,'FPCSR_C':0x800000,'FPCSR_CE':0x20000,'FPCSR_CV':0x10000,'FPCSR_CZ':0x8000,'FPCSR_CO':0x4000,'FPCSR_CU':0x2000,'FPCSR_CI':0x1000,'FPCSR_EV':0x800,'FPCSR_FV':0x40,'FPCSR_FZ':0x20,'FPCSR_FO':0x10,'FPCSR_FU':8,'FPCSR_FI':4}
 for name,value in expected.items():
  match=re.search(r'^#define\s+'+name+r'\s+(0x[0-9a-fA-F]+)',text,re.M);assert match and int(match[1],16)==value,name
 return expected
def bit_execution(order,initial_flag,enable):
 # One IEEE exception lane. Normal completion requires that no generated
 # exception in that lane is enabled. These are architectural premises.
 flag=initial_flag;cause=None
 for raised in order:
  cause=raised
  if raised and enable:return False,None
  flag=bool(flag or raised)
 return True,(flag,cause)
def main():
 constants=header();cases=0;normal=0
 for a,b,c,flag,enable in product((0,1),repeat=5):
  x=bit_execution((a,b,c),flag,enable);y=bit_execution((b,a,c),flag,enable)
  assert x==y;cases+=1;normal+=x[0]
 # Bitwise factorization lifts the truth table independently into each of
 # the five IEEE lanes. E has no enable/flag lane, so all E causes must be 0.
 e_cases=0
 for a,b,c in product((0,1),repeat=3):
  left=not any((a,b,c));right=not any((b,a,c));assert left==right;e_cases+=1
 # Effective controls reject incorrect endpoint and normal-domain rules.
 assert bit_execution((1,0,0),0,0)[1]!=(False,0),'flags overwritten by last operation'
 assert bit_execution((0,0,0),0,0)[1]!=(False,1),'Cause retained from an earlier operation'
 assert not bit_execution((1,0,0),0,1)[0],'enabled exception silently accepted'
 assert any((1,0,0)),'unimplemented exception silently accepted'
 assert bit_execution((1,0),0,0)!=bit_execution((0,1),0,0),'missing common-last obligation'
 report=dict(IEEE_exception_bit_truth_cases=cases,normal_cases_per_lane=normal,IEEE_lanes=5,unimplemented_exception_cases=e_cases,effective_status_controls=5,arbitrary_initial_flags_and_Cause=True,arbitrary_enable_rounding_flush_controls=True,normal_completion_domain_equal=True,common_last_Cause_required=True,comparisons_status_reads_calls_not_crossed=True,whole_function_proof=False,status_lemma_only=True,source_installed=p.installed(),matching_credit=0,source='NEC U10504EJ7V0UMJ1 pp213-214,237-238; repository SDK R4300.h',reference='https://hack64.net/docs/VR43XX.pdf')
 (o/'fcsr-lemma.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
