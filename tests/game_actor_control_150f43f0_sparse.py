"""Check held-field reads are skipped only on the original branch paths."""
import json
from tools.experiments import game_actor_control_150f43f0_match as p
from tools.tests import game_actor_control_150f43f0_oracle as g
from tools.experiments.game_actor_state_tick_integration import symbol_rows
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');lookup={r[1]:r[2][1]for r in symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});skipped=required=0
 for c in (g.Case(kind=0x3B,state=0x100),g.Case(kind=0x3B,state=0x100,first=0),g.Case(kind=0,state=0),g.Case(kind=0,state=0x100)):
  m=g.Oracle(words,c)
  for i in range(4):del m.memory[g.ACTOR+0x6C8+i]
  m.initial=dict(m.memory);m.run();want,calls=g.reference(m.initial,c);public=lambda x:{a:v for a,v in x.items()if not g.STACK-512<=a<g.STACK+512};assert public(m.memory)==public(want)and m.calls==calls;skipped+=1
 for c in (g.Case(kind=0x3B,state=0),g.Case(kind=0,state=8)):
  m=g.Oracle(words,c)
  for i in range(4):del m.memory[g.ACTOR+0x6C8+i]
  try:m.run()
  except AssertionError as exc:
   assert exc.args==(('unmapped read',g.ACTOR+0x6C8,4),),exc;required+=1
  else:raise AssertionError('Expected held-field read')
 r=dict(skipped_held_reads=skipped,required_held_reads=required,guest_sparse_memory_only=True,portable_C_fault_not_qualified=True,source_installed=False);(p.out/'sparse.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
