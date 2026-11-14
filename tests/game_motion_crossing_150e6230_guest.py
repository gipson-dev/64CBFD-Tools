"""Private independent modeled-helper screen for motion crossing."""
from pathlib import Path
import itertools,json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-motion-crossing-150e6230-durable';entry=0x150e6230;actor=0x30000;callback=0x15003450
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};dot=symbols['func_15144A74'];table=symbols['D_80088A10'];tick=symbols['D_800BE9A4']
truth=list(struct.unpack_from('>92I',(root/'conker/conker.us.bin').read_bytes(),0x1136e0));candidate=bound_blob(*payload(out/'formatted.o','func_150E6230'),symbols);guarded=bound_blob(*payload(out/'guarded.o','func_150E6230'),symbols);assert guarded==truth
def f32(x):return floating(bits(x))
def fixture(enabled,sign,selector,seed):
 m={STACK+i:(i*17+seed*31+0x41)&255 for i in range(-1024,128)}
 m.update({actor+i:(i*19+seed*13+0x19)&255 for i in range(0x180)});m[actor+0x110]=enabled;m[actor+0x13c]=selector&255
 for off,value in ((0x34,2.),(0x38,-3.),(0x3c,4.),(0x40,.5),(0x44,-1.),(0x48,2.),(0x50,3.),(0x114,5.),(0x118,7.),(0x11c,-2.),(0x138,sign)):
  put(m,actor+off,bits(value))
 put(m,tick,bits(.5));put(m,table,callback);return m
def mutate_dot(m):put(m,actor+0x138,bits(1.));put(m,actor+0x40,bits(1.5));put(m,tick,bits(.75))
def mutate_callback(m):put(m,actor+0x50,bits(2.));put(m,actor+0x38,bits(9.));put(m,tick,bits(1.25))
def model(initial,dotvalue,mutation,cbret):
 m=initial.copy();state=actor+0x110;calls=[];result=1
 if m[state]&1:
  delta=tuple(bits(f32(floating(read(m,state+4+4*i))-floating(read(m,actor+0x34+4*i)))) for i in range(3))
  statevec=tuple(read(m,state+4+4*i) for i in range(3));calls.append((dot,delta,statevec))
  if mutation&1:mutate_dot(m)
  sign=-1. if dotvalue<0. else 1.
  if sign!=floating(read(m,state+0x28)):
   result=0;selector=m[state+0x2c]
   if selector!=255:
    assert selector==0;calls.append((callback,(actor,),None))
    if mutation&2:mutate_callback(m)
    value=cbret&255;result=value-256 if value&128 else value
 speed=floating(read(m,actor+0x50))
 velocity=[f32(floating(read(m,actor+0x40+i*4))*speed) for i in range(3)]
 for i in range(3):
  position=actor+0x34+i*4;put(m,position,bits(f32(floating(read(m,position))+f32(velocity[i]*floating(read(m,tick))))))
 return result&0xffffffff,calls,m
class Oracle(FactoryOracle):
 def __init__(self,code,memory,dotvalue,mutation,cbret):
  self.dotvalue=dotvalue;self.mutation=mutation;self.cbret=cbret;self.observed=[]
  super().__init__(code,memory,Case(),entry=entry,s={},arguments=(actor,))
 def record_call(self,target):
  if target==dot:
   a=tuple(self.arguments(2));self.observed.append((dot,tuple(read(self.memory,a[0]+4*i) for i in range(3)),tuple(read(self.memory,a[1]+4*i) for i in range(3))))
  else:
   assert target==callback;self.observed.append((callback,tuple(self.arguments(1)),None))
  self.calls.append((target,()))
 def hook(self,target):
  if target==dot and self.mutation&1:mutate_dot(self.memory)
  if target==callback and self.mutation&2:mutate_callback(self.memory)
  for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)]
  if target==dot:self.f[0]=bits(self.dotvalue)
  if target==callback:self.r[2]=self.cbret
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+128}

def main():
 cases=0;differences=[]
 for enabled,dotvalue,sign,selector,mutation,cbret in itertools.product((0,1),(-1.,0.,1.,float('nan')),(-1.,1.,float('nan')),(-1,0),range(4),(0x100,0x1fe)):
  initial=fixture(enabled,sign,selector,cases&1);result,calls,want=model(initial,dotvalue,mutation,cbret)
  for label,code in (('retail',truth),('candidate',candidate),('guarded',guarded)):
   m=Oracle(code,initial.copy(),dotvalue,mutation,cbret).run();observed=(m.r[2],m.observed,public(m.memory));expected=(result,calls,public(want))
   if label=='retail':assert observed==expected,(enabled,dotvalue,sign,selector,mutation,cbret,observed[:2],expected[:2])
   elif observed!=expected:differences.append((enabled,str(dotvalue),str(sign),selector,mutation,cbret))
  cases+=1
 controls=((0x460a003c,0x460a003e),(0x00074603,0x00074602),(0x46009082,0x46009080))
 for before,after in controls:
  altered=list(candidate);assert altered.count(before)==1;altered[altered.index(before)]=after;caught=False
  for enabled,dotvalue,sign,selector,mutation in itertools.product((0,1),(-1.,0.,1.),(-1.,1.),(-1,0),(0,1,2)):
   initial=fixture(enabled,sign,selector,0);result,calls,want=model(initial,dotvalue,mutation,0x1fe)
   m=Oracle(altered,initial.copy(),dotvalue,mutation,0x1fe).run()
   if (m.r[2],m.observed,public(m.memory))!=(result,calls,public(want)):caught=True;break
  assert caught,hex(before)
 assert cases==384 and not differences
 report={'cases_per_stream':cases,'candidate_differences':len(differences),'examples':differences[:8],'negative_controls':len(controls),'modeled_helpers':True,'fcsr_not_modeled':True,'uncredited':True}
 (out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=='__main__':main()
