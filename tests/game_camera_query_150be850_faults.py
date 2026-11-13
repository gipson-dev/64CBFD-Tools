from pathlib import Path
import runpy,sys
root=Path.cwd();sys.path.insert(0,str(root));out=root/'conker/build/game-camera-condition-150be850-screen'
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def audit(machine,programs,cases,fixture):
 total=0
 for case in cases:
  initial=fixture(case);complete=machine(programs[0],case,initial.copy()).run()
  for cut in range(complete.all_accesses):
   states=[]
   for words in (programs[0],programs[-1]):
    m=machine(words,case,initial.copy());m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('fault not triggered',case,cut))
    states.append((m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.trace,m.current_pc,m.delay_of))
   assert states[0]==states[1],(case,cut)
   total+=1
 return total
h=runpy.run_path(str(out/'query-guest.py'));C=h['Case'];helper=audit(h['Machine'],h['programs'],[C(-1,0x1001,0,0),C(0,0x2fff,0xffffffff,1),C(4,0xfabc,0x7fffffff,1)],h['fixture'])
g=runpy.run_path(str(out/'guest.py'));C=g['Case'];camera=audit(g['Machine'],g['programs'],[C(3,1,0,0,1,0,1),C(0,0,-1,8,0,1,0)],g['fixture'])
print('modeled access fault prefixes: helper',helper,'camera',camera,'retail equals guarded')
