"""Independent bounded motion/contact model with retained probe mutations."""
from pathlib import Path
from dataclasses import dataclass,asdict
import itertools,json,struct,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_motion_impact_151b118c_screen as source
p=source.OUT;f=source.FROZEN;ENTRY=0x151B118C
A,MARK,TIME,COEF=0x30000,0x70000,0x800BE9A4,0x800AA2F0
PROBE,RNG,FIRST,SECOND=0x15046C80,0x150ADA20,0x151D9B8C,0x151DAB58
COUNTS={PROBE:4,RNG:0,FIRST:11,SECOND:7}
data=lambda m,a,n:bytes(m[a+i]for i in range(n))
u32=lambda n:n&0xffffffff
f32=lambda n:floating(bits(n))
add=lambda a,b:f32(a+b)
sub=lambda a,b:f32(a-b)
mul=lambda a,b:f32(a*b)
ld=lambda m,a:floating(read(m,a))
st=lambda m,a,v:put(m,a,bits(v))
public=lambda m:{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}

@dataclass(frozen=True)
class Case:
 seed:int=0;enabled:int=1;hit:int=1;parity:int=0;mutation:int=0;phase:int=0;time:float=1.;blend:float=.75

def cases():
 for seed in range(256):
  yield Case(seed=seed,enabled=seed&255,hit=seed%3!=0,parity=seed&1,mutation=seed%16,phase=8*(seed&1),
   time=(0.,.5,1.,1.5,2.)[seed%5],blend=(0.,.25,.75,1.,1.5)[seed%5])
 for enabled,hit,parity,mutation,time in itertools.product((0,1,255),(0,1),(0,1),(0,15),(0.,1.,2.)):
  yield Case(seed=173,enabled=enabled,hit=hit,parity=parity,mutation=mutation,time=time,phase=8)
 for seed in range(32):yield Case(seed=seed,enabled=1,hit=1,parity=seed&1,mutation=15,time=1.25,blend=-.5)

def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for a,n in((A,512),(MARK,4),(TIME,4),(COEF,12)):
  assert a+n<=STACK-2048 or a>=STACK+1024
  m.update({a+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for i,off in enumerate((0x30,0x34,0x38,0x3C,0x40,0x44,0x48,0x78,0x110,0x114,0x118,0x11C,0x124,0x128,0x12C,0x130)):
  st(m,A+off,(c.seed+i-120)*.25)
 st(m,TIME,c.time);st(m,COEF,c.blend);st(m,COEF+4,.125);st(m,COEF+8,.375)
 m[A+0x134]=c.enabled;m[A+0x135]=c.seed;m[A+0x5C]=(c.seed+0x81)&255;m[A+12]=0xE7;m[A+1]=0x93
 return m

class Service:
 def __init__(self,m,c):self.m,self.c=m,c;self.calls=[];self.probe=None
 def invoke(self,t,args):
  m,c=self.m,self.c;normal=list(args);observed=b''
  if t==PROBE:
   assert args[1]==0 and args[3]==A+0x78
   self.probe=args[0];normal[0]='probe';observed=data(m,self.probe,12)
  elif t==FIRST:
   assert args[3]==A+0x7C and args[5:9]==(100,0,1,0)
   normal[4]='impact';observed=data(m,args[4],12)+data(m,args[3],18)
  elif t==SECOND:
   assert args[4]==1;normal[3]='impact';observed=data(m,args[3],12)
  else:assert t==RNG
  self.calls.append((t,tuple(normal),observed));ordinal=len(self.calls)
  put(m,MARK,u32(0x13579BDF+ordinal*0x10203+t))
  if t==PROBE:
   for i in range(36):m[A+0x78+i]=(c.seed+i*19)&255
   st(m,A+0x78,(c.seed-75)*.375)
   if c.mutation&1:
    for j in range(3):st(m,self.probe+4*j,(c.seed+j-85)*.5)
   if c.mutation&2:
    m[A+0x135]^=0xA7;m[A+0x5C]^=0x51;m[A+12]^=7;m[A+1]^=0x33
    for j in range(4):st(m,A+0x124+4*j,(c.seed+j-80)*.125)
   if c.mutation&4:
    st(m,A+0x30,-125.);st(m,A+0x34,33.);st(m,A+0x38,-55.);st(m,A+0x3C,75.);st(m,TIME,3.)
   return int(c.hit)
  if t==RNG:
   if c.mutation&8:
    for j in range(3):st(m,self.probe+4*j,(-c.seed+j)*.25)
    for j in range(4):st(m,A+0x124+4*j,-(c.seed+j)*.125)
    m[A+0x135]^=0x55;m[A+0x5C]^=0x31;m[A+12]^=0x19;m[A+1]^=0xA1
    st(m,COEF+4,.625);st(m,COEF+8,-.25)
    for i in range(18):m[A+0x7C+i]^=(i*7+c.seed)&255
   return 0xABCDEF00|c.parity
  return 0xDEADBEEF

def reference(initial,c):
 m=dict(initial);s=Service(m,c);probe=STACK+c.phase-44;impact=STACK+c.phase-56
 oldY,oldX,oldZ=ld(m,A+0x38),ld(m,A+0x110),ld(m,A+0x118)
 st(m,A+0x110,mul(oldX,mul(.25,ld(m,TIME))))
 st(m,A+0x118,mul(oldZ,mul(.25,ld(m,TIME))))
 oldVertical=ld(m,A+0x114)
 dx=mul(mul(add(ld(m,A+0x110),oldX),.5),ld(m,TIME))
 acceleration=mul(ld(m,A+0x11C),ld(m,TIME))
 dy=add(mul(oldVertical,ld(m,TIME)),mul(mul(acceleration,ld(m,TIME)),.5))
 dz=mul(mul(add(ld(m,A+0x118),oldZ),.5),ld(m,TIME))
 st(m,A+0x114,add(oldVertical,acceleration));st(m,A+0x38,add(oldY,dy));y=ld(m,A+0x38)
 st(m,A+0x34,add(ld(m,A+0x34),dx));x=ld(m,A+0x34)
 st(m,A+0x3C,add(ld(m,A+0x3C),dz));st(m,A+0x40,add(ld(m,A+0x40),dx));z=ld(m,A+0x3C)
 st(m,A+0x44,add(ld(m,A+0x44),dy));st(m,A+0x48,add(ld(m,A+0x48),dz))
 coefficient=ld(m,COEF)
 for off,v in((0x40,x),(0x44,y),(0x48,z)):st(m,A+off,add(v,mul(sub(ld(m,A+off),v),coefficient)))
 answer=1
 if m[A+0x134]:
  for j,v in enumerate((x,sub(oldY,ld(m,A+0x30)),ld(m,A+0x3C))):st(m,probe+4*j,v)
  if s.invoke(PROBE,(probe,0,bits(sub(ld(m,A+0x38),ld(m,A+0x30))),A+0x78)):
   st(m,impact,ld(m,probe));st(m,impact+8,ld(m,probe+8));st(m,impact+4,add(ld(m,A+0x78),5.))
   extent=mul(add(add(ld(m,A+0x124),mul(ld(m,A+0x12C),.5)),add(ld(m,A+0x128),mul(ld(m,A+0x130),.5))),.5)
   first=s.invoke(RNG,())&1
   amplitude=bits(mul(extent,ld(m,COEF+(4 if first else 8))))
   if first:s.invoke(FIRST,(m[A+0x135],amplitude,m[A+0x5C],A+0x7C,impact,100,0,1,0,m[A+12],m[A+1]))
   else:s.invoke(SECOND,(m[A+0x135],amplitude,m[A+0x5C],impact,1,m[A+12],m[A+1]))
   answer=0
 return m,s,answer

class Oracle(FactoryOracle):
 def __init__(self,words,initial,c):
  super().__init__(words,initial,c,entry=ENTRY,s={},arguments=(A,))
  self.service=Service(self.memory,c);self.saved=tuple(self.r[16:24])+tuple(self.r[28:]);self.saved_fp=tuple(self.f[20:])
 def record_call(self,t):
  assert t in COUNTS,hex(t);self.pending=t,tuple(self.arguments(COUNTS[t]))
 def hook(self,t):
  target,args=self.pending;assert t==target;answer=self.service.invoke(t,args)
  for i in range(max(4,COUNTS[t])):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=u32(answer)

def verify(words,c):
 initial=fixture(c);expected,s,answer=reference(initial,c);m=Oracle(words,initial,c).run()
 assert m.service.calls==s.calls,('calls',asdict(c),next(((i,a,b)for i,(a,b)in enumerate(zip(m.service.calls,s.calls))if a!=b),None))
 left,right=public(m.memory),public(expected)
 assert left==right,('public',asdict(c),next(((hex(a),left.get(a),right.get(a))for a in left.keys()|right.keys()if left.get(a)!=right.get(a)),None))
 assert m.r[2]==answer,('answer',c,m.r[2],answer)
 assert tuple(m.r[16:24])+tuple(m.r[28:])==m.saved and tuple(m.f[20:])==m.saved_fp,('ABI',c)
 return m

def streams(labels):
 symbols={row[1]:row[2][1]for row in symbol_rows((f/'conker/build/conker.us.elf').read_bytes())}
 yield'original',list(struct.unpack('>187I',(p/'retail.bin').read_bytes()))
 for label in labels:yield label,bound_blob(*payload(p/(label+'.o'),'func_151B118C'),symbols)

def main(labels=('phase-s8','blend-oldX-ordered')):
 reports=[]
 for label,words in streams(labels):
  seen=set();count=0
  for c in cases():m=verify(words,c);seen.update(m.visits&set(range(ENTRY,ENTRY+len(words)*4,4)));count+=1
  row=dict(stream=label,cases=count,coverage=len(seen),words=len(words),passes=True,all_public_bytes=True,all_call_arguments_and_exposed_vectors=True,saved_GPR_FPR_SP_RA=True,private_unexposed_bytes_uncredited=True,c_match_credit=0)
  reports.append(row);print(json.dumps(row),flush=True)
 (p/'guest-report.json').write_text(json.dumps(dict(passes=True,streams=reports),indent=2)+'\n')
 return dict(passes=True,streams=reports)
if __name__=='__main__':main()
