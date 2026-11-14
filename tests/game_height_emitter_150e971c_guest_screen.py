"""Private finite guest screen, including all 40 copied descriptor bytes."""
from pathlib import Path
import itertools,json,os,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put

root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve(); out=root/'conker/build/game-height-emitter-150e971c-durable'
syms={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
entry=0x150E971C; actor=0x30000
update=syms['func_151337C0']; frng=syms['func_150ADA68']; irng=syms['func_150ADA20']; emit=syms['func_1513C73C']
truth=list(struct.unpack_from('>91I',(root/'conker/conker.us.bin').read_bytes(),0x116bcc))
plain=bound_blob(*payload(out/'plain.o','func_150E971C'),syms)
padded=bound_blob(*payload(out/'padded.o','func_150E971C'),syms)
snapshot=bound_blob(*payload(out/'snapshot.o','func_150E971C'),syms)
guarded=bound_blob(*payload(out/'guarded.o','func_150E971C'),syms);assert guarded==truth

class Oracle(FactoryOracle):
 def __init__(self,words,memory,mutate):
  self.mutate=mutate;self.seen=[]
  super().__init__(words,memory,Case(),entry=entry,s={},arguments=(actor,))
 def record_call(self,target):
  count={update:1,frng:0,irng:0,emit:14}[target]
  args=tuple(self.arguments(count))
  if target==emit:
   descriptor=bytes(self.memory[args[0]+i] for i in range(40))
   self.seen.append((target,args,descriptor))
  else:self.seen.append((target,args,None))
  self.calls.append((target,args))
 def hook(self,target):
  if target==update and self.mutate&1:put(self.memory,actor+0x3c,bits(-3.0))
  if target==irng and self.mutate&2:
   put(self.memory,actor+0x38,bits(9.0));put(self.memory,actor+0x170,bits(15.0));self.memory[actor+1]=0xa9
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xa5000000+register
  self.f[:20]=[0xa5000000+i for i in range(20)]
  if target==frng:self.f[0]=bits(0.25)
  if target==irng:self.r[2]=0x123456ab

def fixture(height,flags,seed):
 m={STACK+i:(i*17+seed*31+0x41)&255 for i in range(-1024,128)}
 m.update({actor+i:(i*19+seed*13+0x19)&255 for i in range(0x1b0)})
 for off,value in ((0x38,4.0),(0x3c,height),(0x40,6.0),(0x170,10.0)):put(m,actor+off,bits(value))
 put(m,actor+0x174,flags);return m

counts={'cases':0,'plain_differs':0,'padded_differs':0,'snapshot_differs':0,'guarded_differs':0,'emissions':0,'plain_packet_differs':0}
examples={}
for height,flags,seed,mutation in itertools.product((-5.,10.,11.),(10,9,42),(0,1),(0,1,2,3)):
 initial=fixture(height,flags,seed)
 machines=[Oracle(code,initial.copy(),mutation).run() for code in (truth,plain,padded,snapshot,guarded)]
 ref=machines[0]
 def observation(m):
  return (m.r[2],[(t, a if t!=emit else (a[1:],a[0]-STACK), d) for t,a,d in m.seen],
          bytes(m.memory[actor+i] for i in range(0x1b0)))
 want=observation(ref);counts['cases']+=1;counts['emissions']+=any(t==emit for t,_,_ in ref.seen)
 if any(t==emit for t,_,_ in ref.seen):
  original=next((a,d) for t,a,d in ref.seen if t==emit)
  observed=next((a,d) for t,a,d in machines[1].seen if t==emit)
  if original[1]!=observed[1]:counts['plain_packet_differs']+=1
  if not examples:
   examples={'retail_descriptor_offset':original[0][0]-STACK,'plain_descriptor_offset':observed[0][0]-STACK,
             'retail_packet_hex':original[1].hex(),'plain_packet_hex':observed[1].hex()}
 for name,m in zip(('plain','padded','snapshot','guarded'),machines[1:]):
  if observation(m)!=want:
   counts[name+'_differs']+=1
assert counts=={'cases':72,'plain_differs':32,'padded_differs':0,'snapshot_differs':0,'guarded_differs':0,'emissions':32,'plain_packet_differs':32},counts
report={'counts':counts,'examples':examples,'limits':'stubbed helpers; finite float samples; uncredited compiler screen'}
(out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
