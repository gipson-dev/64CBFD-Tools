"""Connect the real retail coordinate helper, modeling only sinf and cosf."""
import itertools,json,struct
from tools.tests import game_timed_motion_150f48d0_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_point_transform_match import put
from tools.tests.game_animation_timeline_oracle import bits
COS=g.syms['cosf'];SIN=g.syms['sinf'];rom=(g.root/'conker/conker.us.bin').read_bytes();helper=struct.unpack_from('>22I',rom,0x170bec)
connected={g.HELPER+4*i:w for i,w in enumerate(helper)}
class Oracle(g.Oracle):
 def __init__(self,words,memory,actor,mutation):
  self.actor=actor;self.mutation=mutation;self.observed=[];self.trig=[]
  FactoryOracle.__init__(self,words,memory,Case(),entry=g.ENTRY,s={},arguments=(actor,),connected=connected)
 def record_call(self,t):
  if t==g.HELPER:super().record_call(t)
  else:
   assert t in (COS,SIN);self.trig.append((t,self.f[12]));self.calls.append((t,()))
 def hook(self,t):
  assert t in (COS,SIN)
  if t==SIN and self.mutation:g.mutate(self.memory,self.actor)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.f[0]=bits(0.0 if t==COS else 1.0);self.r[2]=0xdeadbeef
cases=0
for timer,tick,mutation,seed in itertools.product((0.,1.,12.),(.5,2.),(0,1),(0,1)):
 initial=g.fixture(g.NORMAL,timer,tick,seed);want,result,calls=g.model(initial,g.NORMAL,mutation,helper_outputs=(2.0,0.0))
 for words in (g.truth,g.candidate,g.guarded):
  m=Oracle(words,initial.copy(),g.NORMAL,mutation).run()
  assert m.r[2]==result and m.observed==calls and g.public(m.memory)==g.public(want)
  assert m.trig==([] if not calls else [(COS,bits(1.0)),(SIN,bits(1.0))])
 cases+=1
report={'cases_per_stream':cases,'streams':3,'retail_helper_words':22,'trigonometric_returns_modeled':True,'uncredited':True}
(g.out/'connected-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
