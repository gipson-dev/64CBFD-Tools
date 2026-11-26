"""Ordered random targets, modular clocks/rate and normalized literal faults."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,math,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.tests.game_pointer_quad_vertices_150db714_guest import trunc
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_random_targets_1518f1a0_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;ENTRY=0x1518F1A0;ACTOR=0x30000;FOLLOW=0x50000;MARK=0x90000;RNG=0x150ADA20;FRNG=0x150ADA68;DELTA=0x800BE9E4;SCALARS=(0x800A7B68,0x800A7B6C,0x800A7B70);u32=lambda v:v&0xFFFFFFFF;half=lambda v:((v&65535)^32768)-32768;signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000;bits=fp.bits
@dataclass(frozen=True)
class Case:
 object:int=ACTOR
 timers:tuple=(-1,-1,-1)
 delta:int=1
 animation_rate:int=100
 values:tuple=(bits(1.25),bits(-2.5))
 floats:tuple=(bits(.125),bits(.375),bits(.625))
 integers:tuple=(0xFFFFFFFF,2,0x80000000,0xFFFFFFFF)
 mode:int=0
 flags:int=0
 provider_flags:int=0
 rm:int=0
 phase:int=0
 seed:int=0

def symbols():return dict(func_150ADA20=RNG,func_150ADA68=FRNG,D_800BE9E4=DELTA,D_800A7B68=SCALARS[0],D_800A7B6C=SCALARS[1],D_800A7B70=SCALARS[2])
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+1024}
def initial_fcsr(c):return c.rm|c.flags
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for base,n in((c.object-16,352),(FOLLOW-16,352),(MARK,16)):m.update({u32(base+i):(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 put(m,DELTA,c.delta)
 for a,v in zip(SCALARS,(0x3EB7CED9,0x3E3E76C9,0x3E6C8B44)):put(m,a,v)
 for p in(c.object,FOLLOW):
  put(m,p+0x24,c.animation_rate)
  for off,v in zip((0x2C,0x30),c.values):put(m,p+off,v)
  for off,v in((0x110,8.),(0x114,-4.),(0x118,3.),(0x11C,2.),(0x120,-7.),(0x124,13.),(0x128,-3.),(0x130,11.),(0x134,-9.),(0x138,4.)):put(m,p+off,bits(v))
  for off,v in zip((0x12C,0x12E,0x13C),c.timers):put(m,p+off,v,2)
 return m
def effect(m,c,t,n):
 put(m,MARK,read(m,MARK)+1)
 if c.mode&1:
  p=c.object
  if t==FRNG:
   for off,v in((0x110,-6.5),(0x114,4.25),(0x11C,-1.5),(0x120,-9.25),(0x124,7.75),(0x130,-13.5),(0x134,3.25)):put(m,p+off,bits(v+n))
   put(m,p+0x24,0xFFFFFFE0+n);put(m,p+0x2C,bits(2.25+n));put(m,p+0x30,bits(-3.5-n))
 if c.mode&2:
  put(m,DELTA,(0,2,0xFFFFFFFF,0x80000001)[(n+(t==FRNG))&3])
  for a,v in zip(SCALARS,(.25,-.125,.375)):put(m,a,bits(v))
def convert_integer(value,rm):
 n=signed(value);b=bits(float(n));v=fp.floating(b)
 if v!=n:
  if rm==1:b=fp.next_down(b)if n>0 and v>n else fp.next_up(b)if n<0 and v<n else b
  elif rm==2 and v<n:b=fp.next_up(b)
  elif rm==3 and v>n:b=fp.next_down(b)
 return b,0x1004 if fp.floating(b)!=n else 0
def reference(initial,c,initial_csr=None):
 m=dict(initial);p=c.object;csr=initial_fcsr(c)if initial_csr is None else initial_csr;calls=[];ops=[];counts={RNG:0,FRNG:0}
 def operation(a,b,kind):
  nonlocal csr
  ops.append((kind,a,b,csr));v,flags=convert_integer(a,csr&3)if kind==32 else trunc(a)if kind==13 else arithmetic(a,b,kind,csr&3);csr=(csr&~0x3F000)|flags;return v
 def draw(t):
  nonlocal csr
  calls.append((t,()));counts[t]+=1;n=counts[t];effect(m,c,t,n)
  if t==FRNG:csr=(csr&~0x3F000)|c.provider_flags;return c.floats[(n-1)%len(c.floats)]
  return c.integers[(n-1)%len(c.integers)]
 def tick(off):
  put(m,p+off,u32(half(read(m,p+off,2))-read(m,DELTA)),2);return half(read(m,p+off,2))<0
 if tick(0x12E):
  put(m,p+0x12E,draw(RNG)%6,2);which=draw(RNG)&3;sample=draw(FRNG);a,b=(0x11C,0x120)if which else(0x124,0x11C);lower=read(m,p+b);put(m,p+0x128,operation(operation(sample,operation(read(m,p+a),lower,1),2),lower,0))
 current=read(m,p+0x30);put(m,p+0x30,operation(current,operation(operation(read(m,p+0x128),current,1),read(m,SCALARS[0]),2),0))
 if tick(0x12C):
  put(m,p+0x12C,draw(RNG)%17,2);sample=draw(FRNG);lower=read(m,p+0x114);put(m,p+0x118,operation(operation(sample,operation(read(m,p+0x110),lower,1),2),lower,0))
 current=read(m,p+0x2C);put(m,p+0x2C,operation(current,operation(operation(read(m,p+0x118),current,1),read(m,SCALARS[1]),2),0))
 if tick(0x13C):
  put(m,p+0x13C,draw(RNG)%15,2);sample=draw(FRNG);lower=read(m,p+0x134);put(m,p+0x138,operation(operation(sample,operation(read(m,p+0x130),lower,1),2),lower,0))
 value=read(m,p+0x24);converted=operation(value,0,32);difference=operation(read(m,p+0x138),converted,1);adjustment=operation(operation(difference,read(m,SCALARS[2]),2),0,13);put(m,p+0x24,u32(value+adjustment));return m,calls,ops,csr,1
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;self.counts={RNG:0,FRNG:0};self.fp_operations=[];super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(c.object,)if arguments is None else arguments,s=symbols(),connected=connected);self.initial=dict(self.memory);self.fcsr=initial_fcsr(c);self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and((fmt==16 and fn in(0,1,2,13))or(fmt==20 and fn==32)):
   kind=32 if fmt==20 else fn;a=self.f[fs];b=self.f[rt]if kind in(0,1,2)else 0;self.fp_operations.append((kind,a,b,self.fcsr));value,flags=convert_integer(a,self.fcsr&3)if kind==32 else trunc(a)if kind==13 else arithmetic(a,b,kind,self.fcsr&3);self.f[fd]=value;self.fcsr=(self.fcsr&~0x3F000)|flags
  elif op==0 and fn in(0x18,0x19,0x1A,0x1B):
   a,b=self.r[w>>21&31],self.r[rt]
   if fn in(0x18,0x19):v=(signed(a)*signed(b))if fn==0x18 else u32(a)*u32(b);self.lo,self.hi=u32(v),u32(v>>32)
   else:
    a,b=(signed(a),signed(b))if fn==0x1A else(u32(a),u32(b));assert b
    q=(abs(a)//abs(b))*(-1 if(a<0)!=(b<0)else 1);self.lo,self.hi=u32(q),u32(a-q*b)
  else:super().execute(w)
 def record_call(self,t):
  assert t in(RNG,FRNG),hex(t);self.calls.append((t,()));self.events.append(('CALL',t,()));self.counts[t]+=1
 def hook(self,t):
  c=self.c;n=self.counts[t];effect(self.memory,c,t,n);value=c.floats[(n-1)%len(c.floats)]if t==FRNG else c.integers[(n-1)%len(c.integers)]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
  if t==FRNG:self.f[0]=value;self.fcsr=(self.fcsr&~0x3F000)|c.provider_flags
def observable(m):return public(m.memory,m.c),m.calls,m.fp_operations,m.fcsr,m.r[2]
def state(m,trace=True):
 s=(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.fp_operations,m.current_pc,m.delay_of,m.condition);return s+(m.trace,)if trace else s
def check(words,c):
 m=Machine(words,c).run();memory,calls,ops,csr,value=reference(m.initial,c);want=(public(memory,c),calls,ops,csr,value);assert observable(m)==want,dict(case=str(c),parts=[a==b for a,b in zip(observable(m),want)],actual_calls=m.calls,wanted_calls=calls,actual_FP=m.fp_operations,wanted_FP=ops);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(timers=tuple(-1 if mask>>i&1 else 3 for i in range(3)),integers=(a,b,0x80000000,0xFFFFFFFF),floats=f,mode=mode,rm=rm,flags=4 if mode else 0,provider_flags=0x1004 if mode else 0,phase=8*(rm&1),seed=mask+rm)for mask,(a,b),f,mode,rm in itertools.product(range(8),((0,0),(1,1),(0xFFFFFFFF,2),(0x80000000,3)),((bits(0.),bits(.5),bits(1.)),(bits(-0.),bits(.25),bits(.75))),(0,1,2,3),range(4))]
 rows.extend(Case(timers=(timer,)*3,delta=delta,animation_rate=rate,rm=rm)for timer,delta,rate,rm in itertools.product((-32768,-1,0,32767),(0,1,0xFFFFFFFF,0x80000000),(-2147483648,2147483647),(0,3)))
 rows.extend(Case(object=DELTA-offset,mode=0,rm=rm)for offset,rm in itertools.product((0x2C,0x30),range(4)));return rows
def main():
 files=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o'];streams=[bound_blob(*payload(o/f,'func_1518F1A0'),symbols())for f in files];literal=[streams[i]for i in(0,2,3,4)];assert all(w==literal[0]for w in literal);seen=set();rows=cases();raw_memory_order_difference=False
 for c in rows:
  models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for i,m in enumerate(models)if i!=1);assert state(models[1],False)==state(models[0],False);raw_memory_order_difference|=models[1].trace!=models[0].trace;assert[x for x in models[1].trace if x[0]=='W']==[x for x in models[0].trace if x[0]=='W'];seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+484)
 cuts=0
 for c in(Case(),Case(timers=(3,3,3)),Case(timers=(-32768,0,32767),mode=3,rm=3),Case(object=DELTA-0x30)):
  full=Machine(literal[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in literal:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);cuts+=1
 assert len(seen)==121 and raw_memory_order_difference,(len(seen),raw_memory_order_difference)
 q=dict(cases_per_stream=len(rows),streams=5,literal_streams=4,executed_words=121,normalized_fault_prefix_quadruples=cuts,normalized_literal_full_private_and_fault_states_equal=True,raw_full_completion_memory_registers_FP_HILO_FCSR_calls_equal=True,raw_memory_write_order_equal=True,raw_scalar_read_order_differs_and_raw_fault_identity_not_claimed=True,independent_reference_full_public_memory_calls_ordered_FP_FCSR_and_return_equal=True,all_four_rounding_modes_existing_flags_unsigned_draws_modular_clocks_and_rate=True,live_provider_record_global_mutations_and_global_delta_aliases=True,finite_and_bounded_invalid_conversion_software_model_not_hardware=True,other_services_opaque=True,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
