"""Modeled effect callback connected to original dispatcher windows."""
import itertools,struct
from tools.experiments import game_actor_point_emit_150bed4c_match as match
from tools.tests import game_actor_point_emit_150bed4c_oracle as oracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
def run(state):
 g=vars(oracle)
 one,_=match.pad_both(state)
 bodies=(state['retail_words'],state['raw_words'],oracle.words(one))
 class Connected(g['Oracle']):
  def __init__(self,entry,parent,initial,c,body):
   self.cc=c;self.obs=[];self.point=g['STACK']+c.phase-12;self.result=g['STACK']+c.phase-48
   connected=dict(zip(range(g['ENTRY'],g['ENTRY']+356,4),body));g['g'].Oracle.__init__(self,parent,initial,c,entry=entry,connected=connected);self.home=g['STACK']+c.phase
  def record_call(self,t):
   if t==g['ENTRY']:
    a=tuple(map(g['g'].u32,self.arguments(3)));self.calls.append((t,a));self.home=self.r[29]
   else:super().record_call(t)
 rom=state['rom'];table=0x8008a0b4;index=18;record=0x70000;n=0
 for which,mode,amount,active,answer,phase in itertools.product(range(2),(0,1,7,0xabcd00ff),(-32768,0,75,76,32767),(0,0x50000),(0,1),(0,8)):
  amount=0 if which==0 else amount;c=g['Case'](mode=mode,amount=amount,active=active,answer=answer,phase=phase);initial=g['fixture'](c);g['put'](initial,table+index*8,g['ENTRY']);g['put'](initial,table+index*8+4,85)
  for i in range(64):initial[record+i]=165
  g['put'](initial,record+14,amount&0xffff,2);entry,off,num,end=(0x15141B4C,0x16EFFC,5,0x15141B60)if which==0 else(0x15141BAC,0x16F05C,8,0x15141BCC);parent=struct.unpack_from('>%dI'%num,rom,off)
  want,calls,obs=g['reference'](initial,c)
  for body in bodies:
   m=Connected(entry,parent,initial,c,body);m.r[18]=c.actor;m.r[19]=mode;m.r[16]=table;m.r[14]=table+index*8;m.r[12]=index;m.r[2]=record;m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run();raise AssertionError('window did not stop')
   except WindowBoundary:pass
   assert g['public'](m.memory)==want,c;assert m.calls==[(g['ENTRY'],(c.actor,mode,amount&0xffffffff))]+calls,(c,m.calls,calls);assert m.obs==obs,c
  n+=1
 return dict(cases=n,programs=3,parent_windows=['0x15141B4C','0x15141BAC'],table='D_8008A0B4 entry 18',retail_count=85)
