"""Screen retail and compiled factory against an independent packet model."""
from pathlib import Path
import itertools,json,math,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-effect-config-1519c09c-durable'
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
rom=(root/'conker/conker.us.bin').read_bytes();ENTRY=0x1519c09c;FACTORY=symbols['func_151602C0'];COPY=symbols['memcpy']
CONST=symbols['D_800A8AF8'];POS=0x30000;RESULT=0x50000;OWNER=0x60000
retail=list(struct.unpack_from('>89I',rom,0x1c954c));candidate=bound_blob(*payload(out/'formatted.o','func_1519C09C'),symbols)
u32=lambda x:x&0xffffffff
def data(m,p,n):return bytes(m[p+i] for i in range(n))
def public(m):return {a:v for a,v in m.items() if not STACK-2048<=a<STACK+512}
def fixture(values,constant,overlap,seed):
 m={STACK+i:(i*17+seed*11+0x5a)&255 for i in range(-2048,512)}
 for base,n in ((POS-16,80),(RESULT-16,160),(OWNER-16,64),(CONST-8,20)):
  m.update({base+i:(i*29+seed*13+0x37)&255 for i in range(n)})
 position=RESULT+0x18 if overlap else POS
 for i,v in enumerate(values):put(m,position+4*i,bits(v))
 put(m,CONST,constant)
 return m,position
def reference(initial,position,params,outcome,mutation):
 m=initial.copy();coords=tuple(u32(math.trunc(floating(read(m,position+4*i)))) for i in range(3));constant=read(m,CONST)
 config=struct.pack('>6fI f',35.,5.,110.,1.,0.,7.,constant,127.)
 if mutation:
  put(m,position,0x42f60000);put(m,CONST,0xbf000000)
 if outcome:
  for i,b in enumerate(config):m[RESULT+0x18+i]=b
  put(m,RESULT+0x38,OWNER)
 return m,coords,config
class Oracle(FactoryOracle):
 def __init__(self,words,memory,position,params,outcome,mutation):
  self.position,self.params,self.outcome,self.mutation=position,params,outcome,mutation;self.observed=[]
  args=(OWNER,position,*params)
  super().__init__(words,memory,Case(),entry=ENTRY,s={},arguments=args)
 def execute(self,w):
  if w>>26==17 and (w>>21&31)==16 and (w&63)==13:
   fs=w>>11&31;fd=w>>6&31;v=floating(self.f[fs]);assert math.isfinite(v) and -2147483648.<=v<2147483648.
   self.f[fd]=u32(math.trunc(v));return
  super().execute(w)
 def record_call(self,t):
  n=11 if t==FACTORY else 3 if t==COPY else 0;assert n,hex(t)
  a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==FACTORY:self.observed.append((data(self.memory,a[0],6),tuple(read(self.memory,a[1]+i*4) for i in range(3))))
  else:self.observed.append(data(self.memory,a[1],a[2]))
 def hook(self,t):
  args=self.calls[-1][1]
  if t==FACTORY:
   if self.mutation:
    put(self.memory,self.position,0x42f60000);put(self.memory,CONST,0xbf000000)
    put(self.memory,args[1],0xdeadbeef)
   value=RESULT if self.outcome else 0
  else:
   block=data(self.memory,args[1],args[2])
   for i,b in enumerate(block):self.memory[args[0]+i]=b
   value=args[0]
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010;self.r[2]=u32(value)
cases=0
valueset=((0.,-0.,1.75),(-10.75,42.9,-1.25),(123456.,-654321.,32767.75))
for values,constant,outcome,mutation,overlap,seed in itertools.product(valueset,(bits(0.),bits(-.75)),(0,1),(0,1),(0,1),(0,1)):
 initial,position=fixture(values,constant,overlap,seed);params=(0x12340011,0x87650022,0xdead0033,0xbeef0044,0xcafe0055,0x34567890)
 expected,coords,config=reference(initial,position,params,outcome,mutation)
 for code in (retail,candidate):
  m=Oracle(code,initial.copy(),position,params,outcome,mutation).run();head,seen=m.observed[0]
  assert head[:5]==bytes([2,2,1,44,34]) and head[5]==initial[STACK-7],(head,initial[STACK-7])
  assert seen==coords and m.r[2]==(RESULT if outcome else 0)
  args=m.calls[0][1];assert args[2:]==(0x11,0x22,0x33,0x44,255,0,36,0x55,0x34567890),args
  assert len(m.calls)==(3 if outcome else 1)
  if outcome:assert m.observed[1:]==[config,struct.pack('>I',OWNER)]
  if public(m.memory)!=public(expected):
   diffs=[(hex(a),expected.get(a),m.memory.get(a)) for a in set(expected)|set(m.memory) if not STACK-2048<=a<STACK+512 and expected.get(a)!=m.memory.get(a)]
   raise ValueError((values,outcome,mutation,overlap,seed,diffs[:10]))
 cases+=1
report={'cases':cases,'streams':2,'header_padding_preserved':True,'overlap_and_mutation':True,'uncredited':True}
(out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
