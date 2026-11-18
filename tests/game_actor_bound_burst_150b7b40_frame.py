"""Locate all observed private homes; this is a proof input, not an equivalence proof."""
from collections import defaultdict
import json
from tools.tests import game_actor_bound_burst_150b7b40_oracle as g
def main():
 reports=[]
 for label,words in g.streams():
  if label=='portable-11':continue
  frame=65536-(words[0]&65535);roles=defaultdict(set);touched=set();incoming=set();seen=set()
  for c in g.cases():
   machine=g.Oracle(words,c,entry=g.ENTRY if label=='retail' else 0x15200000).run();home=g.STACK+c.phase
   for k,v in machine.roles.items():roles[k].add(v-home)
   for action,address,size,*rest in machine.trace:
    if action not in('R','W'):continue
    for at in range(address-home,address-home+size):
     if -frame<=at<0:touched.add(at)
     elif 0<=at<16:incoming.add(at)
   seen.update(machine.visits)
  assert set(roles)==set(range(1,14)) and all(len(v)==1 for v in roles.values())
  blocks={k:next(iter(v))for k,v in roles.items()};known=set(range(-frame,-frame+128))
  for k,off in blocks.items():
   span=set(range(off,off+g.SPANS[k]));assert not known&span;known.update(span)
  unmapped=touched-known
  def runs(values):
   answer=[]
   for n in sorted(values):
    if not answer or n!=answer[-1][0]+answer[-1][1]:answer.append([n,1])
    else:answer[-1][1]+=1
   return answer
  reports.append(dict(stream=label,frame=frame,escaped_blocks={str(k):dict(incoming_offset=v,bytes=g.SPANS[k])for k,v in sorted(blocks.items())},saved_and_outgoing_prefix_bytes=128,unmapped_touched_runs=runs(unmapped),observed_touched_bytes=len(touched),incoming_touched_runs=runs(incoming),unobserved_private_bytes=frame-len(touched),scope='129 finite guest cases; arbitrary-state proof pending'))
 report=dict(streams=reports,c_match_credit=0)
 (g.p/'frame-ledger.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
