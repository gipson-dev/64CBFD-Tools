from pathlib import Path
import itertools,runpy,sys
root=Path.cwd();sys.path.insert(0,str(root));out=root/'conker/build/game-camera-condition-150be850-screen'
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
g=runpy.run_path(str(out/'guest.py'));Machine=g['Machine'];Case=g['Case'];ENTRY=g['ENTRY'];CAMERA=g['CAMERA'];STACK=g['STACK'];SYMS=g['SYMS'];programs=g['programs']
HELPER=0x1509BE40;PACKET=0x800D2F60;COUNT=0x800D3840;TABLE=0x80088498;CALLBACK=0x15140000
HSYMS=dict(D_800D2F60=PACKET,D_800D2F64=PACKET+4,D_800D3840=COUNT,D_80088498=TABLE)
helpers=[bound_blob(*payload(out/x,'func_1509BE40'),HSYMS) for x in ('query-retail.o','query-generic.o')]
class Connected(Machine):
 def __init__(self,words,helper,c,m):
  self.c=c;self.dispatch=[];code=dict(zip(range(HELPER,HELPER+4*len(helper),4),helper));FactoryOracle.__init__(self,words,m,c,entry=ENTRY,s=SYMS,arguments=(CAMERA,),connected=code)
 def record_call(self,t):
  if CALLBACK<=t<CALLBACK+60:
   self.dispatch.append((t,tuple(self.arguments(3)),read(self.memory,COUNT),read(self.memory,PACKET),read(self.memory,PACKET+4)))
  else:super().record_call(t)
 def hook(self,t):
  if CALLBACK<=t<CALLBACK+60:
   result=(self.c.first,self.c.second,self.c.third)[len(self.dispatch)-1]
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010;self.r[2]=result&0xffffffff
  else:super().hook(t)
count=0
for values in itertools.product((0,3),(0,1),(-1,0),(0,8),(0,1),(0,1),(0,1)):
 c=Case(*values);initial=g['fixture'](c)
 for base,n in ((PACKET,64),(TABLE,60),(COUNT,4)):initial.update({base+i:(i*29+0x35)&255 for i in range(n)})
 put(initial,COUNT,0x87654321)
 for i in range(15):put(initial,TABLE+4*i,CALLBACK+4*i)
 public,calls=g['reference'](initial,c);put(public,PACKET,0);put(public,PACKET+4,0xbb)
 expected=[(CALLBACK+4,(6,0xb7,PACKET),2,6,0xb7),(CALLBACK+4,((c.first|0x2000)&0xfff,0xbc,PACKET),2,(c.first|0x2000)&0xfff,0xbc),(CALLBACK+4,(0,0xbb,PACKET),2,0,0xbb)]
 for words in (programs[0],programs[1],programs[2],programs[3]):
  for helper in helpers:
   m=Connected(words,helper,c,initial.copy()).run();outside={a:b for a,b in m.memory.items() if not STACK-512<=a<STACK+512};assert (outside,m.calls,m.dispatch)==(public,calls,expected),(c,m.calls,m.dispatch)
 count+=1
print(count,'camera cases per callback/helper stream with original and candidate query helpers connected')
