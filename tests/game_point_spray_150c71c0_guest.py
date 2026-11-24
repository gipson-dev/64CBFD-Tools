"""Independent point-difference model, five ordered RNG draws and live emitter."""
from dataclasses import dataclass
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_point_spray_150c71c0_match as packet
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
root,out=packet.ROOT,packet.OUT;ENTRY=0x150c71c0;FRNG=0x150ada68;RNG=0x150ada20;EMIT=0x151db5d0
EMITTER=0x50000;OTHER=0x52000;VECTOR=0x30000;OUTPUT=0x70000;SIZE=0x1d8
GLOBALS=(0x800a0498,0x800a049c,0x800a04a0,0x800a04a4);COEFFICIENT=0x800a0494
bits,floating=fp.bits,fp.floating;u32=lambda n:n&0xffffffff
@dataclass(frozen=True)
class Case:
 vectors:tuple=tuple(bits(v)for v in(1.,-2.,3.,8.,5.,-9.,.5,1.25,-.75,3.,-4.,2.))
 fraction:int=bits(.25)
 coefficient:int=bits(2.)
 constants:tuple=tuple(bits(v)for v in(.5,1.25,4.,-2.))
 floats:tuple=(bits(.125),bits(.75),bits(.25))
 integers:tuple=(0xffffffff,0x80000000)
 kind:int=0xab
 context:int=0xcd
 alias:int=0
 mode:int=0
 phase:int=0
 fcsr:int=0
 caller:bool=False
 rng_flags:tuple=(0,0,0)
def pointers(c):
 if c.caller:
  home=STACK+c.phase;return tuple(home+i for i in(0xd4,0xc8,0xf8,0xec))
 if c.alias==1:return(VECTOR,)*4
 if c.alias==2:return(VECTOR,VECTOR,VECTOR+64,VECTOR+64)
 if c.alias==3:return(EMITTER+0x6c,VECTOR+32,VECTOR+64,VECTOR+96)
 return tuple(VECTOR+32*i for i in range(4))
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-1024,2048)}
 for base,n in((VECTOR-16,160),(EMITTER-16,SIZE+32),(OTHER-16,SIZE+32),(OUTPUT-16,64)):m.update({base+i:(i*19+0xa5)&255 for i in range(n)})
 for p in(EMITTER,OTHER):put(m,p+0x74,c.coefficient);m[p+0xc]=c.kind;m[p+1]=c.context
 for i,p in enumerate(pointers(c)):
  for j in range(3):put(m,p+4*j,c.vectors[3*i+j])
 if c.alias==3:put(m,EMITTER+0x74,c.coefficient)
 for p,v in zip(GLOBALS,c.constants):put(m,p,v)
 put(m,COEFFICIENT,0x3ed0624e);return m
def public(m):return{a:v for a,v in m.items()if not STACK-1024<=a<STACK+2048}
def snapshot(m,c):return(tuple(read(m,p+4*j)for p in pointers(c)for j in range(3)),tuple(read(m,p)for p in GLOBALS),bytes(m[EMITTER+i]for i in range(SIZE)),bytes(m[OTHER+i]for i in range(SIZE)))
def effect(m,c,target,ordinal,home):
 if target==FRNG:
  if c.mode&1 and ordinal==1:
   for p in pointers(c):
    for j in range(3):put(m,p+4*j,bits(40.+j))
   put(m,EMITTER+0x74,bits(17.))
  if c.mode&2 and ordinal==2:
   for p,v in zip(GLOBALS,(2.,3.,5.,7.)):put(m,p,bits(v))
   m[EMITTER+0xc]^=0x55;m[EMITTER+1]^=0xaa
  return c.floats[ordinal-1]
 if target==RNG:
  if c.mode&4:put(m,GLOBALS[2],bits(8.+ordinal));m[EMITTER+0xc]=(c.kind+ordinal)&255
  if c.mode&8 and ordinal==2:put(m,home+16,bits(99.));put(m,home+20,OTHER);m[OTHER+0xc]=0xfe;m[OTHER+1]=0x81
  return c.integers[ordinal-1]
 assert target==EMIT;put(m,OUTPUT,0x13579bdf);return OUTPUT
def reference(initial,c,connected=False):
 m=dict(initial);home=STACK+c.phase;fcsr=c.fcsr;calls=[];observations=[];counts={}
 def calc(a,b,fn):
  nonlocal fcsr
  value,flags=arithmetic(a,b,fn,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return value
 velocity=[calc(calc(read(m,pointers(c)[1]+4*j),read(m,pointers(c)[0]+4*j),1),0x3ed0624e,2)for j in range(3)]
 def call(t,args):
  nonlocal fcsr
  counts[t]=counts.get(t,0)+1;calls.append((t,tuple(map(u32,args))));position=tuple(read(m,pointers(c)[0]+4*j)for j in range(3));observations.append((snapshot(m,c),position,tuple(velocity),fcsr));value=effect(m,c,t,counts[t],home)
  if connected and t==FRNG:fcsr=(fcsr&~0x3f000)|c.rng_flags[counts[t]-1]
  return value
 lifetime=call(RNG,())%31+42;first=call(FRNG,());second=call(FRNG,());third=call(FRNG,());opacity=call(RNG,())%101+155
 size=calc(calc(first,bits(70.),2),bits(30.),0);spread=calc(calc(second,read(m,GLOBALS[0]),2),read(m,GLOBALS[1]),0);other=calc(calc(third,read(m,GLOBALS[2]),2),read(m,GLOBALS[3]),0);emitter=OTHER if c.mode&8 else EMITTER
 call(EMIT,(0,pointers(c)[0],home-12,size,spread,bits(1.),other,lifetime,opacity,lifetime,255//lifetime,1,m[emitter+0xc],m[emitter+1]));return m,calls,observations,fcsr
class Oracle(fp.Oracle):
 def __init__(self,words,c,entry=ENTRY,connected=None,memory=None,arguments=None):
  self.c=c;args=(*pointers(c),c.fraction,EMITTER)if arguments is None else arguments;FactoryOracle.__init__(self,words,fixture(c)if memory is None else memory,c,entry=entry,arguments=args,connected=connected);self.initial=dict(self.memory);self.before_f=self.f[:];self.fcsr=c.fcsr;self.counts={};self.observations=[]
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2):self.f[fd],flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags;self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  assert t in(FRNG,RNG,EMIT,ENTRY),hex(t);a=tuple(map(u32,self.arguments(14 if t==EMIT else 6 if t==ENTRY else 0)));self.calls.append((t,a));self.events.append(('CALL',t,a));self.counts[t]=self.counts.get(t,0)+1;home=STACK+self.c.phase;position=tuple(read(self.memory,pointers(self.c)[0]+4*j)for j in range(3));velocity=tuple(read(self.memory,home-12+4*j)for j in range(3));self.observations.append((snapshot(self.memory,self.c),position,velocity,self.fcsr))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],STACK+self.c.phase)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
  if t==FRNG:self.f[0]=value
@lru_cache(maxsize=1)
def streams():
 syms={'D_800A0494':COEFFICIENT,'D_800A0498':GLOBALS[0],'D_800A049C':GLOBALS[1],'D_800A04A0':GLOBALS[2],'D_800A04A4':GLOBALS[3],'func_150ADA20':RNG,'func_150ADA68':FRNG,'func_151DB5D0':EMIT};programs=[]
 for path in[out/'selected-final/owner-candidate.o',out/'qualified-owner/generic.o',out/'qualified-owner/generated.o',out/'original-target.o']:
  data,refs=payload(path,packet.FUNCTION);refs={k:[(typ,'D_800A0494'if n=='.rodata'else n)for typ,n in a]for k,a in refs.items()};programs.append(bound_blob(data,refs,syms))
 assert all(v==programs[0]for v in programs);assert programs[0]==list(struct.unpack_from('>99I',(root/'conker/conker.us.bin').read_bytes(),0xf4670));return tuple(programs)
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def check(ws,c,entry=None):
 m=Oracle(ws,c,entry=ENTRY if entry is None else entry).run();expected,calls,observations,fcsr=reference(m.initial,c);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory)==public(expected),(c,'memory')
 for actual,wanted in zip(m.observations,observations):assert actual[:3]==wanted[:3],(c,'packet/boundary');assert actual[3]&0x7f==wanted[3]&0x7f,(c,'sticky flags')
 assert m.fcsr==fcsr,(c,'FCSR',m.fcsr,fcsr);assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];return m
def cases():
 yield from(Case(kind=i,context=255-i)for i in range(256))
 for alias,mode,phase,rm in itertools.product(range(4),(0,1,2,4,7,15),(0,8),range(4)):yield Case(alias=alias,mode=mode,phase=phase,fcsr=rm)
 for a,b in itertools.product((0,1,30,31,100,101,0x7fffffff,0x80000000,0xffffffff),repeat=2):yield Case(integers=(a,b))
 for a in range(31):yield Case(integers=(a,0x80000000))
 for b in range(101):yield Case(integers=(0xffffffff,b))
 for v in(0,0x80000000,bits(.1),bits(-2.)):yield Case(vectors=(v,)*12)
def main():
 visits=set();count=0
 for c in cases():
  models=[check(ws,c)for ws in streams()];assert all(state(m)==state(models[0])for m in models[1:]);visits.update(models[0].visits);count+=1
 faults=0
 for c in(Case(),Case(alias=1,mode=7,phase=8),Case(alias=3,mode=15)):
  full=check(streams()[0],c)
  for cut in range(full.all_accesses):
   states=[]
   for ws in streams():
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(m))
   assert all(v==states[0]for v in states);faults+=1
 missing=[i for i in range(99)if ENTRY+4*i not in visits];assert missing==[85,89,90,91],missing
 q=dict(cases_per_stream=count,streams=4,target_body_words=99,executed_words=95,unreachable_words=missing,lifetime_range=[42,72],division_zero_and_overflow_checks_proved_dead=True,access_fault_quads=faults,five_rng_draws_ordered=True,all_256_identity_bytes=True,all_four_rounding_modes=True,finite_bounded_IEEE_model=True,source_installed=packet.installed(),matching_credit=0);(out/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
