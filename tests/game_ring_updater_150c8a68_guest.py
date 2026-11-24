"""Independent finite ring-update model, mutable callbacks and instruction faults."""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,math,struct
from tools.experiments import game_ring_updater_150c8a68_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
ENTRY=0x150c8a68;RNG=0x150ada20;TRIG=0x151423d8;RELEASE=0x1516972c
OWNER=0x30000;PLAYERS=0x70000;MARK=0x90000;SIZE=256
DT=0x800be9a4;TICKS=0x800be9e4;PLAYER_INDEX=0x80082fa4;PLAYER_BASE=0x800dbff0
EMIT_TABLE=0x80088858;FINISH_TABLE=0x80088860;UPDATE_TABLE=0x80088864
EMIT=0x15f00000;UPDATE=0x15f00040;FINISH=0x15f00080
LITERALS=(0x800a052c,0x800a0530,0x800a0534);CONSTANTS=(0x40c90fdb,0x4b263bd7,0x3f360b61)
bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xffffffff
signed=lambda v:((v&0xffffffff)^0x80000000)-0x80000000
half=lambda v:((v&65535)^32768)-32768
byte=lambda v:((v&255)^128)-128
@dataclass(frozen=True)
class Case:
 flags:int=1
 life:int=30
 ticks:int=1
 fade_start:int=20
 fade_end:int=10
 initial:int=40
 emission:int=0
 update:int=0
 finish:int=0
 finish_result:int=1
 remainder:int=bits(2.25)
 radius:int=bits(2.)
 growth:int=bits(.25)
 rate:int=bits(0.)
 step:int=bits(.5)
 heading:int=bits(90.)
 x:int=bits(1.)
 z:int=bits(-2.)
 mode:int=0
 phase:int=0
 fcsr:int=0
 seed:int=0
 rng:tuple=(0xffffffff,0,1,80,81,0x80000000)

def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-1024<=a<STACK+c.phase+2048}
def fixture(c):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,2048)}
 for base,n in((OWNER-16,SIZE+32),(PLAYERS-16,2*0x9a0+32),(MARK,32)):
  m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for at,v in[(0x10,c.x),(0x14,bits(3.)),(0x18,c.z),(0x20,c.growth),(0x24,3),(0x2c,bits(.125)),(0x34,bits(.25)),(0x38,c.rate),(0x40,bits(7.)),(0x44,c.radius),(0x48,bits(.1)),(0x50,c.remainder)]:put(m,OWNER+at,v)
 for at,v in[(0x28,c.life),(0x2a,c.fade_start),(0x30,c.fade_end),(0x4c,c.initial)]:put(m,OWNER+at,v,2)
 for at,v in[(0x1c,c.flags),(0x1d,c.finish),(0x3c,c.emission),(0x3d,c.update)]:put(m,OWNER+at,v,1)
 for at,v in[(DT,c.step),(TICKS,c.ticks),(PLAYER_INDEX,0),(PLAYER_BASE,PLAYERS),(EMIT_TABLE,EMIT),(UPDATE_TABLE,UPDATE),(FINISH_TABLE,FINISH),*zip(LITERALS,CONSTANTS)]:put(m,at,v)
 put(m,PLAYERS+0x380,c.heading);put(m,PLAYERS+0x9a0+0x380,bits(-45.));return m

def effect(m,c,t,n,args):
 if t==RNG:
  if c.mode&1:put(m,PLAYER_INDEX,1);put(m,OWNER+0x44,bits(.25));put(m,OWNER+0x10,bits(5.));put(m,DT,bits(-.25))
  return c.rng[(n-1)%len(c.rng)]
 if t==TRIG:
  if c.mode&2:put(m,OWNER+0x44,bits(2.5));put(m,OWNER+(0x10 if n&1 else 0x18),bits(.5 if n&1 else -.25))
  return bits(((n%7)-3)*.125)
 if t==EMIT:
  if c.mode&4:put(m,OWNER+0x50,bits(1.5));put(m,OWNER+0x3d,255,1);put(m,OWNER+0x1d,0,1)
  put(m,MARK+4,read(m,MARK+4)+1);return 0x8bad0001
 if t==UPDATE:
  if c.mode&8:put(m,OWNER+0x1d,255,1);put(m,OWNER+0x44,bits(9.))
  put(m,MARK+8,0x13572468);return 0x8bad0002
 if t==FINISH:
  put(m,MARK+12,0x24681357);return 0 if c.mode&16 else c.finish_result
 assert t==RELEASE,hex(t);put(m,MARK+16,OWNER);return 0x8bad0003

def snapshot(m):return data(m,OWNER,SIZE),data(m,MARK,32),read(m,DT),read(m,PLAYER_INDEX)
def reference(initial,c):
 m=dict(initial);calls=[];obs=[];counts={};fcsr=c.fcsr;point=STACK+c.phase-36
 def calc(a,b,fn):
  nonlocal fcsr
  value,flags=arithmetic(a,b,fn,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return value
 def compare(a,b):
  nonlocal fcsr
  fcsr&=~0x3f000;return floating(a)<floating(b)
 def call(t,args):
  args=tuple(map(u32,args));calls.append((t,args));counts[t]=counts.get(t,0)+1;obs.append((snapshot(m),data(m,point,12)if t==EMIT else b'',fcsr));return effect(m,c,t,counts[t],args)
 expired=False
 if m[OWNER+0x1c]&1:
  put(m,OWNER+0x28,half(read(m,OWNER+0x28,2))-signed(read(m,TICKS)),2);expired=half(read(m,OWNER+0x28,2))<0
 if not expired:
  previous=read(m,OWNER+0x44);put(m,OWNER+0x44,calc(previous,calc(read(m,OWNER+0x20),read(m,DT),2),0));life=half(read(m,OWNER+0x28,2))
  if half(read(m,OWNER+0x2a,2))<life:
   elapsed=half(half(read(m,OWNER+0x4c,2))-life);fcsr&=~0x3f000;put(m,OWNER+0x40,calc(bits(float(elapsed)),read(m,OWNER+0x2c),2))
  if life<half(read(m,OWNER+0x30,2)):fcsr&=~0x3f000;put(m,OWNER+0x40,calc(bits(float(life)),read(m,OWNER+0x34),2))
  if byte(m[OWNER+0x3c])!=-1:
   rate=calc(read(m,OWNER+0x38),read(m,DT),2);circ=calc(CONSTANTS[0],read(m,OWNER+0x44),2);put(m,OWNER+0x50,calc(read(m,OWNER+0x50),calc(rate,circ,2),0));iterations=0
   while compare(bits(1.),read(m,OWNER+0x50)):
    head=calc(read(m,read(m,PLAYER_BASE)+signed(read(m,PLAYER_INDEX))*0x9a0+0x380),CONSTANTS[2],2);x=floating(head);heading=math.trunc(x);assert -2147483648<=heading<=2147483647;fcsr=(fcsr&~0x3f000)|(0x1004 if x!=heading else 0)
    angle=(call(RNG,())%81+heading-40)&255;sine=call(TRIG,((angle-64)&255,));cosine=call(TRIG,(angle,))
    put(m,point,calc(read(m,OWNER+0x10),calc(sine,read(m,OWNER+0x44),2),0));put(m,point+4,read(m,OWNER+0x14));put(m,point+8,calc(read(m,OWNER+0x18),calc(cosine,read(m,OWNER+0x44),2),0))
    x2=calc(read(m,point),read(m,point),2);z2=calc(read(m,point+8),read(m,point+8),2);distance=calc(x2,z2,0)
    if compare(distance,CONSTANTS[1]):call(read(m,EMIT_TABLE+byte(m[OWNER+0x3c])*4),(OWNER,point,angle,sine,cosine))
    put(m,OWNER+0x50,calc(read(m,OWNER+0x50),bits(1.),1));iterations+=1;assert iterations<16
  if byte(m[OWNER+0x3d])!=-1:call(read(m,UPDATE_TABLE+byte(m[OWNER+0x3d])*4),(OWNER,previous))
  if byte(m[OWNER+0x1d])!=-1 and call(read(m,FINISH_TABLE+byte(m[OWNER+0x1d])*4),(OWNER,))==0:expired=True
 if expired:call(RELEASE,(OWNER,))
 return m,calls,obs,fcsr

class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=None,memory=None,arguments=None,connected=None):
  self.c=c;self.counts={};self.observations=[];self.fcsr=c.fcsr
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(OWNER,)if arguments is None else arguments,connected=connected);self.initial=dict(self.memory);self.before_f=self.f[:]
 def get(self,a,n):
  if getattr(self,'recording',False)and self.own_instruction:assert all(a+i in self.memory for i in range(n)),('Unmapped read',hex(a),n)
  return super().get(a,n)
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2):self.f[fd],flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  elif op==17 and fmt==20 and fn==32:self.f[fd]=bits(float(signed(self.f[fs])));self.fcsr&=~0x3f000
  elif op==17 and fmt==16 and fn==13:
   x=floating(self.f[fs]);n=math.trunc(x);assert -2147483648<=n<=2147483647;self.f[fd]=u32(n);self.fcsr=(self.fcsr&~0x3f000)|(0x1004 if x!=n else 0)
  elif op==17 and fmt==16 and fn==60:self.condition=floating(self.f[fs])<floating(self.f[rt]);self.fcsr&=~0x3f000
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  assert t in(ENTRY,RNG,TRIG,RELEASE,EMIT,UPDATE,FINISH),hex(t);n={ENTRY:1,RNG:0,TRIG:1,RELEASE:1,EMIT:5,UPDATE:2,FINISH:1}[t];args=tuple(map(u32,self.arguments(n)));self.calls.append((t,args));self.events.append(('CALL',t,args));self.counts[t]=self.counts.get(t,0)+1
  if t!=ENTRY:self.observations.append((snapshot(self.memory),data(self.memory,args[1],12)if t==EMIT else b'',self.fcsr))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
  if t==TRIG:self.f[0]=value

@lru_cache(maxsize=1)
def streams():
 symbols=dict(func_150ADA20=RNG,func_151423D8=TRIG,func_1516972C=RELEASE,D_800BE9A4=DT,D_800BE9E4=TICKS,D_80082FA4=PLAYER_INDEX,D_800DBFF0=PLAYER_BASE,D_80088858=EMIT_TABLE,D_80088860=FINISH_TABLE,D_80088864=UPDATE_TABLE,**{'D_%08X'%a:a for a in LITERALS});rows=[]
 for f in[p.OUT/'normalized-target.o',p.OUT/'qualified-owner/generic.o',p.OUT/'qualified-owner/generated.o',p.OUT/'original-target.o']:rows.append(bound_blob(*payload(f,p.FUNCTION),symbols))
 assert all(v==rows[0]for v in rows);assert rows[0]==list(struct.unpack_from('>212I',(p.ROOT/'conker/conker.us.bin').read_bytes(),0xf5f18));return rows
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def check(ws,c):
 m=Oracle(ws,c).run();wanted,calls,obs,fcsr=reference(m.initial,c);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory,c)==public(wanted,c),(c,'memory');assert m.fcsr==fcsr,(c,'FCSR',m.fcsr,fcsr)
 for i,(a,b)in enumerate(zip(m.observations,obs)):assert a[:2]==b[:2]and a[2]&127==b[2]&127,(c,'observation',i,a[2],b[2])
 assert m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(flags=flags,life=life,remainder=bits(rem),mode=mode,phase=phase,fcsr=rm)for flags,life,rem,mode,phase,rm in itertools.product((0,1),(0,30),(0.,1.,3.25),(0,7,24),(0,8),range(4))]
 rows += [Case(life=life,ticks=ticks,emission=-1,update=update,finish=finish,finish_result=answer)for life,ticks,update,finish,answer in itertools.product((-32768,-1,0,32767),(-2147483648,-1,0,1,2147483647),(-1,0),(-1,0),(0,1))]
 rows += [Case(x=bits(x),z=bits(z),heading=bits(h),mode=mode)for x,z,h,mode in itertools.product((0.,4000.),(0.,-4000.),(-540.,0.,359.5),(0,31))]
 return rows
def main():
 programs=streams();visits=set();count=0;prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models);visits.update(models[0].visits);count+=1
 for c in[Case(life=0),Case(emission=-1,update=-1,finish=-1),Case(mode=31,phase=8),Case(x=bits(4000.))]:
  full=Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models);prefixes+=1
 missing=set(range(ENTRY,ENTRY+848,4))-visits;assert missing=={ENTRY+119*4},missing
 q=dict(cases_per_stream=count,streams=4,executed_words=211,unreachable_divide_safety_break_word=119,access_fault_quads=prefixes,all_four_rounding_modes=True,finite_bounded_IEEE_model=True,mutable_callbacks=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
