from pathlib import Path
from importlib.machinery import SourceFileLoader
import itertools,struct
from tools.tests import game_state_trajectory_15072f10_oracle as G
from tools.tests import game_state_trajectory_15072f10_reference as R
SIN=0x150ad78c;COS=0x150ad780;PITCHSCALE=0x800994b8;YAWSCALE=0x800994bc
class Connected(G.Machine):
 def __init__(self,ws,c,m,code):self.ntrig=0;super().__init__(ws,c,m);self.code.update(code)
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==7:self.f[(w>>6)&31]=self.f[(w>>11)&31]^0x80000000
  else:super().execute(w)
 def record_call(self,t):
  if t in (SIN,COS):self.calls.append((t,(self.f[12],)))
  else:super().record_call(t)
 def hook(self,t):
  if t not in (SIN,COS):return super().hook(t)
  n=self.ntrig;self.ntrig+=1;assert t==(SIN,COS,COS,SIN)[n];value=(.125,.75,-.5,.25)[n]
  if n==0:
   if self.c.mutation&1:G.put(self.memory,G.CURRENT,G.ACTOR2)
   if self.c.mutation&2:G.put(self.memory,G.SCALE,G.bits(-.5))
   if self.c.mutation&4:self.memory[G.PLAYER]=0x6c
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.f[0]=G.bits(value)
def run():
 rom=(G.root/'conker/conker.us.bin').read_bytes();off=0x2d4b0+G.VECTOR-0x15000000;code=dict(zip(range(G.VECTOR,G.VECTOR+51*4,4),struct.unpack_from('>51I',rom,off)));programs=G.programs();count=0;visited=set()
 for pitch,angle,mutation,phase in itertools.product((-128,-1,0,1,127),(0,0xffff),range(8),(0,8)):
  c=G.Case(phase=phase,pitch=pitch,timer=8,angle=angle,offset=-123,mutation=mutation);initial=G.fixture(c);G.put(initial,PITCHSCALE,G.bits(.25));G.put(initial,YAWSCALE,G.bits(1/65536));states=[]
  for w in programs:
   m=Connected(w,c,initial.copy(),code).run();states.append((G.public(m.memory,c),m.calls,m.r[2]));visited.update(m.visits&set(code))
  assert states.count(states[0])==4,c
  public,calls,result=states[0];assert result==0xdeadbeef;assert [t for t,a in calls]==[G.VECTOR,SIN,COS,COS,SIN,G.SUBMIT]
  a=calls[0][1];scaled=G.bits(R.f32(G.floating(a[2])*.25));yaw=G.bits(R.f32(float(a[0])/65536));assert [v[1][0] for v in calls[1:5]]==[scaled,scaled,yaw,yaw]
  actor=G.ACTOR2 if mutation&1 else G.ACTOR;scale=-.5 if mutation&2 else .25;ax,ay,az=[G.floating(G.read(public,actor+o))for o in (0x14,0x18,0x1c)];height=R.s16(G.read(public,actor+0xd6,2));wx=R.f32(-375.0*scale+ax);wz=R.f32(-187.5*scale+az);wy=R.f32(-125.0*scale+ay)
  assert calls[-1][1]==(actor,G.bits(ax),G.bits(R.f32(ay+height)),G.bits(az),G.bits(wx),G.bits(wy),G.bits(wz),0x6c if mutation&4 else 0xd2,18);count+=1
 print('connected vector cases',count,'visited',len(visited),'of',len(code),'trig helpers modeled')
