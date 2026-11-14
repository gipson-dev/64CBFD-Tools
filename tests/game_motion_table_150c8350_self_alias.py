"""Check records overlapping the table-pointer storage up to mapped faults."""
from tools.tests import game_motion_table_150c8350_common as g
from tools.tests.game_motion_table_150c8350_common import *
class UnmappedWrite(Exception):pass
class Bounded(FactoryOracle):
 def put(self,address,value,size):
  if self.recording and self.own_instruction and not all(address+i in self.memory for i in range(size)):raise UnmappedWrite(address,size)
  return super().put(address,value,size)
count=0;faults=0
for delta,pattern,tick,half in itertools.product((-8,-6,-4,-2),range(4),(0,1),(1,255)):
 g.table=s['D_800BE4E0']+delta;initial=fixture(pattern,tick,half,1);put(initial,s['D_800BE4E0'],g.table);states=[]
 for label in ('retail','raw','guarded'):
  m=Bounded(programs[label],initial.copy(),Case(),entry=entry,s={},arguments=(0,))
  try:m.run();outcome=('return',)
  except AssertionError as e:
   assert e.args and isinstance(e.args[0],tuple) and e.args[0][0]=='unmapped read',e;outcome=('read-fault',*e.args[0][1:])
  except UnmappedWrite as e:outcome=('write-fault',*e.args)
  states.append((outcome,m.memory,m.trace,m.r,m.hi,m.lo,m.current_pc,m.delay_of))
 assert states[0]==states[1]==states[2],(delta,pattern,tick,half);faults+=states[0][0][0]!='return';count+=1
assert count==64 and faults>0,(count,faults)
report={'cases_per_stream':count,'mapped_fault_cases':faults,'uncredited':True};(out/'self-alias.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
