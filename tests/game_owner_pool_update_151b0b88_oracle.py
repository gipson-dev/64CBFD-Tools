"""Independent semantic screen; unspecified private bytes are not credited."""
from pathlib import Path
from dataclasses import dataclass,asdict
from functools import lru_cache
import itertools,json,struct,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_owner_pool_update_151b0b88_screen as recovery
p=recovery.OUT;f=recovery.FROZEN
ENTRY=0x151B0B88
RECORD,OWNER,MATRIX,MARK=0x30000,0x80000,0x50000,0x70000
STATE=RECORD+0x28
RNG,FLOAT,TRANSFORM,RELEASE,ALLOCATE,COPY,CLEAN=0x150ADA20,0x150ADA68,0x15143134,0x1513F680,0x1513D524,0x10022EC0,0x151B1918
POINTS,ALT,PALETTE,TICKS,TIME,INV=0x800AA12C,0x800AA1DC,0x800AB310,0x800BE9E4,0x800BE9A4,0x800BE9A8
COEF=0x800AA2E0
COUNTS={RNG:0,FLOAT:0,TRANSFORM:3,RELEASE:5,ALLOCATE:9,COPY:3,CLEAN:1}
REQ_DEFINED=tuple(i for i in range(88)if i not in(1,6,7)and i<70)
PAY_DEFINED=tuple(range(12,38))
u32=lambda n:n&0xffffffff
data=lambda m,a,n:bytes(m[a+i]for i in range(n))
f32=lambda x:floating(bits(x))
mul=lambda a,b:f32(a*b)
add=lambda a,b:f32(a+b)
child=lambda i:0x90000+i*0x200
output=lambda i:0xA0000+i*0x200

@dataclass(frozen=True)
class Case:
 seed:int=0;phase:int=0;route:int=0;mask:int=0;expires:int=0;accumulator:float=1.25;alternate:int=0;failure:int=0;mutation:int=0;lifetime:int=100

def cases():
 for seed in range(96):
  yield Case(seed=seed,phase=8*(seed&1),mask=(seed*137)&2047,expires=(seed*113)&2047,
    accumulator=(-1.,0.,1.,1.0001,2.25,5.5,12.5)[seed%7],alternate=seed&1,failure=seed%4,mutation=seed%16)
 for route,mask in itertools.product(range(1,5),(0,1,2047)):
  yield Case(seed=51,route=route,mask=mask)
 for slot in range(11):
  for mask,exp in ((1<<slot,0),(1<<slot,1<<slot),(2047,1<<slot)):
   yield Case(seed=17+slot,mask=mask,expires=exp,accumulator=4.,alternate=slot&1,mutation=15)
 for mask,failure,accumulator in itertools.product((0,2047),(0,1,3),(-0.,1.,1.000000119,16.)):
  yield Case(seed=71,mask=mask,expires=0,accumulator=accumulator,failure=failure)
 for lifetime,mutation in itertools.product((1,3,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1)):
  yield Case(seed=12,mask=2047,lifetime=lifetime,accumulator=1.,mutation=mutation)
 for mask in(0,1,1024,2047):yield Case(seed=0,mask=mask,accumulator=1.)

def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-4096,1024)}
 for at,n in ((RECORD,256),(OWNER,512),(MATRIX,4096),(MARK,4),(POINTS,176),(ALT,176),(PALETTE,256),(TICKS,4),(TIME,4),(INV,4),(COEF,16)):
  assert at+n<=STACK-4096 or at>=STACK+1024,('public/private overlap',hex(at),n)
  m.update({at+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for i in range(11):
  for base in(child(i),output(i)):
   m.update({base+j:(j*19+c.seed*7+i)&255 for j in range(512)})
  slot=STATE+12+i*12;put(m,slot,child(i)if c.mask>>i&1 else 0)
  put(m,slot+4,0 if c.expires>>i&1 else c.lifetime);put(m,slot+8,0xDEADBEEF)
  for j in range(3):put(m,child(i)+52+4*j,bits((i+j-c.seed)*.25))
 for base in(POINTS,ALT):
  for i in range(11):
   m[base+i*16]=(i*3+(2 if base==ALT else 1))%32
   for j in range(3):put(m,base+i*16+4+4*j,bits((i+j+c.seed-60)*.125))
 put(m,STATE,OWNER);m[STATE+4]=0x87;put(m,STATE+8,c.mask.bit_count());put(m,STATE+144,bits(c.accumulator));m[STATE+148]=c.seed%13
 put(m,OWNER,0 if c.route==1 else 0x12345678);m[OWNER+59]=0x86 if c.route==2 else 0x87
 put(m,OWNER+468,0 if c.route==3 else MATRIX);m[OWNER+116]=0xAF if c.route==4 else 0x20;m[OWNER+4]=54 if c.alternate else 1
 m[RECORD+12]=0xE1;m[RECORD+1]=0x83;put(m,RECORD+14,0x7FFF,2)
 for a,v in((TICKS,1),(TIME,bits(1.)),(INV,bits(.25)),(COEF,bits(307.)),(COEF+4,bits(.001)),(COEF+8,bits(-703.)),(COEF+12,bits(.001))):put(m,a,v)
 return m

class Service:
 def __init__(self,m,c):self.m,self.c=m,c;self.calls=[];self.rng=self.floats=self.allocations=0;self.outputs=set()
 def copy(self,args,perform):
  dest,src,n=args;assert n==40
  self.calls.append((COPY,(dest,'payload',n),bytes(self.m[src+i]for i in PAY_DEFINED)))
  if perform:
   values=data(self.m,src,n)
   for i,b in enumerate(values):self.m[dest+i]=b
 def invoke(self,t,args):
  m,c=self.m,self.c;observed=b'';normal=args
  if t==COPY:self.copy(args,True);return args[0]
  if t==ALLOCATE:
   a=args[0];observed=bytes(m[a+i]for i in REQ_DEFINED);normal=('request',*args[1:]);assert args[1:7]==(17,0,0,16,2,40)
  elif t==TRANSFORM:
   a,dest,matrix=args
   assert a in tuple(base+16*i+4 for base in(POINTS,ALT)for i in range(11)),hex(a)
   assert MATRIX<=matrix<MATRIX+4096
   normal=(a,'position'if STACK-4096<=dest<STACK+1024 else dest,matrix)
   observed=data(m,a,12)
  self.calls.append((t,normal,observed));ordinal=len(self.calls)
  put(m,MARK,u32(0x13579BDF+ordinal*0x10203+t))
  if t==RNG:
   answer=u32((c.seed+1)*0x9E3779B9+self.rng*0x10203047);self.rng+=1;return answer
  if t==FLOAT:
   answer=(.0,.5,1.,2.)[(c.seed+self.floats)%4];self.floats+=1;return bits(answer)
  if t==TRANSFORM:
   a,dest,matrix=args
   for j in range(3):put(m,dest+4*j,bits(add(floating(read(m,a+4*j)),(matrix-MATRIX)*.015625+j*.25)))
   if c.mutation&1:put(m,TICKS,3);put(m,INV,bits(.5));m[RECORD+12]^=1
   if c.mutation&8:m[OWNER+4]=54;m[OWNER+116]=0xAF
   return 0xBAADF00D
  if t==RELEASE:
   assert args[1:]==(16,27,0,16)
   if c.mutation&2:
    i=(args[0]-child(0))//512;put(m,STATE+12+i*12,child((i+1)%11))
   return 0xBAADF00D
  if t==ALLOCATE:
   i=self.allocations;self.allocations+=1
   if c.mutation&4:m[STATE+148]=(m[STATE+148]+1)%13;m[RECORD+1]^=3
   if c.failure==3 or c.failure==1 and i%2==0:return 0
   assert len(self.outputs)<11
   answer=output(len(self.outputs));self.outputs.add(answer);return answer
  if t==CLEAN:
   assert args==(RECORD,);put(m,STATE+8,0);put(m,STATE+144,bits(0.))
   for i in range(11):
    slot=STATE+12+i*12
    for off in(0,4,8):put(m,slot+off,0)
   return 0xBAADF00D
  raise AssertionError(hex(t))

def reference(initial,c):
 m=dict(initial);s=Service(m,c);request=STACK-800;packet=STACK-1000
 owner=read(m,STATE)
 if read(m,owner)==0 or m[STATE+4]!=m[owner+59]:put(m,RECORD+14,0xFFFF,2);return m,s
 if read(m,owner+468)==0 or m[owner+116]&15==15:
  if read(m,STATE+8)!=0:s.invoke(CLEAN,(RECORD,))
  return m,s
 free=[]
 for i in range(11):
  slot=STATE+12+12*i;current=read(m,slot);empty=True
  if current:
   values=data(m,current+52,12)
   for j,b in enumerate(values):m[current+64+j]=b
   owner=read(m,STATE);base=ALT if m[owner+4]==54 else POINTS;point=base+16*i
   matrix=read(m,owner+468)+m[point]*64
   s.invoke(TRANSFORM,(point+4,read(m,slot)+52,matrix))
   ticks=u32(read(m,slot+4)-read(m,TICKS));put(m,slot+4,ticks)
   if signed(ticks)<0:
    current=read(m,slot);velocity=current+272;put(m,velocity+4,bits(0.))
    put(m,velocity,bits(mul(add(floating(read(m,current+52)),-floating(read(m,current+64))),floating(read(m,INV)))))
    current=read(m,slot)
    put(m,velocity+8,bits(mul(add(floating(read(m,current+60)),-floating(read(m,current+72))),floating(read(m,INV)))))
    s.invoke(RELEASE,(read(m,slot),16,27,0,16));current=read(m,slot);put(m,current+88,read(m,current+88)|1)
    put(m,slot,0);put(m,STATE+8,u32(read(m,STATE+8)-1))
   else:empty=False
  if empty:
   put(m,slot+8,free[0]if free else 0);free.insert(0,slot)
 if not free:return m,s
 available=len(free);head=free[0];tail=free[-1]
 inc=mul(mul(mul(floating(s.invoke(FLOAT,())),floating(read(m,COEF))),floating(read(m,COEF+4))),floating(read(m,TIME)))
 put(m,STATE+144,bits(add(floating(read(m,STATE+144)),inc)))
 if not floating(read(m,STATE+144))>1.:return m,s
 put(m,tail+8,head);m[request]=m[PALETTE+m[STATE+148]];put(m,request+2,0x1001,2)
 put(m,request+4,s.invoke(RNG,())%51+52,2)
 for off in(8,12,20,24,40,44,48,64):put(m,request+off,0)
 for off in(16,17,18):m[request+off]=0
 m[request+19]=255
 for off in(52,56,60):put(m,request+off,bits(1.))
 m[packet+16]=m[packet+17]=0;m[packet+37]=m[STATE+148];m[packet+36]=s.invoke(RNG,())&1
 for off,v in((20,5.),(24,25.),(28,2.),(32,8.)):put(m,packet+off,bits(v))
 while True:
  selected=s.invoke(RNG,())%available
  for _ in range(selected):tail=head;head=read(m,head+8)
  index=(head-STATE-12)//12;point=POINTS+index*16
  m[request+69]=(s.invoke(RNG,())%101+100)&255;m[request+68]=(s.invoke(RNG,())%101+155)&255
  m[packet+18]=s.invoke(RNG,())%5+4;m[packet+19]=s.invoke(RNG,())%5+4
  put(m,packet+12,bits(mul(add(mul(floating(s.invoke(FLOAT,())),506.),floating(read(m,COEF+8))),floating(read(m,COEF+12)))))
  owner=read(m,STATE);s.invoke(TRANSFORM,(point+4,request+28,read(m,owner+468)+m[point]*64))
  values=data(m,request+28,12)
  for j,b in enumerate(values):m[request+40+j]=b
  s.invoke(RNG,());created=s.invoke(ALLOCATE,(request,17,0,0,16,2,40,m[RECORD+12],m[RECORD+1]));put(m,head,created)
  if created:
   s.invoke(COPY,(created+272,packet,40));put(m,head+4,s.invoke(RNG,())%31+20);head=read(m,head+8);available-=1
   put(m,tail+8,head);put(m,STATE+8,u32(read(m,STATE+8)+1))
  put(m,STATE+144,bits(add(floating(read(m,STATE+144)),-1.)))
  if not(floating(read(m,STATE+144))>1. and available!=0):break
 return m,s

@lru_cache(maxsize=1)
def copy_code():
 raw=(f/'conker/conker.us.bin').read_bytes()[0x22EC0:0x22EEC]
 return dict(zip(range(COPY,COPY+44,4),struct.unpack('>11I',raw)))

class Oracle(FactoryOracle):
 def __init__(self,words,initial,c):
  super().__init__(words,initial,c,entry=ENTRY,s={},arguments=(RECORD,),connected=dict(copy_code()))
  self.service=Service(self.memory,c);self.saved=tuple(self.r[16:24]);self.saved_fp=tuple(self.f[20:]);self.saved_s8=self.r[30]
 def record_call(self,t):
  assert t in COUNTS,hex(t);args=tuple(self.arguments(COUNTS[t]));self.pending=t,args
  if t==COPY:self.service.copy(args,False)
 def hook(self,t):
  target,args=self.pending;assert target==t and t!=COPY;answer=self.service.invoke(t,args)
  for i in range(max(4,COUNTS[t])):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=u32(answer)
  if t==FLOAT:self.f[0]=answer

def public(m,outputs):
 skip={base+272+i for base in outputs for i in(*range(12),38,39)}
 return{a:b for a,b in m.items()if not STACK-4096<=a<STACK+1024 and a not in skip}

def verify(words,c):
 initial=fixture(c);expected,s=reference(initial,c);machine=Oracle(words,initial,c).run()
 actual=machine.service
 assert actual.calls==s.calls,('calls',asdict(c),len(actual.calls),len(s.calls),next(((i,a,b)for i,(a,b)in enumerate(zip(actual.calls,s.calls))if a!=b),None))
 assert actual.outputs==s.outputs
 left,right=public(machine.memory,s.outputs),public(expected,s.outputs)
 assert left==right,('public',asdict(c),next(((hex(a),left.get(a),right.get(a))for a in left.keys()|right.keys()if left.get(a)!=right.get(a)),None))
 assert tuple(machine.r[16:24])==machine.saved and tuple(machine.f[20:])==machine.saved_fp and machine.r[30]==machine.saved_s8,('saved',c)
 return machine

def streams(labels):
 symbols={row[1]:row[2][1]for row in symbol_rows((f/'conker/build/conker.us.elf').read_bytes())}
 yield'original',list(struct.unpack('>385I',(p/'retail.bin').read_bytes()))
 for label in labels:yield label,bound_blob(*payload(p/(label+'.o'),'func_151B0B88'),symbols)

def main(labels=('byte-pre',)):
 reports=[]
 for label,words in streams(labels):
  seen=set();copy_seen=set();count=0
  for c in cases():
   machine=verify(words,c);seen.update(machine.visits&set(range(ENTRY,ENTRY+len(words)*4,4)));copy_seen.update(machine.visits&set(copy_code()));count+=1
  row=dict(stream=label,cases=count,target_words=len(words),target_coverage=len(seen),original_memcpy_coverage=len(copy_seen),defined_request_bytes=len(REQ_DEFINED),defined_payload_bytes=len(PAY_DEFINED),private_padding_uncredited=True,c_match_credit=0)
  reports.append(row);print(json.dumps(row),flush=True)
 (p/'semantic-screen.json').write_text(json.dumps(dict(passes=True,streams=reports),indent=2)+'\n')

 return dict(passes=True,streams=reports)
