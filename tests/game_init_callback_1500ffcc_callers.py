"""Private original callback-table dispatcher window for the initialization screen."""
import itertools,json,struct
from tools.experiments import game_init_callback_1500ffcc_match as p
from tools.experiments import game_init_callback_1500ffcc_match as n
from tools.tests import game_init_callback_1500ffcc_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
START=0x1500e53c;END=0x1500e564;STATE_GLOBAL=0x800b0df0;STATE=0x32000;TABLE=0x80082d90
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>10I',rom,0x3b9ec)
 retail=struct.unpack_from('>79I',rom,p.ROM);raw,refs=p.payload(p.out/'independent-selected.o');normal,nrefs=n.normalize(raw,refs)
 elf=p.out/'frozen/conker/build/conker.us.elf';lookup={v[1]:v[2][1] for v in p.symbol_rows(elf.read_bytes())}
 syms={name:lookup[name] for es in refs.values() for _,name in es};variants=(retail,p.bound_blob(raw,refs,syms),p.bound_blob(normal,nrefs,syms))
 class Caller(g.Oracle):
  def record_call(self,t):
   if t==p.ENTRY:self.target_called=True
   else:super().record_call(t)
 cases=0
 for a,b,mutation in itertools.product((0,1),(0,1),(0,1)):
  c=g.Case(a,b,mutation,0,cases%3);models=[]
  for ws in variants:
   m=Caller(window,c);m.target_called=False;m.code=dict(zip(range(START,END,4),window));m.code.update(zip(range(p.ENTRY,p.ENTRY+4*len(ws),4),ws));m.code[END]=0;m.code=WindowCode(m.code,m);m.code.ends=(END,);m.entry=START
   g.put(m.memory,STATE_GLOBAL,STATE);m.memory[STATE+0xa]=12;g.put(m.memory,TABLE+12*4,p.ENTRY);m.initial=dict(m.memory)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('dispatcher did not reach bounded exit')
   want,calls=g.reference(c,m.initial);assert g.public(m.memory)==g.public(want) and m.calls==calls
   assert m.target_called and END in m.visits and m.r[31]==END;models.append(m)
  x,y,z=models;assert (x.memory,x.r,x.f,x.calls,x.trace)==(z.memory,z.r,z.f,z.calls,z.trace)
  cases+=1
 result=dict(cases=cases,executions=3*cases,dispatcher='func_1500E470',call_site='0x1500E55C',table='D_80082D90',table_index=12,full_parent_not_qualified=True,helpers_modeled=True,source_installed=False)
 (p.out/'caller-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
