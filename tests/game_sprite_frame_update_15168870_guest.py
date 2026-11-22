"""Independent signed-phase state model and bounded callback/cleanup contracts."""
from pathlib import Path
from dataclasses import dataclass,replace
from types import FunctionType
import itertools,json,struct,sys
from tools.experiments import game_sprite_frame_update_15168870_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x15168870;STATE=0x30000;OTHER=0x31000;META=0x70000;CB0=0x15600000;CB1=0x15600100;CLEAN=0x1516972C;SIZE=0xB8
SYMS=dict(D_800BE9E4=0x800BE9E4,D_8008CA4C=0x8008CA4C,D_8008C9C8=0x8008C9C8,func_1516972C=CLEAN)
u32=lambda x:x&0xFFFFFFFF;s16=lambda x:((x&65535)^32768)-32768
def half(m,a,order='big'):return s16(int.from_bytes(bytes(m[a+i]for i in range(2)),order))
def put_half(m,a,v,order='big'):m.update({a+i:b for i,b in enumerate((v&65535).to_bytes(2,order))})
def remainder(a,b):return a-(-1 if(a<0)!=(b<0)else 1)*(abs(a)//abs(b))*b
@dataclass(frozen=True)
class Case:
 position:int=255
 speed:int=1
 frames:int=2
 ticks:int=1
 flags:int=0
 index:int=2
 callback:bool=True
 mode:int=0
 texture:int=17
 alias:int=0
 phase:int=0
def metadata(c):return META+16*c.texture if c.alias==0 else STATE+(0x90,0x94,0x96)[c.alias-1]
def fixture(c,order='big',s=SYMS):
 assert META>=STACK+512 or META+4096<=STACK-2048
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
 for rec in(STATE,OTHER):m.update({rec+i:(i*13+rec//256+7)&255 for i in range(-16,SIZE+16)})
 for tex in range(256):
  at=META+16*tex;m.update({at+i:(tex*11+i*17+3)&255 for i in range(16)});m[at+4]=(c.frames+29*tex+7)&255
  put(m,s['D_8008CA4C']+tex*4,metadata(c)if tex==c.texture else at)
 # The real callback table occupies22 words before D_8008CA20. Extending
 # signed-selector fixtures overlaps the later texture-pointer storage;
 # those guest-only cases therefore skip texture arithmetic with speed0.
 extended=c.index<-1 or c.index>=22
 assert not extended or c.speed==0
 for index in(range(-128,128)if extended else range(22)):put(m,u32(s['D_8008C9C8']+index*4),(CB1 if index&1 else CB0)if c.callback else 0)
 put_half(m,STATE+0x98,c.position,order);put_half(m,STATE+0x9A,c.speed,order);put_half(m,STATE+0xA8,c.flags,order)
 m[STATE+0xB0]=c.texture;m[STATE+0xB2]=c.index&255;m[metadata(c)+4]=c.frames
 put_half(m,OTHER+0x98,-1,order);put_half(m,OTHER+0x9A,0x1234,order);put(m,s['D_800BE9E4'],c.ticks)
 return m
def effects(m,c,t,record,home,order='big',s=SYMS):
 if t in(CB0,CB1):
  if c.mode&1:put_half(m,record+0x98,-1,order)
  if c.mode&2:put_half(m,record+0x98,123,order)
  if c.mode&4:put_half(m,record+0x9A,-3,order)
  if c.mode&8:
   index=s16(m[record+0xB2])if m[record+0xB2]<128 else m[record+0xB2]-256
   put(m,u32(s['D_8008C9C8']+index*4),0);m[record+0xB2]=255
  if c.mode&16:put(m,home,OTHER)
  if c.mode&32:m[record+0xB0]^=0x80;put(m,s['D_800BE9E4'],0x13579BDF)
 elif t==s['func_1516972C']:
  if c.mode&64:put(m,record+8,0);m[record+0x40]^=0xA5
 else:raise AssertionError(hex(t))
def observation(m,record,order='big',s=SYMS):return(record,half(m,record+0x98,order),half(m,record+0x9A,order),m[record+0xB2],read(m,s['D_800BE9E4']))
def reference(initial,c,order='big',s=SYMS,home=None,record=STATE):
 m=dict(initial);calls=[];observations=[];h=STACK+c.phase if home is None else home;speed=half(m,record+0x9A,order)
 if speed:
  frames=m[read(m,s['D_8008CA4C']+4*m[record+0xB0])+4];upper=256*frames-1
  position=s16(half(m,record+0x98,order)+speed*read(m,s['D_800BE9E4']));put_half(m,record+0x98,position,order)
  flags=half(m,record+0xA8,order)&65535
  if position>upper:
   if flags&64:put_half(m,record+0x98,upper-remainder(position,upper),order);put_half(m,record+0x9A,-speed,order)
   elif flags&4:put_half(m,record+0x98,-1,order)
   else:
    steps=0
    while position>upper:
     position=s16(position-upper);put_half(m,record+0x98,position,order);steps+=1;assert steps<=65536
  elif position<0:
   if flags&64:put_half(m,record+0x98,remainder(-position,upper),order);put_half(m,record+0x9A,-speed,order)
   elif flags&4:put_half(m,record+0x98,-1,order)
   else:
    steps=0
    while position<0:
     position=s16(position+upper);put_half(m,record+0x98,position,order);steps+=1;assert steps<=65536
 index=m[record+0xB2];index=index if index<128 else index-256
 if index!=-1:
  callback=read(m,u32(s['D_8008C9C8']+index*4))
  if callback:
   assert callback in(CB0,CB1);put(m,h,record);calls.append((callback,(record,)));observations.append(observation(m,record,order,s));effects(m,c,callback,record,h,order,s);record=read(m,h)
 if half(m,record+0x98,order)==-1:
  calls.append((s['func_1516972C'],(record,)));observations.append(observation(m,record,order,s));effects(m,c,s['func_1516972C'],record,h,order,s)
 return m,calls,observations
class Oracle(FactoryOracle):
 # Preserve the existing interpreter, extending only its finite instruction budget.
 run=FunctionType(TriangleOracle.run.__code__,dict(TriangleOracle.run.__globals__,range=lambda *args:range(400000)if args==(50000,)else range(*args)))
 def __init__(self,ws,memory,c,s=SYMS,connected=None,entry=ENTRY,arguments=None):
  super().__init__(ws,memory,c,entry=entry,s=s,connected=connected,arguments=(STATE,)if arguments is None else arguments)
  self.before=self.r[:];self.before_f=self.f[:];self.initial=dict(self.memory);self.observations=[]
 def record_call(self,t):
  assert t in(CB0,CB1,self.syms['func_1516972C']);record=self.arguments(1)[0];self.calls.append((t,(record,)));self.observations.append(observation(self.memory,record,s=self.syms))
 def hook(self,t):
  effects(self.memory,self.case,t,self.calls[-1][1][0],self.target_home,s=self.syms)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+512}
def check(m,c,s=SYMS):
 want,calls,observations=reference(m.initial,c,s=s)
 assert(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),c
 h=STACK+c.phase;assert all(m.memory[a]==want[a]for a in range(h,h+64)),('Incoming homes',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],('Saved ABI',c)
def words(path,s=SYMS):return bound_blob(*payload(path,'func_15168870'),s)
def cases():
 rows=[Case(position=p,speed=v,frames=f,flags=flags,phase=(p&1)*8)for p,v,f,flags in itertools.product((-32768,-256,-1,0,1,254,255,256,511,32767),(-32768,-257,-1,0,1,257,32767),(1,2,127,128,255),(0,4,64,68))]
 rows +=[Case(frames=f,flags=64,position=32767,speed=-1)for f in range(256)]
 rows +=[Case(index=i,callback=b,mode=1,speed=0)for i,b in itertools.product(range(-128,128),(False,True))]
 rows +=[Case(mode=m,index=3,position=-1,speed=0)for m in range(128)]
 rows +=[Case(texture=t,position=32767,speed=1,frames=(t*31+1)&255,flags=64)for t in range(256)]
 rows +=[Case(alias=a,frames=f,position=p,speed=v,flags=flags)for a,f,p,v,flags in itertools.product((1,2,3),(0,1,128),(255,32512),(1,-1),(4,64))]
 rows +=[Case(ticks=t,position=p,speed=v,flags=flags)for t,p,v,flags in itertools.product((0,0x80000000,0x7FFFFFFF,0xFFFFFFFF),(-32768,32767),(-32768,32767),(0,64))]
 rows +=[Case(frames=0,position=p,speed=1,ticks=0,flags=0,callback=False)for p in(0,-32768)]
 return rows
def main():
 paths={'raw':out/'frames-mod32/candidate.o','padded':out/'qualified-owner/game_1944C0.c.o','retail':out/'original-target.o'};reports={}
 for label,path in paths.items():
  ws=words(path);seen=set()
  for c in cases():
   m=Oracle(ws,fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  reports[label]=dict(cases=len(cases()),unexecuted=[i for i in range(111)if ENTRY+4*i not in seen])
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s=dict(D_800BE9E4=0x80300000+low,D_8008CA4C=0x80400000+low,D_8008C9C8=0x80500000+low,func_1516972C=0x15300000)
  for path in paths.values():
   for c in(Case(mode=1),Case(mode=18),Case(flags=64,frames=0)):
    m=Oracle(words(path,s),fixture(c,s=s),c,s);m.run();check(m,c,s);rebases+=1
 assert all((256*n-1)!=0 for n in range(256))
 r=dict(streams=reports,guest_rebase_runs=rebases,all_frame_count_texture_and_signed_selector_bytes=True,full_record_and_public_state=True,completed_saved_ABI=True,
  unsigned32_tick_math=True,frame_alias_and_incoming_home_mutations=True,cleanup_and_callback_are_contracts=True,divide_traps_not_portable_domains=True,source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
