from importlib.machinery import SourceFileLoader
from pathlib import Path
import itertools
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests import game_angular_smoother_15049688_oracle as G
f32=lambda x:floating(bits(x))
def delta(a,b):
 x=f32(a-b)
 if x>180.0:a=f32(a-360.0)
 elif x<=-180.0:b=f32(b-360.0)
 return f32(b-a)
def reference(initial,args):
 m=dict(initial);p,t,v,k,d,dt=args;t,k,d,dt=map(floating,(t,k,d,dt));calls=[]
 a=floating(read(m,p));calls.append((G.DELTA,(bits(a),bits(t))));diff=delta(a,t);direction=-1 if diff<0 else 1;old=floating(read(m,v));result=f32(old+f32(f32(f32(f32(diff*k)-old)*d)*dt));put(m,v,bits(result))
 if abs(diff)<10:
  stepped=f32(f32(floating(read(m,v))*dt)+floating(read(m,p)));calls.append((G.DELTA,(bits(stepped),bits(t))));nextdiff=delta(stepped,t);nextdir=-1 if nextdiff<0 else 1
  if nextdir!=direction:put(m,p,bits(t));put(m,v,0)
  else:put(m,p,bits(f32(floating(read(m,p))+f32(floating(read(m,v))*dt))))
 else:put(m,p,bits(f32(floating(read(m,p))+f32(floating(read(m,v))*dt))))
 calls.append((G.NORMALIZE,(p,)));value=floating(read(m,p))
 while value<0:value=f32(value+360.0);put(m,p,bits(value))
 while value>=360:value=f32(value-360.0);put(m,p,bits(value))
 return G.public(m),calls
def run():
 programs=G.programs();total=0;paths=set()
 for row,alias,phase in itertools.product(G.corpus(),(False,True),(0,8)):
  initial,args=G.fixture(row,alias);expected=reference(initial,args);states=[]
  for w in programs:
   m=G.Machine(w,initial.copy(),args,phase,G.code).run();states.append((G.public(m.memory),m.calls))
  assert states.count(expected)==4,(row,alias,phase,states[0][1],expected[1]);paths.add(len(expected[1]));total+=1
 print('independent model cases',total,'helper call paths',sorted(paths),'programs',len(programs))
