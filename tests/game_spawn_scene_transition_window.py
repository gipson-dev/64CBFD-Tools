import json,struct
from dataclasses import replace
from tools.tests import game_spawn_scene_transition_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START=0x1500807c;END=0x15008094
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(2))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();data,fs,rs=parse_object(g.out/'candidate.o');a,n=fs['func_1507DFE4']['value'],fs['func_1507DFE4']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>76I',rom,0xab494);window=struct.unpack_from('>6I',rom,START-0x15000000+0x2d4b0);assert window[4]==(0x0c000000|((g.ENTRY>>2)&0x03ffffff));count=0
 for base in g.cases():
  c=replace(base,phase=-0x180);calls,public=g.reference(c);sp=g.STACK+c.phase
  for words,offset in ((retail,0x38),(candidate,0x38)):
   m=Caller(words,base,offset);m.case=c;m.memory.update(g.fixture(c));m.entered=False;m.r[29]=sp;g.put(m.memory,sp+0x2c,8);g.put(m.memory,sp+0x30,0x12345678)
   code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));code.update(zip(range(START,END,4),window));code[END]=0
   if c.connected:code.update(zip(range(g.TRANSFORM,g.TRANSFORM+88,4),struct.unpack_from('>22I',rom,0x4f640)))
   if c.query_connected:code.update(zip(range(g.QUERY,g.QUERY+1696,4),struct.unpack_from('>424I',rom,0xb2220)))
   m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   actual={a:v for a,v in m.memory.items()if not g.STACK-1024<=a<g.STACK+512}
   assert m.entered and m.target_args==(0x12345678,7) and (m.calls,actual)==(calls,public),(c,m.calls,calls)
  count+=1
 report=dict(cases=count,caller='func_15007B3C selection window',caller_window_only=True,full_parent_qualified=False,query_mixed_original_and_modeled=True,dispatch_modeled=True,source_installed=False);(g.out/'window_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
