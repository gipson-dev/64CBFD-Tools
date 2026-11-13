from pathlib import Path
from importlib.machinery import SourceFileLoader
import itertools
from tools.tests import game_state_trajectory_15072f10_oracle as G
def runone(c,initial,programs):
 states=[]
 for w in programs:
  m=G.Machine(w,c,initial.copy());error=''
  try:m.run()
  except (AssertionError,KeyError)as e:
   if not (isinstance(e,KeyError) or str(e).startswith("('saved register',") or str(e).startswith("('unowned jump',") or str(e).startswith("('unmapped read',")):raise
   error=type(e).__name__+':'+str(e)
  span=tuple(m.memory.get(G.STACK+c.phase+i)for i in range(-0xa0,0x80));states.append((error,G.public(m.memory,c),m.calls,m.r[2],span))
 assert states[0][:4]==states[2][:4]==states[3][:4];assert states[0][:4]==states[1][:4],([s[0]for s in states], [s[2]for s in states]);return bool(states[0][0])
def run():
 programs=G.programs()
 count=0;partial=0
 for role,delta,phase,mutation in itertools.product(('actor','state'),range(-0x80,0x41,4),(0,8),(0,1)):
  c=G.Case(phase=phase,pitch=3,timer=7,angle=0x2345,offset=-123,mutation=mutation);m=G.fixture(c);home=G.STACK+phase
  if role=='actor':
   a=home+delta
   for i in range(0x400):m.setdefault(a+i,(i*29+0x5a)&255)
   G.put(m,G.CURRENT,a);G.put(m,a+0x31c,G.STATE);m[a+0x1d1]=3;G.put(m,a+0x7a,0x2345,2);G.put(m,a+0xd6,-30,2)
   for off,val in zip((0x14,0x18,0x1c),(100.5,-25.25,300.75)):G.put(m,a+off,G.bits(val))
  else:
   state=home+delta
   for i in range(0x30):m.setdefault(state+i,(i*29+0x5a)&255)
   G.put(m,G.ACTOR+0x31c,state);G.put(m,state+0x12,-123,2);G.put(m,state+0x24,7,2)
  try:partial+=runone(c,m,programs);count+=1
  except AssertionError as e:raise AssertionError((role,delta,phase,mutation,e))
 print('stack-alias cases',count,'stopped',partial)
 # State timer aliases another field of the active actor.
 count=0
 for offset in range(-0x24,0x200,2):
  c=G.Case(pitch=3,timer=7,angle=0x2345,offset=-123);m=G.fixture(c);state=G.ACTOR+offset;G.put(m,G.ACTOR+0x31c,state)
  try:runone(c,m,programs);count+=1
  except (AssertionError,KeyError)as e:raise AssertionError(('actor-state overlap',offset,e))
 print('actor-state alias cases',count)
 # Timer overwrites the high half of the global actor pointer; the second load must observe it.
 c=G.Case(pitch=2,timer=3,angle=0x1234,offset=5);m=G.fixture(c);new_actor=0x20000
 for i in range(0x400):m[new_actor+i]=m[G.ACTOR2+i]
 G.put(m,G.ACTOR+0x31c,G.CURRENT-0x24);G.put(m,G.CURRENT-0x12,5,2)
 runone(c,m,programs);print('global-pointer alias passed')
