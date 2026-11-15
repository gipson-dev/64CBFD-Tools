"""Independent byte-addressed renderer model and instruction-level private screen."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,math,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_perpendicular_offset_1519ef90_oracle import sqrt_word
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_side_ring_renderer_1519fe6c_recovery as source
R,O,ENTRY=source.ROOT,source.OUT,source.ENTRY
E,P,A,ALT,PALT,V,OUT=0x30000,0x50000,0x60000,0x70000,0x71000,0x80000,0x90000
BACKEND,TEXTURE,GEOMETRY,ENV,PRIM,COMBINE,MODE=0x151D5D60,0x15142E24,0x15142B7C,0x15142C10,0x15142CF0,0x1513F4E4,0x15142FBC
COUNTS={BACKEND:5,TEXTURE:11,GEOMETRY:3,ENV:6,PRIM:8,COMBINE:3,MODE:4}
SYNC={TEXTURE:9,ENV:5,PRIM:7,COMBINE:2,MODE:3}
u32=lambda n:n&0xFFFFFFFF
half=lambda n:((n&65535)^32768)-32768
byte=lambda n:((n&255)^128)-128
def syms():return {x[1]:x[2][1] for x in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())}
S=syms()
@dataclass(frozen=True)
class Case:
 count:int=3
 cap:int=5
 head:int=0
 tail:int=3
 flags:int=0
 kind:int=0
 mode:int=6
 fade1:int=2
 fade2:int=2
 pattern:int=0
 texture:int=32760
 extent:int=32
 mutation:int=0
 view:int=0
 success:int=1
 phase:int=0
 seed:int=0
def public(m):return {p:v for p,v in m.items() if not STACK-2048<=p<STACK+512}
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xA5+c.seed)&255 for i in range(-2048,512)}
 for base,n in ((E,160),(P,80),(PALT,80),(V,2048),(OUT,2048)):
  m.update({base+i:(i*13+c.seed+0x5A)&255 for i in range(n)})
 for base in (A,ALT):
  for i in range(-1,c.cap+1):
   p=base+36*i
   for k in range(36):m[p+k]=(i*17+k*3+0xA5)&255
   xyz=(3.25*i+1.,2.*i-5.,.5*i) if c.pattern==0 else (0.,0.,0.) if c.pattern==1 else (.00001*i,.000001*i,0.) if c.pattern==2 else (0.,2.*i-5.,.5*i)
   # In-record order is x,z,height; positions passed to vertex fields are x,height,z.
   for off,value in zip((0,4,8,12),(*xyz,1.+i*.125)):put(m,p+off,bits(value+(10. if base==ALT and off in(0,4,8) else 0.)))
   for off,value in ((16,(-32768,-1,0,123,32767)[i%5]),(20,(0,255,128,-1,32767)[i%5]),(22,i*32+7)):put(m,p+off,value,2)
 put(m,E+0x94,A);put(m,E+0x98,P);put(m,E+0x1E,c.flags,2);put(m,E+32,c.mode)
 for off,value in ((0x25,c.cap),(0x2C,c.count),(0x2D,c.head),(0x2E,c.tail),(0x31,5)):m[E+off]=value&255
 for i,value in enumerate((1.25,2.5,-3.75)):put(m,E+16+4*i,bits(value))
 for base in (P,PALT):
  m[base+4]=c.kind
  for off,value in ((0x2A,10),(0x2B,20),(0x2C,30),(0x40,c.fade1),(0x41,37),(0x42,c.fade2),(0x43,83)):m[base+off]=value&255
  for off,value in ((0x46,c.texture),(0x4A,c.extent)):put(m,base+off,value,2)
  put(m,base+0x38,bits(1.25))
 put(m,S['D_800D2C9C'],0x10001);put(m,S['D_800A8D00'],0x38D1B717)
 return m

def mutate(m,c,t):
 if t==BACKEND and c.mutation&1:put(m,E+0x94,ALT);put(m,E+0x98,PALT)
 if t==TEXTURE:
  if c.mutation&2:put(m,E+0x94,ALT);put(m,E+0x98,PALT)
  if c.mutation&4:m[P+0x2A]=90;m[P+0x2B]=80;m[P+0x2C]=70;put(m,E+0x1E,2,2);put(m,E+32,7)
 if t==COMBINE and c.mutation&8:put(m,S['D_800D2C9C'],0x789ABCD)
 if t==MODE and c.mutation&16:m[E+0x2D]=1;m[E+0x2E]=2;put(m,P+0x46,-1025,2);put(m,P+0x4A,-32768,2)

def service(m,c,t,args,ordinal,cursor_home=None,sync_home=None):
 if t==BACKEND:
  if cursor_home is not None:put(m,cursor_home,V if c.success else 0)
  result=0
 else:
  put(m,args[0],0xBA000000|ordinal);put(m,args[0]+4,t)
  if sync_home is not None:m[sync_home]=0
  result=u32(args[0]+8)
 mutate(m,c,t);return result

def reference(initial,c):
 m=dict(initial);calls=[];out=OUT;cursor=V
 get=lambda p,n=4:read(m,p,n)
 h=lambda p:half(get(p,2))
 b=lambda p:byte(get(p,1))
 op=lambda x,y,k:fp(x,y,k,'left')
 def call(t,args):
  nonlocal out
  calls.append((t,tuple(args)));out=service(m,c,t,args,len(calls)-1);return out
 if b(E+0x2C)<2:return m,OUT,calls,0
 call(BACKEND,(E+0x84,u32(half(c.view)),get(E+0x25,1)*48+0x120,'cursor',0))
 if not c.success:return m,OUT,calls,0
 out=OUT;p=get(E+0x98);records=get(E+0x94)
 if get(p+4,1)&2:
  remaining=get(p+0x40,1);factor=0;i=b(E+0x2D);n=0
  while True:
   put(m,records+i*36+20,factor,2);factor=(factor+get(p+0x41,1))&255;i+=1
   if i==get(E+0x25,1):i=0
   remaining=half(remaining-1);n+=1;assert n<=c.cap+1
   if remaining==0 or i==b(E+0x2E):break
 if get(p+4,1)&4:
  i=b(E+0x2E)-1;factor=0;remaining=get(p+0x42,1);n=0
  if i<0:i=get(E+0x25,1)-1
  while True:
   at=records+i*36+20;put(m,at,(h(at)*factor)>>8,2);factor=(factor+get(p+0x43,1))&255;i-=1
   if i<0:i=get(E+0x25,1)-1
   remaining=half(remaining-1);n+=1;assert n<=c.cap+1
   if remaining==0 or i==b(E+0x2E):break
 call(TEXTURE,(out,S['D_80090E0C'],0,0,0,0,57,0,0,'sync',62))
 call(GEOMETRY,(out,1,0x160600))
 call(ENV,(out,get(p+42,1),get(p+43,1),get(p+44,1),255,'sync'))
 call(PRIM,(out,0,0,255,255,255,0,'sync'))
 call(COMBINE,(out,7,'sync'));call(MODE,(out,get(S['D_800D2C9C'])|0x82CA0,0x5049D8,'sync'))
 def prev(i):return i-1 if i-1>=0 else get(E+0x25,1)-1
 def position(at):return [get(at),get(at+8),get(at+4)]
 def alpha(at):return(h(at+20)*h(at+16))>>8
 i=prev(b(E+0x2E))
 if get(E+30,2)&2:previous=[get(E+16+4*k) for k in range(3)];old_width=get(p+56);old_alpha=alpha(records+i*36);old_tag=h(records+i*36+22)
 else:
  at=records+i*36;previous=position(at);old_width=get(at+12);old_alpha=alpha(at);old_tag=h(at+22);i=prev(i)
 at=records+i*36;current=position(at);current_width=get(at+12);new_alpha=alpha(at);new_tag=h(at+22)
 dx=op(current[0],previous[0],'sub');dz=op(current[2],previous[2],'sub')
 def inverse():return op(bits(1.),sqrt_word(op(op(dx,dx,'mul'),op(dz,dz,'mul'),'add')),'div')
 inv=inverse() if floating(get(S['D_800A8D00']))<abs(floating(dx)) or floating(get(S['D_800A8D00']))<abs(floating(dz)) else bits(1.)
 texture=[h(p+70),0,half(h(p+70)+h(p+74))]
 if texture[2]<texture[0]:
  value=h(p+70);texture[0]=value-(abs(value)//1024)*(-1024 if value<0 else 1024);put(m,p+70,texture[0],2);texture[2]=half(h(p+70)+h(p+74))
 texture[1]=half((texture[2]+texture[0])>>1);high,low=(0,2) if get(E+32)==6 else (2,0)
 def trunc(value):
  v=floating(value);return u32(math.trunc(v)) if math.isfinite(v) and -2147483648<=v<2147483648 else 0x80000000
 def vertices(pos,width,a,tag):
  nonlocal cursor
  x=op(op(dz^0x80000000,inv,'mul'),width,'mul');z=op(op(dx,inv,'mul'),width,'mul')
  for coords,t,opacity in (([op(pos[0],x,'add'),pos[1],op(pos[2],z,'add')],texture[high],0),(pos,texture[1],a),([op(pos[0],x,'sub'),pos[1],op(pos[2],z,'sub')],texture[low],0)):
   for k,value in enumerate(coords):put(m,cursor+2*k,trunc(value),2)
   put(m,cursor+8,tag,2);put(m,cursor+10,t,2)
   for k,value in enumerate((255,255,255,opacity)):m[cursor+12+k]=value&255
   put(m,cursor+6,0,2);cursor+=16
 vertices(previous,old_width,old_alpha,old_tag);segments=0
 while True:
  vertices(current,current_width,new_alpha,new_tag)
  for w0,w1 in ((0x0100600C,cursor-96),(0x05000608,0),(0x05000802,0),(0x0502080A,0),(0x05020A04,0)):
   put(m,out,w0);put(m,out+4,w1);out+=8
  previous_index=i;i=prev(i);segments+=1;assert segments<=c.cap+1
  if previous_index!=b(E+0x2D):
   previous=current;at=records+i*36;current=position(at);current_width=get(at+12);new_alpha=alpha(at);new_tag=h(at+22)
   dx=op(current[0],previous[0],'sub');dz=op(current[2],previous[2],'sub')
   inv=bits(1.) if floating(current[0])==floating(previous[0]) and floating(dz)==0. else inverse()
  if previous_index==b(E+0x2D):break
 return m,out,calls,segments

class Machine(FactoryOracle):
 def __init__(self,w,m,c,connected=None,entry=ENTRY,args=None):
  self.c=c;self.fp_ops=[];self.raw_calls=[];self.private_homes=[]
  super().__init__(w,m,BaseCase(phase=c.phase),entry=entry,s={},arguments=(E,OUT,c.view) if args is None else args,connected=connected)
 def execute(self,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==0 and fn==3:
   value=self.r[w>>16&31];self.r[w>>11&31]=u32(((value^0x80000000)-0x80000000)>>(w>>6&31));return
  if op==17 and fmt==16 and fn in (0,1,2,3,4,5,6,7,13,50,60):
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31;x,y=self.f[fs],self.f[ft]
   if fn<4:
    k=('add','sub','mul','div')[fn];self.fp_ops.append((k,x,y));self.f[fd]=fp(x,y,k,'left')
   elif fn==4:self.fp_ops.append(('sqrt',x));self.f[fd]=sqrt_word(x)
   elif fn==5:self.fp_ops.append(('abs',x));self.f[fd]=x&0x7FFFFFFF
   elif fn==6:self.f[fd]=x
   elif fn==7:self.fp_ops.append(('neg',x));self.f[fd]=x^0x80000000
   elif fn==13:
    value=floating(x);self.fp_ops.append(('trunc',x));self.f[fd]=u32(math.trunc(value)) if math.isfinite(value) and -2147483648<=value<2147483648 else 0x80000000
   else:self.fp_ops.append(('eq' if fn==50 else 'lt',x,y));self.condition=(floating(x)==floating(y)) if fn==50 else (floating(x)<floating(y))
   return
  return super().execute(w)
 def record_call(self,t):
  a=list(self.arguments(COUNTS[t]));raw=a[:]
  if t==BACKEND:self.cursor_home=a[3];self.private_homes.append(('cursor',a[3]-self.target_home));a[3]='cursor'
  if t in SYNC:
   self.sync_home=a[SYNC[t]];self.private_homes.append(('sync',self.sync_home-self.target_home));assert self.get(self.sync_home,1)==(1 if t==TEXTURE else 0);a[SYNC[t]]='sync'
  self.calls.append((t,tuple(a)));self.raw_calls.append((t,tuple(raw)))
 def hook(self,t):
  value=service(self.memory,self.c,t,self.raw_calls[-1][1],len(self.calls)-1,self.cursor_home if t==BACKEND else None,self.sync_home if t in SYNC else None)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=value

def programs():
 return dict(retail=list(struct.unpack_from('>632I',(R/'conker/conker.us.bin').read_bytes(),0x1CD31C)),
             previous=bound_blob(*payload(O/'previous.o','func_1519FE6C'),{**S,'.rodata':S['D_800A8CF4']}),
             candidate=bound_blob(*payload(O/'qualified.o','func_1519FE6C'),{**S,'.rodata':S['D_800A8CF4']}))

def cases():
 for kind,fade1,fade2 in itertools.product((2,4,6),(0,1,255),(0,1,255)):
  yield Case(kind=kind,fade1=fade1,fade2=fade2)
 for texture,extent,mode in itertools.product((-32768,-1025,-1,0,1023,32767),(-32768,-32,-1,0,1,32,32767),(6,7,0x106)):
  yield Case(texture=texture,extent=extent,mode=mode)
 for count,success,view in itertools.product((-128,-1,0,1,2,127),(0,1),(0,0xFFFF,0x12340002)):
  yield Case(count=count,success=success,view=view)
 for cap,flags,kind,mode,fade1,fade2,pattern,tex,extent in itertools.product((2,5),(0,2),(0,2,4,6),(6,7,0x106),(0,1,255),(0,2),(0,1,2,3),(32760,-1025,0),(32,-32768)):
  if (cap+flags+kind+mode+fade1+fade2+pattern+tex+extent)%41:continue
  yield Case(cap=cap,tail=cap-1,count=cap,flags=flags,kind=kind,mode=mode,fade1=fade1,fade2=fade2,pattern=pattern,texture=tex,extent=extent)
 for mutation,head,tail,flags,phase in itertools.product((1,2,4,8,16,31),(0,1),(0,2),(0,2),(0,8)):
  yield Case(mutation=mutation,head=head,tail=tail,flags=flags,phase=phase)

def check(w,c,label):
 m=fixture(c);expected,result,calls,segments=reference(m,c);q=Machine(w,m,c).run()
 got,want=(public(q.memory),q.r[2],q.calls),(public(expected),result,calls)
 if got!=want:
  before,after=public(expected),public(q.memory)
  raise AssertionError((label,c,'bytes',[(hex(p),before.get(p),after.get(p)) for p in before if before.get(p)!=after.get(p)][:8],'result',q.r[2],result,'calls',q.calls,calls))
 return q,segments

def controls(retail):
 result=[]
 for name,offset,change,c in (
  ('signed-count',0x34,lambda w:w^(4<<26),Case(count=128)),
  ('allocation-size',0x64,lambda w:w+16,Case()),
  ('zero-fade-entry',0xE8,lambda w:w^(1<<26),Case(kind=2,fade1=0)),
  ('signed-texture-remainder',0x460,lambda w:w^0x200,Case(texture=-1025,extent=-32)),
  ('record-height-component',0x384,lambda w:w-4,Case()),
  ('last-triangle-index',0x8BC,lambda w:w^2,Case())):
  wrong=retail[:];wrong[offset//4]=change(wrong[offset//4])
  try:check(wrong,c,'control-'+name)
  except AssertionError as error:
   reason=str(error);assert not any(x in reason for x in ('unsupported','execution limit','unmapped instruction')),('invalid control',name,reason[:200])
   result.append(name)
  else:raise AssertionError(('ineffective semantic control',name))
 return result

def main():
 p=programs();coverage={k:set() for k in p};count=0;fp_differences=0;homes={k:set() for k in p}
 for c in cases():
  machines={}
  for label,w in p.items():
   q,n=check(w,c,label);coverage[label]|=q.visits;homes[label]|=set(q.private_homes);machines[label]=q
  fp_differences+=machines['retail'].fp_ops!=machines['candidate'].fp_ops;count+=1
 report=dict(cases_per_stream=count,streams=len(p),visited_words={k:len(v) for k,v in coverage.items()},public_snapshots_and_semantic_provider_arguments_equal=True,private_provider_homes={k:sorted(v) for k,v in homes.items()},FP_order_disagreement_cases=fp_differences,effective_controls=controls(p['retail']),normalization_proved=False,c_match_credit=0)
 assert homes['candidate']==homes['retail']=={('cursor',-4),('sync',-95)},homes
 assert homes['previous']!=homes['retail'],'exposed-home positive control lost'
 (O/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
