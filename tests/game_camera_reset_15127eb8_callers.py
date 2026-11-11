"""Six original direct caller windows through the camera reset."""
import itertools,json,struct
from tools.experiments import game_camera_reset_15127eb8_match as p
from tools.tests import game_camera_reset_15127eb8_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
SITES=(0x15122eb0,0x15125464,0x15126ce4,0x15128e6c,0x15129240,0x1512925c);SCRATCH=0x36000
class Caller(g.Oracle):
 def record_call(self,t):
  if t==p.ENTRY:self.callback_args=tuple(self.arguments(1))
  else:super().record_call(t)
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();words=struct.unpack('>77I',(p.out/'original-function.bin').read_bytes());n=0
 for site,slot,idx,mut in itertools.product(SITES,(0,2),(0,1,3),(0,3,12,15)):
  c=g.Case(slot,idx,mut,0,n%3);offset=site-0x15000000+0x2d4b0;window=struct.unpack_from('>2I',rom,offset);assert window[0]==0x0d449fae
  m=Caller(window,c);m.code=dict(zip((site,site+4),window));m.code.update(zip(range(p.ENTRY,p.ENTRY+308,4),words));m.code[site+8]=0;m.code=WindowCode(m.code,m);m.code.ends=(site+8,);m.entry=site;m.r[16]=g.CAMERA;m.r[17]=g.CAMERA;m.r[4]=g.CAMERA;m.r[13]=SCRATCH
  for i in range(4):m.memory[SCRATCH+i]=0x7b+i
  expected_initial=dict(m.memory)
  if window[1]==0xA620073C:g.put(expected_initial,g.CAMERA+0x73c,0,2)
  elif window[1]==0xADA00000:g.put(expected_initial,SCRATCH,0)
  else:assert window[1]==0x02002025,hex(window[1])
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('window did not return')
  want,calls=g.reference(c,expected_initial);assert g.public(m.memory)==g.public(want),(site,c,'memory');assert m.calls==calls,(site,c,'calls');assert m.callback_args==(g.CAMERA,);assert m.r[29]==g.STACK and m.r[31]==site+8;n+=1
 result=dict(original_call_sites=len(SITES),cases=n,helpers_modeled=True,bounded_windows_only=True,source_installed=False);(p.out/'callers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
