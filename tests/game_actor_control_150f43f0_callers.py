"""Connect the original actor-control callback-table dispatcher window."""
import itertools,json,struct
from tools.experiments import game_actor_control_150f43f0_match as p
from tools.tests import game_actor_control_150f43f0_oracle as g
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
WINDOW,END,ROM,TABLE,CONTEXT_GLOBAL,CONTEXT=0x15130230,0x15130264,0x15D6E0,0x80089670,0x800B0DF0,0x32000
class Caller(g.Oracle):
 def record_call(self,t):
  if t==p.ENTRY:self.target_arguments=tuple(self.arguments(1))
  else:super().record_call(t)
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x22E190)[0]==p.ENTRY and (0x800896D0-TABLE)//4==24
 window=struct.unpack_from('>13I',rom,ROM);raw,refs=p.payload(p.out/'independent-selected.o');lookup={r[1]:r[2][1]for r in symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});connected=dict(zip(range(p.ENTRY,p.ENTRY+376,4),words));connected[END]=0;count=0
 for kind,state,held,gate,first,second,mutation in itertools.product((0,0x3B),(0,8,0x100),(0,1),(0,1),(0,1),(0,1),(0,31)):
  c=g.Case(kind,state,held,gate,first,second,mutation);m=Caller(window,c,entry=WINDOW,connected=connected);g.put(m.memory,CONTEXT_GLOBAL,CONTEXT);g.put(m.memory,TABLE+24*4,p.ENTRY);m.memory[CONTEXT+0xF]=24;m.initial=dict(m.memory);m.code=WindowCode(m.code,m);m.code.ends=(END,)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Dispatcher continuation not reached')
  want,calls=g.reference(m.initial,c);public=lambda x:{a:v for a,v in x.items()if not g.STACK-512<=a<g.STACK+512};assert public(m.memory)==public(want)and m.calls==calls and m.target_arguments==(g.ACTOR,);assert m.r[29]==g.STACK-24 and m.r[31]==END;count+=1
 r=dict(caller_cases=count,table='D_80089670',index=24,table_ROM='0x22E190',dispatcher='func_15130230',window_words=13,return_value_ignored_at_continuation=True,full_parent_not_qualified=True,source_installed=False);(p.out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
