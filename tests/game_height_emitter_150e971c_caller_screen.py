"""Uncredited original dispatch-window comparison."""
import itertools,json,struct
from tools.tests import game_height_emitter_150e971c_guest_screen as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
start,end=0x15132244,0x1513226c;table=0x800898b0
rom=(g.root/'conker/conker.us.bin').read_bytes()
window=list(struct.unpack_from('>10I',rom,start-0x15000000+0x2d4b0));assert window[8]==0x0320f809
assert struct.unpack_from('>I',rom,0x22e3b4)[0]==g.entry
class Caller(g.Oracle):
 def __init__(self,words,memory,mutation):
  self.mutate=mutation;self.seen=[]
  code={g.entry+4*i:w for i,w in enumerate(words)};code[end]=0
  FactoryOracle.__init__(self,window,memory,Case(),entry=start,s={},arguments=(g.actor,),connected=code)
  self.r[16]=g.actor;self.code=WindowCode(self.code,self);self.code.ends=(end,)
 def record_call(self,t):
  if t==g.entry:self.calls.append((t,tuple(self.arguments(1))))
  else:super().record_call(t)
cases=0
for height,flags,seed,mutation in itertools.product((-5.,10.,11.),(10,9),(0,1),(0,1,2,3)):
 initial=g.fixture(height,flags,seed);initial[g.actor+0x71]=17;put(initial,table+17*4,g.entry)
 expected=g.Oracle(g.truth,initial.copy(),mutation).run()
 for words in (g.truth,g.snapshot,g.guarded):
  m=Caller(words,initial.copy(),mutation)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('caller did not reach continuation')
  assert m.calls[0]==(g.entry,(g.actor,)) and g.observation(m)==g.observation(expected)
 cases+=1
assert cases==48
report={'cases_per_stream':cases,'streams':3,'caller':'func_151321D0','slot':17,'window':'0x15132244..0x1513226c','uncredited':True}
(g.out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
