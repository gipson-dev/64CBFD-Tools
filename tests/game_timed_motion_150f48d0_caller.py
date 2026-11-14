"""Connect the original indirect dispatch window to the screened target."""
import itertools,json,struct
from tools.tests import game_timed_motion_150f48d0_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
start,end=0x15132244,0x1513226c;rom=(g.root/'conker/conker.us.bin').read_bytes();table=0x800898b0
window=list(struct.unpack_from('>10I',rom,start-0x15000000+0x2d4b0));assert window[8]==0x0320f809
assert struct.unpack_from('>I',rom,0x22e3c8)[0]==g.ENTRY
class Caller(g.Oracle):
 def __init__(self,words,memory,actor,mutation):
  self.actor=actor;self.mutation=mutation;self.observed=[]
  code={g.ENTRY+4*i:w for i,w in enumerate(words)};code[end]=0
  FactoryOracle.__init__(self,window,memory,Case(),entry=start,s={},arguments=(actor,),connected=code)
  self.r[16]=actor;self.code=WindowCode(self.code,self);self.code.ends=(end,)
 def record_call(self,t):
  if t==g.ENTRY:self.calls.append((t,tuple(self.arguments(1))))
  else:super().record_call(t)
cases=0
for timer,tick,mutation,seed in itertools.product((0.,1.,12.),(.5,2.),(0,1),(0,1)):
 initial=g.fixture(g.NORMAL,timer,tick,seed);initial[g.NORMAL+0x71]=22;put(initial,table+22*4,g.ENTRY)
 want,result,calls=g.model(initial,g.NORMAL,mutation)
 for words in (g.truth,g.candidate,g.guarded):
  m=Caller(words,initial.copy(),g.NORMAL,mutation)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Indirect caller did not reach its continuation')
  assert m.calls[0]==(g.ENTRY,(g.NORMAL,)) and m.r[2]==result and m.observed==calls
  assert g.public(m.memory)==g.public(want)
 cases+=1
report={'cases_per_stream':cases,'streams':3,'caller':'func_151321D0','slot':22,'window':'0x15132244..0x1513226c','uncredited':True}
(g.out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
