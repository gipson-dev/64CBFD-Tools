from pathlib import Path
import itertools,struct,sys
from tools.experiments.game_point_descriptor_151382e0_match import ROOT as root, OUT as out
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_scaled_descriptor_match import ScaledOracle
from tools.tests.test_game_grid_channel_updater_match import STACK,external,put,read

ENTRY=0x151382E0;SUBMIT=0x15153F18;SOURCE=0x30000;SURFACE=0x60000
symbols={name:field[1] for _,name,field,_ in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
def words(path):
 data,relocs=payload(path,'func_151382E0')
 return bound_blob(data,relocs,{name:symbols[name] for rows in relocs.values() for _,name in rows})
truth=list(struct.unpack_from('>81I',(root/'conker/conker.us.bin').read_bytes(),0x165790))
padded=words(out/'durable-point-padded.o');raw=words(out/'durable-point-after.o');assert padded==truth
class Oracle(ScaledOracle):
 def __init__(self,code,mem,args,phase):
  super().__init__(code,mem,args,phase=phase);self.entry=ENTRY;self.code={ENTRY+4*i:w for i,w in enumerate(code)};self.snapshots=[]
 def record_call(self,target):
  assert target==SUBMIT,(hex(target),hex(self.entry));a=self.arguments(5)
  self.snapshots.append((tuple(a),bytes(self.get(a[0]+i,1) for i in range(76))))
 def hook(self,target):
  assert target==SUBMIT
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)]

def fixture(kind,cat,group,phase,seed,position):
 mem={STACK+i:(i*17+seed*7+13)&255 for i in range(-0x600,0x140)}
 for i,v in enumerate((0x7FC12345+seed,0x80000000,0x3F800000+seed)):put(mem,position+4*i,v)
 for i,v in enumerate((0x3f012345,0x80000000,0x7fc12345,0x7f800000,0xff800000)):put(mem,0x800A4830+4*i,(v+seed)&0xffffffff)
 mem[0x800A3FE6+kind*16]=cat
 return mem,(position,kind,SURFACE,group,0x81552341+seed)
def expected(mem,args,cat,base):
 b={i:mem[base+i] for i in range(76)};put(b,8,read(mem,args[0]));put(b,12,read(mem,args[0]+4));put(b,16,read(mem,args[0]+8))
 for i in range(4):put(b,20+4*i,read(mem,0x800A4830+4*i))
 for off,val in ((36,0x40800000),(40,0x41100000),(64,read(mem,0x800A4840)),(72,0)):put(b,off,val)
 for off,val in ((0,0),(2,255),(4,0xffc1),(6,78),(44,18),(46,7),(48,3),(50,3),(52,20),(54,30),(56,155),(58,100),(68,16),(70,15)):put(b,off,val,2)
 b[60]=int(cat==1);return bytes(b[i] for i in range(76))
cases=0;visits=set()
for kind,cat,group,phase,seed,alias in itertools.product((0,1,7,19),(0,1,2,255),(0,1,127,128,255),(0,8),(0,1),(0,1)):
 position=(SOURCE,STACK+phase+0x20)[alias];mem,args=fixture(kind,cat,group,phase,seed,position)
 models=[Oracle(code,mem,args,phase).run() for code in (truth,padded,raw)]
 a,b,c=models;assert (a.memory,a.snapshots,a.events)==(b.memory,b.snapshots,b.events);visits.update(a.visits)
 assert external(a.memory)==external(mem) and external(c.memory)==external(mem)
 if cat==2:assert not a.snapshots and not c.snapshots
 else:
  for model,delta in ((a,0),(c,-8)):
   assert len(model.snapshots)==1
   call,body=model.snapshots[0];base=STACK+phase-0x4c+delta
   assert call==(base,base+8,SURFACE,group,args[4]),(call,args,delta)
   wanted=expected(mem,args,cat,base)
   assert all(body[i]==wanted[i] for i in range(76) if i not in (61,62,63)),(kind,cat,group,phase,seed,alias,delta)
   assert body[61:64]==wanted[61:64]
  assert all(a.snapshots[0][1][i]==c.snapshots[0][1][i] for i in range(76) if i not in (61,62,63))
 cases+=1
print('guest nonoverlap cases',cases,'retail words visited',len(visits),'of 81; raw and padded descriptors verified; caller-owned stack position included')
# Guest-only overlaps into the callee frame establish whether frame adjustment is semantically transparent.
changed=[]
for offset in range(-0x70,-0x20,4):
 mem,args=fixture(0,0,7,0,1,STACK+offset)
 a=Oracle(truth,mem,args,0).run();b=Oracle(padded,mem,args,0).run();c=Oracle(raw,mem,args,0).run()
 assert (a.memory,a.snapshots,a.events)==(b.memory,b.snapshots,b.events)
 if a.snapshots[0][1][8:20]!=c.snapshots[0][1][8:20]:changed.append(offset)
print('guest-only input overlaps with different raw-frame result:',[hex(x) for x in changed])
