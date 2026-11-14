"""Explore actor/private-stack overlap without treating it as portable C."""
import itertools,json
from tools.tests import game_motion_crossing_150e6230_guest as g
original=g.actor;cases=0;raw_diff=[];guard_diff=[];errors=[]
try:
 for delta,(enabled,dotvalue,sign,selector,mutation) in itertools.product(range(-128,129,4),((0,1.,1.,-1,0),(1,-1.,1.,-1,0),(1,-1.,1.,0,3))):
  g.actor=g.STACK-0x110+delta;initial=g.fixture(enabled,sign,selector,0);results=[]
  for code in (g.truth,g.candidate,g.guarded):
   try:
    m=g.Oracle(code,initial.copy(),dotvalue,mutation,0x1fe).run()
    results.append(('ok',m.r[2],m.observed,bytes(m.memory[g.actor+i] for i in range(0x180))))
   except Exception as ex:results.append(('exception',type(ex).__name__,str(ex)))
  if results[0]!=results[1]:raw_diff.append(delta)
  if results[0]!=results[2]:guard_diff.append(delta)
  if any(result[0]=='exception' for result in results):errors.append((delta,[x[0:2] for x in results]))
  cases+=1
finally:g.actor=original
assert cases==195 and len(raw_diff)==116 and not guard_diff and len(errors)==22
report={'cases_per_stream':cases,'raw_differences':len(raw_diff),'guarded_differences':len(guard_diff),'exception_cases':len(errors),'exception_examples':errors[:4],'uncredited':True}
(g.out/'overlap-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
