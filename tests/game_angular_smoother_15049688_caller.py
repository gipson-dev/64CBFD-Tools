from pathlib import Path
from importlib.machinery import SourceFileLoader
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests import game_angular_smoother_15049688_oracle as G
from tools.tests import game_angular_smoother_15049688_reference as R
CALLER=0x15121c00;ACTOR=0x30000;SCALE=0x800a3430;rom=(G.root/'conker/conker.us.bin').read_bytes();off=0x2d4b0+CALLER-0x15000000;caller=struct.unpack_from('>25I',rom,off)
class Caller(G.Machine):
 def __init__(self,ws,m,args,phase,code):FactoryOracle.__init__(self,ws,m,G.Case(phase),entry=CALLER,s=G.SYMS,arguments=args,connected=code)
 def record_call(self,t):
  if t==G.ENTRY:self.calls.append((t,tuple(self.arguments(6))))
  else:super().record_call(t)
def run():
 programs=G.programs();count=0
 for row,phase in itertools.product(G.corpus()[:28],(0,8)):
  angle,target,velocity,strength,damping,dt=row;m={G.STACK+i:(i*17+0xa5)&255 for i in range(-256,256)};m.update({ACTOR+i:(i*29+0x5a)&255 for i in range(0x900)});put(m,ACTOR+0x37c,bits(angle));put(m,ACTOR+0x8c0,bits(velocity));put(m,ACTOR+0x7b4,bits(dt));put(m,SCALE,bits(2.5));args=(ACTOR,bits(target),bits(-123.0),bits(strength),bits(damping));states=[]
  expected,_=R.reference(m,(ACTOR+0x37c,bits(target),ACTOR+0x8c0,bits(strength),bits(damping),bits(dt)))
  for w in programs:
   code=dict(G.code);code.update(zip(range(G.ENTRY,G.ENTRY+len(w)*4,4),w));x=Caller(caller,m.copy(),args,phase,code).run();states.append((G.public(x.memory),x.calls))
  assert states.count(states[0])==4,(row,phase)
  memory,calls=states[0];assert calls[0]==(G.ENTRY,(ACTOR+0x37c,bits(target),ACTOR+0x8c0,bits(strength),bits(damping),bits(dt)))
  assert read(memory,ACTOR+0x37c)==read(expected,ACTOR+0x37c) and read(memory,ACTOR+0x8c0)==read(expected,ACTOR+0x8c0)
  assert read(memory,ACTOR+0x39c)==bits(R.f32(floating(read(expected,ACTOR+0x37c))*2.5));count+=1
 print('retail caller cases',count,'programs',len(programs))
