"""Exercise the original six-argument indirect effect callback window."""
import itertools,json,struct
from tools.experiments import game_effect_callback_150ddfac_match as p
from tools.tests import game_effect_callback_150ddfac_oracle as g
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
WINDOW,END,ROM,TABLE=0x15148D80,0x15148DCC,0x176230,0x8008A430
class Caller(g.Oracle):
 def record_call(self,t):
  if t==p.ENTRY:self.target_arguments=tuple(self.arguments(6))
  else:super().record_call(t)
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x22EEFC)[0]==p.ENTRY and (0x8008A43C-TABLE)//4==3
 window=struct.unpack_from('>19I',rom,ROM);raw,refs=p.payload(p.out/'independent-selected.o');lookup={r[1]:r[2][1]for r in symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});connected=dict(zip(range(p.ENTRY,p.ENTRY+384,4),words));connected[END]=0;count=0
 for choice,index,mutation,phase in itertools.product((0,1),(-1,0,1),(0,1,2,3,8,11),(0,8)):
  c=g.Case(choice=choice,index=index,mutation=mutation,phase=phase);m=Caller(window,c,entry=WINDOW,connected=connected);home=g.STACK+phase
  g.put(m.memory,TABLE+3*4,p.ENTRY);g.put(m.memory,g.ACTOR+0x60,c.height);g.put(m.memory,home+0x40,g.bits(1.));g.put(m.memory,home+0x44,g.bits(2.));g.put(m.memory,home+0x48,g.bits(3.));m.initial=dict(m.memory);m.r[2]=3;m.r[16]=g.ACTOR;m.code=WindowCode(m.code,m);m.code.ends=(END,)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Dispatcher continuation not reached')
  want,args=g.reference(m.initial,c);args=list(args);args[2]=g.ACTOR+0x64;public=lambda x:{a:v for a,v in x.items()if not g.STACK-512<=a<g.STACK+512}
  assert public(m.memory)==public(want);assert m.target_arguments==(g.ACTOR,g.bits(1.),g.bits(2.),g.bits(3.),c.height,g.ACTOR+0x64);assert m.calls[-1][1][1:]==tuple(args);assert m.obs==list(g.descriptor(c));assert m.r[2]==1;count+=1
 r=dict(caller_cases=count,table='D_8008A430',index=3,table_ROM='0x22EEFC',dispatcher='func_15148BA4',window_words=19,six_arguments_checked=True,full_parent_not_qualified=True,source_installed=False);(p.out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
