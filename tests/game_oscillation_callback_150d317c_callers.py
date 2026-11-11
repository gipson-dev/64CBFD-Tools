"""Connect the actual callback table and bounded record-dispatch window."""
import itertools,json,struct
from tools.experiments import game_oscillation_callback_150d317c_match as p
from tools.tests import game_oscillation_callback_150d317c_oracle as g
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
WINDOW,END,ROM,TABLE=0x1513D074,0x1513D0A8,0x16A524,0x80089D60
class Caller(g.Oracle):
 def record_call(self,t):
  if t==p.ENTRY:self.target_arguments=tuple(self.arguments(1))
  else:super().record_call(t)
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x22E8B8)[0]==p.ENTRY and (0x80089DF8-TABLE)//4==38
 window=struct.unpack_from('>13I',rom,ROM);raw,refs=p.payload(p.out/'independent-selected.o');lookup={r[1]:r[2][1]for r in symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});connected=dict(zip(range(p.ENTRY,p.ENTRY+384,4),words));connected[END]=0;count=0
 for timer,rate,mutation,phase,prior in itertools.product((g.bits(-1.),0,g.bits(.5),g.bits(3.)),(0,g.bits(1.),g.bits(100.)),(0,1,2,4,7),(0,8),(0,1)):
  c=g.Case(timer=timer,rate=rate,mutation=mutation,phase=phase);m=Caller(window,c,entry=WINDOW,connected=connected);g.put(m.memory,TABLE+38*4,p.ENTRY);m.initial=dict(m.memory);m.r[2]=38;m.r[7]=prior;m.code=WindowCode(m.code,m);m.code.ends=(END,)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Dispatcher continuation not reached')
  want,calls,ret=g.reference(m.initial,c);assert {a:v for a,v in m.memory.items()if not g.STACK-512<=a<g.STACK+512}=={a:v for a,v in want.items()if not g.STACK-512<=a<g.STACK+512}
  assert m.target_arguments==(g.ACTOR,) and m.calls==calls and m.r[2]==ret and m.r[7]==(prior or not ret) and m.r[4]==g.ACTOR and m.fcsr==c.fcsr;count+=1
 r=dict(caller_cases=count,table='D_80089D60',index=38,table_ROM='0x22E8B8',dispatcher='func_1513CFE4',window_words=13,return_controls_removal=True,full_parent_not_qualified=True,source_installed=False)
 (p.out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
