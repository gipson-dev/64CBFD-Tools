"""Execute the real direct-call window; the enclosing renderer is not modeled."""
from pathlib import Path
import json,struct,sys
from tools.experiments import game_view_trig_render_walker_15167310_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_view_trig_render_walker_15167310_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
WINDOW=0x15018930;END=WINDOW+8
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:return
  super().record_call(t)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();code=rom[0x45DE0:0x45DE8];window=struct.unpack('>2I',code);assert window[0]==(3<<26|((g.ENTRY>>2)&0x3FFFFFF))
 for file in(out/'baseline/conker/build/conker.us.elf',out/'image-qualification/linked.elf',root/'conker/build/conker.us.elf'):
  data=file.read_bytes();at=elf_slot_offset(data,WINDOW,8);assert data[at:at+8]==code
 assert 'void func_15167310(void);'in(out/'proposal/conker/src/game_45B80.c').read_text()
 runs=0
 for path in g.paths().values():
  connected=dict(zip(range(g.ENTRY,g.ENTRY+len(g.words(path))*4,4),g.words(path)));connected[END]=0
  for c in(g.Case(),g.Case(count=-1,shape=0),g.Case(mode=33),g.Case(shape=4,mode=8)):
   m=Caller(window,g.fixture(c),c,connected=connected,entry=WINDOW);m.before[31]=END;m.code=WindowCode(m.code,m);m.code.ends=(END,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller window exit')
   g.check(m,c);runs+=1
 r=dict(caller_window_words=2,cases=runs,direct_JAL_VA=hex(WINDOW),direct_JAL_ROM='0x45DE0',enclosing_function='func_1501878C',all_three_linked_windows_unchanged=True,
  return_type_repaired_to_void=True,limits='Actual JAL and delay slot plus complete callee; enclosing renderer and complete caller behavior are not qualified.',source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
