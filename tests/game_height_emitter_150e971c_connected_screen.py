"""Uncredited finite comparison with the original retail movement helper."""
import itertools,json,struct
from tools.tests import game_height_emitter_150e971c_guest_screen as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits
rom=(g.root/'conker/conker.us.bin').read_bytes()
helper=struct.unpack_from('>53I',rom,0x160c70)
connected={g.update+4*i:w for i,w in enumerate(helper)}
tick=g.syms['D_800BE9A4']
class Oracle(g.Oracle):
 def __init__(self,words,memory,mutation):
  self.mutate=mutation;self.seen=[]
  FactoryOracle.__init__(self,words,memory,Case(),entry=g.entry,s={},arguments=(g.actor,),connected=connected)
def observe(m):
 return (m.r[2],[(t,a,d) for t,a,d in m.seen],bytes(m.memory[g.actor+i] for i in range(0x1b0)))
cases=emissions=transitions=0
for height,vertical,flag,seed,mutation in itertools.product((8.,10.,11.),(0.,1.,2.),(9,10),(0,1),(0,2)):
 initial=g.fixture(height,flag,seed)
 for off,value in ((0x20,0.0),(0x24,0.0),(0x28,0.0),(0x44,.25),(0x48,vertical),(0x4c,-.5),(0x50,0.0),(0x54,0.0),(0x58,0.0),(0x5c,0.0)):
  put(initial,g.actor+off,bits(value))
 put(initial,tick,bits(1.0))
 a,b,c,d=[Oracle(words,initial.copy(),mutation).run() for words in (g.truth,g.padded,g.snapshot,g.guarded)]
 assert observe(a)==observe(b)==observe(c)==observe(d),(height,vertical,flag,seed,mutation)
 assert a.r[2]==(0 if height+vertical<10. else 1)
 assert read(a.memory,g.actor+0x3c)==bits(height+vertical)
 assert any(t==g.emit for t,_,_ in a.seen)==(height+vertical<10. and flag==10)
 if (height<10.)!=(height+vertical<10.):transitions+=1
 emissions+=any(t==g.emit for t,_,_ in a.seen);cases+=1
assert cases==72 and emissions and transitions
report={'cases_per_stream':cases,'streams':4,'retail_helper_words':len(helper),'emissions':emissions,'height_gate_transitions':transitions,'helpers_other_than_update':'stubbed','independent_model':False,'uncredited':True}
(g.out/'connected-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
