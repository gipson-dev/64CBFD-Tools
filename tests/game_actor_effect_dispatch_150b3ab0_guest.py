"""Private bounded guest comparison against an independent helper-call model."""
from pathlib import Path
import itertools, json, struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle, Case
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read

root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-effect-dispatch-150b3ab0-durable'
symbols={r[1]:r[2][1] for r in symbol_rows((out/'frozen/conker/build/conker.us.elf').read_bytes())}
ENTRY=0x150b3ab0; ACTOR=0x30000; FRAME=0x32000; SECOND=0x34000; BASE=0x50000
TARGETS=[symbols[n] for n in ('func_1512D748','func_15143134','func_150ADA20','func_1514C858','func_151D8868','func_151D3FF4')]
G_INDEX=symbols['D_800BE9E8'];G_BASE=symbols['D_800DBFF0'];CONST=symbols['D_8009FBC0']
truth=list(struct.unpack_from('>87I',(root/'conker/conker.us.bin').read_bytes(),0xe0f60))
candidate=bound_blob(*payload(out/'candidate-12.o','func_150B3AB0'),symbols);assert truth==candidate
def raw(m,p,n):return bytes(m[p+i] for i in range(n))
def fixture(seed,frame):
 m={STACK+i:(i*13+seed*37+0x59)&255 for i in range(-1024,128)}
 for base,n in ((ACTOR,0x200),(FRAME,0x700),(SECOND,0x700),(BASE,0x2000),(CONST,12),(G_INDEX,4),(G_BASE,4)):
  m.update({base+i:(i*31+seed*11+7)&255 for i in range(n)})
 put(m,ACTOR+0x1d4,frame);put(m,ACTOR+0x7a,0xff80,2);put(m,G_INDEX,2);put(m,G_BASE,BASE)
 return m
class Oracle(FactoryOracle):
 def __init__(self,words,memory,actor,slot,mutation,randoms):
  self.mutation=mutation;self.randoms=randoms;self.rand=0;self.records=[];self.home=STACK
  super().__init__(words,memory,Case(),entry=ENTRY,s={},arguments=(actor,slot))
 def record_call(self,t):
  count={TARGETS[0]:3,TARGETS[1]:3,TARGETS[2]:0,TARGETS[3]:13,TARGETS[4]:4,TARGETS[5]:3}[t]
  args=list(self.arguments(count))
  if t==TARGETS[3]:args[:2]=self.f[12],self.f[14]
  args=tuple(args);extra=None
  if t==TARGETS[4]:extra=raw(self.memory,args[0],8)
  if t==TARGETS[5]:extra=raw(self.memory,args[0],16)
  self.calls.append((t,args));self.events.append(('CALL',t,args));self.records.append((t,args,extra))
 def hook(self,t):
  args=self.calls[-1][1];value=0xdeadbeef
  if t==TARGETS[0] and self.mutation:
   put(self.memory,ACTOR+0x1d4,SECOND);put(self.memory,ACTOR+0x7a,0x0180,2);self.memory[self.home+7]=0x6d
  if t==TARGETS[1]:
   for i,v in enumerate((1.25,-2.5,3.75)):put(self.memory,args[1]+4*i,bits(v))
  if t==TARGETS[2]:value=self.randoms[self.rand];self.rand+=1
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010;self.r[2]=value

def expected(initial,active,slot,mutation,randoms,home=STACK):
 if not active:return []
 home_slot=0x6d if mutation else slot&255;frame=SECOND if mutation else FRAME;angle=0x41 if mutation else 0x13f
 position=home-16;packet=home-24
 pkt=bytes([1,initial[packet+1]])+struct.pack('>H',(randoms[1]&15)+12)+bytes([(randoms[2]&3)+5,1,255,initial[packet+7]])
 pos=struct.pack('>3I',bits(1.25),bits(-2.5),bits(3.75))+raw(initial,position+12,2)+struct.pack('>H',angle)
 return [(TARGETS[0],(BASE+2*0x9a0,6,1),None),
         (TARGETS[1],(CONST,position,frame+0x640),None),
         (TARGETS[2],(),None),
         (TARGETS[3],(bits(1.25),bits(-2.5),bits(3.75),bits(10.),angle,0,255,randoms[0]%31+40,8,0,0,0,home_slot),None),
         (TARGETS[2],(),None),(TARGETS[2],(),None),
         (TARGETS[4],(packet,0,home_slot,0),pkt),(TARGETS[5],(position,home_slot,0),pos)]
count=0
for active,slot,mutation,seed,randoms in itertools.product((0,1,2),(0x12340000,0x123400ff),(0,1),(0,1),((0,0,0),(0xffffffff,0xffffffff,0xffffffff),(31,15,3))):
 actor=0 if active==0 else ACTOR;frame=FRAME if active==2 else 0
 initial=fixture(seed,frame);want=expected(initial,active==2,slot,mutation,randoms)
 for code in (truth,candidate):
  m=Oracle(code,initial.copy(),actor,slot,mutation,randoms).run()
  assert m.records==want,(active,slot,mutation,seed,randoms,m.records,want)
  assert m.rand==(3 if active==2 else 0)
 count+=1
report={'cases_per_stream':count,'streams':2,'full_helper_call_arguments':True,'slot_home_mutation':True,'packet_and_position_padding':True,'uncredited':True}
(out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
