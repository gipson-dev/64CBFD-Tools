"""Compare actor/private-stack overlaps without treating them as portable C."""
import itertools,json
from tools.tests import game_height_emitter_150e971c_guest_screen as g
original=g.actor;cases=0;raw_diff=[];guard_diff=[];errors=[]
try:
 for delta,(height,flag,mutation) in itertools.product(range(-128,129,4),((-5.,10,0),(-5.,10,2),(11.,9,0))):
  g.actor=g.STACK-0x170+delta
  initial=g.fixture(height,flag,0);results=[]
  for code in (g.truth,g.snapshot,g.guarded):
   try:
    m=g.Oracle(code,initial.copy(),mutation).run()
    results.append(('ok',m.r[2],m.seen,bytes(m.memory[g.actor+i] for i in range(0x1b0))))
   except Exception as ex:results.append(('exception',type(ex).__name__,str(ex)))
  if results[0]!=results[1]:raw_diff.append((delta,height,flag,mutation))
  if results[0]!=results[2]:guard_diff.append((delta,height,flag,mutation))
  if any(result[0]=='exception' for result in results):errors.append((delta,height,flag,mutation,[x[0:2] for x in results]))
  cases+=1
finally:g.actor=original
assert cases==195 and len(raw_diff)==195 and len(guard_diff)==0 and len(errors)==2
report={'cases_per_stream':cases,'raw_differences':len(raw_diff),'raw_examples':raw_diff[:8],
        'guarded_differences':len(guard_diff),'guarded_examples':guard_diff[:8],
        'exception_cases':len(errors),'exception_examples':errors[:5], 'uncredited':True}
(g.out/'overlap-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
