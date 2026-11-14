"""Connect the original record-dispatch window to the candidate callback."""
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_motion_crossing_150e6230_guest import *
start,end=0x1513d034,0x1513d064;parent_table=0x80089cb8;rom=(root/'conker/conker.us.bin').read_bytes()
window=list(struct.unpack_from('>12I',rom,start-0x15000000+0x2d4b0));assert window[9]==0x0320f809
assert struct.unpack_from('>I',rom,0x22e7b4)[0]==entry
class Caller(Oracle):
 def __init__(self,words,memory,dotvalue,mutation,cbret):
  self.dotvalue=dotvalue;self.mutation=mutation;self.cbret=cbret;self.observed=[]
  code={entry+4*i:w for i,w in enumerate(words)};code[end]=0
  FactoryOracle.__init__(self,window,memory,Case(),entry=start,s={},arguments=(actor,),connected=code)
  self.r[7]=0;self.code=WindowCode(self.code,self);self.code.ends=(end,)
 def record_call(self,t):
  if t==entry:self.calls.append((t,tuple(self.arguments(1))))
  else:super().record_call(t)
cases=0
for enabled,dotvalue,sign,selector,mutation,cbret in itertools.product((0,1),(-1.,0.,1.),(-1.,1.),(-1,0),(0,1,2,3),(0x100,0x1fe)):
 initial=fixture(enabled,sign,selector,cases&1);initial[actor+0x70]=15;put(initial,parent_table+15*4,entry)
 result,calls,want=model(initial,dotvalue,mutation,cbret)
 for words in (truth,candidate,guarded):
  m=Caller(words,initial.copy(),dotvalue,mutation,cbret)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('caller did not reach continuation')
  assert m.calls[0]==(entry,(actor,)) and (m.r[2],m.observed,public(m.memory))==(result,calls,public(want))
 cases+=1
report={'cases_per_stream':cases,'streams':3,'caller':'func_1513CFE4','table_slot':15,'window':'0x1513D034..0x1513D064','uncredited':True}
(out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
