"""Guest differential checks for the linked-owner motion candidate."""
import itertools,math
from dataclasses import dataclass
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_actor_intensity_byte_oracle import Oracle as FloatOracle,float32
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
NAME='func_150D6F0C';ENTRY=0x150d6f0c;HELPER=0x150d6c98;OWNER=0x30000;TARGET=0x40000;DELTA=0x800be9a4
@dataclass(frozen=True)
class Case:
 phase:int;target_word:int;match:int;elapsed:int;alpha:int;decay:int;mutation:int;fcsr:int

def words(obj):
 t,f,r=parse_object(obj);a=f[NAME]['value'];n=f[NAME]['size'];return bound_blob(t[a:a+n],{i-a:v for i,v in r.items()if a<=i<a+n},{'func_150D6C98':HELPER,'D_800BE9A4':DELTA})
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
 for base,n in ((OWNER,512),(TARGET,256)):m.update({base+i:(i*29+0x59)&255 for i in range(n)})
 put(m,OWNER+0xa8,TARGET);m[OWNER+0xac]=0x41;put(m,TARGET,c.target_word);m[TARGET+0x3b]=0x41 if c.match else 0x42
 for offset,value in ((0xb0,c.elapsed),(0xb4,0x40800000),(0xb8,0x40000000),(0xbc,c.alpha),(0xc0,c.decay)):put(m,OWNER+offset,value)
 for offset,value in ((0x14,0x3f800000),(0x18,0x40000000),(0x1c,0x40400000)):put(m,TARGET+offset,value)
 put(m,DELTA,0x3e800000);return m
def public(mem):return {a:b for a,b in mem.items()if not STACK-512<=a<STACK+512}
class Machine(FloatOracle):
 def __init__(self,ws,c,mem):
  self.case=c;self.syms={'func_150D6C98':HELPER,'D_800BE9A4':DELTA};FactoryOracle.__init__(self,ws,mem,c,entry=ENTRY,s=self.syms,arguments=(OWNER,0x12345678));self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=c.fcsr
 def execute(self,w):
  if w>>26==17 and (w>>21&31)==16 and (w&63)==4:
   value=floating(self.f[w>>11&31]);out=math.sqrt(value) if value>=0.0 else math.nan;self.f[w>>6&31]=bits(out);self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  assert t==HELPER;args=tuple(self.arguments(2));assert args==(TARGET,OWNER+0x40),args;self.calls.append((t,args))
 def hook(self,t):
  c=self.case
  for i in range(3):
   value=read(self.memory,TARGET+0x14+4*i)
   if i==1:value=bits(float32(floating(value)+60.0))
   put(self.memory,OWNER+0x40+4*i,value)
  if c.mutation&1:put(self.memory,OWNER+0xb0,0x40800000);put(self.memory,OWNER+0xbc,0x42a00000)
  if c.mutation&2:put(self.memory,OWNER+0xb8,0x3f000000);put(self.memory,OWNER+0xc0,0x3f800000)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)]

def run(state):
    a=words(state['after']);b=words(state['retail']);c=words(state['generated']);assert b==c
    count=0;order_changed=0
    for x in itertools.product((0,8),(0,1),(0,1),(0,0x3f800000,0x40800000,0xbf800000,0x7f800000,0x7fc12345),(0,0x42c80000,0xbf800000),(0,0x3f800000),(0,1,2,3),(0,0xa5a50003)):
     case=Case(*x);initial=fixture(case);machines=[Machine(ws,case,initial.copy()).run()for ws in(a,b,c)];states=[(public(m.memory),m.calls,m.r[2],m.fcsr)for m in machines];assert states[0]==states[1]==states[2],case;assert all(m.fcsr==case.fcsr for m in machines),case
     traces=[[e for e in m.trace if not STACK-512<=e[1]<STACK+512]for m in machines];assert traces[1]==traces[2],case
     if traces[0]!=traces[1]:
      changed=[i for i,(l,r)in enumerate(zip(traces[0],traces[1]))if l!=r];assert len(changed)==2 and changed[1]==changed[0]+1 and traces[0][changed[0]]==traces[1][changed[1]] and traces[0][changed[1]]==traces[1][changed[0]],(case,changed);assert {traces[0][i][1]for i in changed}=={OWNER+0xb0,OWNER+0xc0};order_changed+=1
     count+=1
    return {'cases':count,'bodies':3,'reordered_read_pairs':order_changed,'fcsr':'modeled only'}
