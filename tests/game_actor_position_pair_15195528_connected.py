"""Connect original 22-word direction helper; model sine and cosine."""
import itertools,json,struct
from tools.experiments import game_actor_position_pair_15195528_match as p
from tools.tests import game_actor_position_pair_15195528_oracle as g
COS=0x15047c00;SIN=0x15047d60
class Connected(g.Oracle):
 def record_call(self,t):
  if t in (COS,SIN):self.calls.append((t,(self.f[12],)))
  else:super().record_call(t)
 def hook(self,t):
  if t==COS:
   g.mutate(self.memory,self.c);super().hook(t);self.f[0]=self.c.cos
  elif t==SIN:super().hook(t);self.f[0]=self.c.sin
  else:super().hook(t)
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();body=struct.unpack('>74I',(p.out/'original-function.bin').read_bytes());helper=struct.unpack_from('>22I',rom,0x170bec);code=dict(zip(range(g.TRIG,g.TRIG+88,4),helper));n=0
 for source,yaw,mutation in itertools.product((0,1),(g.bits(0.),g.bits(45.),g.bits(180.)),(0,1)):
  c=g.Case(source,1,yaw,g.bits(-30.),g.bits(.5),g.bits(.25),g.bits(-.75),g.bits(.25),mutation,0,n%3);m=Connected(body,c);m.code.update(code);m.run();want,angle,start,end,direction=g.reference(c,m.initial);assert g.public(m.memory)==g.public(want),(c,'memory');assert m.calls==[(g.TRIG,(angle,g.bits(1.))),(COS,(angle,)),(SIN,(angle,)),(g.SUBMIT,(g.ACTOR,255,1))],(c,m.calls);assert m.observation==(start,end,direction),(c,m.observation);n+=1
 result=dict(cases=n,original_direction_helper_words=len(helper),sine_cosine_modeled=True,submit_modeled=True,finite_nearest_rounding_only=True,source_installed=False);(p.out/'connected.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
