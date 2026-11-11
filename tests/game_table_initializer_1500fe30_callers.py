"""Bounded original caller window from the initialization callback."""
import itertools,json,struct
from tools.experiments import game_table_initializer_1500fe30_match as p
from tools.tests import game_table_initializer_1500fe30_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
START=0x15010038;END=0x15010040
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>2I',rom,0x3d4e8);retail=struct.unpack_from('>91I',rom,p.ROM)
 raw,refs=p.payload(p.out/'independent-selected.o');elf=p.out/'frozen/conker/build/conker.us.elf';lookup={v[1]:v[2][1] for v in p.symbol_rows(elf.read_bytes())}
 candidate=p.bound_blob(raw,refs,{n:lookup[n] for es in refs.values() for _,n in es});assert tuple(candidate)==retail
 class Caller(g.Oracle):
  def record_call(self,t):
   if t==p.ENTRY:self.target_called=True
   else:super().record_call(t)
 count=0
 for mutation,seed in itertools.product((0,1),range(4)):
  c=g.Case(mutation,seed);m=Caller(window,c);m.target_called=False
  m.code=dict(zip(range(START,END,4),window));m.code.update(zip(range(p.ENTRY,p.ENTRY+4*len(retail),4),retail));m.code[END]=0;m.code=WindowCode(m.code,m);m.code.ends=(END,);m.entry=START;m.initial=dict(m.memory)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('caller did not reach bounded window exit')
  want,calls=g.reference(c,m.initial);assert g.public(m.memory)==g.public(want) and m.calls==calls
  assert m.target_called and END in m.visits and m.r[31]==END;count+=1
 result=dict(cases=count,caller='func_1500FFCC',call_site='0x15010038',delay_slot_is_nop=True,full_parent_not_qualified=True,helpers_modeled=True,source_installed=False)
 (p.out/'caller-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
