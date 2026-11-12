import itertools,json,math,struct
from tools.tests import game_actor_radial_offset_1514be20_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_cached_vector_basis_oracle import normalize
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob

class Connected(g.Oracle):
 def __init__(self,ws,c,initial,connected):
  FactoryOracle.__init__(self,ws,initial,c,entry=g.ENTRY,arguments=(g.ACTOR,),connected=connected);self.before=self.r[:];self.before_f=self.f[:];self.sample=None
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==4:
   rd,fd=w>>11&31,w>>6&31;self.f[fd]=g.bits(math.sqrt(g.real(self.f[rd])));return
  super().execute(w)
 def hook(self,t):raise AssertionError(('unexpected modeled helper',hex(t)))

def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();helper=struct.unpack_from('>50I',rom,0x1725D8);connected=dict(zip(range(g.HELPER,g.HELPER+200,4),helper))
 text,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_1514BE20']['value'],fs['func_1514BE20']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>76I',rom,0x1792D0)
 cases=[(g.Case(*v),False) for v in itertools.product((-100.,0.,200.),(-100.,0.,200.),(-100.,0.,200.),(0.,.5,1.,2.),(0,1))]+[(g.Case(0.,0.,0.,0.,0),True)]
 seen=set();zero=0
 for c,iszero in cases:
  initial=g.fixture(c)
  if iszero:
   for i in range(3):g.put(initial,g.ACTOR+0x40+4*i,g.read(initial,g.ACTOR+0x34+4*i))
  # Compute the same interpolation from the initial actor without modeling the callee.
  origin=[g.real(g.read(initial,g.ACTOR+0x34+4*i)) for i in range(3)];current=[g.real(g.read(initial,g.ACTOR+0x40+4*i)) for i in range(3)];target=[origin[0],g.f32(origin[1]+100.),origin[2]];f=g.real(g.read(initial,g.ACTOR+0x15c))
  interp=[g.f32(current[i]+g.f32(g.f32(target[i]-current[i])*f)) for i in range(3)];sample=tuple(g.bits(g.f32(interp[i]-origin[i])) for i in range(3))
  temporary={};p=0x70000
  for i,v in enumerate(sample):g.put(temporary,p+4*i,v)
  answer=normalize(temporary,(p,p,p+12,p+16));expected=g.public(initial.copy())
  for i in range(3):
   value=g.bits(g.f32(origin[i]+g.f32(g.real(g.read(temporary,p+4*i))*100.))) if answer else g.read(initial,g.ACTOR+0x34+4*i)
   g.put(expected,g.ACTOR+0x40+4*i,value)
  zero+=not answer
  for ws in (retail,candidate):
   m=Connected(ws,c,initial.copy(),connected);m.run();assert m.sample==sample and m.r[2]==answer,(c,iszero,'call');assert g.public(m.memory)==expected,(c,iszero,'output');assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];seen.update(m.visits)
 report=dict(cases=len(cases),zero_length_cases=zero,retail_helper_words_visited=sum(g.HELPER+4*i in seen for i in range(50)),original_helper_executed=True,source_installed=False)
 (g.out/'connected_1514BE20_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
