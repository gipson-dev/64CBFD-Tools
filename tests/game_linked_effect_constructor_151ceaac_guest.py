"""Compare the constructor with a packet model and the real position helper."""
from pathlib import Path
import itertools,json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-linked-effect-constructor-151ceaac-durable'
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};rom=(root/'conker/conker.us.bin').read_bytes()
ENTRY=0x151ceaac;HELPER=0x151cec10;RANDOM=symbols['func_150ADA68'];FACTORY=symbols['func_15147A80'];COPY=symbols['memcpy'];CONST=symbols['D_800AB008']
OWNER=0x30000;ATTACH=0x32000;RESULT=0x40000;OUTPUT=0x42000
retail=list(struct.unpack_from('>89I',rom,0x1fbf5c));candidate=bound_blob(*payload(out/'formatted.o','func_151CEAAC'),symbols);assert retail==candidate
helper=list(struct.unpack_from('>17I',rom,0x1fc0c0));connected={HELPER+i*4:w for i,w in enumerate(helper)}
def raw(m,p,n):return bytes(m[p+i] for i in range(n))
def public(m):return {a:v for a,v in m.items() if not STACK-2048<=a<STACK+512}
def fixture(seed):
 m={STACK+i:(i*19+seed*31+0x5b)&255 for i in range(-2048,512)}
 for base,n in ((OWNER,128),(ATTACH,128),(RESULT,0xb0),(OUTPUT,96),(CONST,4)):
  m.update({base+i:(i*29+seed*13+0x31)&255 for i in range(n)})
 m[OWNER+0x3b]=0x87
 for i,v in enumerate((1.25,-2.5,3.75)):put(m,OWNER+0x14+i*4,bits(v))
 for i,v in enumerate((-4.25,5.5,-6.75)):put(m,ATTACH+0x40+i*4,bits(v))
 put(m,CONST,bits(2.));put(m,RESULT+0x98,OUTPUT)
 return m
def f32(x):return floating(bits(x))
def mutate(m):
 m[OWNER+0x3b]=0x22;put(m,OWNER+0x14,bits(8.5));put(m,ATTACH+0x40,bits(9.25));put(m,CONST,bits(3.))
def reference(initial,owner,attachment,mode,success,mutation,home=STACK):
 m=initial.copy();identity=m[owner+0x3b] if owner else 0;initial_stack=initial.copy()
 if mutation:mutate(m)
 vec=raw(m,(attachment+0x40) if attachment else (owner+0x14),12)
 extent=bits(f32(f32(.25*400.)+400.));velocity=bits(f32(f32(.5+.5)*floating(read(m,CONST))))
 payload=struct.pack('>I',owner)+bytes([identity])+raw(initial_stack,home-63,3)+struct.pack('>I',attachment)
 payload+=struct.pack('>4f',0.,1.,0.,1.)+bytes([2 if mode&255 else 0])+raw(initial_stack,home-39,3)+struct.pack('>II',extent,velocity)
 request=vec+struct.pack('>HHI',300,16,17)+bytes([3,25])+raw(initial_stack,home-6,6)
 assert len(payload)==40 and len(request)==28
 if success:
  for i,b in enumerate(payload):m[OUTPUT+i]=b
 return m,payload,request
class Oracle(FactoryOracle):
 def __init__(self,words,memory,owner,attachment,mode,channel,context,success,mutation):
  self.success,self.mutation=success,mutation;self.random_count=0;self.observed=[]
  super().__init__(words,memory,Case(),entry=ENTRY,s={},arguments=(owner,attachment,mode,channel,context),connected=connected)
 def record_call(self,t):
  n={RANDOM:0,HELPER:3,FACTORY:11,COPY:3}.get(t);assert n is not None,hex(t)
  args=tuple(self.arguments(n));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==FACTORY:self.observed.append(('request',raw(self.memory,args[0],28)))
  if t==COPY:self.observed.append(('payload',raw(self.memory,args[1],args[2])))
 def hook(self,t):
  args=self.calls[-1][1]
  if t==RANDOM:
   self.random_count+=1
   if self.mutation and self.random_count==1:mutate(self.memory)
   value=0;fresult=bits(.25 if self.random_count==1 else .5)
  elif t==FACTORY:value=RESULT if self.success else 0;fresult=None
  else:
   assert t==COPY and args[2]==40;block=raw(self.memory,args[1],args[2])
   for i,b in enumerate(block):self.memory[args[0]+i]=b
   value=args[0];fresult=None
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010;self.r[2]=value
  if fresult is not None:self.f[0]=fresult
cases=0
for (owner,attachment),mode,success,mutation,seed in itertools.product(((OWNER,0),(0,ATTACH),(OWNER,ATTACH)),(0,1,0x100,0x1ff),(0,1),(0,1),(0,1)):
 initial=fixture(seed);want,expected_payload,expected_request=reference(initial,owner,attachment,mode,success,mutation)
 for code in (retail,candidate):
  m=Oracle(code,initial.copy(),owner,attachment,mode,0x123400ab,0x87654321,success,mutation).run()
  assert m.r[2]==(RESULT if success else 0) and m.random_count==2
  assert m.observed[0]==('request',expected_request),(m.observed[0],expected_request)
  factory=[a for t,a in m.calls if t==FACTORY];assert len(factory)==1 and factory[0][1:]==(40,40,0,15,15,0,0,0,0xab,0x87654321),factory
  if success:assert m.observed[1]==('payload',expected_payload)
  assert public(m.memory)==public(want)
 cases+=1
for code in (retail,candidate):
 m=Oracle(code,fixture(0),0,0,0,0,0,0,0)
 try:m.run()
 except AssertionError as ex:
  assert ex.args==(('unmapped read',20,4),),ex
  assert all(t!=FACTORY for t,_ in m.calls)
 else:raise AssertionError('Null owner and attachment should fault in real helper')
report={'cases':cases,'streams':2,'real_position_helper':True,'null_helper_fault':True,'untouched_request_and_payload_bytes':True,'uncredited':True}
(out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
