from pathlib import Path
import itertools,json,struct
from tools.tests.game_motion_table_150c8350_common import *
rom=(root/'conker/conker.us.bin').read_bytes();wrapper_entry=0x150c84f4;wrapper=list(struct.unpack_from('>10I',rom,0xf59a4));guard=programs['guarded'];assert guard==truth;assert struct.unpack_from('>I',rom,0x2317e8)[0]==wrapper_entry
class Caller(FactoryOracle):
 def record_call(self,t):
  assert t==entry,hex(t);self.calls.append((t,()))
count=0
for view,pattern,ticks,half in itertools.product((0,1,0xffffffff,0x10000),range(4),(0,1),(0,255)):
 initial=fixture(pattern,ticks,half,1);want=public(model(initial) if view==0 else initial);states=[]
 for code in (truth,programs['raw'],guard):
  connected={entry+4*i:w for i,w in enumerate(code)}
  m=Caller(wrapper,initial.copy(),Case(),entry=wrapper_entry,s={},arguments=(view,),connected=connected).run()
  assert public(m.memory)==want and m.calls==([(entry,())] if view==0 else []),(view,pattern,ticks,half)
  states.append((m.r,m.hi,m.lo,public(m.memory)))
 assert states[0]==states[1]==states[2];count+=1
report={'cases_per_stream':count,'wrapper':'func_150C84F4','callback_slot':9,'streams':['retail','raw','guarded'],'uncredited':True};(out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
