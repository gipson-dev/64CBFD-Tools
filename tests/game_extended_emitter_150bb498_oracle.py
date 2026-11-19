"""Independent 124-byte descriptor reference and original callback/wrapper checks."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,itertools,json,struct
from tools.experiments import game_extended_emitter_150bb498_match as s
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.test_game_point_transform_match import put,read
ROOT=s.ROOT;PACKET=s.OUT;ENTRY=0x150bb498;RNG,REAL,SINE,FACTORY=0x150ada20,0x150ada68,0x151423d8,0x15132a4c
GLOBALS=(0x8009fe7c,0x8009fe80,0x8009fe84,0x8009fe88,0x8009fe8c);OUTPUT=0x50000
COUNTS={RNG:0,REAL:0,SINE:1,FACTORY:6};u32=lambda n:n&0xffffffff
POINTS=((0.,-0.,0.),(-0.,0.,-0.),(1.25,-2.5,3.75),(-17.75,91.5,-255.25),(32768.5,-32769.5,65535.75),(-65536.5,1000000.25,-1000000.25))
ANGLES=(0,1,63,64,127,128,255,0xffffffff)
public=lambda m:{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def unspecified(i):return 0x59<=i<0x5c or i in(0x69,0x6b,0x71)or 0x76<=i<0x7c
@dataclass(frozen=True)
class Case:
 seed:int=0;angle:int=0;slot:int=255;success:int=1;mutation:int=0;phase:int=0;coords:int=2
def cases():
 for seed,angle,success,mutation,phase in itertools.product((0,1,127,255),ANGLES,(0,1),range(4),(0,8)):
  yield Case(seed,angle,u32(0xabcdef00|seed),success,mutation,phase,seed%6)
def args(c):return(u32(0x87654321+c.seed),u32(-32768+c.seed),*(bits(v)for v in POINTS[c.coords]),bits(5.5),bits(-6.25),bits(7.75),c.angle,0xa50000ff,bits(11.25),0x80000000,bits(-13.5),0xffffffff,c.slot)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2048)};m.update({OUTPUT+i:(i*11+c.seed*7+7)&255 for i in range(512)})
 for i,v in enumerate(args(c)):put(m,STACK+c.phase+4*i,v)
 for i,a in enumerate(GLOBALS):put(m,a,bits((.125,-0.,-2.25,3.5,7.75)[(c.seed+i)%5]))
 return m
def randoms(c):
 values=(0,0xffffffff,0x80000000,0x7fffffff,12,13,67,68,38,100,0x12345678,255)
 return(values[c.seed%12],values[(c.seed+3)%12])
def reals(c):return tuple(bits((0.,-0.,.125,.5,1.,-.5,1.25)[(c.seed+i*3)%7])for i in range(5))
def sine(c,a):a&=255;return bits(-0. if a==0 and c.seed&1 else((a^128)-128)/128.)
def mutation_effect(m,c,stage):
 if (stage==0 and c.mutation&1)or(stage==1 and c.mutation&2):
  for i,a in enumerate(GLOBALS):put(m,a,bits((i+1)*(-1.25 if stage else 1.5)))
def factory_effect(m,c,d):
 if c.success:
  for i in range(124):m[OUTPUT+16+i]=m[d+i]
 mutation_effect(m,c,1)
def reference(initial,c):
 m=dict(initial);d=STACK+c.phase-0x94;calls=[];obs=[];ri=fi=0
 def field(i,v,n=4):put(m,d+i,v,n)
 def rng():
  nonlocal ri
  calls.append((RNG,()));v=randoms(c)[ri];ri+=1;return v
 def real():
  nonlocal fi
  calls.append((REAL,()));v=reals(c)[fi]
  if fi==3:mutation_effect(m,c,0)
  fi+=1;return v
 def trig(a):a&=255;calls.append((SINE,(a,)));return sine(c,a)
 hc=trig(c.angle-64);hs=trig(c.angle)
 field(0x50,0x9e8)
 for i in range(3):field(0x1c+4*i,bits(1.));field(0x10+4*i,0);field(0x28+4*i,bits(POINTS[c.coords][i]))
 field(4,read(m,GLOBALS[0]));pitch=rng()%13-52;pc=trig(pitch-64);ps=trig(pitch)
 speed=fp(fp(real(),bits(9.),'mul','left'),bits(3.),'add','left');horizontal=fp(speed,ps,'mul','left')
 field(0x34,fp(horizontal,hc,'mul','left'));field(0x38,fp(speed^0x80000000,pc,'mul','left'));field(0x3c,fp(horizontal,hs,'mul','left'))
 field(0x40,fp(fp(real(),bits(50.),'mul','left'),bits(-25.),'add','left'));field(0x44,0)
 field(0x48,fp(fp(real(),bits(50.),'mul','left'),bits(-25.),'add','left'));field(0x54,rng()%68+38,2)
 sample=real();field(0x4c,fp(fp(sample,read(m,GLOBALS[1]),'mul','left'),read(m,GLOBALS[2]),'add','left'));field(0,bits(1.))
 sample=real();scale=fp(fp(sample,read(m,GLOBALS[3]),'mul','left'),read(m,GLOBALS[4]),'add','left');field(8,scale);field(12,scale)
 for i,v,n in((0x56,31,2),(0x58,0,1),(0x5c,0,4),(0x60,255,1),(0x61,1,1),(0x62,0,1),(0x63,0,1),(0x64,0,1),(0x65,0,1),(0x66,0,1),(0x67,0,1),(0x68,0,1),(0x6a,0,1),(0x6c,0,4),(0x70,0,1),(0x72,1,2),(0x74,255,2)):field(i,v,n)
 calls.append((FACTORY,(d,3,255,0,c.slot&255,0)));obs.append(tuple(m[d+i]for i in range(124)));factory_effect(m,c,d)
 return m,calls,obs
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,arguments=None,connected=None):
  super().__init__(words,initial,c,entry=entry,s={},arguments=args(c)if arguments is None else arguments,connected=connected)
  self.cc=c;self.ri=self.fi=0;self.obs=[];self.calls=[];self.home=STACK+c.phase
  self.saved={i:self.r[i]for i in(*range(16,24),28,29,30)};self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2,3):self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul','div')[fn],'left');return
  if op==17 and fmt==16 and fn==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000;return
  return super().execute(w)
 def record_call(self,t):
  assert t in COUNTS,hex(t);a=tuple(self.arguments(COUNTS[t]));self.calls.append((t,a))
  if t==FACTORY:self.obs.append(tuple(self.memory[a[0]+i]for i in range(124)))
 def hook(self,t):
  c=self.cc;a=self.calls[-1][1];value=0xdeadbeef;floating=None
  if t==RNG:value=randoms(c)[self.ri];self.ri+=1
  elif t==REAL:
   floating=reals(c)[self.fi]
   if self.fi==3:mutation_effect(self.memory,c,0)
   self.fi+=1
  elif t==SINE:floating=sine(c,a[0])
  elif t==FACTORY:factory_effect(self.memory,c,a[0]);value=OUTPUT if c.success else 0
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=u32(value);self.hi=self.lo=0xdeadbeef
  if floating is not None:self.f[0]=floating
def run(state=None):
 state=s.state()if state is None else state;seen=set();n=0
 assert payload(PACKET/'owner.o',s.NAME)==payload(PACKET/'original.o',s.NAME)
 for c in cases():
  initial=fixture(c);expected,calls,obs=reference(initial,c)
  for body in(state['raw_words'],state['retail_words']):
   m=Oracle(body,initial,c).run();assert(public(m.memory),m.calls,m.obs)==(public(expected),calls,obs),(c,m.calls,calls)
   assert m.r[2]==1 and all(m.r[i]==v for i,v in m.saved.items())and tuple(m.f[20:])==m.saved_fp;seen|=m.visits
  n+=1
 assert len(seen)==151
 row=dict(passes=True,cases=n,guest_executions=2*n,body_words_visited=151,descriptor_bytes=124,unspecified_descriptor_bytes=12,source_literal_retail=True,source_installed=s.installed(),c_match_credit=0)
 (PACKET/'guest-report.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True);return row

def factory(state=None):
 from tools.match_progress import load_elf_functions
 state=s.state()if state is None else state;backend=0x1513264c
 words=struct.unpack_from('>15I',state['rom'],0x15fefc)
 live,_,_=load_elf_functions(str(s.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');assert tuple(live['func_15132A4C'])==words
 connected=dict(zip(range(FACTORY,FACTORY+60,4),words));seen=set();count=0
 class Connected(Oracle):
  def record_call(self,t):
   if t==backend:self.calls.append((t,tuple(self.arguments(7))))
   else:super().record_call(t)
  def hook(self,t):
   if t!=backend:return super().hook(t)
   a=self.calls[-1][1];factory_effect(self.memory,self.cc,a[0])
   for i in range(7):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xdeadbeef;self.r[2]=OUTPUT if self.cc.success else 0
 for seed,angle,success,mutation,phase in itertools.product((0,127),(0,1,127,255),(0,1),range(4),(0,8)):
  c=Case(seed,angle,0xabcd0000|seed,success,mutation,phase,seed%6);initial=fixture(c);expected,calls,obs=reference(initial,c);d=STACK+phase-0x94
  calls=calls+[(backend,(d,3,255,0,0,c.slot&255,0))]
  for body in(state['raw_words'],state['retail_words']):
   m=Connected(body,initial,c,connected=connected).run();assert(public(m.memory),m.calls,m.obs)==(public(expected),calls,obs),('factory',c,m.calls,calls)
   assert m.r[2]==1 and all(m.r[i]==v for i,v in m.saved.items())and tuple(m.f[20:])==m.saved_fp;seen|=m.visits&set(connected)
  count+=1
 assert len(seen)==15
 source=(s.FROZEN/'conker/src/game/generated_15F680.c').read_text();assert 'memcpy(result + 0x10, descriptor, 0x7C);'in source
 row=dict(passes=True,cases=count,programs=2,actual_wrapper_words=15,wrapper_words_visited=len(seen),all7_backend_argument_words_checked=True,production_wrapper_literal=True,descriptor_copy_bytes=124,backend='opaque modeled service',full_backend_qualified=False,full_allocator_qualified=False)
 (s.OUT/'factory-report.json').write_text(json.dumps(row,indent=2)+'\n');return row

def caller(state=None):
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 state=s.state()if state is None else state;entry,end=0x1514c3c4,0x1514c404
 parent=list(struct.unpack_from('>16I',state['rom'],0x179874));seen=set();zero_seen=set();count=0;controls=0
 class CallerCode(WindowCode):
  def __getitem__(self,pc):
   if pc in self.ends:self.owner.stopped_pc=pc
   return super().__getitem__(pc)
 def machine(body,initial,c,ends):
  connected=dict(zip(range(ENTRY,ENTRY+628,4),body));m=Oracle(parent,initial,c,entry=entry,arguments=(1,7,bits(1.25),bits(-2.5)),connected=connected)
  m.r[2]=ENTRY;m.r[7]=bits(-2.5);m.r[18]=c.angle;m.r[20]=8;m.r[22]=9;m.r[23]=10;m.r[30]=c.slot&255
  for reg,value in((2,3.75),(6,1.25),(22,2.),(24,-2.5),(26,0.),(28,3.75),(30,4.)):m.f[reg]=bits(value)
  original=m.record_call;observed=[]
  def record(t):
   if t==ENTRY:observed.append(tuple(m.arguments(15)))
   else:original(t)
  m.record_call=record;m.code=CallerCode(m.code,m);m.code.ends=ends
  return m,observed
 for angle,success,flags,mutation,phase in itertools.product((0,1,127,128,255),(0,1),range(4),range(4),(0,8)):
  c=Case(seed=flags,angle=angle,slot=0xabcd0000|angle,success=success,mutation=mutation,phase=phase,coords=2)
  initial=fixture(c);expected,calls,obs=reference(initial,c)
  for body in(state['raw_words'],state['retail_words']):
   m,observed=machine(body,initial,c,(end,))
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller did not reach its original continuation')
   # In this retail window F26/F24/F28 hold original x/y/z; F22 is radius.
   assert observed==[(1,7,bits(1.25),bits(-2.5),bits(3.75),bits(0.),bits(-2.5),bits(3.75),angle,8,bits(2.),9,bits(4.),10,c.slot&255)],observed
   assert(public(m.memory),m.calls,m.obs)==(public(expected),calls,obs),('caller',c,m.calls,calls)
   assert m.r[2]==1 and m.stopped_pc==end
   seen|=m.visits&set(range(entry,end,4))
   if count==0:
    wrong=list(body);assert wrong[-5]==0x24020001;wrong[-5]=0x24020000
    bad,_=machine(wrong,initial,c,(end,0x1514c42c))
    try:bad.run()
    except WindowBoundary:pass
    else:raise AssertionError('return-zero control failed to reach a continuation')
    assert bad.stopped_pc==0x1514c42c and bad.r[2]==0,hex(bad.stopped_pc)
    zero_seen|=bad.visits&set(range(entry,end,4));controls+=1
  count+=1
 assert set(range(entry,end,4))-seen=={0x1514c400}and len(seen|zero_seen)==16 and controls==2
 row=dict(passes=True,cases=count,programs=2,caller_words=16,positive_words_visited=len(seen),annulled_positive_word='0x1514C400',words_with_return_zero_control=len(seen|zero_seen),effective_return_zero_controls=controls,window='0x1514C3C4..0x1514C404',registry='D_8008AA00[6]',all15_argument_words_checked=True,return_one_keeps_loop=True,complete_parent_qualified=False)
 (s.OUT/'caller-report.json').write_text(json.dumps(row,indent=2)+'\n');return row
