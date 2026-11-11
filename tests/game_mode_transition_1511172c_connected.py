"""Connect the original slot-release helper on bounded defined cases."""
import json,struct
from tools.experiments import game_mode_transition_1511172c_match as p
from tools.tests import game_mode_transition_1511172c_oracle as g
CLEAN_NESTED=0x1510D608;FLAGS=0x800BC448;COUNTS=0x800D9F68;LOW=0x800D9F58;HIGH=0x800D9F5C
class Connected(g.Oracle):
 def record_call(self,t):
  if t==CLEAN_NESTED:self.calls.append((t,tuple(self.arguments(2))))
  else:super().record_call(t)
 def hook(self,t):
  if t==CLEAN_NESTED:
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
  else:super().hook(t)
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();body=struct.unpack('>75I',(p.out/'original-function.bin').read_bytes());helper=struct.unpack_from('>35I',rom,0x13ab44);code=dict(zip(range(g.CLEAN,g.CLEAN+140,4),helper));n=0
 for pattern in range(6):
  c=g.Case(6,1,4,1,pattern&1,0,0,pattern%3);m=Connected(body,c);m.code.update(code);base=0x1200
  for i in range(360):m.memory[FLAGS+base+i]=(i+pattern)%3!=0;m.memory[COUNTS+base+i]=(i+pattern)%4
  g.put(m.memory,LOW,base+180);g.put(m.memory,HIGH,base+180);m.initial=dict(m.memory);want,calls=g.reference(c,m.initial);expanded=[]
  for target,args in calls:
   expanded.append((target,args))
   if target==g.CLEAN:
    k=args[0]
    if want[FLAGS+k] and want[COUNTS+k]:
     v=want[COUNTS+k]-1;want[COUNTS+k]=v
     if v==0:
      if k<g.read(want,LOW):g.put(want,LOW,k)
      if k>g.read(want,HIGH):g.put(want,HIGH,k)
      expanded.append((CLEAN_NESTED,(k,3)))
  m.run();assert g.public(m.memory)==g.public(want),(pattern,'memory');assert m.calls==expanded,(pattern,'calls',m.calls[:5],expanded[:5]);n+=1
 result=dict(cases=n,original_cleanup_words=len(helper),cleanup_calls=360*n,nested_calls_modeled=True,other_helpers_modeled=True,source_installed=False);(p.out/'connected.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
