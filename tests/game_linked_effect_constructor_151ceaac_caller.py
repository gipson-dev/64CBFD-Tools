"""Execute both original direct caller windows around the constructor."""
from pathlib import Path
import importlib.util,itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-linked-effect-constructor-151ceaac-durable'
from tools.tests import game_linked_effect_constructor_151ceaac_guest as g
windows=((0x1506ac58,0x1506ac7c),(0x151d0e78,0x151d0e94))
class Caller(g.Oracle):
 def __init__(self,words,start,end,initial,success,mutation,kind,channel,context):
  self.success,self.mutation=success,mutation;self.random_count=0;self.observed=[]
  code=dict(g.connected);code.update({g.ENTRY+4*i:w for i,w in enumerate(words)});code[end]=0
  window=list(struct.unpack_from('>%dI'%((end-start)//4),g.rom,start-0x15000000+0x2d4b0))
  FactoryOracle.__init__(self,window,initial,Case(),entry=start,s={},arguments=((g.OWNER,) if kind==0 else ()),connected=code)
  if kind==1:self.r[2]=self.r[16]=g.ATTACH;self.r[18]=channel;self.r[19]=context
  self.code=WindowCode(self.code,self);self.code.ends=(end,)
 def record_call(self,t):
  if t==g.ENTRY:self.calls.append((t,tuple(self.arguments(5))))
  else:super().record_call(t)
cases=0
for kind,success,mutation,seed,channel in itertools.product((0,1),(0,1),(0,1),(0,1),(0,0x1ff)):
 start,end=windows[kind];initial=g.fixture(seed)
 if kind==1:initial.update({g.ATTACH+i:(i*29+seed*13+0x31)&255 for i in range(128,192)})
 owner,attachment,mode,ch,context=(g.OWNER,0,1,255,1) if kind==0 else (0,g.ATTACH,0,channel&255,0x87654321)
 expected,packet,request=g.reference(initial,owner,attachment,mode,success,mutation,home=g.STACK-32 if kind==0 else g.STACK)
 if kind==1:put(expected,g.ATTACH+0xa8,g.RESULT if success else 0)
 for code in (g.retail,g.candidate):
  m=Caller(code,start,end,initial.copy(),success,mutation,kind,channel,0x87654321)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Expected caller continuation')
  assert m.calls[0]==(g.ENTRY,(owner,attachment,mode,ch,context)),m.calls[0]
  assert m.observed[0]==('request',request)
  if success:assert m.observed[1]==('payload',packet)
  assert g.public(m.memory)==g.public(expected)
  if kind==0:assert m.r[2]==(g.RESULT if success else 0)
 cases+=1
report={'cases':cases,'streams':2,'call_sites':['0x1506ac74','0x151d0e88'],'bounded_windows':True,'uncredited':True}
(out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
