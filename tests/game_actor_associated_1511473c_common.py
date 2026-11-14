"""Bounded actor update oracle; FCSR behavior is explicitly modeled."""
from pathlib import Path
from dataclasses import dataclass
import itertools,math,struct,json,os
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-associated-update-1511473c-screen';conker=root/'conker';entry=0x1511473c
symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};sym=lambda k:symbols[k]
programs={'retail':list(struct.unpack_from('>91I',(conker/'conker.us.bin').read_bytes(),0x141bec)),'raw':bound_blob(*payload(Path(os.environ.get('ACTOR_ASSOC_RAW',out/'selected.o')),'func_1511473C'),symbols),'guarded':bound_blob(*payload(Path(os.environ.get('ACTOR_ASSOC_GUARDED',out/'guarded.o')),'func_1511473C'),symbols)};assert programs['retail']==programs['guarded']
actor=sym('D_800CC2D0')+0x32c*2;record=0x30000;helper=sym('func_15114348')
class Oracle(FactoryOracle):
 def __init__(self,words,memory,args,mode=0):
  super().__init__(words,memory,Case(),entry=entry,s={},arguments=args);self.fcsr=0;self.mode=mode
 def execute(self,w):
  op=w>>26;rs=(w>>21)&31;rt=(w>>16)&31;rd=(w>>11)&31;fd=(w>>6)&31;fn=w&63
  if op==17 and rs==2:self.r[rt]=self.fcsr;return
  if op==17 and rs==6:self.fcsr=self.r[rt];return
  if op==17 and rs==20 and fn==32:self.f[fd]=bits(float(signed(self.f[rd])));return
  if op==17 and rs==16 and fn==36:
   value=floating(self.f[rd]);valid=math.isfinite(value) and -2147483648<=value<2147483648
   self.f[fd]=math.trunc(value)&0xffffffff if valid else 0x80000000
   if not valid:self.fcsr|=0x40
   return
  return super().execute(w)
 def record_call(self,t):
  assert t==helper,hex(t);args=tuple(self.arguments(4));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  assert t==helper
  if self.mode & 1:put(self.memory,actor+0x76,1234,2)
  if self.mode & 2:put(self.memory,sym('D_800A2F60'),bits(2.0))
  if self.mode & 4:put(self.memory,sym('D_800DBEF4'),record+0x140)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def fixture(index,count,value,scale,increment,flag,match,mode):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-256,128)};m.update({actor+i:(i*13+5)&255 for i in range(0x32c)});m.update({record+i:(i*11+7)&255 for i in range(0x400)})
 for n in ('D_800DBEF0','D_800DBEF4','D_800A2F60'):m.update({sym(n)+i:0 for i in range(4)})
 m.update({sym('D_800CBDA0')+i:0 for i in range(16)})
 put(m,sym('D_800DBEF0'),count&0xffffffff);put(m,sym('D_800DBEF4'),record+0xa0);put(m,sym('D_800A2F60'),bits(scale));put(m,record+0xa0+index*0xa0+0x64,bits(increment));put(m,actor+0x76,value,2);m[actor+0x137]=flag;put(m,sym('D_800CBDA0')+4,index+1 if match else index+2,2)
 return m

def public(m):return {a:v for a,v in m.items() if not STACK-256<=a<STACK+128}
def model(m,index,count,mode,has_actor):
 m=m.copy()
 if has_actor and index<count:
  if mode:put(m,actor+0x76,1234,2)
  val=read(m,actor+0x76,2);x=floating(read(m,record+0xa0+index*0xa0+0x64));scale=floating(read(m,sym('D_800A2F60')));result=floating(bits(float(val)+floating(bits(x*scale))))
  value=math.trunc(result) if -1<result<4294967296 else 0xffffffff
  put(m,actor+0x76,value,2)
  if m[actor+0x137] and read(m,sym('D_800CBDA0')+4,2)==index+1:put(m,actor+0x7a,value,2)
 return public(m)
