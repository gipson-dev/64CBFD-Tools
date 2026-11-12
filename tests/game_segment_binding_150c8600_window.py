import json,struct
from tools.tests import game_segment_binding_150c8600_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START=0x1510BB4C;END=0x1510BB98
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(1))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();text,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_150C8600']['value'],fs['func_150C8600']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>76I',rom,0xF5AB0);words=struct.unpack_from('>19I',rom,START-0x15000000+0x2D4B0);assert words[0]==0x0d432180
 count=0
 for c in g.cases():
  expected,calls,answer=g.reference(c)
  for ws in (retail,candidate):
   m=Caller(ws,c);m.entered=False;m.r[16]=g.CURSOR
   code=dict(zip(range(START,END,4),words));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   assert m.entered and m.target_args==(g.CURSOR,) and END in m.visits and m.r[16]==answer,(c,'caller outcome')
   assert g.public(m.memory)==expected and m.normalized==calls,(c,'memory or calls')
  count+=1
 report=dict(cases=count,caller='func_1510B9D0 dispatch window',helper='modeled',full_parent_qualified=False,source_installed=False);(g.out/'caller_150C8600_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
