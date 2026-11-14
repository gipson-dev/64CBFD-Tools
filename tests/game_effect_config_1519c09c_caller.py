"""Execute the original caller dispatch, delay slot and returned-pointer store."""
from pathlib import Path
import importlib.util,itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-effect-config-1519c09c-durable'
from tools.tests import game_effect_config_1519c09c_guest as g
START,END=0x151997c8,0x1519981c;ACTOR,HOLDER=0x61000,0x62000
words=list(struct.unpack_from('>21I',g.rom,START-0x15000000+0x2d4b0))
guarded=g.bound_blob(*g.payload(out/'generated-guarded.o','func_1519C09C'),g.symbols);assert guarded==g.retail
class Caller(g.Oracle):
 def __init__(self,code,memory,position,params,outcome,mutation):
  self.position,self.params,self.outcome,self.mutation=position,params,outcome,mutation;self.observed=[]
  connected={g.ENTRY+i*4:w for i,w in enumerate(code)};connected[END]=0
  FactoryOracle.__init__(self,words,memory,Case(),entry=START,s={},arguments=(),connected=connected)
  self.r[16]=ACTOR;self.code=WindowCode(self.code,self);self.code.ends=(END,)
 def record_call(self,target):
  if target==g.ENTRY:self.calls.append((target,tuple(self.arguments(8))))
  else:super().record_call(target)
cases=0
for flags,values,outcome,mutation,priority,seed in itertools.product((0,1),((0.,-0.,1.75),(-10.75,42.9,-1.25),(123456.,-654321.,32767.75)),(0,1),(0,1),(0,255),(0,1)):
 initial,_=g.fixture(values,g.bits(-.75),False,seed)
 for base,n in ((ACTOR,128),(HOLDER,0x200)):
  initial.update({base+i:(i*19+3)&255 for i in range(n)})
 position=g.STACK+0x1c0
 for i,v in enumerate(values):put(initial,position+4*i,g.bits(v))
 initial[ACTOR+0x54]=flags
 for i,v in enumerate((17,34,51,68)):initial[ACTOR+0x50+i]=v
 put(initial,g.STACK+0x1dc,g.OWNER);put(initial,g.STACK+0x54,HOLDER)
 put(initial,g.STACK+0x1e8,0x11223300|priority);put(initial,g.STACK+0x1ec,0x34567890)
 params=(17,34,51,68,priority,0x34567890)
 expected,coords,config=g.reference(initial,position,params,outcome,mutation) if flags else (initial.copy(),None,None)
 put(expected,HOLDER+0x148,g.RESULT if flags and outcome else 0)
 for code in (g.retail,g.candidate,guarded):
  m=Caller(code,initial.copy(),position,params,outcome,mutation)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Expected caller continuation')
  if flags:
   assert m.calls[0]==(g.ENTRY,(g.OWNER,position,*params)),m.calls[0]
   assert m.observed[0][1]==coords
  else:assert not m.calls
  assert g.public(m.memory)==g.public(expected)
 cases+=1
report={'caller':'func_151994B8 dispatch window','call_site':'0x15199804','cases':cases,'streams':3,'uncredited':True}
(out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
