import json,struct
from tools.tests import game_registered_update_walker_151670c0_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START=0x1501936c;END=0x15019374
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();data,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_151670C0']['value'],fs['func_151670C0']['size']
 refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())}
 candidate=bound_blob(data[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>74I',rom,0x194570)
 window=struct.unpack_from('>2I',rom,START-0x15000000+0x2d4b0);assert window==(0x0d459c30,0)
 count=0
 for c in (g.Case(pattern,mutation,depth,0) for pattern in (0,1,2,3) for mutation in (0,1,2,3) for depth in (0,2)):
  expected,calls=g.reference(c)
  for words in (retail,candidate):
   m=Caller(words,c);m.entered=False;m.r[29]=g.STACK-0x180
   code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));code.update(zip(range(START,END,4),window));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   assert m.entered and m.r[29]==g.STACK-0x180 and m.r[31]==END
   assert g.public(m.memory)==expected and [x[:3] for x in m.observed]==calls,(c,m.observed,calls)
  count+=1
 report=dict(cases=count,caller='func_15019130 call window',callbacks='modeled',caller_window_only=True,full_parent_qualified=False,source_installed=False)
 (g.out/'caller_151670C0_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
