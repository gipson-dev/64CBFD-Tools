"""Extended emitter: complete o32 inputs, descriptor snapshots and FP/trunc order."""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,math,struct
from tools.experiments import game_tuned_extended_150b3188_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.tests.game_radial_angle_150c16c0_guest import TRIG,angle_value,state
ENTRY,FRNG,ANGLE,SUBMIT=0x150b3188,0x150ada68,0x151423d8,0x15132a4c
CONSTANTS=tuple(range(0x8009fb9c,0x8009fbb4,4))
VALUES=(0x3a83126f,0x3a83126f,0x3dcccccd,0x3dcccccd,0x3e4ccccd,0x3dcccccd)
OUTPUT,MARK=0x90000,0x70000
TWEAK,COPY=0x151422dc,0x10022ec0
LABELS=(0x8009f968,0x8009f970,0x8009f998,0x8009f9a4,0x8009f9cc,0x8009f9d8,0x8009fa00,0x8009fa0c,0x8009fa34,0x8009fa44,0x8009fa6c,0x8009fa78,0x8009faa0,0x8009fab0,0x8009fad8,0x8009fae4,0x8009fb0c,0x8009fb18)
TWEAK_META=((1,500,300,0x742),(-5000,0,0,0x750),(-5000,0,0,0x752),(0,500,0,0x75a),(0,500,0,0x75c),(0,5000,1000,0x761),(0,5000,0,0x763),(-255,255,0,0x769),(-255,255,0,0x76f))
bits,floating=fp.bits,fp.floating
u32=lambda n:n&0xffffffff
signed=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
short=lambda n:((n&65535)^32768)-32768
def unspecified(i):return 0x59<=i<0x5c or i in(0x69,0x6b,0x71)or 0x76<=i<0x7c
KNOWN=tuple(i for i in range(124)if not unspecified(i))
@dataclass(frozen=True)
class Case:
 coords:tuple=tuple(map(bits,(1.25,-2.5,3.75)))
 angle:int=0xabcd80fe
 start:int=0x9876fff0
 radius:int=bits(2.)
 extra:int=bits(.75)
 slot:int=0x123400e1
 samples:tuple=tuple(map(bits,(.125,.375,.625,.875,.25)))
 tweaks:tuple=(300,-333,-777,18,31,299,125,60,48)
 constants:tuple=VALUES
 unused:tuple=(0xa1234567,0xffff8001,0x7fc12345,0x3f123456,0xffc54321,0x87654321,0xabcdef01)
 outcome:int=1
 mode:int=0
 phase:int=0
 fcsr:int=0
 seed:int=0
 home_mutations:bool=False
 invalid_trunc:bool=False
def args(c):
 a,b,ox,oy,oz,style,context=c.unused
 return tuple(map(u32,(a,b,*c.coords,ox,oy,oz,c.angle,c.start,c.radius,style,c.extra,context,c.slot)))
def descriptor(c):return STACK+c.phase-192
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+4096}
def records(m,c):return data(m,descriptor(c),124)
def fixture(c):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,4096)}
 for base,n in((OUTPUT-16,0x194),(MARK,32)):m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for i,v in enumerate(args(c)):put(m,home+4*i,v)
 for a,v in zip(CONSTANTS,c.constants):put(m,a,v)
 return m
def snapshot(m,c):return tuple(read(m,a)for a in CONSTANTS),data(m,OUTPUT,0x174),data(m,MARK,32)

def effect(m,c,t,n,a):
 home=STACK+c.phase
 if t!=COPY:put(m,MARK,read(m,MARK)+1)
 if t==ANGLE:
  if n==1 and c.mode&1:put(m,CONSTANTS[0],bits(.002))
  if c.home_mutations and n==1:put(m,home+32,0xabcd0041)
  return angle_value(a[0])
 if t==TWEAK:
  if c.mode&1:
   if n in(2,3,6,7):put(m,CONSTANTS[{2:0,3:1,6:2,7:3}[n]],bits((n+1)*.0125))
   if n==9:put(m,CONSTANTS[4],bits(3.5))
  if c.home_mutations and n==9:
   for i,v in enumerate((5.,-7.,9.)):put(m,home+8+4*i,bits(v))
  return u32(c.tweaks[n-1])
 if t==FRNG:
  if c.mode&1 and n==5:put(m,CONSTANTS[5],bits(-.625))
  if c.home_mutations:
   if n==1:put(m,home+36,0x1234003f);put(m,home+40,bits(-1.25));put(m,home+48,bits(.5))
   if n==5:put(m,home+56,0xaabbccfe)
  return c.samples[(n-1)%5]
 if t==COPY:
  assert a==(OUTPUT+0x170,home-200,4),a
  value=data(m,a[1],a[2])
  for i,v in enumerate(value):m[a[0]+i]=v
  return a[0]
 assert t==SUBMIT
 if c.mode&2:put(m,a[0]+0x4c,bits(7.))
 if c.mode&4:put(m,OUTPUT,0x12345678)
 return OUTPUT if c.outcome else 0

def cvt_word(v,rm):
 exact=signed(v);z=bits(float(exact));value=floating(z)
 if value!=exact:
  if rm==1:z=fp.next_down(z)if exact>0 and value>exact else fp.next_up(z)if exact<0 and value<exact else z
  elif rm==2 and value<exact:z=fp.next_up(z)
  elif rm==3 and value>exact:z=fp.next_down(z)
 return z,0x1004 if floating(z)!=exact else 0

def trunc_word(v):
 x=floating(v);n=math.trunc(x)if math.isfinite(x)else None;valid=n is not None and -2147483648<=n<2147483648
 return(u32(n)if valid else 0x80000000),(0x10040 if not valid else 0x1004 if n!=x else 0)
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase;d=descriptor(c);calls=[];obs=[];counts={};fcsr=c.fcsr
 for i,v in enumerate(args(c)[:4]):put(m,home+4*i,v)
 def store(at,v,n=4):put(m,d+at,v,n)
 def calc(a,b,op):
  nonlocal fcsr
  v,flags=arithmetic(a,b,op,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return v
 def trunc(v):
  nonlocal fcsr
  n,flags=trunc_word(v);fcsr=(fcsr&~0x3f000)|flags;return n
 def call(t,a):
  a=tuple(map(u32,a));counts[t]=counts.get(t,0)+1;calls.append((t,a));obs.append((snapshot(m,c),records(m,c),data(m,home,60),fcsr));return effect(m,c,t,counts[t],a)

 def cvt(v):
  nonlocal fcsr
  n,flags=cvt_word(v,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return n
 hc=call(ANGLE,((read(m,home+32)-64)&255,));hs=call(ANGLE,(read(m,home+32)&255,))
 values=[]
 for i,(minimum,maximum,default,line)in enumerate(TWEAK_META):
  v=call(TWEAK,(i+6,LABELS[2*i],minimum,maximum,default,LABELS[2*i+1],line))
  if i==0:duration=short(v);continue
  v=cvt(v)
  if i in(1,2,5,6):v=calc(v,read(m,CONSTANTS[{1:0,2:1,5:2,6:3}[i]]),2)
  values.append(v)
 bias,fieldrange,speedbase,speedrange,sizebase,sizerange,yawscale,pitchscale=values
 store(0x50,0x29e9)
 for i in range(3):store(0x1c+4*i,bits(1.));store(0x10+4*i,0)
 put(m,home-200,bits(-18.))
 for i in range(3):store(0x28+4*i,read(m,home+8+4*i))
 store(4,read(m,CONSTANTS[4]))
 sample=call(FRNG,());first=calc(sample,speedrange,2);yawfactor=calc(yawscale,hs,2);speed=calc(first,speedbase,0)
 yawfactor=calc(yawfactor,read(m,home+40),2);yawfactor=calc(yawfactor,read(m,home+48),2);yaw=short(read(m,home+36)+signed(trunc(yawfactor))-64)
 yc=call(ANGLE,((yaw-64)&255,));ys=call(ANGLE,(yaw&255,))
 pitch=short(signed(trunc(calc(pitchscale,hc,2)))-20);pc=call(ANGLE,((pitch-64)&255,));ps=call(ANGLE,(pitch&255,))
 horizontal=calc(speed,ps,2);vx=calc(horizontal,yc,2);vy=calc(speed^0x80000000,pc,2);vz=calc(horizontal,ys,2)
 store(0x34,vx);store(0x38,vy);store(0x3c,vz)
 sample=call(FRNG,());a=calc(sample,bits(4.),2);store(0x44,0);store(0x40,calc(a,bits(-2.),0))
 sample=call(FRNG,());a=calc(sample,bits(4.),2);store(0x54,duration+32,2);store(0x48,calc(a,bits(-2.),0))
 sample=call(FRNG,());a=calc(sample,fieldrange,2);store(0x4c,calc(a,bias,0))
 sample=call(FRNG,());a=calc(sample,sizerange,2);size=calc(a,sizebase,0);scale=calc(size,read(m,CONSTANTS[5]),2)
 for at,v,n in[(8,size,4),(0x56,28,2),(0x58,0,1),(0x5c,0,4),(0x60,255,1),(0x61,1,1),(0x62,0,1),(0x63,5,1),(0,scale,4),(0x64,0,1),(0x65,0,1),(0x66,0,1),(0x67,0,1),(0x68,0,1),(0x6a,2,1),(0x6c,0,4),(0x70,0,1),(0x72,32,2),(0x74,7,2),(12,size,4)]:store(at,v,n)
 answer=call(SUBMIT,(d,3,255,4,read(m,home+56)&255,0))
 if answer:call(COPY,(answer+0x170,home-200,4))
 return m,calls,obs,fcsr
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=None,memory=None,arguments=None,connected=None,raw=False):
  self.c=c;self.raw=raw;self.counts={};self.observations=[];self.fcsr=c.fcsr
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=args(c)if arguments is None else arguments,connected=connected);self.initial=dict(self.memory);self.before_f=self.f[:]
 def get(self,a,n):
  if getattr(self,'recording',False)and self.own_instruction:assert all(a+i in self.memory for i in range(n)),('Unmapped read',hex(a),n)
  return super().get(a,n)
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==20 and fn==32:self.f[fd],flags=cvt_word(self.f[fs],self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  elif op==17 and fmt==16 and fn in(0,1,2):self.f[fd],flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  elif op==17 and fmt==16 and fn==13:self.f[fd],flags=trunc_word(self.f[fs]);self.fcsr=(self.fcsr&~0x3f000)|flags
  elif op==17 and fmt==16 and fn==7:self.f[fd]=self.f[fs]^0x80000000
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  n={ENTRY:15,FRNG:0,SUBMIT:6,ANGLE:1,TWEAK:7,COPY:3};assert t in n,hex(t);a=tuple(map(u32,self.arguments(n[t])));self.calls.append((t,a));self.events.append(('CALL',t,a));self.counts[t]=self.counts.get(t,0)+1
  if t!=ENTRY:self.observations.append((snapshot(self.memory,self.c),records(self.memory,self.c),data(self.memory,STACK+self.c.phase,60),self.fcsr))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
  if t in(FRNG,ANGLE):self.f[0]=value
def symbols():return dict(func_150ADA68=FRNG,func_151423D8=ANGLE,func_15132A4C=SUBMIT,func_151422DC=TWEAK,memcpy=COPY,**{'D_%08X'%a:a for a in (*CONSTANTS,*LABELS)})
@lru_cache(maxsize=1)
def streams():
 rows=[bound_blob(*payload(f,p.FUNCTION),symbols())for f in[p.OUT/'normalized-target.o',p.OUT/'qualified-owner/generic.o',p.OUT/'qualified-owner/generated.o',p.OUT/'original-target.o']]
 assert all(v==rows[0]for v in rows);assert rows[0]==list(struct.unpack_from('>329I',(p.ROOT/'conker/conker.us.bin').read_bytes(),0xe0638));return rows
def canonical(m):return state(m)
def check(ws,c,entry=None,raw=False):
 m=Oracle(ws,c,entry=entry,raw=raw).run();wanted,calls,obs,fcsr=reference(m.initial,c)
 assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory,c)==public(wanted,c),(c,'public');assert records(m.memory,c)==records(wanted,c),(c,'descriptor');assert m.fcsr==fcsr,(c,'FCSR',m.fcsr,fcsr)
 for i,(a,b)in enumerate(zip(m.observations,obs)):assert a[:3]==b[:3]and a[3]&127==b[3]&127,(c,'observation',i)
 assert len(m.observations)==len(obs);assert m.r[2]==1 and m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(angle=0xabcd0000|i,slot=0x12340000|i,start=u32(i-128),mode=i%8,fcsr=i%4,seed=i%16,outcome=i%2)for i in range(256)]
 rows +=[Case(angle=angle,start=start,radius=bits(radius),extra=bits(extra),mode=mode,phase=8*(rm&1),fcsr=rm,outcome=outcome)for angle,start,radius,extra,mode,rm,outcome in itertools.product((0x80000000,0x7fffffff),(0x80000000,0x7fffffff,0xffffffff),(-.5,1.25),(-.25,.75),(0,7),range(4),(0,1))]
 rows +=[Case(home_mutations=True,mode=mode,phase=phase,outcome=outcome)for mode,phase,outcome in itertools.product((0,7),(0,8),(0,1))]
 rows +=[Case(extra=bits(value),invalid_trunc=True,fcsr=rm)for value,rm in itertools.product((-1e30,1e30),range(4))]
 rows +=[Case(tweaks=(duration,bias,-777,18,31,299,125,yaw,pitch),fcsr=rm,outcome=outcome)for duration,bias,yaw,pitch,rm,outcome in itertools.product((-32768,-1,32767,65535),(-16777217,-1),(-255,255),(-255,255),range(4),(0,1))]
 rows +=[Case(tweaks=tuple(row[2]for row in TWEAK_META),outcome=v)for v in(0,1)]
 return rows
def main():
 programs=streams();raw=bound_blob(*payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION),symbols());visits=set();count=prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models);visits.update(models[0].visits);m=check(raw,c,raw=True);assert state(m)==state(models[0]);count+=1
 for c in[Case(),Case(mode=7,phase=8),Case(home_mutations=True,mode=7),Case(start=0x80000000,outcome=0)]:
  full=Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models);prefixes+=1
 assert visits==set(range(ENTRY,ENTRY+1316,4))
 q=dict(cases_per_stream=count,retail_equal_streams=4,raw_same_memory_and_return_cases=count,retail_body_words=329,executed_words=329,access_fault_quads=prefixes,all_four_rounding_modes=True,all_256_heading_and_slot_bytes=True,signed_start_and_angle_word_boundaries=True,guest_home_reload_mutations=True,guest_modeled_invalid_trunc_cases=8,full_descriptor_bytes=124,initialized_factory_bytes=len(KNOWN),unspecified_bytes=124-len(KNOWN),float_RNG_calls_per_case=5,angle_calls_per_case=6,factory_calls_per_case=1,tweak_calls_per_case=9,conditional_payload_copy_bytes=4,CVT_signed32_rounding_boundaries=True,source_installed=p.installed(),matching_credit=0)
 (p.OUT/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
