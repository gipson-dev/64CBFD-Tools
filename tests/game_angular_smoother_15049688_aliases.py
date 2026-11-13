from importlib.machinery import SourceFileLoader
from pathlib import Path
import itertools
from tools.tests.test_game_point_transform_match import put
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests import game_angular_smoother_15049688_oracle as G
def run():
 results=[0,0,0];complete=0;incomplete=0;examples={}
 for role,delta,phase in itertools.product(('angle','velocity'),range(-0x50,0x21,4),(0,8)):
  row=(30.0,40.0,2.0,4.0,6.0,0.25);initial,args=G.fixture(row,False);sp=G.STACK+phase;address=sp+delta;put(initial,address,bits(30.0 if role=='angle' else 2.0));args=list(args);args[0 if role=='angle' else 2]=address;states=[]
  for w in G.programs():
   m=G.Machine(w,initial.copy(),tuple(args),phase,G.code);error=''
   try:m.run()
   except (AssertionError,KeyError,OverflowError) as e:error=type(e).__name__+':'+str(e)[:120]
   public=G.public(m.memory);span=tuple(m.memory.get(address+i)for i in range(4));states.append((error,public,m.calls,span))
  if any(x[0] for x in states):
   assert len({x[0] for x in states})==1,(role,delta,phase);assert states[0]==states[2]==states[3];incomplete+=1;continue
  complete+=1
  for i in range(1,4):
   if states[0]!=states[i]:results[i-1]+=1;examples.setdefault(i,{'role':role,'delta':hex(delta),'phase':phase,'retail_calls':states[0][2],'candidate_calls':states[i][2]})
 print('complete',complete,'incomplete',incomplete,'mismatches',results,'examples',examples)
