from pathlib import Path
import json
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_motion_table_150c8350_common import *
guard=programs['guarded'];assert guard==truth
cases=((0,0,0,1),(3,1,255,1),(1,0xffffffff,127,3),(6,0x08000000,1,3));total=0
for spec in cases:
 initial=fixture(*spec);complete=FactoryOracle(truth,initial.copy(),Case(),entry=entry,s={},arguments=(0,)).run()
 for cut in range(complete.all_accesses+1):
  states=[]
  for code in (truth,programs['raw'],guard):
   m=FactoryOracle(code,initial.copy(),Case(),entry=entry,s={},arguments=(0,));m.cut=cut
   try:m.run();done=True
   except AccessBoundary:done=False
   states.append((done,m.memory,m.trace,m.r,m.hi,m.lo,m.current_pc,m.delay_of))
  assert states[0]==states[1]==states[2],(spec,cut);total+=1
report={'fixtures':len(cases),'prefixes_per_stream':total,'streams':['retail','raw','guarded'],'full_machine_state':True,'uncredited':True};(out/'fault.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
