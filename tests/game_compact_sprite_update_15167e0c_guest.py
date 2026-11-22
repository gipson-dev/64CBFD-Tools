"""Independent lifetime/fade/fixed-point/animation model and callback contracts."""
from pathlib import Path
from dataclasses import dataclass,replace
from types import FunctionType
import itertools,json,struct,sys
from tools.experiments import game_compact_sprite_update_15167e0c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x15167E0C;STATE=0x30000;OTHER=0x31000;META=0x70000;SIZE=0x4C
CB0=0x15600000;CB1=0x15600100;END0=0x15600200;END1=0x15600300;CLEAN=0x1516972C
SYMS=dict(D_800BE9E4=0x800BE9E4,D_8008C9C8=0x8008C9C8,D_8008CA20=0x8008CA20,func_1516972C=CLEAN)
u32=lambda x:x&0xFFFFFFFF;s16=lambda x:((x&65535)^32768)-32768;s8=lambda x:((x&255)^128)-128;s32=lambda x:((x&0xFFFFFFFF)^0x80000000)-0x80000000
def word(m,a,order='big'):return int.from_bytes(bytes(m[u32(a+i)]for i in range(4)),order)
def put_word(m,a,v,order='big'):m.update({u32(a+i):b for i,b in enumerate(u32(v).to_bytes(4,order))})
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
 remaining:int=20
 fade:int=0
 alpha:int=255
 index:int=2
 completion:int=2
 callback:bool=True
 coords:tuple=(32767,-32768,-1)
 velocities:tuple=(3,-4,5)
 acceleration:int=1
 mode:int=0
 alias:int=0
 phase:int=0
def metadata(c):return META if c.alias==0 else STATE+(0x18,0x19,0x1A)[c.alias-1]
def fixture(c,order='big',s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
 for p in(STATE,OTHER):m.update({p+i:(i*13+p//256+7)&255 for i in range(-16,SIZE+16)})
 for i in range(96):m[META+i]=(i*17+3)&255
 def record(p,other=False):
  for offset,value in((0x1C,23 if other else c.position),(0x1E,-1 if other else c.speed),(0x20,17 if other else c.coords[0]),(0x22,19 if other else c.coords[1]),(0x24,21 if other else c.coords[2]),(0x26,3 if other else c.velocities[0]),(0x28,-2 if other else c.velocities[2]),(0x30,1 if other else c.velocities[1]),(0x32,0 if other else c.acceleration),(0x38,5 if other else c.remaining),(0x44,2 if other else c.flags)):put_half(m,p+offset,value,order)
  for offset,value in((0x2C,255),(0x2D,128),(0x2E,1),(0x2F,255 if other else c.index),(0x3A,0 if other else c.fade),(0x3F,144 if other else c.alpha),(0x48,255 if other else c.completion)):m[p+offset]=value&255
  put_word(m,p+0x10,META+32 if other else metadata(c),order)
 record(STATE);record(OTHER,True);m[META+36]=2;m[metadata(c)+4]=c.frames
 for i in range(22):put_word(m,s['D_8008C9C8']+4*i,(CB1 if i&1 else CB0)if c.callback else 0,order)
 for i in range(11):put_word(m,s['D_8008CA20']+4*i,END1 if i&1 else END0,order)
 if c.index not in(-1,*range(22)):put_word(m,u32(s['D_8008C9C8']+4*c.index),(CB1 if c.index&1 else CB0)if c.callback else 0,order)
 if c.completion not in(-1,*range(11)):put_word(m,u32(s['D_8008CA20']+4*c.completion),END1 if c.completion&1 else END0,order)
 put_word(m,s['D_800BE9E4'],c.ticks,order);return m
def effects(m,c,t,record,home,order='big',s=SYMS):
 if t in(CB0,CB1):
  if c.mode&1:put_half(m,record+0x38,0,order)
  if c.mode&2:put_half(m,record+0x38,123,order)
  if c.mode&4:
   put_half(m,record+0x1C,-1,order);put_half(m,record+0x1E,-3,order);put_half(m,record+0x26,-7,order)
  if c.mode&8:put_word(m,s['D_800BE9E4'],0x13579BDF,order)
  if c.mode&16:put_word(m,home,OTHER,order)
  if c.mode&128:
   i=s8(m[record+0x2F]);put_word(m,u32(s['D_8008C9C8']+4*i),0,order);m[record+0x2F]=255
  if c.mode&512:put_word(m,record+0x10,META+64,order);m[META+68]=3
 elif t in(END0,END1):
  if c.mode&32:put_word(m,home,OTHER,order)
  if c.mode&256:put_half(m,record+0x38,99,order);put_half(m,record+0x44,0xA55A,order)
 elif t==s['func_1516972C']:
  if c.mode&64:put_word(m,record+8,0,order);m[record+0x40]^=0xA5
 else:raise AssertionError(hex(t))
def observation(m,t,record,finished=None,order='big',s=SYMS):
 return(t,record,bytes(m[record+i]for i in range(SIZE)),word(m,s['D_800BE9E4'],order),finished if t in(CB0,CB1)else None)
def reference(initial,c,order='big',s=SYMS,home=None,record=STATE):
 m=dict(initial);calls=[];observations=[];h=STACK+c.phase if home is None else home;finished=0
 def call(t,rec,flag=None):
  calls.append((t,(rec,)));observations.append(observation(m,t,rec,flag,order,s));effects(m,c,t,rec,h,order,s)
 if half(m,record+0x38,order)!=32767:
  remaining=s16(half(m,record+0x38,order)-word(m,s['D_800BE9E4'],order));put_half(m,record+0x38,remaining,order)
  if remaining<0:put_half(m,record+0x38,0,order);finished=1
 fade=s8(m[record+0x3A])
 if fade>0:
  if fade<m[record+0x3F]:m[record+0x3F]=(m[record+0x3F]-fade)&255
  else:put_half(m,record+0x38,0,order);finished=1
 index=s8(m[record+0x2F])
 if index!=-1:
  target=word(m,u32(s['D_8008C9C8']+4*index),order)
  if target:put_word(m,h,record,order);call(target,record,finished);record=word(m,h,order)
 if half(m,record+0x38,order)!=0:
  put_half(m,record+0x30,half(m,record+0x30,order)+half(m,record+0x32,order),order)
  for at,frac,velocity in((0x22,0x2E,0x30),(0x20,0x2C,0x26),(0x24,0x2D,0x28)):
   packed=u32((half(m,record+at,order)<<8)|m[record+frac]);delta=u32(half(m,record+velocity,order)*word(m,s['D_800BE9E4'],order));value=u32(packed+delta)
   put_half(m,record+at,s32(value)>>8,order);m[record+frac]=value&255
  speed=half(m,record+0x1E,order)
  if speed:
   upper=256*m[word(m,record+0x10,order)+4]-1;position=s16(half(m,record+0x1C,order)+speed*word(m,s['D_800BE9E4'],order));put_half(m,record+0x1C,position,order)
   flags=half(m,record+0x44,order)&65535
   if position>upper:
    if flags&0x20:put_half(m,record+0x38,0,order);finished=1
    else:
     flags|=0x80;put_half(m,record+0x44,flags,order)
     if flags&2:put_half(m,record+0x1C,upper-remainder(position,upper),order);put_half(m,record+0x1E,-half(m,record+0x1E,order),order)
     else:
      steps=0
      while position>upper:position=s16(position-upper);put_half(m,record+0x1C,position,order);steps+=1;assert steps<=65536
   elif position<0:
    if flags&0x40:put_half(m,record+0x38,0,order);finished=1
    elif flags&2:put_half(m,record+0x1C,remainder(-position,upper),order);put_half(m,record+0x1E,-speed,order)
    else:
     steps=0
     while position<0:position=s16(position+upper);put_half(m,record+0x1C,position,order);steps+=1;assert steps<=65536
 else:finished=1
 if finished:
  index=s8(m[record+0x48])
  if index!=-1:put_word(m,h,record,order);call(word(m,u32(s['D_8008CA20']+4*index),order),record);record=word(m,h,order)
  call(s['func_1516972C'],record)
 return m,calls,observations
class Oracle(FactoryOracle):
 run=FunctionType(TriangleOracle.run.__code__,dict(TriangleOracle.run.__globals__,range=lambda *a:range(400000)if a==(50000,)else range(*a)))
 def __init__(self,ws,memory,c,s=SYMS,connected=None,entry=ENTRY,arguments=None):
  super().__init__(ws,memory,c,entry=entry,s=s,connected=connected,arguments=(STATE,)if arguments is None else arguments)
  self.before=self.r[:];self.before_f=self.f[:];self.initial=dict(self.memory);self.observations=[]
 def record_call(self,t):
  assert t in(CB0,CB1,END0,END1,self.syms['func_1516972C']),hex(t)
  record=self.arguments(1)[0];self.calls.append((t,(record,)));self.observations.append(observation(self.memory,t,record,self.r[7],s=self.syms))
 def hook(self,t):
  effects(self.memory,self.case,t,self.calls[-1][1][0],self.target_home,s=self.syms)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+512}
def check(m,c,s=SYMS):
 want,calls,obs=reference(m.initial,c,s=s)
 assert(public(m.memory),m.calls,m.observations)==(public(want),calls,obs),c
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],('Saved ABI',c)
def paths():return {'raw':out/'selected/candidate.o','padded':out/'qualified-owner/game_1944C0.c.o','retail':out/'original-target.o'}
def words(path,s=SYMS):return bound_blob(*payload(path,'func_15167E0C'),s)
def cases():
 rows=[Case(position=p,speed=v,frames=f,flags=flags,remaining=32767)for p,v,f,flags in itertools.product((-32768,-1,0,254,255,256,511,32767),(-32768,-257,-1,0,1,257,32767),(1,2,127,255),(0,2,0x20,0x40,0x42,0x60,0x22))]
 rows +=[Case(remaining=r,ticks=t,fade=f,alpha=a,speed=0)for r,t,f,a in itertools.product((-32768,-1,0,1,32766,32767),(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(-128,-1,0,1,127),(0,1,127,255))]
 rows +=[Case(index=i,remaining=0,speed=0,callback=b,completion=-1)for i,b in itertools.product(range(-128,128),(False,True))]
 rows +=[Case(completion=i,remaining=0,speed=0,index=-1)for i in range(-128,128)]
 rows +=[Case(remaining=r,mode=mode,index=3,completion=3,speed=0)for r,mode in itertools.product((0,1,32767),tuple(range(32))+(32,64,128,256,512,65,96,258,520,528))]
 rows +=[Case(remaining=32767,position=-1,speed=0,coords=(p,p,p),velocities=(v,v,v),acceleration=a,ticks=t)for p,v,a,t in itertools.product((-32768,-1,0,32767),(-32768,-1,1,32767),(-32768,1,32767),(0,1,0xFFFFFFFF))]
 rows +=[Case(alias=a,frames=f,remaining=32767,flags=2)for a,f in itertools.product((1,2,3),(0,1,127,255))]
 rows +=[Case(frames=f,remaining=32767,flags=2)for f in range(256)]
 rows +=[Case(frames=0,position=p,speed=1,ticks=0,remaining=32767,callback=False)for p in(0,-1)]
 rows +=[Case(frames=0,position=-32768,speed=1,ticks=0,remaining=32767,flags=2)]
 return rows
def main():
 reports={}
 for label,path in paths().items():
  ws=words(path);seen=set()
  for c in cases():
   m=Oracle(ws,fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  reports[label]=dict(cases=len(cases()),unexecuted=[i for i in range(len(ws))if ENTRY+4*i not in seen])
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s=dict(D_800BE9E4=0x80300000+low,D_8008C9C8=0x80400000+low,D_8008CA20=0x80500000+low,func_1516972C=CLEAN)
  for path in paths().values():
   for c in(Case(mode=2,remaining=0),Case(mode=16),Case(mode=32,remaining=0)):
    m=Oracle(words(path,s),fixture(c,s=s),c,s);m.run();check(m,c,s);rebases+=1
 r=dict(streams=reports,guest_rebase_runs=rebases,full_records_metadata_tables_and_ordered_callback_observations=True,completed_saved_ABI=True,low32_multiply_and_signed16_stores=True,
  sticky_completion_and_both_incoming_home_retargets=True,all_frame_count_and_signed_selector_bytes=True,
  limits='Mapped records and bounded callback/completion/cleanup contracts. Extended selector slots and incoming-home changes are guest extensions. DIV traps, FCSR, asynchronous mutation and helper internals are not ordinary C domains.',source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
