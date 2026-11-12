import json,struct
from dataclasses import replace
from tools.tests import game_six_record_setup_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START=0x1500e53c;END=0x1500e564;TABLE=0x80082d90;GLOBAL=0x800b0df0;CONTEXT=0x31000;INDEX=19
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x227850+4*INDEX)[0]==g.ENTRY
 data,fs,rs=parse_object(g.out/'candidate.o');a,n=fs['func_15010110']['value'],fs['func_15010110']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>74I',rom,0x3d5c0);window=struct.unpack_from('>10I',rom,START-0x15000000+0x2d4b0);count=0
 for base in g.cases():
  c=replace(base,phase=-0x180);calls,packets,public=g.reference(c);sp=g.STACK+c.phase
  extra={};g.put(extra,GLOBAL,CONTEXT);g.put(extra,TABLE+4*INDEX,g.ENTRY);extra[CONTEXT+10]=INDEX;public.update(extra)
  for words in (retail,candidate):
   m=Caller(words,base);m.case=c;m.entered=False;m.r[29]=sp;m.memory.update(extra)
   code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));code.update(zip(range(START,END,4),window));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   actual={a:v for a,v in m.memory.items()if not g.STACK-1024<=a<g.STACK+512}
   assert m.entered and (m.calls,m.packets,actual)==(calls,packets,public),(c,m.calls,calls)
  count+=1
 report=dict(cases=count,table_index=INDEX,caller='func_1500E470 callback window',caller_window_only=True,full_parent_qualified=False,helpers='modeled',source_installed=False);(g.out/'window_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
