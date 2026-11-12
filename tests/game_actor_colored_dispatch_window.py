import itertools,json,struct
from tools.tests import game_actor_colored_dispatch_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START=0x1503394c;END=0x15033968
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(6))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>75I',rom,0x12fb6c);window=struct.unpack_from('>7I',rom,START-0x15000000+0x2d4b0);assert window[5]==(0x0c000000|((g.ENTRY>>2)&0x03ffffff))
 elf=(g.root/'conker/build/conker.us.elf').read_bytes();data,fs,rs=parse_object(g.out/'mixed-generated.o');a,n=fs['func_151026BC']['value'],fs['func_151026BC']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};lookup={v[1]:v[2][1]for v in symbol_rows(elf)};candidate=bound_blob(data[a:a+n],refs,{nm:lookup[nm]for es in refs.values()for _,nm in es});assert tuple(candidate)==retail
 count=0
 for identity,kind,mode,phase in itertools.product((0,0x58,0x59,0x5a,0x5b,0x5f,0x74,0x75,0x7a,0x80,0xff),(0x3a,0x3b),(4,5,6),(0,8)):
  c=g.Case(identity,kind,mode,phase);expected,value=g.reference(c,g.fixture(c));args=list(expected[0][1]);args[4]=0xffffffff;args[12:15]=[1,255,1];expected=[(g.HELPER,tuple(args))]
  for words in (retail,candidate):
   m=Caller(words,c);m.entered=False;m.r[29]=g.STACK+phase-0x100;m.r[5]=0xffffffff;m.r[6]=mode;g.put(m.memory,m.r[29]+0x24,g.ACTOR)
   code=dict(zip(range(g.ENTRY,g.ENTRY+300,4),words));code.update(zip(range(START,END,4),window));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('missing caller continuation')
   assert m.entered and m.target_args==(g.ACTOR,0xffffffff,mode,1,255,1),(c,m.target_args)
   assert m.calls==expected and m.r[2]==value,(c,m.calls,expected)
  count+=1
 report=dict(cases=count,executions=count*2,caller='func_15033838',caller_window_words=7,full_parent_not_claimed=True,helper='modeled',source_installed=False);(g.out/'window_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
