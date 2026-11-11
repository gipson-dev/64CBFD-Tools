"""Bounded original callback dispatch windows for table index 27."""
import itertools,json,struct
from tools.experiments import game_actor_position_pair_15195528_match as p
from tools.tests import game_actor_position_pair_15195528_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
TABLE=0x80086694
class Caller(g.Oracle):
 def record_call(self,t):
  if t==p.ENTRY:self.callback_args=tuple(self.arguments(3))
  else:super().record_call(t)
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();words=struct.unpack('>74I',(p.out/'original-function.bin').read_bytes());windows=((0x1505c6dc,0x1505c6fc),(0x1505bd74,0x1505bd9c));n=0
 assert int.from_bytes(rom[0x22b1c0:0x22b1c4],'big')==p.ENTRY
 for kind,source,yaw,mutation in itertools.product((0,1),(0,1),(g.bits(0.),g.bits(45.),g.bits(180.)),(0,1)):
  c=g.Case(source,1,yaw,g.bits(-30.),g.bits(.5),g.bits(.25),g.bits(-.75),g.bits(.25),mutation,0,n%3);start,end=windows[kind];offset=start-0x15000000+0x2d4b0;window=struct.unpack_from('>%dI'%((end-start)//4),rom,offset);m=Caller(window,c);m.code=dict(zip(range(start,end,4),window));m.code.update(zip(range(p.ENTRY,p.ENTRY+296,4),words));m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,);m.entry=start;g.put(m.memory,TABLE+27*4,p.ENTRY);m.r[2]=27;m.r[16]=g.ACTOR;m.r[17]=g.SOURCE if source else 0
  if kind==1:m.r[15]=0;m.r[1]=0x27;m.r[9]=0x77777777;g.put(m.memory,g.STACK+0x68,g.SOURCE if source else 0)
  m.initial=dict(m.memory)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('callback window did not return')
  want,angle,startpos,endpos,direction=g.reference(c,m.initial);assert g.public(m.memory)==g.public(want),(kind,c,'memory');assert m.calls==[(g.TRIG,(angle,g.bits(1.))),(g.SUBMIT,(g.ACTOR,255,1))];assert m.observation==(startpos,endpos,direction);assert m.callback_args==(g.SOURCE if source else 0,g.ACTOR,g.STACK+(0x54 if kind==0 else 0x67));assert m.r[29]==g.STACK and m.r[31]==end; n+=1
 result=dict(dispatcher_windows=2,callback_index=27,cases=n,source_nullable_actor_nonnull=True,helpers_modeled=True,full_parents_not_qualified=True,source_installed=False);(p.out/'callers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
