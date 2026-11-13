"""Guest differential checks for the linked-owner velocity candidate."""
import itertools
from dataclasses import dataclass
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_actor_intensity_byte_oracle import Oracle as FloatOracle,float32
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
NAME='func_150D6CC4';ENTRY=0x150d6cc4;COPY=0x150d6c98;SCALE=0x15131958;OWNER=0x30000;TARGET=0x40000;DT=0x800be9a4;ACCEL=0x800be9a8;COUNT=0x800be9e4
@dataclass(frozen=True)
class Case:
 phase:int;target_word:int;identity:int;factor:int;count:int;dt:int;mutation:int;vector:int

def words(obj):
 t,f,r=parse_object(obj);a=f[NAME]['value'];n=f[NAME]['size'];return bound_blob(t[a:a+n],{i-a:v for i,v in r.items()if a<=i<a+n},{'func_150D6C98':COPY,'func_15131958':SCALE,'D_800BE9A4':DT,'D_800BE9A8':ACCEL})
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
 for base,n in ((OWNER,512),(TARGET,256)):m.update({base+i:(i*29+0x59)&255 for i in range(n)})
 put(m,OWNER+0xa8,TARGET);m[OWNER+0xac]=0x41;put(m,TARGET,c.target_word);m[TARGET+0x3b]=0x41 if c.identity else 0x42;put(m,OWNER+0xb0,c.factor)
 for offset,value in ((0x14,0x3f800000),(0x18,0x40000000),(0x1c,0x40400000)):put(m,TARGET+offset,value)
 values=((0x3f800000,0x40000000,0x40400000),(0xbf800000,0x3f000000,0x40800000),(0x7fc12345,0x3f000000,0x40800000),(0x7f800000,0x3f000000,0x40800000))[c.vector]
 for i,v in enumerate(values):put(m,OWNER+0x58+4*i,v)
 for offset,value in ((0x4c,0x41200000),(0x50,0x41a00000),(0x54,0x41f00000),(0x64,0x40000000)):put(m,OWNER+offset,value)
 put(m,DT,c.dt);put(m,ACCEL,0x3f000000);put(m,COUNT,c.count);return m
def public(mem):return {a:b for a,b in mem.items()if not STACK-512<=a<STACK+512}
class Machine(FloatOracle):
 def __init__(self,ws,c,mem):
  self.case=c;self.syms={'func_150D6C98':COPY,'func_15131958':SCALE,'D_800BE9A4':DT,'D_800BE9A8':ACCEL};FactoryOracle.__init__(self,ws,mem,c,entry=ENTRY,s=self.syms,arguments=(OWNER,0x12345678));self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=0
 def record_call(self,t):
  assert t in(COPY,SCALE);args=tuple(self.arguments(2));assert args[0]==(TARGET if t==COPY else OWNER+0x58),args
  if t==COPY:assert args[1]==OWNER+0x40,args
  else:assert args[1]==read(self.memory,OWNER+0xb0),args
  self.calls.append((t,args))
 def hook(self,t):
  c=self.case
  if t==COPY:
   for i in range(3):
    value=read(self.memory,TARGET+0x14+4*i)
    if i==1:value=bits(float32(floating(value)+60.0))
    put(self.memory,OWNER+0x40+4*i,value)
   if c.mutation&1:put(self.memory,OWNER+0xb0,0x3f000000);put(self.memory,OWNER+0x58,0x40400000);put(self.memory,DT,0x3f000000)
  else:
   factor=floating(self.r[5]);count=read(self.memory,COUNT);assert 0<=count<=2
   for _ in range(count):
    values=[bits(float32(floating(read(self.memory,OWNER+0x58+4*i))*factor))for i in range(3)]
    for i,v in enumerate(values):put(self.memory,OWNER+0x58+4*i,v)
   if c.mutation&2:put(self.memory,DT,0x3f800000);put(self.memory,ACCEL,0x3f800000);put(self.memory,OWNER+0x4c,0x42480000)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)]
def run(state):
    a,b,c=[words(state[x])for x in ('after','retail','generated')];assert b==c;count=0
    for args in itertools.product((0,8),(0,1),(0,1),(0x3f000000,0x3fa00000),(0,1,2),(0x3e800000,0xbe800000),(0,1,2,3),(0,1,2,3)):
     case=Case(*args);initial=fixture(case);machines=[Machine(ws,case,initial.copy()).run()for ws in(a,b,c)];states=[(public(m.memory),m.calls,m.r[2],m.fcsr,[e for e in m.trace if not STACK-512<=e[1]<STACK+512])for m in machines];assert states[0]==states[1]==states[2],case;count+=1
    return {'cases':count,'bodies':3,'accesses':'full public read/write traces','helper_mutations':True}
