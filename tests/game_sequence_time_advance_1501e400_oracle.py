"""Independent sequence-time model, bounded global providers and literal guest execution."""
import itertools
from dataclasses import dataclass,replace
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:(u32(n)^0x80000000)-0x80000000
ENTRY=0x1501E400
S={n:int(n.split('_')[1],16)for n in ('D_800C3A58','D_800C35B0','D_800C35B8','D_800C35EA','D_800BEAC0','D_800BEA08','D_800C35C0','D_800C3C8E','D_800C3640','func_1501E1B4','func_151F2CDC','func_15080228')}
@dataclass(frozen=True)
class Case:
 slot:int=0
 active:int=1
 count:int=2
 time:int=10
 limit:int=100
 delta:int=1
 paused:int=0
 gate:int=0
 marker:int=10
 poll:int=1
 mutation:int=0
 phase:int=0
def ea(s,n,c,width=4):return u32(s[n]+width*u32(c.slot))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def fixture(c,s=S):
 m={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
 for n in S:
  if n.startswith('D_'):
   for i in range(-16,32):m[u32(s[n]+i)]=(i*13+91)&255
 for n,v,w,indexed in [('D_800C3A58',c.count,1,False),('D_800C35B0',c.time,4,True),('D_800C35B8',0x12345678,4,True),('D_800C35EA',c.active,1,True),('D_800BEAC0',c.paused,1,False),('D_800BEA08',c.delta,4,False),('D_800C35C0',c.gate,1,True),('D_800C3C8E',c.marker,2,False),('D_800C3640',c.limit,4,True)]:put(m,ea(s,n,c,w)if indexed else s[n],v,w)
 return m
def effect(m,c,s,kind):
 time=ea(s,'D_800C35B0',c);previous=ea(s,'D_800C35B8',c);limit=ea(s,'D_800C3640',c)
 if c.mutation==1 and kind==1:put(m,time,read(m,time)+17)
 if c.mutation==2 and kind==1:
  marker=read(m,s['D_800C3C8E'],2);put(m,previous,marker);put(m,time,marker+1);put(m,ea(s,'D_800C35C0',c,1),0,1)
 if c.mutation==3 and kind==1:put(m,s['D_800BEAC0'],c.paused^1,1);put(m,s['D_800BEA08'],0xFFFFFFF1)
 if c.mutation==4 and kind==2:put(m,limit,0x80000000);put(m,time,0x7FFFFFFF)
 if c.mutation==5 and kind==3:put(m,limit,0x7FFFFFFF);put(m,time,0x80000000)
 if c.mutation==6 and kind==1:put(m,ea(s,'D_800C35EA',c,1),0,1);put(m,s['D_800C3C8E'],0xFFFF,2)
 if c.mutation==7 and kind==3:put(m,time,9);put(m,limit,9)
def reference(initial,c,s=S):
 m=dict(initial);calls=[];snaps=[];current=ea(s,'D_800C35B0',c);previous=ea(s,'D_800C35B8',c)
 def call(kind,args=()):
  n=('func_1501E1B4','func_151F2CDC','func_15080228')[kind-1];calls.append((s[n],args));snaps.append(public(m));effect(m,c,s,kind)
 count=read(m,s['D_800C3A58'],1)
 if count:put(m,s['D_800C3A58'],count-1,1)
 put(m,previous,read(m,current))
 if read(m,ea(s,'D_800C35EA',c,1),1)==1:
  call(1,(u32(c.slot),))
  if c.slot!=0 or read(m,s['D_800BEAC0'],1)==0:put(m,current,read(m,current)+read(m,s['D_800BEA08']))
  marker=read(m,s['D_800C3C8E'],2)
  if read(m,ea(s,'D_800C35C0',c,1),1)==0 and marker==read(m,previous) and marker!=read(m,current):put(m,previous,0xFFFFFFFF)
  call(2)
  if c.poll==1:call(3)
  if signed(read(m,current))>=signed(read(m,ea(s,'D_800C3640',c))):put(m,current,read(m,ea(s,'D_800C3640',c)))
 return public(m),calls,snaps
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=None,entry=ENTRY,connected=None):
  s=dict(S)if s is None else s
  self.s=s;self.snapshots=[]
  super().__init__(words,memory,c,entry=entry,s=s,arguments=(u32(c.slot),),connected=connected)
 def record_call(self,t):
  counts={self.s['func_1501E1B4']:1,self.s['func_151F2CDC']:0,self.s['func_15080228']:0};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.snapshots.append(public(self.memory))
 def hook(self,t):
  kind=('func_1501E1B4','func_151F2CDC','func_15080228').index(next(n for n in self.s if self.s[n]==t))+1
  effect(self.memory,self.case,self.s,kind)
  for i in range(4):self.put(u32(self.r[29]+4*i),0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(self.case.poll if kind==2 else 0x81234560)
def cases():
 pairs=((0,0),(0,1),(1,0),(0x7FFFFFFF,0x80000000),(0x80000000,0x7FFFFFFF),(0xFFFFFFFF,0))
 for slot,active,count,(time,limit),mutation,phase in itertools.product((0,1),(0,1,2,255),(0,1,255),pairs,range(8),(0,8)):
  yield Case(slot=slot,active=active,count=count,time=time,limit=limit,delta=0x80000001 if mutation&1 else 1,paused=(mutation>>1)&1,gate=(mutation>>2)&1,marker=time&65535,poll=(0,1,2,0xFFFFFFFF)[mutation&3],mutation=mutation,phase=phase)
 for marker in(0,1,127,255,32767,32768,65535):
  for slot,gate,paused,poll in itertools.product((0,1),(0,1,255),(0,1,255),(0,1,2,5,6,7,0xFFFFFFFF)):
   yield Case(slot=slot,time=marker,marker=marker,gate=gate,paused=paused,poll=poll)
 for n in range(256):yield Case(count=n,active=n,marker=n*257,time=n*257,delta=1,poll=1)

def observation(m,s=None):
 s=S if s is None else s
 return (read(m,s['D_800C3A58'],1),*[read(m,s['D_800C35B0']+i*4)for i in range(2)],*[read(m,s['D_800C35B8']+i*4)for i in range(2)],*[read(m,s['D_800C35EA']+i,1)for i in range(2)],read(m,s['D_800BEAC0'],1),read(m,s['D_800BEA08']),*[read(m,s['D_800C35C0']+i,1)for i in range(2)],read(m,s['D_800C3C8E'],2),*[read(m,s['D_800C3640']+i*4)for i in range(2)])
