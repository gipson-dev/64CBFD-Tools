"""Independent finite guest model for the uncredited timed-motion candidate."""
from pathlib import Path
import itertools,json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-timed-motion-150f48d0-durable';syms={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
ENTRY=0x150f48d0;TICK=syms['D_800BE9A4'];HELPER=syms['func_1514373C'];NORMAL=0x30000
truth=list(struct.unpack_from('>90I',(root/'conker/conker.us.bin').read_bytes(),0x121d80));candidate=bound_blob(*payload(out/'formatted.o','func_150F48D0'),syms)
guarded=bound_blob(*payload(out/'guarded.o','func_150F48D0'),syms);assert guarded==truth
def f32(value):return floating(bits(value))
def fixture(actor,timer,tick,seed):
 m={STACK+i:(i*17+seed*31+0x41)&255 for i in range(-1024,128)}
 m.update({actor+i:(i*19+seed*13+0x19)&255 for i in range(0x1b0)})
 for offset,value in ((0x170,timer),(0x174,3.0),(0x178,-4.0),(0x17c,5.0),(0x180,1.0),(0x184,.25),(0x188,4.0),(0x18c,6.0),(0x190,2.0),(0x20,10.0),(0x24,11.0),(0x28,12.0),(0x44,.5),(0x48,1.0),(0x4c,1.5),(0x50,2.0),(0x54,2.5),(0x58,3.0)):put(m,actor+offset,bits(value))
 put(m,TICK,bits(tick));return m
def mutate(m,actor):put(m,TICK,bits(.75));put(m,actor+0x184,bits(.5));put(m,actor+0x44,bits(2.0))
def model(initial,actor,mutation,helper_outputs=(2.0,-3.0)):
 m=initial.copy();s=actor+0x170
 def get(p):return floating(read(m,p))
 def putf(p,v):put(m,p,bits(v))
 putf(s,f32(get(s)-get(TICK)))
 if get(s)<=0:return m,0,[]
 calls=[(read(m,s+0x10),read(m,s+0x20))]
 if mutation:mutate(m,actor)
 def update(dst,velocity):putf(dst,f32(get(dst)+f32(get(velocity)*get(TICK))))
 update(s+0x10,s+0x14)
 for i in range(3):update(s+4+i*4,actor+0x44+i*4)
 putf(actor+0x38,f32(get(s+4)+f32(helper_outputs[0]*get(s+0x18))))
 putf(actor+0x3c,f32(get(s+8)+helper_outputs[1]))
 putf(actor+0x40,f32(get(s+0xc)-f32(helper_outputs[0]*get(s+0x1c))))
 for i in range(3):update(actor+0x20+i*4,actor+0x50+i*4)
 return m,s,calls
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+128}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,actor,mutation):
  self.actor=actor;self.mutation=mutation;self.observed=[]
  super().__init__(words,memory,Case(),entry=ENTRY,s={},arguments=(actor,))
 def record_call(self,t):
  assert t==HELPER;args=(self.f[12],self.f[14]);self.observed.append(args);self.calls.append((t,tuple(self.arguments(4))))
 def hook(self,t):
  a=self.calls[-1][1];put(self.memory,a[2],bits(2.0));put(self.memory,a[3],bits(-3.0))
  if self.mutation:mutate(self.memory,self.actor)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=0xdeadbeef
cases=0
for actor,timer,tick,mutation,seed in itertools.product((NORMAL,TICK-0x170,TICK-0x20,TICK-0x44),(0.,1.,12.),(.5,2.),(0,1),(0,1)):
 initial=fixture(actor,timer,tick,seed);want,result,calls=model(initial,actor,mutation)
 for code in (truth,candidate,guarded):
  m=Oracle(code,initial.copy(),actor,mutation).run();assert m.r[2]==result and m.observed==calls,(actor,timer,tick,mutation,m.r[2],result,m.observed,calls)
  assert public(m.memory)==public(want),(hex(actor),timer,tick,mutation)
 cases+=1
controls=((0x46062201,0x46062200),(0xe4900038,0xe490003c),(0xc4860050,0xc4860054))
for old,new in controls:
 altered=list(candidate);assert altered.count(old)==1;altered[altered.index(old)]=new
 detected=False
 for timer,tick in ((1.,2.),(12.,.5)):
  initial=fixture(NORMAL,timer,tick,0);want,result,calls=model(initial,NORMAL,0);m=Oracle(altered,initial,NORMAL,0).run()
  if m.r[2]!=result or m.observed!=calls or public(m.memory)!=public(want):detected=True;break
 assert detected,('ineffective negative control',hex(old))
report={'cases_per_stream':cases,'streams':3,'retail_words':len(truth),'candidate_words':len(candidate),'tick_alias_modes':3,'helper_mutation':True,'effective_negative_controls':len(controls),'finite_values_only':True,'uncredited':True}
(out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
