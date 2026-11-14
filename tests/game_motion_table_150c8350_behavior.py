"""Compare independent state and access order on signed boundary cases."""
from tools.tests.game_motion_table_150c8350_common import *
count=0
for pattern,ticks,half,seed in itertools.product(range(8),(0,1,3,0xffffffff,0x08000000),(0,1,127,255),(1,3)):
 initial=fixture(pattern,ticks,half,seed);wanted=public(model(initial));states=[]
 for label in ('retail','raw','guarded'):
  m=FactoryOracle(programs[label],initial.copy(),Case(),entry=entry,s={},arguments=(0,)).run();assert public(m.memory)==wanted,(label,pattern,ticks,half,seed)
  states.append((accesses(m),m.r,m.hi,m.lo))
 assert states[0]==states[1]==states[2];count+=1
assert count==320
report={'cases_per_stream':count,'streams':3,'full_registers_and_public_access':True,'uncredited':True}
(out/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
