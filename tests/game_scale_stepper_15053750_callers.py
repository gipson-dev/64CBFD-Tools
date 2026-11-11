"""Private original direct-call window for the scale-stepper screen."""
import itertools,json,struct
from tools.experiments import game_scale_stepper_15053750_match as p
from tools.tests import game_scale_stepper_15053750_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
START=0x15052634;END=0x1505263c
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>2I',rom,0x7fae4)
 retail=struct.unpack_from('>81I',rom,p.ROM)
 raw,refs=p.payload(p.out/'independent-selected.o')
 elf=p.out/'frozen/conker/build/conker.us.elf'
 lookup={v[1]:v[2][1] for v in p.symbol_rows(elf.read_bytes())}
 candidate=p.bound_blob(raw,refs,{n:lookup[n] for es in refs.values() for _,n in es});assert tuple(candidate)==retail
 class Caller(g.Oracle):
  def record_call(self,t):
   if t==p.ENTRY:self.target_arguments=tuple(self.arguments(1))
   else:super().record_call(t)
 samples=[(0,0,0,0,1),(0,0,.5,.5,1),(0,0,2,-2,1),(1,1,-2,2,.5),(0,0,1,-1,1),(2,-1,2,1,.5),(1,1,-1,1,2),(0,1,0,-1,0),(0,0,2,-2,-1)]
 cases=0
 for values,mutation in itertools.product(samples,(0,1)):
  c=g.Case(*(g.b(v) for v in values),mutation,0,cases%3)
  m=Caller(window,c);m.code=dict(zip(range(START,END,4),window));m.code.update(zip(range(p.ENTRY,p.ENTRY+4*len(retail),4),retail));m.code[END]=0;m.code=WindowCode(m.code,m);m.code.ends=(END,);m.entry=START;m.r[16]=g.ACTOR;m.initial=dict(m.memory)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('caller did not reach bounded window exit')
  want,calls=g.reference(c,m.initial);assert g.public(m.memory)==g.public(want) and m.calls==calls
  assert m.target_arguments==(g.ACTOR,) and END in m.visits and m.r[31]==END
  cases+=1
 result=dict(cases=cases,call_site='0x15052634',delay_slot_supplies_actor=True,full_parent_not_qualified=True,helper_modeled=True,source_installed=False)
 (p.out/'caller-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
