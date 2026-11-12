import itertools,math,struct,sys,json
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_rotation_matrix_15187d6c_match as match
root=match.ROOT;p=match.OUT
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY=0x15187D6C;MATRIX=0x30000;FACTOR=0x8008D578
syms={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
SIN=syms['sinf'];COS=syms['cosf'];IDENTITY=syms['func_151EFE00']
def words(o):
 d,f,r=parse_object(o);at=f['func_15187D6C']['value'];n=f['func_15187D6C']['size'];refs={k-at:v for k,v in r.items() if at<=k<at+n};return tuple(bound_blob(d[at:at+n],refs,syms))

@dataclass(frozen=True)
class Case:
 x:int;y:int;z:int;phase:int=0
def fixture():
 m={STACK+i:(i*17+0xa5)&255 for i in range(-2048,512)};m.update({MATRIX+i:(i*29+0x5a)&255 for i in range(-8,72)});put(m,FACTOR,0x3c8efa35);return m
def mul(a,b):return fp(a,b,'mul')
def add(a,b):return fp(a,b,'add')
def sub(a,b):return fp(a,b,'sub')
def neg(a):return a^0x80000000
def expected(c):
 angles=[mul(v,0x3c8efa35) for v in (c.x,c.y,c.z)];sx,sy,sz=[bits(math.sin(floating(v))) for v in angles];cx,cy,cz=[bits(math.cos(floating(v))) for v in angles];a=mul(sx,sy);b=mul(sx,cy)
 out=[bits(1.) if i%5==0 else bits(0.) for i in range(16)]
 for idx,v in ((6,sx),(0,sub(mul(cy,cz),mul(a,sz))),(1,add(mul(cy,sz),mul(a,cz))),(2,mul(neg(sy),cx)),(4,mul(neg(cx),sz)),(5,mul(cx,cz)),(8,add(mul(sy,cz),mul(b,sz))),(9,sub(mul(sy,sz),mul(b,cz))),(10,mul(cx,cy))):out[idx]=v
 calls=[(SIN,angles[0]),(COS,angles[0]),(SIN,angles[1]),(COS,angles[1]),(SIN,angles[2]),(COS,angles[2]),(IDENTITY,MATRIX)];return out,calls
class Guest(FactoryOracle):
 def __init__(self,code,c):
  super().__init__(code,fixture(),c,entry=ENTRY,arguments=(MATRIX,c.x,c.y,c.z));self.saved_f=self.f[20:].copy()
 def execute(self,w):
  op=w>>26;rs=w>>21&31;rt=w>>16&31
  if op in (53,61):
   off=w&65535;addr=(self.r[rs]+(off if off<32768 else off-65536))&0xffffffff
   if op==61:self.put(addr,(self.f[rt+1]<<32)|self.f[rt],8)
   else:v=self.get(addr,8);self.f[rt]=v&0xffffffff;self.f[rt+1]=v>>32
  elif op==17 and rs==16 and w&63==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
  else:super().execute(w)
 def record_call(self,t):self.calls.append((t,self.f[12] if t in (SIN,COS) else self.r[4]))
 def hook(self,t):
  if t==IDENTITY:
   assert self.r[4]==MATRIX
   for i in range(16):put(self.memory,MATRIX+4*i,bits(1.) if i%5==0 else 0)
   answer=0xdeadbeef
  else:answer=bits((math.sin if t==SIN else math.cos)(floating(self.f[12])))
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.f[:20]=[0xa5000000+i for i in range(20)];self.f[0]=answer;self.hi=self.lo=0xa5000010
def run(state):
 one,_=match.pad_both(state)
 raw,retail,padded=state['raw_words'],state['retail_words'],words(one)
 assert padded==retail
 n=0;seen=set()
 for xyz in itertools.product((-90.,-45.,-1.,0.,1.,30.,90.),repeat=3):
  for phase in (0,8):
   c=Case(*[bits(v) for v in xyz],phase);want,calls=expected(c)
   for code in (raw,retail,padded):
    m=Guest(code,c).run();assert [read(m.memory,MATRIX+4*i) for i in range(16)]==want,(c,code is raw);assert m.calls==calls,(c,m.calls,calls);assert m.r[29]==STACK+phase and m.f[20:]==m.saved_f
    if code is retail:seen.update(m.visits)
   n+=1
 assert len(seen)==83,(len(seen),sorted(seen))
 return dict(cases=n,bodies=3,visited_words=len(seen),trig='modeled finite math.sin/cos helper outputs',identity='modeled',phases=[0,8])
