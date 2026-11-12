"""Execute both original wrapper bodies connected to the candidate effect."""
import itertools,struct
from tools.experiments import game_actor_point_flagged_15146bf8_match as match
from tools.tests import game_actor_point_flagged_15146bf8_oracle as o

def run(state):
 one,_=match.pad_both(state);bodies=(state['retail_words'],state['raw_words'],o.words(one));rom=state['rom'];count=0
 class Connected(o.Oracle):
  def __init__(self,entry,parent,c,body):
   self.cc=c;self.obs=[];code=dict(zip(range(o.ENTRY,o.ENTRY+360,4),body))
   o.g.Oracle.__init__(self,parent,o.fixture(c),c,entry=entry,connected=code);self.home=o.STACK+c.phase
  def record_call(self,t):
   if t==o.ENTRY:
    self.calls.append((t,tuple(map(o.g.u32,self.arguments(4)))));self.home=self.r[29]
   else:super().record_call(t)
 for flag,mode,amount,active,answer,phase in itertools.product((0,1),(0,1,2,255),(0,114,115,130),(0,0x50000),(0,1),(0,8)):
  entry,off=((0x15146BB8,0x174068),(0x15146BD8,0x174088))[flag];parent=struct.unpack_from('>8I',rom,off)
  c=o.Case(flag=flag,mode=mode,amount=amount,active=active,answer=answer,phase=phase,mutation=(mode%4)*4)
  want,calls,obs=o.reference(o.fixture(c),c,home=o.STACK+phase-0x18)
  for body in bodies:
   m=Connected(entry,parent,c,body).run();m.assert_control();assert m.r[29]==o.STACK+phase
   assert o.public(m.memory)==want,c
   assert m.calls==[(o.ENTRY,(c.actor,o.g.u32(c.mode),o.g.u32(c.amount),flag))]+calls,(c,m.calls,calls)
   assert m.obs==obs,c
  count+=1
 return dict(cases=count,programs=3,wrappers=['func_15146BB8','func_15146BD8'],flag_delay_slots=[0,1])
