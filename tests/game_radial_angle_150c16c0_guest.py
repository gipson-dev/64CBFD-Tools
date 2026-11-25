"""Radial angle effect: captured heading/coefficient and one iteration."""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_radial_angle_150c16c0_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
ENTRY,RNG,FRNG,SUBMIT,ANGLE=0x150c16c0,0x150ada20,0x150ada68,0x15147da0,0x151423d8
OUTPUT,MARK,DIRECTION=0x90000,0x70000,0x60000
CONSTANTS=tuple(range(0x800a01f0,0x800a0204,4))
VALUES=(1099641651, 1101109658, 1103468954, 1045220557, 1053609165)
TRIG=(1065353216, 1065348163, 1065333006, 1065307756, 1065272429, 1065227043, 1065171628, 1065106213, 1065030845, 1064945565, 1064850423, 1064745478, 1064630794, 1064506438, 1064372487, 1064229022, 1064076126, 1063913894, 1063742422, 1063561817, 1063372182, 1063173636, 1062966298, 1062750290, 1062525745, 1062292797, 1062051586, 1061802258, 1061544962, 1061279856, 1061007097, 1060726848, 1060439282, 1060144570, 1059842889, 1059534421, 1059219352, 1058897872, 1058570176, 1058236457, 1057896921, 1057551770, 1057201212, 1056726308, 1056004841, 1055273844, 1054533757, 1053785034, 1053028116, 1052263464, 1051491538, 1050712803, 1049927727, 1049136785, 1048104902, 1046502417, 1044891072, 1043271836, 1041645694, 1039839822, 1036565808, 1033283836, 1028193052, 1019808416, 0)
bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xffffffff
REQUEST_KNOWN=tuple([*range(20),21]);PAYLOAD_KNOWN=tuple([*range(20),*range(24,28)]);RENDER_KNOWN=tuple(range(30))
KNOWN=tuple([*REQUEST_KNOWN,*[28+i for i in PAYLOAD_KNOWN],*[60+i for i in RENDER_KNOWN]])
@dataclass(frozen=True)
class Case:
 coords:tuple=(bits(1.25),bits(-2.5),bits(3.75))
 normals:tuple=tuple(map(bits,(.25,-.5,.75,-1.,2.,-3.)))
 angle:int=0xabcd80fe
 slot:int=0x123400e1
 rng:tuple=(0xffffffff,0xffffffff,0xffffffff)
 samples:tuple=tuple(map(bits,(.125,.375,.625)))
 constants:tuple=VALUES
 unused:tuple=(0xa1234567,0xffff8001,0x7fc12345,0x3f123456,0xffc54321,0x987654ff,0x40000000,0x87654321,0x3f400000,0xabcdef01)
 outcome:int=1
 mode:int=0
 phase:int=0
 fcsr:int=0
 seed:int=0
 home_mutations:bool=False
 alias:int=0
def request(c):return STACK+c.phase-32
def packet(c):return STACK+c.phase-64
def render(c):return STACK+c.phase-96
def direction(c):return DIRECTION if not c.alias else request(c)if c.alias==1 else packet(c)+4 if c.alias==2 else packet(c)
def args(c):
 a,b,ox,oy,oz,start,radius,style,extra,context=c.unused
 return tuple(map(u32,(a,b,*c.coords,ox,oy,oz,c.angle,start,radius,style,extra,context,c.slot)))
def angle_value(angle):
 angle&=255;i=64-(angle&63)if angle&64 else angle&63
 return TRIG[i]^(0x80000000 if angle&192 not in(0,192)else 0)
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+4096}
def records(m,c):return data(m,request(c),28)+data(m,packet(c),32)+data(m,render(c),32)
def fixture(c):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,4096)}
 for base,n in((OUTPUT-16,0xcc),(MARK,32),(DIRECTION,64)):m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for i,v in enumerate(args(c)):put(m,home+4*i,v)
 put(m,home+8,0x7fc12345);put(m,home+12,0xffc54321)
 for i,v in enumerate(c.normals):put(m,DIRECTION+(0 if i<3 else 32)+4*(i%3),v)
 for a,v in zip(CONSTANTS,c.constants):put(m,a,v)
 return m
def snapshot(m,c):return tuple(read(m,a)for a in CONSTANTS),data(m,OUTPUT,0xac),data(m,MARK,32),data(m,DIRECTION,64)
def effect(m,c,t,n,a):
 put(m,MARK,read(m,MARK)+1)
 if t==RNG:return c.rng[(n-1)%3]
 if t==ANGLE:
  if n==1 and c.mode&2:put(m,CONSTANTS[0],bits(.375))
  if n==1 and c.home_mutations:
   for i,v in enumerate((5.,-7.,9.)):put(m,STACK+c.phase+8+4*i,bits(v))
   put(m,STACK+c.phase+32,0x98760011);put(m,STACK+c.phase+56,0xaabbccfe)
  return angle_value(a[0])
 if t==FRNG:
  if c.mode&1:
   rows=(((0,.25),),((1,.5),(2,-.25)),((3,.75),(4,-.375)))
   for i,v in rows[(n-1)%3]:put(m,CONSTANTS[i],bits(v))
  if n==1 and c.mode&2:
   for i,v in enumerate((2.,-3.,4.)):put(m,DIRECTION+4*i,bits(v))
  if n==3 and c.home_mutations:put(m,STACK+c.phase+56,0xaabbccfd)
  return c.samples[(n-1)%3]
 assert t==SUBMIT
 put(m,a[0]+16,1)
 if c.mode&2:put(m,a[0],bits(7.));put(m,a[1]+16,bits(1.5));put(m,a[11],0x73)
 if c.mode&4:put(m,OUTPUT,0x12345678)
 return OUTPUT if c.outcome else 0
def reference(initial,c):
 m=dict(initial);calls=[];obs=[];counts={};fcsr=c.fcsr;q,d,h=request(c),packet(c),render(c)
 for i,v in enumerate(args(c)[:2]):put(m,STACK+c.phase+4*i,v)
 def store(base,at,v,n=4):put(m,base+at,v,n)
 def calc(a,b,op):
  nonlocal fcsr
  v,flags=arithmetic(a,b,op,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return v
 def call(t,a):
  a=tuple(map(u32,a));counts[t]=counts.get(t,0)+1;calls.append((t,a));obs.append((snapshot(m,c),records(m,c),data(m,STACK+c.phase,60),fcsr));return effect(m,c,t,counts[t],a)
 for at,v in[(0,0),(4,1),(8,0x160600),(12,3),(16,16),(20,128),(24,32)]:store(h,at,v)
 store(h,28,0,1);store(h,29,9,1);store(q,16,1);store(q,14,1,2)
 store(d,25,10,1);store(d,26,255,1);store(d,24,40,1);store(d,27,255,1)
 store(q,0,c.coords[0]);store(q,4,c.coords[1]);scale=read(m,CONSTANTS[0]);store(q,8,read(initial,STACK+c.phase+16));heading=c.angle&255;quarter=(c.angle-64)&255;slot=args(c)[14]&255
 pitch=(call(RNG,())%13-63)&65535;pv=call(ANGLE,(pitch&255,));pq=call(ANGLE,((pitch-64)&255,));hv=call(ANGLE,(heading,));hq=call(ANGLE,(quarter,))
 sample=call(FRNG,());speed=calc(calc(sample,scale,2),bits(25.5),0)
 store(q,21,call(RNG,())%9+5,1);store(q,12,(call(RNG,())&63)+90,2)
 sample=call(FRNG,());value=calc(calc(sample,read(m,CONSTANTS[1]),2),read(m,CONSTANTS[2]),0);store(d,0,value)
 sample=call(FRNG,());third=calc(sample,read(m,CONSTANTS[3]),2);horizontal=calc(speed,pv,2);third=calc(third,read(m,CONSTANTS[4]),0);vx=calc(horizontal,hq,2);vy=calc(speed^0x80000000,pq,2);vz=calc(horizontal,hv,2)
 store(d,16,third);store(d,4,vx);store(d,8,vy);store(d,12,vz)
 call(SUBMIT,(q,d,0,1,5,0,0,0,0,0,0,h,0,slot,0));return m,calls,obs,fcsr
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=None,memory=None,arguments=None,connected=None,raw=False):
  self.c=c;self.raw=raw;self.counts={};self.observations=[];self.fcsr=c.fcsr
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=args(c)if arguments is None else arguments,connected=connected);self.initial=dict(self.memory);self.before_f=self.f[:]
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
  assert t in(ENTRY,RNG,FRNG,SUBMIT,ANGLE),hex(t);n={ENTRY:15,RNG:0,FRNG:0,SUBMIT:15,ANGLE:1}[t];a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a));self.counts[t]=self.counts.get(t,0)+1
  if t!=ENTRY:self.observations.append((snapshot(self.memory,self.c),records(self.memory,self.c),data(self.memory,STACK+self.c.phase,60),self.fcsr))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
  if t in(FRNG,ANGLE):self.f[0]=value
def symbols():return dict(func_150ADA20=RNG,func_150ADA68=FRNG,func_15147DA0=SUBMIT,func_151423D8=ANGLE,**{'D_%08X'%a:a for a in CONSTANTS})
@lru_cache(maxsize=1)
def streams():
 rows=[bound_blob(*payload(f,p.FUNCTION),symbols())for f in[p.OUT/'normalized-target.o',p.OUT/'qualified-owner/generic.o',p.OUT/'qualified-owner/generated.o',p.OUT/'original-target.o']]
 assert all(v==rows[0]for v in rows);assert rows[0]==list(struct.unpack_from('>174I',(p.ROOT/'conker/conker.us.bin').read_bytes(),0xeeb70));return rows
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def canonical(m):return state(m)
def check(ws,c,entry=None,raw=False):
 m=Oracle(ws,c,entry=entry,raw=raw).run();wanted,calls,obs,fcsr=reference(m.initial,c);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory,c)==public(wanted,c),(c,'public');assert records(m.memory,c)==records(wanted,c),(c,'records');assert m.fcsr==fcsr,(c,'FCSR',m.fcsr,fcsr)
 for i,(a,b)in enumerate(zip(m.observations,obs)):assert a[:3]==b[:3]and a[3]&127==b[3]&127,(c,'observation',i)
 assert len(m.observations)==len(obs);assert m.r[2]==1 and m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(angle=0xabcd0000|i,slot=0x12340000|i,rng=(i,i+1,i+2),mode=i%8,fcsr=i%4,seed=i%16,outcome=i%2)for i in range(256)]
 rows +=[Case(rng=draws,samples=tuple(map(bits,(0.,.5,1.)if rm&1 else(.1,-.25,.67))),angle=angle,mode=mode,phase=8*(rm&1),fcsr=rm,outcome=outcome)for draws,mode,rm,outcome,angle in itertools.product(((0,0,0),(12,8,63),(13,9,64),(0xffffffff,)*3,(0x80000000,)*3),(0,7),range(4),(0,1),(0x80000000,0x7fffffff))]
 rows +=[Case(rng=(i,8,63),mode=i%8,fcsr=i%4)for i in range(13)]
 rows +=[Case(rng=(12,i,63),mode=i%8,fcsr=i%4)for i in range(9)]
 rows +=[Case(rng=(12,8,i),mode=i%8,fcsr=i%4)for i in range(64)]
 rows +=[Case(home_mutations=True,mode=mode,phase=phase,outcome=outcome)for mode,phase,outcome in itertools.product((0,7),(0,8),(0,1))]
 return rows
def main():
 programs=streams();raw=bound_blob(*payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION),symbols());visits=set();count=prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models);visits.update(models[0].visits);m=check(raw,c,raw=True);assert state(m)==state(models[0]);count+=1
 for c in[Case(),Case(mode=7,phase=8),Case(home_mutations=True,mode=7),Case(rng=(0,0,0),outcome=0)]:
  full=Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models);prefixes+=1
 assert visits==set(range(ENTRY,ENTRY+696,4))-{ENTRY+76*4,ENTRY+103*4}
 q=dict(cases_per_stream=count,retail_equal_streams=4,raw_same_memory_and_return_cases=count,retail_body_words=174,executed_words=172,statically_unreachable_break7_words=2,access_fault_quads=prefixes,all_four_rounding_modes=True,all_256_heading_and_slot_bytes=True,all_13_pitch_remainders=True,all_9_count_remainders=True,all_64_lifetime_mask_values=True,full_three_guest_records_bytes=92,initialized_factory_bytes=75,captured_coefficient_heading_coordinates_slot=True,RNG_calls_per_case=3,float_RNG_calls_per_case=3,angle_calls_per_case=4,factory_calls_per_case=1,source_installed=p.installed(),matching_credit=0);(p.OUT/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
