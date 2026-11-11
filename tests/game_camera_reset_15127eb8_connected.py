"""Connect the original camera-mode helper; model its nested helper."""
import itertools,json,struct
from tools.experiments import game_camera_reset_15127eb8_match as p
from tools.tests import game_camera_reset_15127eb8_oracle as g
NESTED=0x15124b18
class Connected(g.Oracle):
 def record_call(self,t):
  if t==NESTED:self.calls.append((t,tuple(self.arguments(1))))
  else:super().record_call(t)
 def hook(self,t):
  if t==NESTED:
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
  else:super().hook(t)
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();body=struct.unpack('>77I',(p.out/'original-function.bin').read_bytes());helper=struct.unpack_from('>34I',rom,0x150e7c);code=dict(zip(range(g.ENABLE,g.ENABLE+136,4),helper));n=0
 for gate,slot,idx,mut in itertools.product((0,1),(0,2),(0,1,3),(0,2,4,8)):
  c=g.Case(slot,idx,mut,0,n%3);m=Connected(body,c);m.code.update(code);g.put(m.memory,g.CAMERA+0x20e,gate,2);initial=dict(m.memory)
  if gate:
   for dest,src,size in ((0,4,2),(0x2c,0x34,4),(0xdc,0xe4,4),(0x84,0x8c,4),(0x134,0x13c,4),(0x1b4,0x1b8,2),(0x1e0,0x1e4,2)):g.put(initial,g.CAMERA+dest,g.read(initial,g.CAMERA+src,size),size)
   g.put(initial,g.CAMERA+0x20e,0,2)
  want,calls=g.reference(c,initial)
  if gate:calls.insert(1,(NESTED,(g.CAMERA,)))
  m.run();assert g.public(m.memory)==g.public(want),(c,gate,'memory');assert m.calls==calls,(c,gate,m.calls,calls);n+=1
 result=dict(cases=n,original_camera_helper_words=len(helper),nested_helper_modeled=True,other_helpers_modeled=True,source_installed=False);(p.out/'connected.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
