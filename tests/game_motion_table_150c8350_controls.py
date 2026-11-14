"""Reject retail instruction mutations with the independent model."""
from tools.tests.game_motion_table_150c8350_common import *
controls=((0x240c0500,0x240c04ff),(0x84450008,0x84450006),(0x00077900,0x000778c0),(0x240d04ff,0x240d04fe));results=[]
for before,after in controls:
 assert truth.count(before)==1,hex(before);altered=truth.copy();altered[altered.index(before)]=after;caught=False
 for pattern,ticks,half,seed in itertools.product(range(8),(0,1,3,0xffffffff),(0,1,127,255),(1,3)):
  initial=fixture(pattern,ticks,half,seed);wanted=public(model(initial));m=FactoryOracle(altered,initial.copy(),Case(),entry=entry,s={},arguments=(0,)).run();caught=public(m.memory)!=wanted
  if caught:break
 assert caught,hex(before);results.append(hex(before))
print(json.dumps({'controls_rejected':results,'uncredited':True}),flush=True)
