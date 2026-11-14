from pathlib import Path
import json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.test_game_viewport_command_helper import ViewportOracle,case,ENTRY,PAGE,TABLE,BASE
from tools.tests import test_game_queued_segment_writer as queue
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-viewport-helper-shape-screen';sym={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};truth=list(struct.unpack_from('>105I',(root/'conker/conker.us.bin').read_bytes(),0x138c64));raw=bound_blob(*payload(out/'owner-candidate.o','func_1510B7B4'),sym);guard=bound_blob(*payload(out/'guarded.o','func_1510B7B4'),sym)
class Stop(Exception):pass
class Fence(ViewportOracle):
 def __init__(self,*a,cut=None):self.cut=cut;self.accesses=0;super().__init__(*a)
 def step(self):
  if self.cut==self.accesses:raise Stop()
  self.accesses+=1
 def get(self,address,size):self.step();return super().get(address,size)
 def put(self,address,value,size):
  if self.recording:self.step()
  return super().put(address,value,size)
def execute(code,initial,output,slot,cut):
 machine=Fence(code,ENTRY,initial,(output,slot),cut=cut)
 try:machine.run();done=True
 except Stop:done=False
 return done,machine
prefixes=0;cases=0;rawdiff=0
for output in (queue.OUTPUT,PAGE-12,TABLE-84,PAGE-76,BASE-68):
 for slot,page in ((0,0),(3,1)):
  initial=case(slot,page,0x8001,output);done,complete=execute(truth,initial,output,slot,None);assert done
  for n in range(complete.accesses+1):
   states=[]
   for code in(truth,raw,guard):
    done,m=execute(code,initial,output,slot,n);states.append((done,m.memory,m.reads,m.stores,m.r[2] if done else None))
   assert states[0]==states[1]==states[2],(output,slot,page,n);prefixes+=1
  cases+=1
report={'fixture_cases':cases,'access_prefixes_per_stream':prefixes,'streams':['retail','raw','guarded'],'uncredited':True};(out/'fault.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
