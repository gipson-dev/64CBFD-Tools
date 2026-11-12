import itertools,json,struct
from tools.tests import game_scene_transition_dispatch_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START=0x151E3304;END=0x151E3318;S=0x800BE3DF;C=0x800BE3E0
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(5))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>74I',rom,0x49be0);window=struct.unpack_from('>5I',rom,START-0x15000000+0x2d4b0);assert window[3]==(0x0c000000|((g.ENTRY>>2)&0x03ffffff))
 data,fs,rs=parse_object(g.out/'candidate.o');a,n=fs['func_1501C730']['value'],fs['func_1501C730']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};lookup={v[1]:v[2][1] for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};lookup['.rodata']=g.TABLE;candidate=bound_blob(data[a:a+n],refs,{nm:lookup[nm] for es in refs.values() for _,nm in es});assert tuple(candidate)==retail
 count=0
 for scene,channel,phase in itertools.product((0,1,127,128,254,255),(0,1,127,128,255),(0,8)):
  signed=scene if scene<128 else scene-256;c=g.Case(6,1,0,phase)
  for words in (retail,candidate):
   m=Caller(words,c);m.memory.update({g.STACK+i:(i*17+0xa5)&255 for i in range(-512,-256)});m.entered=False;m.r[29]=g.STACK+phase-0x100;m.r[2]=1;m.r[4]=6;m.r[5]=m.r[6]=0x800c0000;m.memory[S]=scene;m.memory[C]=channel
   code=dict(zip(range(g.ENTRY,g.ENTRY+296,4),words));code.update(zip(range(START,END,4),window));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('missing original caller boundary')
   assert m.entered and m.target_args==(6,signed&0xffffffff,channel,0,1),(scene,channel,m.target_args)
   assert m.calls==[g.RESET] and g.read(m.memory,g.SCENE)==(signed&0xffffffff) and m.memory[g.CHANNEL]==channel and g.read(m.memory,g.ARG4)==1 and g.read(m.memory,g.ARG3)==0 and g.read(m.memory,g.RESULT,2)==0 and m.memory[g.MODE]==2
  count+=1
 report=dict(cases=count,executions=count*2,caller='func_151E327C',window_words=5,caller_window_only=True,signed_scene_unsigned_channel=True,reset_modeled=True,source_installed=False)
 (g.out/'window_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
