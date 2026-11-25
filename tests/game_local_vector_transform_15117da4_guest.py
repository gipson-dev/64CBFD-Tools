"""Independent ordered scalar reference and bounded finite FP instruction execution."""
from pathlib import Path
from dataclasses import dataclass
from collections import Counter
from unittest.mock import patch
import itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_local_vector_transform_15117da4_match as p
o=p.OUT;ENTRY=0x15117da4;POINT=0x30000;ALT=0x32000;OUTPUT=0x50000;LOOKUP=0x151149ac;UPDATE=0x1511f31c;SIN=0x15047d60;COS=0x15047c00;CATEGORY=0x800be9f0;CONSTANTS=(0x800a2ff4,0x800a2ff8,0x800a2ffc)
symbols=lambda:dict(func_151149AC=LOOKUP,func_1511F31C=UPDATE,sinf=SIN,cosf=COS,D_800BE9F0=CATEGORY,**{'D_%08X'%a:a for a in CONSTANTS})
bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xffffffff;short=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 kind:int=0x8006
 category:int=53
 values:tuple=tuple(map(bits,(1.25,-2.5,3.75)))
 angles:tuple=tuple(map(bits,(.5,-.25)))
 position:tuple=(32767,-32768,13)
 trig:tuple=tuple(map(bits,(.25,.75,-.5,.625)))
 alias:int=0
 mode:int=0
 phase:int=0
 seed:int=0
 fcsr:int=0
 home_mutation:bool=False
def destination(c):return (OUTPUT,POINT,POINT+4,POINT+12,POINT+16,POINT+20,POINT+80,ALT,ALT+4,ALT+16)[c.alias]
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,256)}
 for p in(POINT,ALT,OUTPUT):m.update({p+i:(i*29+c.seed*11+0x5a)&255 for i in range(-32,160)})
 for p in(POINT,ALT):
  for i,v in enumerate(c.angles):put(m,p+4*i,v)
  for i,v in enumerate(c.position):put(m,p+16+2*i,v,2)
  put(m,p+84,c.kind,2)
 put(m,CATEGORY,c.category)
 for a,v in zip(CONSTANTS,map(bits,(7.5,.25,.5))):put(m,a,v)
 return m
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-512<=a<STACK+c.phase+256}
def effect(m,c,t,ordinal):
 if c.mode&1:
  p=POINT if ordinal&1 else ALT
  for i,v in enumerate((3.25+ordinal,-4.5-ordinal)):put(m,p+4*i,bits(v))
  for i,v in enumerate((-300+ordinal,700-ordinal,-800+ordinal)):put(m,p+16+2*i,v,2)
 if c.mode&2:
  for i in range(3):put(m,destination(c)+4*i,bits((i+1)*.125+ordinal))
 if c.mode&4:
  for a,v in zip(CONSTANTS,(1.+ordinal,.125+ordinal/16,.25+ordinal/32)):put(m,a,bits(v))
  put(m,CATEGORY,0x87654321)
 if c.home_mutation:
  for i,v in enumerate((20.+ordinal,-30.-ordinal,40.+ordinal)):put(m,STACK+c.phase+4+4*i,bits(v))
def provider_fcsr(c,ordinal):return(c.fcsr&3)|(1<<((ordinal%5)+2))
def reference(initial,c):
 m=dict(initial);calls=[];observations=[];fcsr=c.fcsr;home=STACK+c.phase;record=POINT;trig_index=0;ordinal=0;output=destination(c)
 put(m,home+4,c.values[0]);put(m,home+12,c.values[2])
 def calc(a,b,fn):
  nonlocal fcsr
  v,flags=arithmetic(a,b,fn,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return v
 def call(t,arg):
  nonlocal ordinal,trig_index,fcsr
  args=(u32(arg),);calls.append((t,args));observations.append((public(m,c),fcsr));ordinal+=1;effect(m,c,t,ordinal);fcsr=provider_fcsr(c,ordinal)
  if t in(SIN,COS):v=c.trig[trig_index];trig_index+=1;return v
  return ALT if t==LOOKUP else 0xa5000002
 y=c.values[1]
 if read(m,record+84,2)==0x8006 and read(m,CATEGORY)==53:
  record=call(LOOKUP,253);call(UPDATE,record);y=read(m,CONSTANTS[0]);put(m,home+4,0);put(m,home+12,0)
 angle=calc(read(m,record),read(m,CONSTANTS[1]),2);put(m,home+8,y);sine=call(SIN,angle);cosine=call(COS,angle)
 y,z=read(m,home+8),read(m,home+12);yc=calc(y,cosine,2);x=read(m,home+4);zs=calc(z,sine,2);put(m,output,x);ys=calc(y,sine,2);zc=calc(z,cosine,2);put(m,output+4,calc(yc,zs,1));put(m,output+8,calc(ys,zc,0))
 angle=calc(read(m,record+4),read(m,CONSTANTS[2]),2);sine=call(SIN,angle);cosine=call(COS,angle);z,x=read(m,output+8),read(m,output);zs=calc(z,sine,2);negative=x^0x80000000;xc=calc(x,cosine,2);zc=calc(z,cosine,2);ns=calc(negative,sine,2);put(m,output,calc(zs,xc,0));z=calc(zc,ns,0);oldX,oldY=read(m,output),read(m,output+4);put(m,output+8,z)
 translation=bits(float(short(read(m,record+16,2))));fcsr&=~0x3f000;x=calc(oldX,translation,0);oldZ=read(m,output+8);put(m,output,x);translation=bits(float(short(read(m,record+18,2))));fcsr&=~0x3f000;put(m,output+4,calc(oldY,translation,0));translation=bits(float(short(read(m,record+20,2))));fcsr&=~0x3f000;put(m,output+8,calc(oldZ,translation,0))
 return m,calls,observations,fcsr
class Machine(FactoryOracle):
 def __init__(self,words,c,entry=None,memory=None,arguments=None,connected=None):
  self.c=c;super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(POINT,*c.values,destination(c))if arguments is None else arguments,connected=connected);self.before_f=self.f[:];self.initial=dict(self.memory);self.fcsr=c.fcsr;self.ordinal=0;self.trig_index=0;self.provider_observations=[];self.provider_frames=[];self.fp_operations=[]
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2):
   self.fp_operations.append((fn,self.f[fs],self.f[rt],self.fcsr));self.f[fd],flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  elif op==17 and fmt==16 and fn==7:self.f[fd]=self.f[fs]^0x80000000
  elif op==17 and fmt==20 and fn==32:
   v=((self.f[fs]^0x80000000)-0x80000000);assert-32768<=v<=32767;self.f[fd]=bits(float(v));self.fcsr&=~0x3f000
  else:super().execute(w)
 def record_call(self,t):
  assert t in(LOOKUP,UPDATE,SIN,COS),hex(t);a=(self.f[12],)if t in(SIN,COS)else tuple(map(u32,self.arguments(1)));self.calls.append((t,a));self.events.append(('CALL',t,a));self.provider_observations.append((public(self.memory,self.c),self.fcsr));self.provider_frames.append((bytes(self.memory[STACK+self.c.phase-48+i]for i in range(68)),self.r[:],self.f[:],self.fcsr))
 def hook(self,t):
  self.ordinal+=1;effect(self.memory,self.c,t,self.ordinal)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=ALT if t==LOOKUP else 0xa5000002;self.fcsr=provider_fcsr(self.c,self.ordinal)
  if t in(SIN,COS):self.f[0]=self.c.trig[self.trig_index];self.trig_index+=1
def cases():
 rows=[Case(kind=k,category=cat,alias=a,mode=mode,seed=(a+mode)&31,fcsr=rm,phase=8*(rm&1))for k,cat,a,mode,rm in itertools.product((0x8006,0x8005),(0,53),range(10),(0,7),range(4))]
 rows +=[Case(kind=0x8005,values=tuple(map(bits,v)),position=pos,mode=mode,fcsr=rm)for v,pos,mode,rm in itertools.product(((0.,-0.,0.),(.1,-.2,.3),(-100.25,200.5,-300.75)),((-32768,32767,0),(0,-1,1)),(0,7),range(4))]
 rows +=[Case(home_mutation=True,mode=mode,kind=k)for mode,k in itertools.product((0,7),(0x8005,0x8006))]
 return rows
def check(words,c):
 m=Machine(words,c).run();wanted,calls,obs,fcsr=reference(m.initial,c);assert public(m.memory,c)==public(wanted,c),(c,'memory');assert m.calls==calls,(c,'calls',m.calls,calls);assert m.provider_observations==obs,(c,'provider observations');assert m.fcsr==fcsr,(c,'FCSR',hex(m.fcsr),hex(fcsr));assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];assert m.r[2]==destination(c)and m.f[0]==c.trig[-1];return m

from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
g=sys.modules[__name__]
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.provider_observations,m.provider_frames,m.fp_operations,m.trace,m.current_pc,m.delay_of,m.condition
def main():
 files=['normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o','original-target.o','selected-final/owner-candidate.o'];programs=[g.bound_blob(*g.payload(o/f,'func_15117DA4'),g.symbols())for f in files];assert all(ws==programs[0]for ws in programs[:4]);seen=set();prefixes=0
 for c in g.cases():
  models=[g.check(ws,c)for ws in programs];a=models[0];assert all(state(m)==state(a)for m in models[1:4]);raw=models[-1];assert(raw.memory,raw.r,raw.fcsr,raw.hi,raw.lo,raw.provider_frames,raw.fp_operations)==(a.memory,a.r,a.fcsr,a.hi,a.lo,a.provider_frames,a.fp_operations);seen.update(a.visits)
 for c in(g.Case(),g.Case(mode=7),g.Case(kind=0x8005,alias=3),g.Case(home_mutation=True,mode=7)):
  full=g.Machine(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs[:4]:
    m=g.Machine(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 assert seen==set(range(g.ENTRY,g.ENTRY+408,4))
 q=dict(cases_per_stream=len(g.cases()),streams=5,retail_equal_streams=4,all102_words_visited=True,access_fault_quads=prefixes,full_public_private_memory_and_GPRs_and_provider_frames_equal=True,all_ordered_FP_operands_and_bounded_FCSR_equal=True,raw_scratch_FPR_and_fault_order_not_claimed=True,not_a_hardware_IEEE_FPU_or_trig_implementation_proof=True,source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
