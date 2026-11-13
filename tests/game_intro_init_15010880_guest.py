"""Bounded guest model for the intro initializer; helper effects are explicit."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-intro-init-15010880-durable';NAME='func_15010880';ENTRY=0x15010880
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
AUDIO=symbols['func_15177410'];CREATE=symbols['func_15149130'];COPY=symbols['memcpy'];CALLBACK=symbols['func_150DE32C']
BASE=symbols['D_800D3098'];HOOK=symbols['D_800E0934'];GATE=symbols['D_800D2E4C'];INFO=0x320000;OUTPUT=0x330000
@dataclass(frozen=True)
class Case:
 base:int;flag:int;result:int;audio_mutation:int;factory_mutation:int;phase:int=0
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
 for base,n in ((BASE-8,24),(HOOK-8,24),(GATE-8,24),(INFO-16,128),(OUTPUT-16,128)):
  m.update({base+i:(i*29+0x35)&255 for i in range(n)})
 put(m,BASE,c.base);put(m,HOOK,0xaabbccdd);put(m,GATE,INFO);m[INFO+18]=c.flag
 return m
def audio_effect(m,c):
 if c.audio_mutation:
  put(m,BASE,c.base^0x80000001);m[INFO+18]^=0x40
def factory_effect(m,c,home):
 if c.factory_mutation&1:m[INFO+18]^=0x40
 if c.factory_mutation&2:
  # The bounded provider can see and alter the caller's private object.
  m[home-10]^=0x5a;put(m,home-8,0x11223344)
def data(m,p,n):return bytes(m[p+i] for i in range(n))
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase;audio_effect(m,c);put(m,HOOK,CALLBACK)
 base=read(m,BASE);put(m,home-12,0,2);put(m,home-8,(base+0xea0)&0xffffffff);put(m,home-4,(base+0xed4)&0xffffffff)
 calls=[(AUDIO,(16,233,0xfffffe4b,1123,0xfffff341,0x42b40000,15000,0x42100000,77,15,127,127,127,127,127,127)),(CREATE,(300,0xffffffff,94,0xffffffff,0,0,12,255,1))]
 factory_effect(m,c,home)
 if c.result:
  calls.append((COPY,(OUTPUT+40,home-12,12)))
  p=data(m,home-12,12)
  for i,b in enumerate(p):m[OUTPUT+40+i]=b
 if m[read(m,GATE)+18]&0x40:calls.append((CREATE,(5,9,0xffffffff,0xffffffff,1,0,0,255,1)))
 return public(m),calls
class Machine(FactoryOracle):
 def __init__(self,w,m,c):super().__init__(w,m,c,entry=ENTRY,s=symbols,arguments=())
 def record_call(self,t):
  n={AUDIO:16,CREATE:9,COPY:3}[t];args=tuple(self.arguments(n));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  c=self.case;home=STACK+c.phase;args=self.calls[-1][1];value=0xdeadbeef
  if t==AUDIO:audio_effect(self.memory,c)
  elif t==CREATE:
   if args[0]==300:
    factory_effect(self.memory,c,home);value=OUTPUT if c.result else 0
   else:assert args[0]==5;value=0
  else:
   assert t==COPY and args[2]==12
   packet=data(self.memory,args[1],args[2])
   for i,b in enumerate(packet):self.memory[args[0]+i]=b
   value=args[0]
  for i in range({AUDIO:16,CREATE:9,COPY:3}[t]):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def main():
 paths=('retail.o','typed.o','padded.o');programs=[bound_blob(*payload(out/p,NAME),symbols) for p in paths];assert programs[0]==programs[2]
 count=cuts=0
 for base,flag,result,am,fm,phase in itertools.product((0,0x7fffffff,0xfffffff0,0x81234567),(0,0x40),(0,1),(0,1),(0,1,2,3),(0,8)):
  c=Case(base,flag,result,am,fm,phase);initial=fixture(c);expected,calls=reference(initial,c)
  for p in programs:
   m=Machine(p,initial.copy(),c).run();assert public(m.memory)==expected and m.calls==calls,(c,m.calls,calls)
  count+=1
 for c in (Case(0x81234567,0x40,1,1,3),Case(0xfffffff0,0,0,0,0)):
  initial=fixture(c);good=Machine(programs[0],initial.copy(),c).run()
  for cut in range(good.all_accesses):
   models=[]
   for p in (programs[0],programs[2]):
    m=Machine(p,initial.copy(),c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('ineffective cut',cut))
    models.append(m)
   assert complete(models[0])==complete(models[1]) and models[0].trace==models[1].trace,(c,cut)
   cuts+=1
 report={'cases':count,'streams':3,'fault_prefixes':cuts,'independent_state_call_model':True,'helper_behavior_modeled':True,'stack_padding_preserved':True}
 (out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
if __name__=='__main__':main()
