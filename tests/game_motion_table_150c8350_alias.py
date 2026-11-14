"""Exercise table overlap with live timing globals."""
from tools.tests import game_motion_table_150c8350_common as g
from tools.tests.game_motion_table_150c8350_common import *
num=0
for base,pattern,ticks,half,seed in itertools.product((s['D_800BE9A0']-4,s['D_800BE9A0']-32,s['D_800BE9E4']-4),range(8),(0,1,0xffffffff),(1,255),(1,)):
 g.table=base;initial=fixture(pattern,ticks,half,seed);wanted=public(model(initial));states=[]
 for label in ('retail','raw','guarded'):
  m=FactoryOracle(programs[label],initial.copy(),Case(),entry=entry,s={},arguments=(0,)).run();assert public(m.memory)==wanted,(label,hex(base),pattern,ticks,half)
  states.append((accesses(m),m.r,m.hi,m.lo))
 assert states[0]==states[1]==states[2];num+=1
assert num==144
report={'cases_per_stream':num,'global_alias_arrangements':3,'full_registers_and_public_access':True,'uncredited':True}
(out/'alias.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
