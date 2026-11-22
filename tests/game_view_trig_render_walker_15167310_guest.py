"""Independent live-view and column-major walker model; helpers are contracts."""
from pathlib import Path
from dataclasses import dataclass,replace
from types import FunctionType
import itertools,json,struct,sys
from tools.experiments import game_view_trig_render_walker_15167310_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x15167310;VIEW=0x40000;ALT=0x50000;NODES=0x60000;CB0=0x15600000;CB1=0x15600100
SYMS={n:int(n[2:],16)for n in('D_80082FA0','D_800DBFF0','D_800DD1D8','D_800DD1E8','D_800DD1D0','D_8008B4A8','D_800DCE50','D_800DD190','D_800DD198')}
SYMS.update(sinf=0x15047D60,cosf=0x15047C00)
u32=lambda v:v&0xFFFFFFFF;s32=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000;s8=lambda v:((v&255)^128)-128
@dataclass(frozen=True)
class Case:
 count:int=1
 shape:int=1
 mode:int=0
 depth:int=1
 phase:int=0
 angle:int=0x3F123456

def node_id(p):return (p-NODES)//0x400
def node_at(row,col,index=0):return NODES+((col*2+row)*3+index)*0x400
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
 for name,size in(('D_8008B4A8',104*52),('D_800DCE50',0x340),('D_800DD198',24),('D_800DD1D0',8),('D_800DD1D8',16),('D_800DD1E8',16)):
  m.update({s[name]+i:0 for i in range(size)})
 for base in(VIEW,ALT):
  for i in range(4):
   for j in range(4):m[base+i*0x9A0+0x3A0+j]=0
   put(m,base+i*0x9A0+0x3A0,u32(c.angle+0x12345*i+(0x100000 if base==ALT else 0)))
 put(m,s['D_80082FA0'],c.count);put(m,s['D_800DBFF0'],VIEW)
 for col in range(104):
  cb=0 if c.shape==0 or c.shape==2 and col%2 else CB0
  put(m,s['D_8008B4A8']+52*col+12,cb)
  for row in range(2):
   active=c.shape==3 or c.shape in(1,2)and col in(0,1,51,103)or c.shape==4 and col==103 and row==1
   put(m,s['D_800DCE50']+416*row+4*col,node_at(row,col)if active else 0)
   if active:
    for i in range(3):
     p=node_at(row,col,i);m.update({p+j:(j*13+col+row+i)&255 for j in range(32)})
     put(m,p+8,node_at(row,col,i+1)if i<2 and c.shape!=4 else 0)
 # Guest-only extended signed depth fixtures map backing bytes explicitly.
 # Existing adjacent rows/cache globals retain their earlier initialized bytes.
 for i in range(-128*4,128*4):m.setdefault(u32(s['D_800DD198']+i),0)
 m[s['D_800DD190']]=c.depth&255
 return m
def trig_value(target,bits,s=SYMS):return u32((bits^ (0x13579BDF if target==s['sinf']else 0x2468ACE0))+0x10203)
def effects(m,c,t,arg,ordinal,s=SYMS):
 if t in(s['sinf'],s['cosf']):
  if ordinal==0:
   if c.mode&32:put(m,s['D_800DBFF0'],ALT);put(m,VIEW+0x3A0,0xBF654321)
   if c.mode&64:put(m,s['D_80082FA0'],u32(-1))
   if c.mode&128:put(m,s['D_80082FA0'],3)
  return
 ident=node_id(arg);col=ident//6;index=ident%3
 if c.mode&1:put(m,s['D_8008B4A8']+52*col+12,CB1)
 if c.mode&2:put(m,arg+8,0)
 if c.mode&4:put(m,u32(s['D_800DD198']+4*s8(m[s['D_800DD190']])),0)
 if c.mode&8 and index==0:
  m[s['D_800DD190']]=(m[s['D_800DD190']]+1)&255
  put(m,u32(s['D_800DD198']+4*s8(m[s['D_800DD190']])),0)
 if c.mode&16 and col==0:put(m,s['D_800DCE50']+4*51,0)
def observation(m,t,arg,s=SYMS):
 if t in(s['sinf'],s['cosf']):return(t,arg,read(m,s['D_80082FA0']),read(m,s['D_800DBFF0']))
 return(t,arg,s8(m[s['D_800DD190']]),read(m,u32(s['D_800DD198']+4*s8(m[s['D_800DD190']]))))
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];obs=[]
 def call(t,arg):
  calls.append((t,(arg,)));obs.append(observation(m,t,arg,s));effects(m,c,t,arg,len(calls)-1,s);return trig_value(t,arg,s)
 i=0
 if s32(u32(read(m,s['D_80082FA0'])+1))>0:
  while True:
   a=read(m,read(m,s['D_800DBFF0'])+i*0x9A0+0x3A0)
   put(m,s['D_800DD1D8']+4*i,call(s['sinf'],a));value=call(s['cosf'],a)
   limit=s32(read(m,s['D_80082FA0']));put(m,s['D_800DD1E8']+4*i,value);i+=1
   if i>limit:break
   assert i<4,'Fixture exceeds four recovered cache entries'
 a=read(m,read(m,s['D_800DBFF0'])+0x3A0)
 put(m,s['D_800DD1D0'],call(s['sinf'],a));put(m,s['D_800DD1D0']+4,call(s['cosf'],a))
 for col in range(104):
  for row in range(2):
   node=read(m,s['D_800DCE50']+416*row+4*col);descriptor=s['D_8008B4A8']+52*col
   if not node or not read(m,descriptor+12):continue
   m[s['D_800DD190']]=(m[s['D_800DD190']]+1)&255
   steps=0
   while node:
    put(m,u32(s['D_800DD198']+4*s8(m[s['D_800DD190']])),read(m,node+8))
    call(read(m,descriptor+12),node);node=read(m,u32(s['D_800DD198']+4*s8(m[s['D_800DD190']])))
    steps+=1;assert steps<4
   m[s['D_800DD190']]=(m[s['D_800DD190']]-1)&255
 return m,calls,obs
class Oracle(FactoryOracle):
 run=FunctionType(TriangleOracle.run.__code__,dict(TriangleOracle.run.__globals__,range=lambda *a:range(100000)if a==(50000,)else range(*a)))
 def __init__(self,ws,memory,c,s=SYMS,connected=None,entry=ENTRY):
  super().__init__(ws,memory,c,entry=entry,s=s,connected=connected,arguments=())
  self.before=self.r[:];self.before_f=self.f[:];self.initial=dict(self.memory);self.observations=[]
 def record_call(self,t):
  assert t in(self.syms['sinf'],self.syms['cosf'],CB0,CB1),hex(t)
  arg=self.f[12]if t in(self.syms['sinf'],self.syms['cosf'])else self.arguments(1)[0]
  self.calls.append((t,(arg,)));self.observations.append(observation(self.memory,t,arg,self.syms))
  if t in(self.syms['sinf'],self.syms['cosf']):assert self.f[20]==arg,'Angle was not retained in F20'
 def hook(self,t):
  arg=self.calls[-1][1][0];effects(self.memory,self.case,t,arg,len(self.calls)-1,self.syms)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  if t in(self.syms['sinf'],self.syms['cosf']):self.f[0]=trig_value(t,arg,self.syms)
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+512}
def check(m,c,s=SYMS):
 want,calls,obs=reference(m.initial,c,s)
 assert(public(m.memory),m.calls,m.observations)==(public(want),calls,obs),c
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],('Saved ABI',c)
def words(path,s=SYMS):return bound_blob(*payload(path,'func_15167310'),s)
def paths():return {'raw':out/'selected/candidate.o','padded':out/'qualified-owner/game_1944C0.c.o','retail':out/'original-target.o'}
def cases():
 rows=[Case(count=n,shape=shape,mode=mode,depth=d,phase=p,angle=a)for n,shape,mode,d,p,a in itertools.product((-3,-1,0,1,3,0x7FFFFFFF,0x80000000),(0,1,2),(0,1,2,4,16,32,64,128),(0,3),(0,8),(0,0x80000000))]
 rows +=[Case(shape=4,mode=8,depth=d)for d in(-128,-1,0,1,126,127)]
 rows +=[Case(shape=3,count=n,mode=mode)for n,mode in itertools.product((-1,3),(0,1,2,4,16))]
 rows +=[Case(count=1,shape=1,mode=mode,angle=a)for mode,a in itertools.product((33,65,129,160),(0x7F800000,0x7FC12345,0x00000001,0xFF7FFFFF))]
 return rows
def main():
 reports={}
 for label,path in paths().items():
  ws=words(path);seen=set()
  for c in cases():
   m=Oracle(ws,fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  reports[label]=dict(cases=len(cases()),unexecuted=[i for i in range(len(ws))if ENTRY+4*i not in seen])
 runs=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={n:0x80300000+i*0x10000+low for i,n in enumerate(SYMS)if n not in('sinf','cosf')};s.update(sinf=0x15047D60,cosf=0x15047C00);s['D_800DD190']=s['D_800DCE50']+0x340
  for path in paths().values():
   for c in(Case(mode=33),Case(mode=64),Case(shape=4,mode=8)):
    m=Oracle(words(path,s),fixture(c,s),c,s);m.run();check(m,c,s);runs+=1
 r=dict(streams=reports,guest_rebase_runs=runs,full_public_state_and_ordered_helper_observations=True,completed_saved_ABI=True,live_base_count_depth_continuation_and_callback_mutations=True,
  wrapped_count_plus_one=True,F20_capture_survives_volatile_clobbers=True,limits='Four views, valid mapped nodes, bounded callbacks and symbolic sin/cos contracts; no helper internals, FCSR or gameplay acceptance.',source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
