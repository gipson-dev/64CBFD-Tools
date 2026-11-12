import json,struct
from dataclasses import replace
from tools.tests import game_animated_packet_renderer_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START=0x151677d8;END=0x15167800;DESC=0x8008b544;ITER=0x70000;SELECTOR=0x1234ffff
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(3))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x23000c)[0]==g.ENTRY
 data,fs,rs=parse_object(g.out/'candidate.o');a,n=fs['func_15167C58']['value'],fs['func_15167C58']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>75I',rom,0x195108);window=struct.unpack_from('>10I',rom,START-0x15000000+0x2d4b0);count=0
 for base in g.cases():
  c=replace(base,phase=-0x180);calls,packets,public=g.reference(c);sp=g.STACK+c.phase;extra={};g.put(extra,DESC+8,g.ENTRY);g.put(extra,ITER,g.read(g.fixture(c),g.STATE+8));public.update(extra)
  for words in (retail,candidate):
   m=Caller(words,base);m.case=c;m.entered=False;m.r[29]=sp;m.r[20]=DESC;m.r[16]=g.STATE;m.r[19]=g.OUTPUT;m.r[22]=SELECTOR;m.r[17]=ITER;m.memory.update(extra)
   code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));code.update(zip(range(START,END,4),window));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   actual={a:v for a,v in m.memory.items()if not g.STACK-1024<=a<g.STACK+512}
   assert m.entered and m.target_args==(g.OUTPUT,g.STATE,0xffffffff) and (m.calls,m.packets,actual,m.r[2])==(calls,packets,public,g.OUTPUT+0x60),(c,m.calls,calls)
  count+=1
 report=dict(cases=count,descriptor_index=3,caller='func_151674F8 renderer callback window',caller_window_only=True,full_parent_qualified=False,helpers='modeled',source_installed=False);(g.out/'window_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
