"""Independent finite model for the uncredited projection candidate."""
from pathlib import Path
import itertools,json,math,os,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-projection-bounds-1510aee0-durable';name='func_1510AEE0';entry=0x1510aee0;MATRIX=0x30000;OUTPUT=0x50000
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
truth=list(struct.unpack_from('>100I',(root/'conker/conker.us.bin').read_bytes(),0x138390));candidate=bound_blob(*payload(out/'candidate-26.o',name),symbols);staged=bound_blob(*payload(out/'staged.o',name),symbols)
def f32(v):return floating(bits(v))
def fixture(x,y,z,which,pattern):
 m={STACK+i:(i*17+0x41)&255 for i in range(-512,512)}
 m.update({MATRIX+i:0 for i in range(64)});m.update({OUTPUT+i:0xa5 for i in range(16)})
 for at in (0,5,10,15):put(m,MATRIX+at*4,bits(1.))
 if pattern:
  for at,value in ((0,1.25),(1,.25),(2,-.125),(4,.5),(5,1.5),(6,.125),(8,-.25),(9,.125),(10,1.),(12,.5),(13,-.25),(14,-1.)):
   put(m,MATRIX+at*4,bits(value))
 output=((OUTPUT,OUTPUT+4),(0,OUTPUT+4),(OUTPUT,0),(OUTPUT,OUTPUT),(MATRIX,MATRIX+4))[which]
 args=(MATRIX,bits(x),bits(y),bits(z),bits(1.),bits(10.),bits(1.),bits(1.),*output)
 return m,args
def model(initial,args):
 m=initial.copy();p,x,y,z,near,far,sx,sy,ox,oy=args;x,y,z,near,far,sx,sy=map(floating,(x,y,z,near,far,sx,sy))
 def transform(i):
  a,b,c,d=(floating(read(m,p+4*j)) for j in (i,i+4,i+8,i+12))
  return f32(d+f32(f32(f32(a*x)+f32(b*y))+f32(c*z)))
 depth=-transform(2)
 if depth<near or far<depth:return 1,m
 horizontal=f32(abs(transform(0))*sx)
 if depth<horizontal:return 1,m
 vertical=f32(abs(transform(1))*sy)
 if depth<vertical:return 1,m
 if ox:put(m,ox,bits(f32(1.-f32(horizontal/depth))))
 if oy:put(m,oy,bits(f32(1.-f32(vertical/depth))))
 return 0,m
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
class Oracle(FactoryOracle):
 def execute(self,word):
  if word>>26==17 and (word>>21)&31==16 and (word&63) in (5,7):
   src=(word>>11)&31;dst=(word>>6)&31
   self.f[dst]=(self.f[src]&0x7fffffff) if (word&63)==5 else (self.f[src]^0x80000000)
  else:super().execute(word)
cases=0;different=[];staged_different=[];corpus=[]
for x,y,z,mode,pattern in itertools.product((0.,2.,6.),(0.,-2.,6.),(-1.,-5.,-10.,1.),range(5),range(2)):
 initial,args=fixture(x,y,z,mode,pattern);result,want=model(initial,args);corpus.append((initial,args,result,want))
 streams=[]
 for code in (truth,candidate,staged):
  m=Oracle(code,initial.copy(),Case(),entry=entry,s={},arguments=args).run()
  streams.append((m.r[2],public(m.memory)))
 assert streams[0]==(result,public(want)),(x,y,z,mode,pattern,'retail')
 if streams[1]!=streams[0]:different.append((x,y,z,mode,pattern))
 if streams[2]!=streams[0]:staged_different.append((x,y,z,mode,pattern))
 cases+=1
controls=((0x4608103c,0x4608103e),(0xc4840028,0xc484002c),(0x46064101,0x46064100))
for before,after in controls:
 changed=list(candidate);assert changed.count(before)==1;changed[changed.index(before)]=after
 caught=False
 for initial,args,result,want in corpus:
  machine=Oracle(changed,initial.copy(),Case(),entry=entry,s={},arguments=args).run()
  if (machine.r[2],public(machine.memory))!=(result,public(want)):caught=True;break
 assert caught,hex(before)
assert cases==360 and not different and not staged_different
report={'cases_per_stream':cases,'candidate_differences':len(different),'staged_differences':len(staged_different),'examples':different[:8], 'finite_only':True,'negative_controls':len(controls),'uncredited':True}
(out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
