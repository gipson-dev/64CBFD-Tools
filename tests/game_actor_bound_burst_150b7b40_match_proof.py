"""Complete raw/normalized parent relation and effective allocation controls.

Uses the established normal-execution/provider domain from the earlier parent
proof. Both frames and all 13 object homes are now identical. Physical faults,
interrupts and undeclared provider inputs are outside this relation.
"""
from copy import deepcopy
import json,struct
from tools.experiments import game_actor_bound_burst_150b7b40_match as source
from tools.tests import game_actor_bound_burst_150b7b40_proof as q
from tools.tests import game_actor_bound_burst_150b7b40_match_normalizer as normalizer

def run(words,terms,counts=False):
 program=q.Program(words,terms);paths=program.paths(0,{-4:'return'},q.State(False))
 if counts:
  assert len(paths)==257
  unseen=set(range(0,4*len(words),4))-program.seen
  assert len(unseen)==1 and words[next(iter(unseen))//4]==0x3c013f80
  for state in paths.values():
   if sum(state.calls.values()):
    assert state.calls[q.CHILD]==state.calls[q.SPRAY]==2 and state.calls[q.REAL]==6 and state.calls[q.SINE]==10
    assert state.calls[q.RNG]==4+state.calls[q.FLOOR]and state.calls[q.BURST]==state.calls[q.RADIAL]==state.calls[q.INIT]==state.calls[q.QUERY]==1
 answers={key:q.observe(state,key[0])for key,state in paths.items()}
 return answers,dict(paths=len(paths),static_words=len(words),reachable_words=len(program.seen),maximum_path_steps=max(s.steps for s in paths.values()))

def main():
 source.check_inputs();programs=source.programs();raw=programs[1][1];fixed=programs[2][1];assert fixed==programs[0][1]
 terms=q.Terms();expected,fixed_stats=run(fixed,terms,True);got,raw_stats=run(raw,terms,True);q.compare(got,expected);controls=[]
 def reject(label,words):
  try:bad,_=run(words,terms);q.compare(bad,expected)
  except(AssertionError,KeyError,ValueError)as error:
   reason=str(error);assert not any(v in reason for v in('unsupported','unbounded proof','opening escaped target')),(label,reason)
   controls.append(dict(label=label,rejected=True,reason=reason or type(error).__name__))
  else:raise AssertionError(('ineffective semantic negative',label))
 def flip(label,predicate,mask):
  at=[i for i,w in enumerate(raw)if predicate(w)];assert len(at)==1,(label,at);bad=raw[:];bad[at[0]]^=mask;reject(label,bad)
 flip('source-frame-size',lambda w:w==0x27bdfd98,8)
 flip('source-slot-width',lambda w:w==0x30b500ff,128)
 flip('source-first-output-home',lambda w:w==0x27a60250,4)
 at=[i for i,w in enumerate(raw)if w>>26==17 and w>>21&31==16 and w&63==3];assert len(at)==2
 bad=raw[:];i=at[0];w=bad[i];bad[i]=(w&~(31<<16|31<<11))|((w>>11&31)<<16)|((w>>16&31)<<11);reject('source-ratio-operand-order',bad)
 at=[i for i,w in enumerate(raw)if w>>26==17 and w>>21&31==4 and w>>16&31==0];assert at;bad=raw[:];bad[at[0]]^=4<<16;reject('source-zero-value-role',bad)
 flip('source-child-duration',lambda w:w>>26==9 and w>>21&31==0 and w&65535==300,1)
 flip('source-spray-resource',lambda w:w>>26==15 and w&65535==0x22,1)
 flip('source-loop-trip-count',lambda w:w==0x2a410002,3)
 flip('source-saved-return-home',lambda w:w==0xafbf007c,4)
 payload,refs=source.payload(source.OUT/'owner.o',source.NAME);lookup={v[1]:v[2][1]for v in source.symbol_rows((source.FROZEN/'conker/build/conker.us.elf').read_bytes())}
 for label in('FP-allocation','trig-copy','zero-transfer','model-read'):
  saved=normalizer.PLAN;plan=deepcopy(saved)
  if label=='FP-allocation':
   for phase in plan['permutations']:phase['f']=[]
  elif label=='model-read':plan['read_role_overrides']=[]
  else:
   emitted=[x['emit']for x in plan['order']if 'emit'in x]
   if label=='trig-copy':next(x for x in emitted if x['kind']=='copy-value'and x['source_register']==25)['source_register']=0
   else:
    for item in emitted:
     if item['kind']=='transfer-zero':item['destination_register']=8
  try:
   normalizer.PLAN=plan;blob,binding=normalizer.derive(payload,refs)
  finally:normalizer.PLAN=saved
  reject('normalizer-'+label,source.bound_blob(blob,binding,lookup))
 bad=fixed[:];assert bad[111]==0x10000009;bad[111]=(bad[111]&0xffff0000)|10;reject('normalizer-joined-radius-entry',bad)
 assert len(controls)==14;source.check_inputs()
 report=dict(passes=True,raw=raw_stats,normalized=fixed_stats,frame=616,all_13_object_homes_identical=True,canonical_private_and_incoming_bytes=544,identity_home_map=True,unmapped_accesses_rejected=True,effective_source_negatives=9,effective_normalizer_negatives=5,controls=controls,normal_execution_only=True,c_match_credit=0)
 (source.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report