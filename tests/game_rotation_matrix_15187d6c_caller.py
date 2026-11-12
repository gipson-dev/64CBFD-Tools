"""Connected retail caller window with bounded helper models."""
import itertools,struct
from tools.experiments import game_rotation_matrix_15187d6c_match as match
from tools.tests import game_rotation_matrix_15187d6c_oracle as oracle
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
def run(state):
 g=vars(oracle)
 one,_=match.pad_both(state)
 padded=oracle.words(one)
 START=0x15187BD8;NEXT=0x150A7A48;OBJ=0x32000;OUT=0x34000;rom=state['rom'];parent=struct.unpack_from('>12I',rom,0x1B5088);assert parent[2]==0x0d461f5b and parent[6]==0x0d429e92
 class End(Exception):pass
 class Connected(g['Guest']):
  def __init__(self,body,c):
   memory=g['fixture']();memory.update({OBJ+i:0 for i in range(0x90)});put(memory,OBJ+0x80,c.x);put(memory,OBJ+0x84,c.y);put(memory,OBJ+0x88,c.z);self.snap=[]
   connected=dict(zip(range(g['ENTRY'],g['ENTRY']+332,4),body));FactoryOracle.__init__(self,parent,memory,c,entry=START,arguments=(g['MATRIX'],0,OBJ,0),connected=connected);self.r[2]=OBJ;self.r[20]=OUT;self.r[22]=g['MATRIX'];self.before[20]=OUT;self.before[22]=g['MATRIX'];self.saved_f=self.f[20:].copy()
  def record_call(self,t):
   if t in (g['ENTRY'],NEXT):self.calls.append((t,tuple(self.r[4:8])))
   else:super().record_call(t)
  def hook(self,t):
   if t==NEXT:raise End()
   super().hook(t)
 n=0
 for xyz in itertools.product((-90.,-1.,0.,1.,90.),repeat=3):
  for phase in (0,8):
   c=g['Case'](*[g['bits'](v) for v in xyz],phase);want,calls=g['expected'](c);m=Connected(padded,c)
   try:m.run();raise AssertionError('caller did not continue')
   except End:pass
   assert m.calls[0]==(g['ENTRY'],(g['MATRIX'],c.x,c.y,c.z)),(c,m.calls[0]);assert m.calls[1:8]==calls;assert m.calls[8][0]==NEXT and m.calls[8][1][:3]==(OUT,g['MATRIX'],OUT);assert [read(m.memory,g['MATRIX']+4*i) for i in range(16)]==want;n+=1
 return dict(cases=n,parent_window='15187BD8..15187BF8',connected_target='guarded retail-exact body',stopped_at='func_150A7A48',note='modeled trig and identity helpers; not full parent')
