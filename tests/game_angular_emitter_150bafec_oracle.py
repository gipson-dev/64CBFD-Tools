"""Independent angular descriptor reference and complete direct-C guest execution."""
from pathlib import Path
from dataclasses import dataclass,replace
import hashlib,itertools,json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments import game_angular_emitter_150bafec_match as s
ROOT=s.ROOT;PACKET=s.OUT;ENTRY=0x150bafec
RNG,REAL,SINE,FACTORY,COPY=0x150ada20,0x150ada68,0x151423d8,0x15130374,0x10022ec0
K0,K1,OUTPUT=0x8009fe74,0x8009fe78,0x50000
COUNTS={RNG:0,REAL:0,SINE:1,FACTORY:5,COPY:3};u32=lambda v:v&0xffffffff
POINTS=((0.,-0.,0.),(-0.,0.,-0.),(1.25,-2.5,3.75),(-17.75,91.5,-255.25),(32768.5,-32769.5,65535.75),(-65536.5,1000000.25,-1000000.25))
ANGLES=(0,1,63,64,127,128,255,0xffffffff)
public=lambda m:{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def unspecified(i):return 0x3c<=i<0x48 or 0x5c<=i<0x60 or 0x64<=i<0x70
@dataclass(frozen=True)
class Case:
 seed:int=0;angle:int=0;slot:int=255;success:int=1;flags:int=0;mutation:int=0;phase:int=0;coords:int=2
def cases():
 for seed,angle,success,flags,mutation,phase in itertools.product((0,1,127,255),ANGLES,(0,1),range(4),range(4),(0,8)):
  yield Case(seed,angle,u32(0xabcdef00|seed),success,flags,mutation,phase,seed%6)
def args(c):
 return(u32(0x87654321+c.seed),u32(-32768+c.seed),*(bits(v)for v in POINTS[c.coords]),bits(5.5),bits(-6.25),bits(7.75),c.angle,0xa50000ff,bits(11.25),0x80000000,bits(-13.5),0xffffffff,c.slot)
def fixture(c):
 h=STACK+c.phase;m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2048)};m.update({OUTPUT+i:(i*11+c.seed*7+7)&255 for i in range(256)})
 for i,v in enumerate(args(c)):put(m,h+4*i,v)
 put(m,K0,bits((1.5,-0.,-2.25,3.5)[c.seed%4]));put(m,K1,bits((2.25,-4.5,0.,.125)[c.seed%4]));return m
def randoms(c):
 v=(0,0xffffffff,0x80000000,0x7fffffff,35,36,51,52,10,11,100,0x12345678)
 return(v[c.seed%12],v[(c.seed+3)%12],v[(c.seed+7)%12],c.flags&1,c.flags>>1)
def reals(c):return(bits((0.,-0.,.125,.5,1.,-.5,1.25)[c.seed%7]),bits((0.,-0.,.125,.5,1.,-.5,1.25)[(c.seed+3)%7]))
def sine(c,angle):
 angle&=255
 return bits(-0.0 if angle==0 and c.seed&1 else ((angle^128)-128)/128.)
def rng_effect(m,c,index):
 if c.mutation&1 and index==3:put(m,K0,bits(3.5));put(m,K1,bits(4.25))
def factory_effect(m,c,d):
 if c.success:
  for i in range(112):m[OUTPUT+16+i]=m[d+i]
  m[OUTPUT+0x9c]=0
 if c.mutation&2:put(m,K0,bits(-9.5));put(m,K1,bits(-8.5))
def reference(initial,c):
 m=dict(initial);h=STACK+c.phase;d=h-0x70;bonus=h-0x78;calls=[];obs=[];ri=0;fi=0
 def rng():
  nonlocal ri
  calls.append((RNG,()));value=randoms(c)[ri];rng_effect(m,c,ri);ri+=1;return value
 def real():
  nonlocal fi
  calls.append((REAL,()));v=reals(c)[fi];fi+=1;return v
 def trig(angle):angle&=255;calls.append((SINE,(angle,)));return sine(c,angle)
 def field(i,v,n=4):put(m,d+i,v,n)
 cosine=trig(c.angle-64);sine_heading=trig(c.angle)
 for at,value,n in((0x1d,41,1),(8,0xe03,2),(0,0x200005,4),(4,0,4)):field(at,value,n)
 field(0xa,rng()%36+70,2);field(0xc,0);field(0x10,0)
 for at,v in((0x18,176),(0x19,160),(0x1a,42),(0x14,64),(0x15,11),(0x16,106),(0x17,255)):field(at,v,1)
 field(0x1b,rng()%52+90,1);field(0x1c,255,1);field(0x60,3,1);field(0x61,3,1)
 scale=fp(fp(real(),bits(165.),'mul','left'),bits(800.),'add','left')
 for i,v in enumerate(POINTS[c.coords]):field(0x30+4*i,bits(v))
 field(0x28,scale);field(0x2c,scale)
 pitch=(rng()%11)-12;pitch_cosine=trig(pitch-64);pitch_sine=trig(pitch)
 speed=fp(fp(real(),bits(11.),'mul','left'),bits(15.),'add','left');horizontal=fp(speed,pitch_sine,'mul','left')
 field(0x58,0xe05)
 field(0x48,fp(horizontal,cosine,'mul','left'));field(0x4c,fp(speed^0x80000000,pitch_cosine,'mul','left'));field(0x50,fp(horizontal,sine_heading,'mul','left'));field(0x54,0)
 if rng()&1:field(0x58,read(m,d+0x58)|0x40)
 if rng()&1:field(0x58,read(m,d+0x58)|0x80)
 for at,v,n in((0x62,2,1),(0x63,255,1),(0x1e,22,2),(0x20,11,2),(0x22,1,2)):field(at,v,n)
 field(0x24,read(m,K0));put(m,bonus,read(m,K1))
 calls.append((FACTORY,(d,0,4,c.slot&255,1)));obs.append(tuple(m[d+i]for i in range(112)));factory_effect(m,c,d)
 if c.success:
  calls.append((COPY,(OUTPUT+0xa8,bonus,4)))
  for i in range(4):m[OUTPUT+0xa8+i]=m[bonus+i]
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
  if t==FACTORY:self.obs.append(tuple(self.memory[a[0]+i]for i in range(112)))
 def hook(self,t):
  c=self.cc;a=self.calls[-1][1];value=0xdeadbeef;float_value=None
  if t==RNG:value=randoms(c)[self.ri];rng_effect(self.memory,c,self.ri);self.ri+=1
  elif t==REAL:float_value=reals(c)[self.fi];self.fi+=1
  elif t==SINE:float_value=sine(c,a[0])
  elif t==FACTORY:factory_effect(self.memory,c,a[0]);value=OUTPUT if c.success else 0
  elif t==COPY:
   assert a[2]==4
   for i in range(a[2]):self.memory[a[0]+i]=self.memory[a[1]+i]
   value=a[0]
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=u32(value);self.hi=self.lo=0xdeadbeef
  if float_value is not None:self.f[0]=float_value
def run(state=None):
 raw,refs=payload(PACKET/'owner.o','func_150BAFEC');truth,trefs=payload(PACKET/'original.o','func_150BAFEC');assert(raw,refs)==(truth,trefs)
 lookup={n:f[1]for _,n,f,_ in symbol_rows((s.FROZEN/'conker/build/conker.us.elf').read_bytes())};source=bound_blob(raw,refs,lookup);retail=bound_blob(truth,trefs,lookup)
 assert struct.pack('>157I',*retail)==(s.FROZEN/'conker/conker.us.bin').read_bytes()[0xe849c:0xe8710]
 seen=set();n=0
 for c in cases():
  initial=fixture(c);expected,calls,obs=reference(initial,c)
  for label,words in(('source',source),('retail',retail)):
   m=Oracle(words,initial,c).run();assert(public(m.memory),m.calls,m.obs)==(public(expected),calls,obs),(label,c,m.calls,calls)
   assert m.r[2]==1 and all(m.r[i]==v for i,v in m.saved.items())and tuple(m.f[20:])==m.saved_fp
   seen|=m.visits
  n+=1
 assert len(seen)==157,len(seen)
 row=dict(passes=True,cases=n,guest_executions=2*n,body_words_visited=len(seen),source_literal_retail=True,raw_sha256=hashlib.sha256(raw).hexdigest(),descriptor_bytes=112,unspecified_descriptor_bytes=28,source_installed=s.installed(),c_match_credit=0)
 (PACKET/'guest-report.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True);return row

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
  c=Case(seed=angle,angle=angle,slot=0xabcd0000|angle,success=success,flags=flags,mutation=mutation,phase=phase,coords=2)
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
 row=dict(passes=True,cases=count,programs=2,caller_words=16,positive_words_visited=len(seen),annulled_positive_word='0x1514C400',words_with_return_zero_control=len(seen|zero_seen),effective_return_zero_controls=controls,window='0x1514C3C4..0x1514C404',registry='D_8008AA00[5]',all15_argument_words_checked=True,return_one_keeps_loop=True,complete_parent_qualified=False)
 (s.OUT/'caller-report.json').write_text(json.dumps(row,indent=2)+'\n');return row

def factory(state=None):
 from tools.match_progress import load_elf_functions
 state=s.state()if state is None else state;rom=state['rom'];helper,allocate=0x15130280,0x15167a68
 live,_,_=load_elf_functions(str(s.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');connected={};regions={}
 for name,entry,offset,words in(('func_15130374',FACTORY,0x15d824,18),('func_15130280',helper,0x15d730,61),('memcpy',COPY,0x22ec0,11)):
  code=struct.unpack_from('>%dI'%words,rom,offset);assert tuple(live[name])==code,name
  connected.update(zip(range(entry,entry+4*words,4),code));regions[name]=(entry,words,set())
 class Connected(Oracle):
  def __init__(self,body,c):super().__init__(body,fixture(c),c,connected=connected)
  def record_call(self,t):
   if t in(helper,allocate):self.calls.append((t,tuple(self.arguments(6))))
   else:super().record_call(t)
  def hook(self,t):
   if t!=allocate:return super().hook(t)
   for i in range(6):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xdeadbeef;self.r[2]=OUTPUT if self.cc.success else 0
 count=0
 for seed,angle,success,flags,mutation,phase in itertools.product((0,127),(0,127,255),(0,1),range(4),(0,1),(0,8)):
  c=Case(seed,angle,0xabcd0000|seed,success,flags,mutation,phase,seed%6);expected,calls,obs=reference(fixture(c),c)
  at=next(i for i,(target,_)in enumerate(calls)if target==FACTORY);d=STACK+phase-0x70
  extra=[(helper,(d,0,0,4,c.slot&255,1)),(allocate,(0x2b,1,0xac,1,c.slot&255,1))]
  if success:extra.append((COPY,(OUTPUT+16,d,112)))
  calls=calls[:at+1]+extra+calls[at+1:]
  for body in(state['raw_words'],state['retail_words']):
   m=Connected(body,c).run();assert(public(m.memory),m.calls,m.obs)==(public(expected),calls,obs),('connected factory',c,m.calls,calls)
   assert m.r[2]==1 and all(m.r[i]==v for i,v in m.saved.items())and tuple(m.f[20:])==m.saved_fp
   for name,(entry,n,seen)in regions.items():seen.update(pc for pc in m.visits if entry<=pc<entry+4*n)
  count+=1
 row=dict(passes=True,cases=count,programs=2,retail_regions={name:dict(words=n,visited_words=len(seen))for name,(_,n,seen)in regions.items()},allocation='opaque modeled provider',factory_mode=0,allocation_category=0x2b,record_bytes=0xac,descriptor_copy_bytes=112,extra_copy_bytes=4,production_helpers_literal=True,full_allocator_qualified=False)
 (s.OUT/'factory-report.json').write_text(json.dumps(row,indent=2)+'\n');return row
