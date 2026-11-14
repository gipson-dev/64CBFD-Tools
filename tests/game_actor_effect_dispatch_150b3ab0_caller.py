"""Run the original 1506FC9C direct caller up to its post-call continuation."""
from pathlib import Path
import itertools, json, struct
from tools.tests import game_actor_effect_dispatch_150b3ab0_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
start,end=0x1506fc9c,0x1506fcb8
rom=(g.root/'conker/conker.us.bin').read_bytes()
window=list(struct.unpack_from('>7I',rom,start-0x15000000+0x2d4b0));assert window[5]==0x0d42ceac and window[6]==0x240500ff
class Caller(g.Oracle):
 def __init__(self,words,memory,mutation,randoms):
  self.mutation=mutation;self.randoms=randoms;self.rand=0;self.records=[];self.home=g.STACK-24
  code={g.ENTRY+i*4:w for i,w in enumerate(words)};code[end]=0
  FactoryOracle.__init__(self,window,memory,Case(),entry=start,s={},arguments=(0xabcdef12,),connected=code)
  self.code=WindowCode(self.code,self);self.code.ends=(end,)
 def record_call(self,t):
  if t==g.ENTRY:self.calls.append((t,tuple(self.arguments(2))))
  else:super().record_call(t)
count=0
for active,mutation,seed,randoms in itertools.product((0,1,2),(0,1),(0,1),((0,0,0),(0xffffffff,0xffffffff,0xffffffff))):
 actor=0 if active==0 else g.ACTOR;frame=g.FRAME if active==2 else 0
 initial=g.fixture(seed,frame);put(initial,g.symbols['D_800D154C'],actor)
 want=g.expected(initial,active==2,255,mutation,randoms,home=g.STACK-24)
 for words in (g.truth,g.candidate):
  m=Caller(words,initial.copy(),mutation,randoms)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Caller did not reach continuation')
  assert m.calls[0]==(g.ENTRY,(actor,255));assert m.records==want,(m.records,want)
 count+=1
report={'cases_per_stream':count,'streams':2,'caller':'func_1506FC9C','bounded_window':True,'uncredited':True}
(g.out/'caller-guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
