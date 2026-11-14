"""Connect the 13-word retail dot-product helper for bounded comparisons."""
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_motion_crossing_150e6230_guest import *
rom=(root/'conker/conker.us.bin').read_bytes();helper=struct.unpack_from('>13I',rom,0x171f24);connected={dot+4*i:w for i,w in enumerate(helper)}
class Connected(Oracle):
 def __init__(self,code,memory,mutation,cbret):
  self.dotvalue=0.;self.mutation=mutation;self.cbret=cbret;self.observed=[]
  FactoryOracle.__init__(self,code,memory,Case(),entry=entry,s={},arguments=(actor,),connected=connected)
cases=0
for enabled,vec,sign,selector,mutation,cbret in itertools.product((0,1),((5.,7.,-2.),(1.,0.,2.),(0.,0.,0.)),(-1.,1.),(-1,0),(0,2),(0x100,0x1fe)):
 initial=fixture(enabled,sign,selector,0)
 for i,value in enumerate(vec):put(initial,actor+0x114+4*i,bits(value))
 pos=(2.,-3.,4.);d=[f32(vec[i]-pos[i]) for i in range(3)]
 value=f32(f32(f32(d[0]*vec[0])+f32(d[1]*vec[1]))+f32(vec[2]*d[2]))
 result,calls,want=model(initial,value,mutation,cbret)
 for code in (truth,candidate,guarded):
  m=Connected(code,initial.copy(),mutation,cbret).run()
  assert (m.r[2],m.observed,public(m.memory))==(result,calls,public(want)),(enabled,vec,sign,selector,mutation,cbret)
 cases+=1
report={'cases_per_stream':cases,'streams':3,'helper_words':len(helper),'callback_modeled':True,'uncredited':True}
(out/'connected-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
