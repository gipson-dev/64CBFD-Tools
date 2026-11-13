from dataclasses import dataclass
from pathlib import Path
import itertools,sys
root=Path.cwd();sys.path.insert(0,str(root));out=root/'conker/build/game-camera-condition-150be850-screen'
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
NAME='func_150BE850';ENTRY=0x150BE850;CAMERA=0x30000
SYMS={x:int(x.split('_')[1],16) for x in ('D_800A00B0','D_800A00B4','D_800CC335','func_1509BE40','func_1509BFB0','func_1512868C','func_15123934','func_151254F4','func_15123070','func_151239CC')}
@dataclass(frozen=True)
class Case: first:int;second:int;third:int;mode:int;activate:int;leave:int;mutate:int;phase:int=0
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)};m.update({CAMERA+i:(i*29+0x35)&255 for i in range(0x800)})
 for a,v in ((0x2c,c.mode),(0x134,42),(0x84,0x12345674),(0x674,bits(2.)),(0x348,bits(3.)),(0x34c,bits(4.)),(0x374,bits(5.)),(0x190,bits(6.))):put(m,CAMERA+a,v)
 put(m,CAMERA+0x73c,42,2);put(m,SYMS['D_800A00B0'],bits(1.25));put(m,SYMS['D_800A00B4'],bits(2.5));m[SYMS['D_800CC335']]=0;return m
class Machine(FactoryOracle):
 def __init__(self,words,c,m):self.c=c;super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(CAMERA,))
 def record_call(self,t):
  counts={'func_1509BE40':3,'func_1509BFB0':3,'func_1512868C':1,'func_15123934':5,'func_151254F4':2,'func_15123070':1,'func_151239CC':2}
  name=next(k for k,v in SYMS.items() if v==t);self.calls.append((t,tuple(self.arguments(counts[name]))))
 def hook(self,t):
  c=self.c;name=next(k for k,v in SYMS.items() if v==t);n=sum(target==t for target,_ in self.calls)
  if c.mutate and name=='func_1512868C':put(self.memory,CAMERA+0x134,77)
  if c.mutate and name=='func_151254F4':put(self.memory,CAMERA+0x84,0x1004)
  result=((c.first,c.second,c.third)[n-1] if name=='func_1509BE40' else c.activate if name=='func_15123934' else c.leave if name=='func_151239CC' else 0xfeedface)
  for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010;self.r[2]=result&0xffffffff
def reference(initial,c):
 m=initial.copy();calls=[]
 def call(name,*args):
  calls.append((SYMS[name],tuple(a&0xffffffff for a in args)))
  if c.mutate and name=='func_1512868C':put(m,CAMERA+0x134,77)
  if c.mutate and name=='func_151254F4':put(m,CAMERA+0x84,0x1004)
 call('func_1509BE40',0,0x2006,0xb7);call('func_1509BE40',0,c.first|0x2000,0xbc);call('func_1509BE40',0,0x2000,0xbb)
 if c.second and c.third!=-1:
  call('func_1509BFB0',0,0x400e,1)
  if read(m,CAMERA+0x2c)!=8:call('func_1512868C',CAMERA)
  call('func_15123934',CAMERA,8,0,read(m,CAMERA+0x134),3)
  if c.activate:
   call('func_151254F4',CAMERA,m[SYMS['D_800CC335']]-1)
   put(m,CAMERA+0x84,read(m,CAMERA+0x84)|0x1000200);put(m,CAMERA+0x73c,0,2);put(m,CAMERA+0x84,read(m,CAMERA+0x84)&~4);put(m,CAMERA+0x674,0)
  width=read(m,SYMS['D_800A00B0']);height=read(m,SYMS['D_800A00B4'])
  for offset,value in ((0x348,width),(0x34c,width),(0x374,height),(0x190,0)):put(m,CAMERA+offset,value)
  call('func_15123070',CAMERA)
 else:
  call('func_151239CC',CAMERA,3)
  if c.leave:call('func_151254F4',CAMERA,0);put(m,CAMERA+0x674,0);call('func_1509BFB0',0,0x400e,0)
 return {a:b for a,b in m.items() if not STACK-512<=a<STACK+512},calls
programs=[bound_blob(*payload(out/x,NAME),SYMS) for x in ('retail.o','abi.o','generated.o','generic.o')];assert programs[0]==programs[2]==programs[3]
count=0
for vals in itertools.product((0,3),(0,1),(-1,0),(0,8),(0,1),(0,1),(0,1)):
 c=Case(*vals);initial=fixture(c);expected=reference(initial,c)
 for p in programs:
  m=Machine(p,c,initial.copy()).run();actual=({a:b for a,b in m.memory.items() if not STACK-512<=a<STACK+512},m.calls)
  assert actual==expected,(c,actual[1],expected[1])
 count+=1
print(count,'guest cases per stream passed; mocked helpers and ordinary nonoverlapping memory only')
