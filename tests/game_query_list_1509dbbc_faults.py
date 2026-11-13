from pathlib import Path
import runpy,sys
root=Path.cwd();sys.path.insert(0,str(root));out=root/'conker/build/game-query-list-1509dbbc-screen';g=runpy.run_path(str(out/'guest.py'))
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_point_transform_match import put
M,C,programs,STACK=g['Machine'],g['Case'],g['programs'],g['STACK'];count=0
for c in (C(0,0,0),C(4,1,0),C(25,4,0),C(25,4,1),C(25,4,7)):
 initial=g['fixture'](c);complete=M(programs[0],c,initial.copy()).run()
 for cut in range(complete.all_accesses):
  states=[]
  for p in (programs[0],programs[2],programs[3]):
   m=M(p,c,initial.copy());m.cut=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('fault not triggered',c,cut))
   states.append((m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.trace,m.current_pc,m.delay_of))
  assert states[0]==states[1]==states[2],(c,cut);count+=1
print(count,'retail and padded access-fault prefixes agree')
aliases=0
for addr in (STACK-0x80,STACK-0x58,STACK-0x48,STACK-0x40,STACK-0x38,STACK-0x34,STACK-0x28,g['ROWS']+0x30):
 for kind in (0,2):
  c=C(25,4,0);initial=g['fixture'](c);put(initial,g['ROWS']+54*4,addr);put(initial,addr+8,0);initial[addr+0x48]=kind
  results=[]
  for p in programs:
   m=M(p,c,initial.copy())
   try:m.run();results.append(('completed',g['public'](m.memory),m.r[2]))
   except (AssertionError,KeyError) as exc:results.append(('invalid',type(exc).__name__,str(exc)))
  assert results.count(results[0])==len(results),(hex(addr),kind,[(r[0],r[-1]) for r in results]);aliases+=1
print(aliases,'constructed stack/global-alias outcomes agree across retail, raw and both guarded streams')
