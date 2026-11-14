"""Compare private-frame and actor overlaps without treating them as portable C."""
import json
from tools.tests import game_timed_motion_150f48d0_guest as g
count=0;different=[];errors=[]
for delta in range(-80,81,4):
 for timer,tick,mutation in ((12.,.5,0),(12.,.5,1),(1.,2.,0)):
  actor=g.STACK-0x170+delta;initial=g.fixture(actor,timer,tick,0);pair=[]
  for words in (g.truth,g.candidate,g.guarded):
   try:
    m=g.Oracle(words,initial.copy(),actor,mutation).run();pair.append((m.memory,m.r[2],m.observed))
   except Exception as ex:pair.append((type(ex).__name__,str(ex)))
  if pair[0]!=pair[1] or pair[0]!=pair[2]:different.append((delta,timer,tick,mutation))
  if any(not isinstance(v[0],dict) for v in pair):errors.append((delta,timer,tick,mutation,*[str(v)[:150] for v in pair]))
  count+=1
report={'cases_per_stream':count,'streams':3,'different':len(different),'examples':different[:8],'modeled_exceptions':len(errors),'exception_examples':errors[:4],'uncredited':True}
(g.out/'stack-alias.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
