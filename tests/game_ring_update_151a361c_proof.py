"""All-word literal identity, structural reachability and semantic controls."""
import hashlib,json
from tools.experiments import game_ring_update_151a361c_recovery as m
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests import game_ring_update_151a361c_oracle as g

def reachable(words):
 todo=[0];seen=set()
 while todo:
  pc=todo.pop()
  if pc in seen:continue
  assert 0<=pc<len(words)*4;seen.add(pc);w=words[pc//4];op=w>>26
  if op in(1,4,5,6,7,20,21,22,23):
   seen.add(pc+4);target=pc+4+4*(((w&65535)^32768)-32768);todo.append(target)
   if not(op==4 and w>>21&31==w>>16&31):todo.append(pc+8)
  elif op==0 and w&63==8:seen.add(pc+4)
  else:todo.append(pc+4)
 return seen

def main():
 m.check_inputs();streams=m.programs();truth=streams['retail'];assert len(truth)==105 and all(words==truth for words in streams.values())
 seen=reachable(truth);dead=set(range(0,420,4))-seen;assert dead=={0xAC,0x188}
 controls=[];corpus=g.cases()[::113]+g.cases()[-256:]
 for label,find,change in(
  ('early-count-gate',lambda w:w>>26==10 and w&65535==2,lambda w:w-1),
  ('mark-byte',lambda w:w>>26==9 and w&65535==255,lambda w:w-1),
  ('clear-flag-bit',lambda w:w>>26==9 and w&65535==65533,lambda w:w+1),
  ('growth-operation',lambda w:w>>26==17 and w>>21&31==16 and w&63==2,lambda w:w-2)):
  at=next(i for i,w in enumerate(truth)if find(w));candidate=truth[:];candidate[at]=change(candidate[at]);caught=False
  for c in corpus:
   try:g.check(candidate,c)
   except AssertionError as error:
    reason=str(error);assert reason and not any(t in reason.lower()for t in('unsupported','instruction limit','unowned','domain','unexpected')),('invalid control',label,reason)
    controls.append(dict(label=label,rejected=True,reason=reason[:600]));caught=True;break
  assert caught,('ineffective semantic control',label)
 raw,refs=payload(m.OUT/'qualified.o',m.NAME)
 report=dict(whole_function=True,all_words_identical=105,reachable_words=len(seen),unreachable_words_retained=sorted(dead),relocation_bindings=len(refs),proof='Literal instruction and binding identity at equal PCs, including unreachable words; no normalization',FP_FCSR_and_fault_prefix_identity=True,controls=controls,raw_sha256=hashlib.sha256(raw).hexdigest(),source_installed=m.installed(),c_match_credit=0)
 (m.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs();return report
if __name__=='__main__':print(json.dumps(main()),flush=True)
