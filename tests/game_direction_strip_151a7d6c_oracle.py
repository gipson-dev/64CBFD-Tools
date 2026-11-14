"""Bounded ordinary-RAM model for the private strip-renderer C candidate.

Providers are modeled. These checks do not qualify unrestricted aliases,
FCSR, hardware rendering, or production matching.
"""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,math,os,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ENTRY,ALLOC,CAMERA,TEXTURE,COMBINE,COLOR,MODE,GEOMETRY,PROJECT=(0x151a7d6c,0x151d5d60,0x15144b34,0x15142e24,0x15142b7c,0x15142c10,0x1513f4e4,0x15142fbc,0x15145548)
OWNER,POINTS,ALT,BUFFER,OUTPUT,CAM,TEX,GLOBAL,TABLE=(0x30000,0x31040,0x32040,0x70000,0x80000,0x90000,0x80090d70,0x800d2c9c,0x800a4ac8)
u32=lambda n:n&0xffffffff
half=lambda n:((n&65535)^32768)-32768
fb=lambda n:bits(rounded(n))
add=lambda a,b:floating(fb(a+b))
sub=lambda a,b:floating(fb(a-b))
mul=lambda a,b:floating(fb(a*b))
def vec(m,p):return tuple(read(m,p+i*4) for i in range(3))
def floats(m,p):return tuple(floating(v) for v in vec(m,p))
def store(m,p,vs):
 for i,v in enumerate(vs):put(m,p+4*i,fb(v))
def public(m):return {p:v for p,v in m.items() if not STACK-2048<=p<STACK+2304}
@dataclass(frozen=True)
class Case:
 flags:int=2
 success:int=1
 count:int=3
 shape:int=0
 mutation:int=0
 phase:int=0
 seed:int=0
 view:int=0x12340002
 width:int=0x40000000
 buffer:int=BUFFER
 output:int=OUTPUT
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2304)}
 for p,n in ((OWNER-32,288),(POINTS-96,512),(ALT-96,512),(BUFFER-32,544),(OUTPUT-32,544),(CAM,12),(TEX,32),(GLOBAL,4),(TABLE,32)):
  m.update({p+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 m[OWNER+0x1c]=c.flags;put(m,OWNER+0x12,c.count,2);put(m,OWNER+0x28,c.width);put(m,OWNER+0x64,POINTS);put(m,OWNER+0x7c,0x87654321)
 for p in (POINTS,ALT):
  for i in range(-3,12):
   point=(i*1.25,1.+i*.5+(i*i*.125 if c.shape==0 else 0.),-2.+i*.75) if c.shape!=2 else (2.,3.,4.)
   if p==ALT:point=tuple(add(v,.25*(j+1)) for j,v in enumerate(point))
   store(m,p+i*24,(11.,12.,13.));store(m,p+i*24+12,point)
 store(m,CAM,(4.,5.,6.) if c.shape!=1 else (0.,1.,-2.))
 for i in range(4):m[OWNER+0x24+i]=(3,129,254,65)[i]
 put(m,GLOBAL,0x01234567)
 for i in range(8):put(m,TABLE+i*4,0x10000000+i*0x01010101)
 return m
def effect(m,c,t):
 if c.mutation&1:
  if t==ALLOC:put(m,OWNER+0x12,2,2);m[OWNER+0x1c]=0
  if t==CAMERA:put(m,OWNER+0x64,ALT)
  if t==TEXTURE:put(m,OWNER+0x12,4,2)
  if t==COMBINE:
   for i in range(4):m[OWNER+0x24+i]^=0x55
  if t==MODE:put(m,OWNER+0x28,fb(-1.5))
  if t==GEOMETRY:put(m,OWNER+0x64,POINTS)
 if c.mutation&2:
  if t==TEXTURE:put(m,GLOBAL,0x55443322);put(m,TABLE+24,0x80200480);put(m,TABLE+28,0x01020804)
  if t==PROJECT:
   store(m,CAM,(3.,-2.,7.));put(m,OWNER+0x12,3,2);put(m,OWNER+0x28,fb(.75));put(m,OWNER+0x64,ALT)
def project(m,c,endpoint,delta,closest,parameter):
 a=floats(m,endpoint);d=floats(m,delta);store(m,closest,[add(x,mul(y,.25)) for x,y in zip(a,d)]);put(m,parameter,fb(.25))
 if c.mutation&2:store(m,delta,(.25,-.5,1.))
 effect(m,c,PROJECT)
def emit_helper(m,t,p):put(m,p,0xa0000000|(t&0xffffff));put(m,p+4,0x12345678);return p+8
def reference(initial,c):
 m=dict(initial);calls=[];observed=[];out=c.output;cur=c.buffer
 if not c.flags&2:return m,calls,observed,out
 calls.append((ALLOC,(OWNER+0x6c,u32(half(c.view)),0x87654321,'cursor',0)));effect(m,c,ALLOC)
 if not c.success:return m,calls,observed,out
 calls.append((CAMERA,(u32(half(c.view)),)));effect(m,c,CAMERA);last=half(half(read(m,OWNER+0x12,2))-1)
 calls.append((TEXTURE,(out,TEX,0,0,0,0,44,0,0,'sync',3)));effect(m,c,TEXTURE);out=emit_helper(m,TEXTURE,out)
 calls.append((COMBINE,(out,0x200005,0x1f0600)));effect(m,c,COMBINE);out=emit_helper(m,COMBINE,out)
 calls.append((COLOR,(out,*[m[OWNER+0x24+i] for i in range(4)],'sync')));effect(m,c,COLOR);out=emit_helper(m,COLOR,out)
 calls.append((MODE,(out,25,'sync')));effect(m,c,MODE);out=emit_helper(m,MODE,out)
 calls.append((GEOMETRY,(out,read(m,GLOBAL)|0x80000|0x2ca0,read(m,TABLE+28)|read(m,TABLE+24),'sync')));effect(m,c,GEOMETRY);out=emit_helper(m,GEOMETRY,out)
 base=read(m,OWNER+0x64);endpoint=base+last*24+12;d=[sub(x,y) for x,y in zip(floats(m,base+12),floats(m,endpoint))]
 # Provider locals live in a private reference area, excluded from observables.
 scratch=STACK-1000;store(m,scratch,d)
 calls.append((PROJECT,(endpoint,'delta',CAM,'closest','parameter')));observed.append((vec(m,endpoint),vec(m,scratch),vec(m,CAM)));project(m,c,endpoint,scratch,scratch+16,scratch+32)
 d=floats(m,scratch);ray=[sub(x,y) for x,y in zip(floats(m,CAM),floats(m,scratch+16))]
 nx=sub(mul(d[1],ray[2]),mul(ray[1],d[2]));ny=sub(mul(d[2],ray[0]),mul(ray[2],d[0]));nz=sub(mul(d[0],ray[1]),mul(ray[0],d[1]));mag=add(add(mul(nx,nx),mul(ny,ny)),mul(nz,nz))
 if mag==0.:offset=(0.,0.,0.)
 else:
  scale=floating(fb(floating(read(m,OWNER+0x28))/floating(fb(math.sqrt(mag)))));offset=tuple(mul(v,scale) for v in (nx,ny,nz))
 first,next=0,1
 while next<half(read(m,OWNER+0x12,2)):
  base=read(m,OWNER+0x64);left=base+first*24+12;right=base+next*24+12
  for point,sign,u,v in ((left,1,0,0),(left,-1,960,0),(right,-1,960,960),(right,1,0,960)):
   for i in range(3):
    value=add(floating(read(m,point+4*i)),offset[i]) if sign==1 else sub(floating(read(m,point+4*i)),offset[i]);put(m,cur+2*i,math.trunc(value),2)
   put(m,cur+8,u,2);put(m,cur+10,v,2)
   for i in range(4):m[cur+12+i]=255
   put(m,cur+6,0,2);cur+=16
  for w0,w1 in ((0x01004008,cur-64),(0x05000204,0),(0x05000406,0)):put(m,out,w0);put(m,out+4,w1);out+=8
  first=half(first+1);next=half(next+1)
 return m,calls,observed,out
class Oracle(FactoryOracle):
 def __init__(self,words,m,c,entry=ENTRY,connected=None):
  self.observed=[];self.roles={};self.actual=();super().__init__(words,m,c,entry=entry,arguments=(c.output,OWNER,c.view),connected=connected)
 def execute(self,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in (0,1,2,3,4,6,13,50):
   a,b=floating(self.f[fs]),floating(self.f[ft])
   if fn==50:self.condition=a==b
   elif fn==6:self.f[fd]=self.f[fs]
   elif fn==13:self.f[fd]=u32(math.trunc(a))
   else:self.f[fd]=fb(a+b if fn==0 else a-b if fn==1 else a*b if fn==2 else a/b if fn==3 else math.sqrt(a))
   self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  n={ENTRY:3,ALLOC:5,CAMERA:1,TEXTURE:11,COMBINE:3,COLOR:6,MODE:3,GEOMETRY:4,PROJECT:5};assert t in n,hex(t);a=list(self.arguments(n[t]));self.actual=tuple(a)
  positions={ALLOC:{3:'cursor'},TEXTURE:{9:'sync'},COLOR:{5:'sync'},MODE:{2:'sync'},GEOMETRY:{3:'sync'},PROJECT:{1:'delta',3:'closest',4:'parameter'}}
  for i,role in positions.get(t,{}).items():self.roles[role]=a[i];a[i]=role
  self.calls.append((t,tuple(a)));self.events.append(('CALL',t,tuple(a)))
  if t==PROJECT:self.observed.append((vec(self.memory,a[0]),vec(self.memory,self.actual[1]),vec(self.memory,a[2])))
 def hook(self,t):
  a=self.actual;c=self.case;m=self.memory;value=0
  if t==ALLOC:put(m,a[3],c.buffer if c.success else 0);effect(m,c,t)
  elif t==CAMERA:value=CAM;effect(m,c,t)
  elif t==PROJECT:project(m,c,*a[:2],a[3],a[4])
  else:
   effect(m,c,t);value=emit_helper(m,t,a[0])
   if t!=COMBINE:m[self.roles['sync']]=(m[self.roles['sync']]+1)&255
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=u32(0xa5000000+reg)
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def cases():
 for i,(flags,success,count,shape,mutation) in enumerate(itertools.product((0,2,3),(0,1),(-1,0,1,2,5),(0,1,2),(0,1,2,3))):yield Case(flags=flags,success=success,count=count,shape=shape,mutation=mutation,phase=(i&1)*8,seed=i%3)
 for view,width in itertools.product((0,1,0x12348000,0x8765ffff,0x7fff),(0,0x80000000,fb(-2.75))):yield Case(view=view,width=width)
def run():
 r=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();o=r/'conker/build/game-direction-strip-151a7d6c-screen'
 name='func_151A7D6C';assembly=(r/'conker/asm/1D4E00.s').read_text();a=assembly.index('glabel '+name+'\n');z=assembly.index('endlabel '+name,a)+len('endlabel '+name)
 (o/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+assembly[a:z]+'\n.size '+name+',.-'+name+'\n')
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'retail.o'),str(o/'retail.s')],cwd=r/'conker',capture_output=True,check=True)
 sy={v[1]:v[2][1] for v in symbol_rows((r/'conker/build/conker.us.elf').read_bytes())};programs=[bound_blob(*payload(o/f,name),sy) for f in ('retail.o','selected.o')];seen=set();count=0
 assert tuple(programs[0])==struct.unpack_from('>373I',(r/'conker/conker.us.bin').read_bytes(),0x1d521c)
 for c in cases():
  initial=fixture(c);expected,calls,obs,value=reference(initial,c)
  for p in programs:
   machine=Oracle(p,initial,c)
   try:machine.run()
   except Exception as error:raise AssertionError((c,programs.index(p),machine.calls,hex(machine.r[29]),machine.trace[-12:])) from error
   seen.update(machine.visits)
   assert (machine.calls,machine.observed,machine.r[2])==(calls,obs,value),(c,machine.calls,calls,machine.observed,obs,machine.r[2],value)
   assert public(machine.memory)==public(expected),(c,[(hex(p),v,expected.get(p)) for p,v in public(machine.memory).items() if v!=expected.get(p)][:12])
  count+=1
 aliases=0
 for buffer,phase,mutation in itertools.product((OUTPUT,STACK+0x300),(0,8),(0,3)):
  c=Case(buffer=buffer,phase=phase,mutation=mutation);initial=fixture(c);expected,calls,obs,value=reference(initial,c)
  for p in programs:
   machine=Oracle(p,initial,c);machine.run();assert (public(machine.memory),machine.calls,machine.observed,machine.r[2])==(public(expected),calls,obs,value),c
   assert bytes(machine.memory[buffer+i] for i in range(192))==bytes(expected[buffer+i] for i in range(192)),c
  aliases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();windows=((0x151677d8,0x15167800),(0x15167894,0x151678b8));callers=0
 assert struct.unpack_from('>I',rom,0x230894)[0]==ENTRY and 0x8008b4a8+45*52+8==0x8008bdd4
 for which,view,mutation,success in itertools.product(range(2),(2,0x1234ffff),(0,3),(0,1)):
  c=Case(view=half(view),mutation=mutation,success=success);initial=fixture(c);slot=0xa0000;initial.update({slot+i:165 for i in range(4)});put(initial,0x8008bdd4,ENTRY)
  expected,calls,obs,value=reference(initial,c);put(expected,slot,read(initial,OWNER+8));pc,end=windows[which];word_count=(end-pc)//4;window=struct.unpack_from('>'+str(word_count)+'I',rom,pc-0x15000000+0x2d4b0)
  for p in programs:
   code=dict(zip(range(ENTRY,ENTRY+4*len(p),4),p));code[end]=0;machine=Oracle(window,initial,c,entry=pc,connected=code);machine.r[16]=OWNER;machine.r[17]=slot;machine.r[19]=c.output;machine.r[20]=0x8008bdcc;machine.r[22]=u32(view);machine.code=WindowCode(machine.code,machine);machine.code.ends=(end,)
   try:machine.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller boundary')
   assert (public(machine.memory),machine.calls,machine.observed,machine.r[2])==(public(expected),[(ENTRY,(c.output,OWNER,u32(c.view)))]+calls,obs,value),(which,c)
   assert machine.r[29]==STACK+c.phase
  callers+=1
 report=dict(cases=count,words=373,observed_words=len(seen),streams=2,caller_windows=2,caller_cases=callers,guest_alias_cases=aliases,providers_modeled=True,private_aliases_not_yet_qualified=True);(o/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':run()
