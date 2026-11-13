from importlib.machinery import SourceFileLoader
from pathlib import Path
import itertools,struct
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests import game_angular_smoother_15049688_oracle as G
def edges():
 programs=G.programs()
 vals=[0x00000000,0x80000000,0x00000001,0x80000001,0x3f800000,0xbf800000,0x7fc12345,0xffc12345];count=0;partial=0
 for field,word,alias,phase in itertools.product(range(6),vals,(0,1),(0,8)):
  row=(30.0,40.0,2.0,4.0,6.0,0.25);initial,args=G.fixture(row,alias);args=list(args)
  if field==0:put(initial,args[0],word)
  elif field==2:put(initial,args[2],word)
  else:args[field]=word
  states=[]
  for w in programs:
   m=G.Machine(w,initial.copy(),tuple(args),phase,G.code);error=''
   try:m.run()
   except (KeyError,AssertionError,OverflowError) as e:error=type(e).__name__+':'+str(e)[:120]
   states.append((error,G.public(m.memory),m.calls))
  if any(s[0]for s in states):partial+=1;continue
  assert states.count(states[0])==4,(field,hex(word),alias,phase,[s[2]for s in states]);count+=1
 print('special bit-pattern cases complete',count,'incomplete',partial,'programs',len(programs))
def faults():
 programs=G.programs()
 rows=G.corpus()[:12];cuts=0;private=0
 for row,alias in itertools.product(rows,(0,1)):
  initial,args=G.fixture(row,alias);full=G.Machine(programs[0],initial.copy(),args,0,G.code).run()
  for cut in range(full.all_accesses):
   machines=[]
   for w in programs:
    m=G.Machine(w,initial.copy(),args,0,G.code);m.cut=cut
    try:m.run();raise AssertionError(('missing cut',cut))
    except AccessBoundary:pass
    machines.append(m)
   retail=machines[0];assert all((m.memory,m.calls,m.trace)==(retail.memory,retail.calls,retail.trace)for m in machines[2:]),(row,alias,cut,'padded')
   assert (G.public(machines[1].memory),machines[1].calls)==(G.public(retail.memory),retail.calls),(row,alias,cut,'raw')
   private+=machines[1].memory!=retail.memory;cuts+=1
 print('modeled access cuts',cuts,'raw private differences',private,'cases',len(rows)*2)
