"""Bounded retail-versus-C guest screen, with a stubbed and mutating cosf."""
from pathlib import Path
import itertools,json,os,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read

root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/'conker/build/game-matrix-phase-150f1a00-durable'
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
rom=(root/'conker/conker.us.bin').read_bytes()
retail=list(struct.unpack_from('>82I',rom,0x11eeb0))
def candidate_words(path):return bound_blob(*payload(path,'func_150F1A00'),symbols)
ACTOR=0x20000; M1=0x30000; M2=0x32000; STATE=0x800cc298; RATES=0x80088b00
E8=0x800a18e8;EC=0x800a18ec;F0=0x800a18f0;TICKS=0x800be9e4;COS=symbols['cosf']
f32=lambda f:floating(bits(f))
s16=lambda n:((n&0xffff)^0x8000)-0x8000

class Oracle(TimingOracle):
 def __init__(self,words,memory,cosval,mutation):
  super().__init__(words,memory,entry=0x150f1a00,arguments=(ACTOR,))
  self.cosval=cosval;self.mutation=mutation
 def record_call(self,target):
  assert target==COS,hex(target)
  self.calls.append((target,self.f[12]))
 def hook(self,target):
  assert target==COS
  if self.mutation:put(self.memory,ACTOR+0x1d4,M2)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)]
  self.f[0]=bits(self.cosval)

def fixture(flags,phase,tick):
 m={STACK+i:0xa5 for i in range(-256,256)}
 for base,n in ((ACTOR,0x330),(M1+0xf80,0x40),(M2+0xf80,0x40),(STATE,0x20),(RATES,8)):
  m.update({base+i:(i*29+17)&255 for i in range(n)})
 for at,val in ((ACTOR+0x2e4,flags),(ACTOR+0x1d4,M1),(TICKS,tick),(E8,bits(.125)),(EC,bits(2.0)),(F0,bits(.5))):put(m,at,val)
 for i,v in enumerate((3,19,0xfffe)):put(m,RATES+i*2,v,2)
 put(m,STATE+20,phase,2)
 for base in (M1,M2):
  for i in range(16):put(m,base+0xf80+i*4,bits((i-7)*.25))
 return m

def expected(initial,flags,phase,tick,cosval,mutation):
 m=initial.copy();index=2 if flags&12==12 else 1 if flags&3==3 else 0
 phase=s16(phase+read(m,RATES+2*index,2)*tick);put(m,STATE+20,phase,2)
 argument=bits(f32(f32(float(phase))*floating(read(m,E8))))
 if mutation:put(m,ACTOR+0x1d4,M2)
 scale=f32(f32(f32(f32(cosval+1.0)*.5)*floating(read(m,EC)))+floating(read(m,F0)))
 base=read(m,ACTOR+0x1d4)+0xf80
 for row in range(3):
  for col in range(3):
   address=base+(row*4+col)*4;put(m,address,bits(f32(floating(read(m,address))*scale)))
 return m,argument

def public(m):return {a:v for a,v in m.items() if not STACK-256<=a<STACK+256}
def verify(code):
 cases=0
 for flags,phase,tick,cosval,mutation in itertools.product((0,3,12,15,7),(-32768,-1,0,32767),(0,1,0x7fffffff,0xffffffff),(-1.0,0.0,1.0),(0,1)):
  initial=fixture(flags,phase,tick);want,arg=expected(initial,flags,phase,tick,cosval,mutation)
  machine=Oracle(code,initial.copy(),cosval,mutation).run()
  if public(machine.memory)!=public(want) or machine.calls!=[(COS,arg)]:
   diffs=[(hex(a),want.get(a),machine.memory.get(a)) for a in set(want)|set(machine.memory) if not STACK-256<=a<STACK+256 and want.get(a)!=machine.memory.get(a)]
   raise ValueError((flags,phase,tick,cosval,mutation,machine.calls,hex(arg),diffs[:10]))
  cases+=1
 return cases
