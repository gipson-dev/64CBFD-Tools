import itertools,json,struct
from tools.tests import game_actor_colored_dispatch_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START=0x15054f0c;END=0x15054f38;OWNER=0x50000
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(6))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>75I',rom,0x12fb6c);window=struct.unpack_from('>11I',rom,START-0x15000000+0x2d4b0);assert window[9]==(0x0c000000|((g.ENTRY>>2)&0x03ffffff))
 elf=(g.root/'conker/build/conker.us.elf').read_bytes();data,fs,rs=parse_object(g.out/'mixed-generated.o');a,n=fs['func_151026BC']['value'],fs['func_151026BC']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};lookup={v[1]:v[2][1]for v in symbol_rows(elf)};candidate=bound_blob(data[a:a+n],refs,{nm:lookup[nm]for es in refs.values()for _,nm in es});assert tuple(candidate)==retail
 count=0
 for identity,kind,phase in itertools.product((0,0x58,0x59,0x5a,0x5b,0x5f,0x74,0x75,0x7a,0x80,0xff),(0x3a,0x3b),(0,8)):
  c=g.Case(identity,kind,3,phase);expected,value=g.reference(c,g.fixture(c));args=list(expected[0][1]);args[4]=0xffffffff;args[12:15]=[1,255,1];expected=[(g.HELPER,tuple(args))]
  for words in(retail,candidate):
   m=Caller(words,c);m.entered=False;m.r[29]=g.STACK+phase-0x100;m.r[16]=OWNER;m.r[13]=g.ACTOR;m.memory.update({OWNER+0x2e8+i:0 for i in range(4)})
   code=dict(zip(range(g.ENTRY,g.ENTRY+300,4),words));code.update(zip(range(START,END,4),window));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   except KeyError as e:raise AssertionError((e,c,hex(m.r[16]),hex(m.r[25]),g.read(m.memory,OWNER+0x2e8),m.calls)) from e
   else:raise AssertionError('missing caller continuation')
   assert m.entered and m.target_args==(g.ACTOR,0xffffffff,3,1,255,1),(c,m.target_args)
   assert m.calls==expected and m.r[2]==value,(c,m.calls,expected)
  count+=1
 report=dict(cases=count,executions=count*2,caller='func_15054A94',caller_window_words=11,full_parent_not_claimed=True,helper='modeled',source_installed=False);(g.out/'window2_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
