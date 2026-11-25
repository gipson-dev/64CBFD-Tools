"""Random-pitch radial color emitter: o32 arguments, sparse packet and order."""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_radial_color_150b2570_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
ENTRY,RNG,FRNG,ANGLE,COLOR,SUBMIT,SECOND=0x150b2570,0x150ada20,0x150ada68,0x151423d8,0x151429e0,0x15156190,0x15156388
OUTPUT,MARK=0x90000,0x70000
CONSTANTS=tuple(range(0x8009f900,0x8009f918,4))
VALUES=(1062987629, 1080486266, 1050555712, 1075297911, 1068624773, 1078816932)
TRIG=(1065353216, 1065348163, 1065333006, 1065307756, 1065272429, 1065227043, 1065171628, 1065106213, 1065030845, 1064945565, 1064850423, 1064745478, 1064630794, 1064506438, 1064372487, 1064229022, 1064076126, 1063913894, 1063742422, 1063561817, 1063372182, 1063173636, 1062966298, 1062750290, 1062525745, 1062292797, 1062051586, 1061802258, 1061544962, 1061279856, 1061007097, 1060726848, 1060439282, 1060144570, 1059842889, 1059534421, 1059219352, 1058897872, 1058570176, 1058236457, 1057896921, 1057551770, 1057201212, 1056726308, 1056004841, 1055273844, 1054533757, 1053785034, 1053028116, 1052263464, 1051491538, 1050712803, 1049927727, 1049136785, 1048104902, 1046502417, 1044891072, 1043271836, 1041645694, 1039839822, 1036565808, 1033283836, 1028193052, 1019808416, 0)
PALETTE=(255, 255, 255, 250, 250, 250, 230, 230, 230, 200, 200, 200)
bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xffffffff
KNOWN=tuple([*range(0x29),*range(0x2a,0x2e),*range(0x30,0x35),*range(0x36,0x3a)])
@dataclass(frozen=True)
class Case:
 coords:tuple=(bits(1.25),bits(-2.5),bits(3.75))
 angle:int=0xabcd80fe
 slot:int=0x123400e1
 rng:tuple=(0xffffffff,0xffffffff)
 samples:tuple=tuple(map(bits,(.125,.375,.625)))
 colors:tuple=(0xffffffff,0x80000000)
 constants:tuple=VALUES
 unused:tuple=(0xa1234567,0xffff8001,0x7fc12345,0x3f123456,0xffc54321,0x987654ff,0x40000000,0x87654321,0x3f400000,0xabcdef01)
 outcome:int=1
 mode:int=0
 phase:int=0
 fcsr:int=0
 seed:int=0
 home_mutations:bool=False

def args(c):
 a,b,ox,oy,oz,start,radius,style,extra,context=c.unused
 return tuple(map(u32,(a,b,*c.coords,ox,oy,oz,c.angle,start,radius,style,extra,context,c.slot)))
def packet(c,raw=False):return STACK+c.phase-(60 if raw else 64)
def floats(c,raw=False):return STACK+c.phase-(76 if raw else 80)
def pitchslot(c,raw=False):return STACK+c.phase-(62 if raw else 66)
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+4096}
def angle_value(angle):
 angle&=255;i=64-(angle&63)if angle&64 else angle&63
 return TRIG[i]^(0x80000000 if angle&192 not in(0,192)else 0)
def fixture(c,raw=False):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,4096)}
 for base,n in((OUTPUT-16,0xcc),(MARK,32)):m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for i,v in enumerate(args(c)):put(m,home+4*i,v)
 for a,v in zip(CONSTANTS,c.constants):put(m,a,v)
 if raw:
  old=dict(m)
  for at,n in((floats(c),12),(pitchslot(c),2),(packet(c),60)):
   for i in range(n):m[at+4+i]=old[at+i]
 return m
def snapshot(m,c):return tuple(read(m,a)for a in CONSTANTS),data(m,OUTPUT,0xac),data(m,MARK,32)
def effect(m,c,t,n,a):
 put(m,MARK,read(m,MARK)+1)
 if t==ANGLE:
  if c.home_mutations and n==4:
   for i,v in enumerate((5.,-7.,9.)):put(m,STACK+c.phase+8+4*i,bits(v))
  return angle_value(a[0])
 if t==FRNG:
  if c.mode&1:
   for i,v in((2*(n-1),.25*n),(2*(n-1)+1,-.125*n)):put(m,CONSTANTS[i],bits(v))
  if c.home_mutations and n==3:put(m,STACK+c.phase+56,0xaabbccfe)
  return c.samples[n-1]
 if t==COLOR:
  assert a[0]==8
  for i,dest in enumerate(a[1:]):put(m,dest,PALETTE[3*(c.colors[n-1]&3)+i],1)
  return 0x8bad0001
 if t==RNG:return c.rng[n-1]
 assert t in(SUBMIT,SECOND),hex(t)
 if t==SUBMIT and c.mode&2:
  put(m,a[0]+0x30,0x3fc00000);put(m,a[0]+0x28,0x73,1)
 if c.mode&4:put(m,OUTPUT+(0 if t==SUBMIT else 4),0x12345678 if t==SUBMIT else 0x87654321)
 return OUTPUT if c.outcome&(1 if t==SUBMIT else 2)else 0

def reference(initial,c,raw=False):
 m=dict(initial);calls=[];obs=[];counts={};fcsr=c.fcsr;out=packet(c,raw)
 for i,v in enumerate(args(c)[:4]):put(m,STACK+c.phase+4*i,v)
 def store(at,v,n=4):put(m,out+at,v,n)
 def calc(a,b,op):
  nonlocal fcsr
  v,flags=arithmetic(a,b,op,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return v
 def call(t,a):
  a=tuple(map(u32,a));counts[t]=counts.get(t,0)+1;calls.append((t,a));obs.append((snapshot(m,c),data(m,out,60),data(m,STACK+c.phase,60),fcsr));return effect(m,c,t,counts[t],a)
 angle=args(c)[8]
 sq=call(ANGLE,((angle-64)&255,));put(m,floats(c,raw)+8,sq)
 sp=call(ANGLE,(angle&255,));put(m,floats(c,raw)+4,sp)
 pitch=(call(RNG,())%21-30)&65535;put(m,pitchslot(c,raw),pitch,2)
 aq=call(ANGLE,((pitch-64)&255,));put(m,floats(c,raw),aq)
 ap=call(ANGLE,(pitch&255,))
 speed=calc(bits(10.),ap,2)
 for i in range(3):store(4*i,read(m,STACK+c.phase+8+4*i))
 store(0xc,calc(speed,sq,2));store(0x10,calc(bits(-10.),aq,2));store(0x14,calc(speed,sp,2))
 for n,at in enumerate((0x18,0x1c)):
  sample=call(FRNG,());store(at,calc(calc(sample,read(m,CONSTANTS[2*n]),2),read(m,CONSTANTS[2*n+1]),0))
 call(COLOR,(8,out+0x20,out+0x21,out+0x22));call(COLOR,(8,out+0x24,out+0x25,out+0x26))
 store(0x23,255,1);store(0x27,255,1);store(0x28,9,1);store(0x2a,call(RNG,())%7+18,2)
 sample=call(FRNG,());value=calc(calc(sample,read(m,CONSTANTS[4]),2),read(m,CONSTANTS[5]),0)
 store(0x2c,0x1601,2);store(0x34,255,1);store(0x36,8,2);store(0x38,31,2);store(0x30,value)
 call(SUBMIT,(out,1,0,m[STACK+c.phase+59],1));return m,calls,obs,fcsr

class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=None,memory=None,arguments=None,connected=None,raw=False):
  self.c=c;self.raw=raw;self.counts={};self.observations=[];self.fcsr=c.fcsr
  super().__init__(words,fixture(c,raw)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=args(c)if arguments is None else arguments,connected=connected);self.initial=dict(self.memory);self.before_f=self.f[:]
 def get(self,a,n):
  if getattr(self,'recording',False)and self.own_instruction:assert all(a+i in self.memory for i in range(n)),('Unmapped read',hex(a),n)
  return super().get(a,n)
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2):self.f[fd],flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  elif op==17 and fmt==16 and fn==7:self.f[fd]=self.f[fs]^0x80000000
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  assert t in(ENTRY,RNG,FRNG,ANGLE,COLOR,SUBMIT,SECOND),hex(t);n={ENTRY:15,RNG:0,FRNG:0,ANGLE:1,COLOR:4,SUBMIT:5,SECOND:3}[t];a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a));self.counts[t]=self.counts.get(t,0)+1
  if t!=ENTRY:self.observations.append((snapshot(self.memory,self.c),data(self.memory,packet(self.c,self.raw),60),data(self.memory,STACK+self.c.phase,60),self.fcsr))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
  if t in(FRNG,ANGLE):self.f[0]=value

def symbols():return dict(func_150ADA20=RNG,func_150ADA68=FRNG,func_151423D8=ANGLE,func_151429E0=COLOR,func_15156190=SUBMIT,func_15156388=SECOND,**{'D_%08X'%a:a for a in CONSTANTS})
@lru_cache(maxsize=1)
def streams():
 rows=[bound_blob(*payload(f,p.FUNCTION),symbols())for f in[p.OUT/'normalized-target.o',p.OUT/'qualified-owner/generic.o',p.OUT/'qualified-owner/generated.o',p.OUT/'original-target.o']]
 assert all(v==rows[0]for v in rows);assert rows[0]==list(struct.unpack_from('>115I',(p.ROOT/'conker/conker.us.bin').read_bytes(),0xdfa20));return rows
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def canonical(m):
 calls=[]
 for t,a in m.calls:
  if m.raw:
   if t==COLOR:a=(a[0],*[v-4 for v in a[1:]])
   if t==SUBMIT:a=(a[0]-4,*a[1:])
  calls.append((t,a))
 c=m.c
 return(public(m.memory,c),calls,m.observations,m.fcsr,m.r[2],m.r[29],m.r[16:24],m.r[28:],m.f[20:],data(m.memory,packet(c,m.raw),60),data(m.memory,floats(c,m.raw),12),data(m.memory,pitchslot(c,m.raw),2),data(m.memory,STACK+c.phase-120,40),data(m.memory,STACK+c.phase,60))
def check(ws,c,entry=None,raw=False):
 m=Oracle(ws,c,entry=entry,raw=raw).run();wanted,calls,obs,fcsr=reference(m.initial,c,raw);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory,c)==public(wanted,c),(c,'memory');assert m.fcsr==fcsr,(c,'FCSR',m.fcsr,fcsr)
 assert len(m.observations)==len(obs)
 for i,(a,b)in enumerate(zip(m.observations,obs)):assert a[:3]==b[:3]and a[3]&127==b[3]&127,(c,'observation',i)
 assert m.r[2]==1 and m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[]
 for angle in range(256):
  unused=list(Case().unused);unused[5]=0x98760000|((angle*37+11)&255)
  rows.append(Case(angle=0xabcd0000|angle,unused=tuple(unused),slot=0x12340000|angle,mode=angle%8,fcsr=angle%4,seed=angle%16,colors=(angle,angle+1),outcome=angle%2))
 rows +=[Case(rng=draws,samples=tuple(map(bits,(0.,.5,1.)if rm&1 else(.1,-.25,.67))),colors=(0,3)if outcome&1 else(4,0xffffffff),mode=mode,phase=8*(rm&1),fcsr=rm,outcome=outcome,angle=angle)for draws,mode,rm,outcome,angle in itertools.product(((0,0),(20,6),(21,7),(0xffffffff,0xffffffff),(0x80000000,0x80000000)),(0,7),range(4),(0,1),(0x80000000,0x7fffffff))]
 rows +=[Case(rng=(pitch,6),mode=pitch%8,fcsr=pitch%4)for pitch in range(21)]
 rows +=[Case(home_mutations=True,mode=mode,phase=phase,outcome=outcome)for mode,phase,outcome in itertools.product((0,7),(0,8),(0,1))]
 return rows
def main():
 programs=streams();raw=bound_blob(*payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION),symbols());visits=set();count=prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models);visits.update(models[0].visits);r=check(raw,c,raw=True);assert canonical(r)==canonical(models[0]);count+=1
 for c in[Case(),Case(mode=7,phase=8),Case(home_mutations=True,mode=7),Case(rng=(0,0),outcome=0)]:
  full=Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models);prefixes+=1
 assert visits==set(range(ENTRY,ENTRY+460,4))
 q=dict(cases_per_stream=count,retail_equal_streams=4,raw_canonical_stack_map_cases=count,executed_words=115,access_fault_quads=prefixes,all_four_rounding_modes=True,all_256_angle_and_start_bytes=True,signed_word_boundaries=True,full_sparse_guest_packet=True,guest_home_mutations_excluded_from_native=True,RNG_calls_per_case=2,float_RNG_calls_per_case=3,angle_calls_per_case=4,color_provider_calls_per_case=2,factory_calls_per_case=1,source_installed=p.installed(),matching_credit=0);(p.OUT/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
