"""Independent height/effect sequencing reference and real MIPS ABI execution."""
from dataclasses import dataclass,replace
import itertools,json,math,struct
from tools.experiments import game_actor_height_effect_150baa14_match as s
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ACTOR,BASE,ALT,MARK=0x60000,0x80000,0xa0000,0x70000
BASE_PTR,INDEX,SCALE=0x800dbff0,0x80082fa4,0x8009fe64
HEIGHT,PREP,COMMAND,EVENT,REAL,RNG,FINAL=0x150ba930,0x151d5404,0x15143e94,0x15165f80,0x150ada68,0x150ada20,0x1514c678
COUNTS={HEIGHT:4,PREP:8,COMMAND:2,EVENT:9,REAL:0,RNG:0,FINAL:12}
ENTRY=s.ENTRY;u32=lambda n:n&0xffffffff
public=lambda m:{a:b for a,b in m.items()if not STACK-2048<=a<STACK+4096}
short=lambda v:u32(((v&65535)^32768)-32768)
STATUS=(0,1,255,256,257,0xffffffff)
POINTS=((0.,-0.,0.),(-0.,0.,-0.),(17.75,-91.5,255.25),(-17.75,91.5,-255.25),(32768.5,-32769.5,65535.75),(-65536.5,1000000.25,-1000000.25))
@dataclass(frozen=True)
class Case:
 seed:int=0;ready:int=1;status:int=1;mutation:int=0;phase:int=0;selector:int=0xabcd0009;unused:int=0x87654321;coords:int=0
def cases():
 for seed in range(256):yield Case(seed,seed&1,STATUS[seed%6],seed%8,(seed&1)*8,0xabcd0000|seed,u32(0x87654321+seed*0x1020304),seed%6)
 for seed,ready,status,mutation,phase in itertools.product((0,1,127,255),(0,1),STATUS,(0,1,2,4,3,5,6,7),(0,8)):
  yield Case(seed,ready,status,mutation,phase,0xabcd0000|seed,u32(0x87654321+seed*0x1020304),seed%6)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,4096)}
 for at,n in((ACTOR,512),(BASE,3*0x9a0),(ALT,3*0x9a0),(MARK,4),(BASE_PTR,4),(INDEX,4),(SCALE,4)):
  m.update({at+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 put(m,ACTOR+468,c.ready);put(m,BASE_PTR,BASE);put(m,INDEX,c.seed%3);put(m,SCALE,bits((1.,-.5,.25,2.)[c.seed%4]))
 for base in(BASE,ALT):
  for i in range(3):put(m,base+i*0x9a0+0x380,bits((c.seed-128)*256.+i*17.25))
 return m
def random(c):return(0,0xffffffff,0x80000000,0x7fffffff,10,11,22,23)[c.seed%8]
def sample(c):return bits((c.seed*37%257)/256.)
def canonical_args(t,args):
 a=list(args)
 if t==HEIGHT:a[3]&=255
 if t==FINAL:
  for i in(4,5,6):a[i]=short(a[i])
  a[7]&=255;a[11]&=255
 return tuple(a)
class Service:
 def __init__(self,m,c):self.m=m;self.c=c;self.calls=[];self.position=None;self.surface=None
 def invoke(self,t,args):
  m,c=self.m,self.c;n=len(self.calls);args=canonical_args(t,args);a=list(args);observed=()
  if t==HEIGHT:
   assert args[1]==ACTOR;self.position,self.surface=args[0],args[2];a[0]='position';a[1]='actor';a[2]='surface'
  elif t==PREP:assert args[0]==self.position;a[0]='position'
  if self.position is not None and t!=HEIGHT:observed=tuple(read(m,self.position+4*i)for i in range(3))+tuple(read(m,self.surface+4*i)for i in range(9))
  self.calls.append((t,tuple(a),observed))
  if c.mutation&1 and self.position is not None:
   for i in range(3):put(m,self.position+4*i,bits((c.seed-100)*.125+n*.25+i))
  if c.mutation&2:
   put(m,BASE_PTR,ALT if n&1 else BASE);put(m,INDEX,(c.seed+n)%3);put(m,SCALE,bits(.25 if n&1 else -1.25))
   for base in(BASE,ALT):
    for i in range(3):put(m,base+i*0x9a0+0x380,bits((c.seed-128)*256.+(n+1)*32.+i*.125))
  if c.mutation&4 and self.surface is not None:
   for i in range(9):put(m,self.surface+4*i,u32(0xabcdef00+n*0x010203+i*0x070b11+c.seed))
  put(m,MARK,u32(0x13579bdf+n*0x10203+t))
  if t==HEIGHT:
   for i,v in enumerate(POINTS[c.coords]):put(m,args[0]+4*i,bits(v))
   for i in range(9):put(m,args[2]+4*i,u32(0x12340000+c.seed*0x10203+i*0x112233))
   return c.status
  if t==COMMAND:return(c.seed+n)&1
  if t==RNG:return random(c)
  if t==REAL:return sample(c)
  return u32(0xdeadbeef+n)
def reference(initial,c,home=None):
 m=dict(initial);service=Service(m,c);home=STACK+c.phase if home is None else home;position,surface=home-12,home-48
 if not read(m,ACTOR+468):return m,service
 hit=service.invoke(HEIGHT,(position,ACTOR,surface,c.selector&255))&255
 service.invoke(PREP,(position,0x44a36000,0x44fa0000,0x3a03126f,12,15,255,0));service.invoke(COMMAND,(5,0x4022))
 if hit:
  center=u32(math.trunc(floating(fp(read(m,read(m,BASE_PTR)+read(m,INDEX)*0x9a0+0x380),read(m,SCALE),'mul','left'))))
  x,y,z=(read(m,position+4*i)for i in range(3))
  service.invoke(EVENT,(0xffffffff,u32(math.trunc(floating(x))),u32(math.trunc(floating(fp(y,bits(6.),'add','left')))),u32(math.trunc(floating(z))),25,18,0,255,1))
  real=service.invoke(REAL,());rng=service.invoke(RNG,())
  service.invoke(FINAL,(*(read(m,position+4*i)for i in range(3)),fp(fp(real,bits(50.),'mul','left'),bits(40.),'add','left'),u32(center+60),u32(center-60),rng%11+30,5,0,0,0,255))
 return m,service
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,arguments=None,connected=None):
  super().__init__(words,initial,c,entry=entry,s={},arguments=(ACTOR,c.selector,c.unused)if arguments is None else arguments,connected=connected)
  self.service=Service(self.memory,c);self.saved={i:self.r[i]for i in(*range(16,24),28,29,30)};self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2,3):self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul','div')[fn],'left');return
  return super().execute(w)
 def record_call(self,t):
  assert t in COUNTS,hex(t);a=tuple(self.arguments(COUNTS[t]))
  if t==FINAL:a=(self.f[12],self.f[14],*a[2:])
  self.pending=t,a
 def hook(self,t):
  target,args=self.pending;assert t==target;answer=self.service.invoke(t,args)
  for i in range(max(4,COUNTS[t])):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=answer;self.hi=self.lo=0xdeadbeef
  if t==REAL:self.f[0]=answer
def verify(words,c):
 initial=fixture(c);expected,service=reference(initial,c);machine=Oracle(words,initial,c).run()
 assert public(machine.memory)==public(expected),('public',c)
 assert machine.service.calls==service.calls,('calls',c,next(((i,a,b)for i,(a,b)in enumerate(zip(machine.service.calls,service.calls))if a!=b),None),len(machine.service.calls),len(service.calls))
 assert all(machine.r[i]==v for i,v in machine.saved.items())and tuple(machine.f[20:])==machine.saved_fp
 return machine
def run(state):
 seen=set();n=0
 for c in cases():seen|=verify(state['raw_words'],c).visits;n+=1
 assert state['raw_words']==state['retail_words']and len(seen)==114
 report=dict(passes=True,cases=n,body_words_visited=len(seen),source_and_original_literal=True,canonical_signed16_and_byte_callee_arguments=True,retained_position_and_surface_mutable=True,valid_signed32_truncations=True,source_installed=s.installed(),c_match_credit=0)
 (s.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
def caller(state):
 entry=0x15028a4c;words=list(struct.unpack_from('>6I',state['rom'],0x55efc));seen=set();n=0
 for seed,ready,status,mutation,phase in itertools.product((0,1,127,255),(0,1),(0,1,256,0xffffffff),(0,7),(0,8)):
  c=Case(seed,ready,status,mutation,phase,9,0xffffffff,seed%6);initial=fixture(c);home=STACK+phase;put(initial,home+0x764,ACTOR)
  expected,service=reference(initial,c);connected=dict(zip(range(ENTRY,ENTRY+456,4),state['raw_words']))
  machine=Oracle(words,initial,c,entry=entry,arguments=(0xabcdef01,),connected=connected);base=machine.record_call
  def record(t):
   if t==ENTRY:assert tuple(machine.arguments(3))==(ACTOR,9,0xffffffff)
   else:base(t)
  machine.record_call=record;machine.code=WindowCode(machine.code,machine);machine.code.ends={0x15029ba4}
  try:machine.run()
  except WindowBoundary:pass
  else:raise AssertionError('caller failed to reach the original continuation')
  assert machine.r[2]==1 and machine.r[29]==home and public(machine.memory)==public(expected)and machine.service.calls==service.calls
  assert all(machine.r[i]==v for i,v in machine.saved.items())and tuple(machine.f[20:])==machine.saved_fp
  seen|=machine.visits&set(range(entry,entry+24,4));n+=1
 assert len(seen)==6
 report=dict(passes=True,cases=n,caller_words=6,caller_words_visited=6,actor_selector_unused_arguments=[9,0xffffffff],return_ignored_and_success_one=True,complete_parent_qualified=False,source_installed=s.installed(),c_match_credit=0)
 (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');return report

def callee_prefix(state):
 entry=FINAL;blob=state['rom'][0x179b28:0x179b28+104]
 elf=(s.FROZEN/'conker/build/conker.us.elf').read_bytes();at=s.elf_slot_offset(elf,entry,104);assert elf[at:at+104]==blob
 words=list(struct.unpack('>26I',blob));assert(words[21],words[22],words[25])==(0x87a400b6,0x87a500b2,0x87b500ba)
 n=0;seen=set()
 for first,last,life,phase in itertools.product((0,0x7fff,0x8000,0xffffffff),(0,0x80008000,0x7fffffff,0xffff0001),(0,0x7fff,0x8000,0xabcd8001),(0,8)):
  c=Case(phase=phase);initial=fixture(c);args=(bits(1.25),bits(-2.5),bits(3.75),bits(4.5),first,last,life,5,0,0,0,255)
  machine=FactoryOracle(words,initial,c,entry=entry,s={},arguments=args);machine.f[12],machine.f[14]=args[:2];machine.code=WindowCode(machine.code,machine);machine.code.ends={entry+0x68,entry+0x88}
  try:machine.run()
  except WindowBoundary:pass
  else:raise AssertionError('callee prefix did not reach its branch boundary')
  assert(machine.r[4],machine.r[5],machine.r[21])==(short(last),short(first),short(life))
  assert(machine.f[26],machine.f[24],machine.f[28],machine.f[22])==args[:4]
  seen|=machine.visits&set(range(entry,entry+104,4));n+=1
 assert len(seen)==26
 report=dict(passes=True,cases=n,actual_prefix_words=26,visited_words=26,production_literal=True,signed16_stack_arguments_confirmed=[4,5,6],float_o32_arguments_confirmed=[0,1,2,3],full_callee_qualified=False)
 (s.OUT/'callee-prefix-report.json').write_text(json.dumps(report,indent=2)+'\n');return report

def indirect_callers(state):
 table,record=0x8008a0b4,0x50000;rom=state['rom'];elf=(s.FROZEN/'conker/build/conker.us.elf').read_bytes();pointer=struct.pack('>2I',ENTRY,0xffffffff)
 assert rom[0x22ebbc:0x22ebc4]==pointer;at=s.elf_slot_offset(elf,table+72,8);assert elf[at:at+8]==pointer;n=0;seen={0:set(),1:set()}
 for which,seed,ready,status,mode,amount,phase in itertools.product((0,1),(0,255),(0,1),(0,1,256,0xffffffff),(0,9,0xabcd00ff),(-32768,0,32767),(0,8)):
  amount=0 if which==0 else amount;c=Case(seed,ready,status,7,phase,mode,u32(amount),seed%6);initial=fixture(c)
  for i,b in enumerate(pointer):initial[table+72+i]=b
  for i in range(64):initial[record+i]=165
  put(initial,record+14,amount,2);expected,service=reference(initial,c)
  entry,off,num,end=(0x15141b4c,0x16effc,5,0x15141b60)if which==0 else(0x15141bac,0x16f05c,8,0x15141bcc)
  parent=list(struct.unpack_from('>%dI'%num,rom,off));at=s.elf_slot_offset(elf,entry,num*4);assert elf[at:at+num*4]==rom[off:off+num*4]
  connected=dict(zip(range(ENTRY,ENTRY+456,4),state['raw_words']));machine=Oracle(parent,initial,c,entry=entry,connected=connected)
  machine.r[18]=ACTOR;machine.r[19]=mode;machine.r[16]=table;machine.r[14]=table+72;machine.r[12]=9;machine.r[2]=record
  saved={i:machine.r[i]for i in(*range(16,24),28,29,30)};base=machine.record_call;targets=[]
  def record_call(t):
   if t==ENTRY:targets.append(tuple(machine.arguments(3)));assert targets[-1]==(ACTOR,mode,u32(amount))
   else:base(t)
  machine.record_call=record_call;machine.code[end]=0;machine.code=WindowCode(machine.code,machine);machine.code.ends={end}
  try:machine.run()
  except WindowBoundary:pass
  else:raise AssertionError('indirect caller failed to reach its continuation')
  assert len(targets)==1 and public(machine.memory)==public(expected)and machine.service.calls==service.calls
  assert all(machine.r[i]==v for i,v in saved.items())and tuple(machine.f[20:])==machine.saved_fp
  seen[which]|=machine.visits&set(range(entry,entry+4*num,4));n+=1
 assert tuple(map(len,seen.values()))==(5,8)
 report=dict(passes=True,cases=n,caller_windows=['0x15141B4C','0x15141BAC'],visited_words=[5,8],callback_index=9,callback_count=-1,production_windows_and_table_literal=True,complete_parent_qualified=False,source_installed=s.installed(),c_match_credit=0)
 (s.OUT/'indirect-callers-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
