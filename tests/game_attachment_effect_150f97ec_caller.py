"""Exercise the retail call window with both private instruction streams."""
import itertools,json,struct
from tools.tests import game_attachment_effect_150f97ec_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
start,end=0x1502890c,0x15028918
window=list(struct.unpack_from('>3I',g.rom,start-0x15000000+0x2d4b0));assert window==[0x93a50773,0x0d43e5fb,0x24060001]
class Caller(g.Oracle):
 def __init__(self,words,memory,selector,mutation,rand):
  self.selector=selector;self.context=1;self.mutation=mutation;self.random=rand;self.nfloat=0;self.nint=0;self.records=[]
  code={g.ENTRY+4*i:w for i,w in enumerate(words)};code[end]=0
  FactoryOracle.__init__(self,window,memory,Case(),entry=start,s={},arguments=(g.ACTOR,),connected=code)
  self.code=WindowCode(self.code,self);self.code.ends=(end,)
 def record_call(self,t):
  if t==g.ENTRY:self.calls.append((t,tuple(self.arguments(3))))
  else:super().record_call(t)
count=0
for attached,index,selector,mutation,rand in itertools.product((0,1),(0,5),(0,255),(0,1),((0,0),(7,155))):
 initial=g.fixture(0,attached,index);initial[g.STACK+0x773]=selector
 for words in (g.truth,g.candidate):
  m=Caller(words,initial.copy(),selector,mutation,rand)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Caller did not reach continuation')
  assert m.calls[0]==(g.ENTRY,(g.ACTOR,selector,1))
  g.validate(m,attached,index,selector,1,mutation,rand)
 count+=1
report={'cases_per_stream':count,'caller':'func_150265CC','window':'0x1502890c..0x15028918','bounded_window':True,'uncredited':True}
(g.out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
