"""Whole-program literal identity plus independent semantic fixture controls."""
import hashlib,json
from tools.experiments import game_owner_setup_151a3390_recovery as m
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests import game_owner_setup_151a3390_oracle as g
from tools.experiments.game_curve_emitter_151a11e4_match import fields

def main():
 m.check_inputs();streams=m.programs();truth=streams['retail'];assert len(truth)==93
 assert all(words==truth for words in streams.values())
 # Equal instruction words at equal PCs, with equal relocation bindings, give
 # identical next-state transitions for every machine state, including FP/FCSR
 # and fault prefixes. Native C remains qualified separately on defined inputs.
 controls=[];sample=g.Case(173,1,home_mutation=1,channel=0xABCD00E7)
 alternate=[]
 for w in truth:
  for shift,kind in fields(w):
   if kind=='g'and w>>shift&31 in(8,9):w=(w&~(31<<shift))|((17-(w>>shift&31))<<shift)
  alternate.append(w)
 g.check(alternate,sample);controls.append(dict(label='independent-T0-T1-allocation',passes=True))
 for label,find,change in(
  ('descriptor-identity-byte',lambda w:w>>26==36 and w&65535==0x3B,lambda w:w+1),
  ('last-priority-slot',lambda w:w>>26==43 and w&65535==0x38,lambda w:w-4),
  ('saved-F20-pair',lambda w:w>>26==61,lambda w:w+(2<<16)),
  ('wrong-audio-distance',lambda w:w&0xFFFF==4000,lambda w:w+1),
  ('wrong-provider-order',lambda w:w==truth[47],lambda w:truth[50])):
  at=next(i for i,w in enumerate(truth)if find(w));bad=truth[:];bad[at]=change(bad[at])
  try:g.check(bad,sample)
  except AssertionError as error:
   reason=str(error);assert reason and not any(t in reason.lower()for t in('unsupported','unexpected provider','unbounded')),('invalid control',label,reason)
   controls.append(dict(label=label,rejected=True,reason=reason[:600]))
  else:raise AssertionError(('ineffective semantic control',label))
 raw,refs=payload(m.OUT/'qualified.o',m.NAME)
 report=dict(whole_function=True,paths=1,all_words_identical=93,relocation_bindings=len(refs),proof='Literal transition identity at identical PCs; no normalization or instruction omissions',FP_FCSR_and_fault_prefix_identity=True,controls=controls,raw_sha256=hashlib.sha256(raw).hexdigest(),source_installed=m.installed(),c_match_credit=0)
 (m.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs();return report
if __name__=='__main__':print(json.dumps(main()),flush=True)
