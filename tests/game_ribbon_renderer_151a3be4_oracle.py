"""Independent complete ribbon model; this finite screen grants no adoption credit."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,math,struct,sys
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as base
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_perpendicular_offset_1519ef90_oracle import sqrt_word
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments import game_ribbon_renderer_151a3be4_recovery as source
R=source.ROOT;O=source.OUT;ENTRY=source.ENTRY
E,P,A,ALT,PALT,V,OUT,WORLD,ALTWORLD=0x30000,0x50000,0x60000,0x70000,0x71000,0x80000,0x90000,0xA0000,0xB0000
BACKEND,TEXTURE,GEOMETRY,ENV,PRIM,COMBINE,MODE=base.BACKEND,base.TEXTURE,base.GEOMETRY,base.ENV,base.PRIM,base.COMBINE,base.MODE
COPY=0x10022EC0;COUNTS={**base.COUNTS,COPY:3};SYNC=base.SYNC;S=base.S
u32=base.u32;half=base.half;byte=base.byte;STACK=base.STACK
public=base.public

@dataclass(frozen=True)
class Case:
 cap:int=5;count:int=3;head:int=0;tail:int=3;flags:int=0;kind:int=0
 fade1:int=2;fade2:int=2;pattern:int=0;mutation:int=0;view:int=0;success:int=1;phase:int=0;seed:int=0;alias:int=0;vertex_offset:int=0

def vertex_base(c):return(V if c.alias==0 else P+32 if c.alias==1 else A+24)+c.vertex_offset

def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,512)}
 for b,n in((E,160),(P,80),(PALT,80),(V,4096),(OUT,4096)):
  m.update({b+i:(i*13+c.seed+0x5A)&255 for i in range(n)})
 for b in(A,ALT):
  for i in range(c.cap):
   at=b+24*i
   for k in range(24):m[at+k]=(i*17+k*3+c.seed+0xA5)&255
   xyz=(3.25*i+1.,2.*i-5.,.5*i*i)if c.pattern==0 else(0.,0.,0.)if c.pattern==1 else(.00001*i,.000001*i,0.)if c.pattern==2 else((-1.)**i*(i+.25),i*.75,i*i*.25-3.)
   for off,value in zip((0,4,8,12),(*xyz,1.+i*.125)):put(m,at+off,bits(value+(10. if b==ALT and off<12 else 0.)))
   put(m,at+16,(-32768,-1,0,123,255,32767)[(i+c.seed)%6],2);put(m,at+18,0x1234,2)
   m[at+20]=(i*57+53+c.seed*3)&255;m[at+21]=(i*43+11+c.seed*13)&255
 put(m,E+0x94,A);put(m,E+0x98,P);put(m,E+0x1E,c.flags,2)
 for off,value in((0x25,c.cap),(0x2C,c.count),(0x2D,c.head),(0x2E,c.tail),(0x31,6)):m[E+off]=value&255
 for i,value in enumerate((1.25,2.5,-3.75)):put(m,E+16+4*i,bits(value))
 for b in(P,PALT):
  for off,value in((0x2B,c.fade1),(0x2C,37),(0x2D,c.fade2),(0x2E,83),(0x30,c.kind),(0x4C,c.seed*5)):m[b+off]=value&255
 for b in(WORLD,ALTWORLD):
  camera=u32(b+half(c.view)*0x9A0+0x2F8)
  for i,value in enumerate((8.25,-3.5,17.75)if b==WORLD else(-7.5,3.25,19.)):put(m,camera+4*i,bits(value))
 put(m,S['D_800DBFF0'],WORLD);put(m,S['D_800D2C9C'],0x10001)
 for i in range(4096):m.setdefault(vertex_base(c)+i,(i*13+c.seed+0x5A)&255)
 return m

def mutation(m,c,t,p):
 if t==BACKEND and c.mutation&1:put(m,E+0x94,ALT);put(m,E+0x98,PALT);put(m,S['D_800DBFF0'],ALTWORLD)
 if t==TEXTURE:
  if c.mutation&2:put(m,E+0x94,ALT);put(m,E+0x98,PALT);put(m,S['D_800DBFF0'],ALTWORLD)
  if c.mutation&4:put(m,E+0x1E,2,2);m[p+0x4C]=237
 if t==COMBINE and c.mutation&8:put(m,S['D_800D2C9C'],0x789ABCD)
 if t==MODE and c.mutation&16:
  m[E+0x2E]=0;m[E+0x2D]=c.cap-2;m[p+0x4C]=73

def service(m,c,t,args,ordinal,p,cursor_home=None,sync_home=None):
 if t==BACKEND:
  if cursor_home is not None:put(m,cursor_home,vertex_base(c)if c.success else 0)
  result=0
 elif t==COPY:
  assert args[2]==32
  data=bytes(m[args[1]+i]for i in range(32))
  for i,value in enumerate(data):m[args[0]+i]=value
  result=args[0]
 else:
  put(m,args[0],0xBA000000|ordinal);put(m,args[0]+4,t)
  if sync_home is not None:m[sync_home]=0
  result=u32(args[0]+8)
 mutation(m,c,t,p);return result

def reference(initial,c):
 m=dict(initial);calls=[];out=OUT;cursor=vertex_base(c);p=P
 get=lambda p,n=4:read(m,p,n);h=lambda p:half(get(p,2));b=lambda p:byte(get(p,1));op=lambda x,y,k:fp(x,y,k,'left')
 def call(t,args):
  nonlocal out
  calls.append((t,tuple(args)));value=service(m,c,t,args,len(calls)-1,p)
  if t not in(BACKEND,COPY):out=value
  return value
 if b(E+0x2C)<2:return m,OUT,calls,0
 call(BACKEND,(E+0x84,u32(half(c.view)),get(E+0x25,1)*32+160,'cursor',0))
 if not c.success:return m,OUT,calls,0
 p=get(E+0x98);records=get(E+0x94);eye=u32(get(S['D_800DBFF0'])+half(c.view)*0x9A0+0x2F8)
 if get(p+0x30,1)&2:
  remaining=get(p+0x2B,1);factor=0;i=b(E+0x2D);n=0
  while True:
   m[records+i*24+20]=factor;factor=(factor+get(p+0x2C,1))&255;i+=1
   if i==get(E+0x25,1):i=0
   remaining=half(remaining-1);n+=1;assert n<=c.cap+1
   if remaining==0 or i==b(E+0x2E):break
 if get(p+0x30,1)&4:
  i=b(E+0x2E)-1;factor=0;remaining=get(p+0x2D,1);n=0
  if i<0:i=get(E+0x25,1)-1
  while True:
   at=records+i*24+20;m[at]=((get(at,1)*factor)>>8)&255;factor=(factor+get(p+0x2E,1))&255;i-=1
   if i<0:i=get(E+0x25,1)-1
   remaining=half(remaining-1);n+=1;assert n<=c.cap+1
   if remaining==0 or i==b(E+0x2E):break
 call(TEXTURE,(out,S['D_80090CD4'],0,0,0,0,31,0,0,'sync',3))
 call(GEOMETRY,(out,1,0x160600));call(ENV,(out,255,255,255,255,'sync'));call(PRIM,(out,0,0,0,0,0,0,'sync'))
 call(COMBINE,(out,6,'sync'));call(MODE,(out,get(S['D_800D2C9C'])|0x82CA0,0x5049D8,'sync'))
 def prev(i):return i-1 if i>0 else get(E+0x25,1)-1
 def position(at):return [get(at+4*i)for i in range(3)]
 def alpha(at):return((get(at+20,1)*h(at+16))>>8)&255
 def phase(at):return(get(at+21,1)+get(p+0x4C,1))&255
 i=prev(b(E+0x2E));at=records+i*24
 if get(E+0x1E,2)&2:old=position(E+16);old_alpha=alpha(at);old_phase=phase(at)
 else:old=position(at);old_alpha=alpha(at);old_phase=phase(at);i=prev(i)
 at=records+i*24;current=position(at);new_alpha=alpha(at);new_phase=phase(at)
 def offset(point,width):
  e=[op(point[k],get(eye+4*k),'sub')for k in range(3)]
  d=[op(old[k],current[k],'sub')for k in range(3)]
  n=[op(op(d[1],e[2],'mul'),op(e[1],d[2],'mul'),'sub'),op(op(d[2],e[0],'mul'),op(e[2],d[0],'mul'),'sub'),op(op(d[0],e[1],'mul'),op(e[0],d[1],'mul'),'sub')]
  length=op(op(op(n[0],n[0],'mul'),op(n[1],n[1],'mul'),'add'),op(n[2],n[2],'mul'),'add')
  if floating(length)==0.:return [bits(0.)]*3
  scale=op(width,sqrt_word(length),'div');return [op(v,scale,'mul')for v in n]
 def trunc(value):
  v=floating(value);return u32(math.trunc(v))if math.isfinite(v)and-2147483648<=v<2147483648 else 0x80000000
 def pair(point,normal,tag,a):
  nonlocal cursor
  for operation,tex in(('add',0x7C0),('sub',0)):
   for k in range(3):put(m,cursor+2*k,trunc(op(point[k],normal[k],operation)),2)
   put(m,cursor+8,tag<<6,2);put(m,cursor+10,tex,2)
   for k,value in enumerate((255,255,255,a)):m[cursor+12+k]=value
   put(m,cursor+6,0,2);cursor+=16
 pair(old,offset(old,get(at+12)),old_phase,old_alpha);segments=0
 while True:
  pair(current,offset(current,get(records+i*24+12)),new_phase,new_alpha)
  for w0,w1 in((0x01004008,cursor-64),(0x05000204,0),(0x05020604,0)):
   put(m,out,w0);put(m,out+4,w1);out+=8
  if old_phase<new_phase:
   call(COPY,(cursor,cursor-32,32))
   put(m,cursor-24,h(cursor-24)-0x4000,2);cursor+=16;put(m,cursor-24,h(cursor-24)-0x4000,2);cursor+=16
  old_index=i;i=prev(i);segments+=1;assert segments<=c.cap+1
  if old_index!=b(E+0x2D):
   old=current;at=records+i*24;current=position(at);new_alpha=alpha(at);old_phase=new_phase;new_phase=phase(at)
  if old_index==b(E+0x2D):break
 return m,out,calls,segments

class Machine(base.Machine):
 def __init__(self,words,m,c):
  super().__init__(words,m,c,entry=ENTRY,args=(E,OUT,c.view));self.cached_p=read(m,E+0x98)
 def record_call(self,t):
  assert t in COUNTS,hex(t);args=list(self.arguments(COUNTS[t]));raw=args[:]
  if t==BACKEND:self.cursor_home=args[3];self.private_homes.append(('cursor',args[3]-self.target_home));args[3]='cursor'
  if t in SYNC:
   self.sync_home=args[SYNC[t]];self.private_homes.append(('sync',self.sync_home-self.target_home));assert self.get(self.sync_home,1)==(1 if t==TEXTURE else 0);args[SYNC[t]]='sync'
  self.calls.append((t,tuple(args)));self.raw_calls.append((t,tuple(raw)))
 def hook(self,t):
  value=service(self.memory,self.c,t,self.raw_calls[-1][1],len(self.calls)-1,self.cached_p,self.cursor_home if t==BACKEND else None,self.sync_home if t in SYNC else None)
  if t==BACKEND:self.cached_p=read(self.memory,E+0x98)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=value

def programs(labels=None):return source.programs()

def cases():
 out=[]
 for kind,fade1,fade2,flags in itertools.product((0,2,4,6),(0,1,255),(0,1,255),(0,2)):
  out.append(Case(kind=kind,fade1=fade1,fade2=fade2,flags=flags,seed=len(out)))
 for count,success,view in itertools.product((-128,-1,0,1,2,127),(0,1),(0,0xFFFF,0x12340002)):
  out.append(Case(count=count,success=success,view=view,seed=len(out)))
 for cap,head,tail,flags,pattern,mutation in itertools.product((2,3,5,7),range(2),range(2),(0,2),range(4),(0,1,2,4,8,16,31)):
  if len(out)%3==1:pass
  out.append(Case(cap=cap,head=head,tail=tail,count=cap,flags=flags,kind=(len(out)%4)*2,pattern=pattern,mutation=mutation,seed=len(out)))
 for alias,cap,flags,kind,pattern in itertools.product((1,2),(2,5),(0,2),(0,6),(0,1,3)):
  out.append(Case(alias=alias,cap=cap,head=0,tail=cap-1,count=cap,flags=flags,kind=kind,pattern=pattern,seed=len(out)))
 return out

def check(w,c,label):
 initial=fixture(c);expected,answer,calls,segments=reference(initial,c);q=Machine(w,initial,c).run()
 assert public(q.memory)==public(expected),(label,c,'memory',[(hex(p),v,q.memory.get(p))for p,v in public(expected).items()if q.memory.get(p)!=v][:8])
 assert(q.r[2],q.calls)==(answer,calls),(label,c,'return/calls',q.r[2],answer,q.calls,calls)
 return q,segments

def main(labels=None):
 streams=programs(labels);seen={k:set()for k in streams};homes={k:set()for k in streams};fp_difference={k:0 for k in streams if k!='retail'};count=0
 for c in cases():
  machines={}
  for label,words in streams.items():
   q,n=check(words,c,label);machines[label]=q;seen[label].update(q.visits);homes[label].update(q.private_homes)
  for label in fp_difference:fp_difference[label]+=machines[label].fp_ops!=machines['retail'].fp_ops
  count+=1
 report=dict(cases_per_stream=count,visited={k:len(v)for k,v in seen.items()},private_homes={k:sorted(v)for k,v in homes.items()},FP_order_disagreement_cases=fp_difference,complete_memory_provider_arguments_and_return_equal=True,whole_function_qualified=False,source_installed=False,c_match_credit=0)
 (O/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main(sys.argv[1:]or['v2','v3'])
