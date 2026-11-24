"""Seeded descriptor, finite conversion domain, original radial caller window."""
from dataclasses import dataclass,replace
import json,math,struct
from tools.experiments import game_random_spray_150c2558_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
r,o=p.ROOT,p.OUT;ENTRY=0x150c2558;RNG=0x150ada68;HELPER=0x15151a38;COEFFICIENT=0x800a0270
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
FIELDS=[(12,4,0x41b00000),(16,4,0x42300000),(20,4,0),(24,4,0),(28,4,0x43480000),(32,4,0x43160000),(36,2,1),(38,2,0),(42,2,9),(44,2,0),(46,2,0),(48,2,3),(50,2,3),(52,2,40),(54,2,21),(56,1,11),(57,1,1),(58,1,40),(60,4,1),(64,4,4),(68,4,0),(72,4,0),(76,4,0),(80,4,0),(84,1,255),(85,1,255),(86,1,0),(88,4,3),(92,4,255),(96,4,0),(100,4,0x220005),(104,4,0x1d0600),(108,4,1),(112,4,59),(116,4,128),(120,4,32),(124,1,0),(125,1,7),(128,2,12),(130,2,21)]
@dataclass(frozen=True)
class Case:
 channel:int=0;seed:int=0;phase:int=0;x:int=0x3fa00000;y:int=0xc0200000;z:int=0x40700000;random:int=0x3f000000;coefficient:int=0x3d8f9c19;mutation:int=0
def cases():
 shapes=[(0,0x80000000,0,0,0x3d8f9c19),(0x7fc12345,0xffcabcde,0xc47a0000,0x3f7fffff,0x3d8f9c19),(0x3f800000,0xbf800000,0x447a0000,0x3e800000,0xbe000000),(1,0x807fffff,0x40800000,0x3f000000,0x3f800000)]
 for channel in range(256):
  for k,(x,y,z,v,c)in enumerate(shapes):yield Case(0xabcd0000|channel,channel^k,8*(k&1),x,y,z,v,c,k&1)
 for z in [0xcf000000,0x4effffff,0xc7000000,0x47000000]:yield Case(0xffffffff,91,8,0x3f800000,0xbf800000,z,0,0x3f800000,0)
def arguments(c):return(1,7,c.x,c.y,c.z,0x12345678,0x87654321,0x80000000,0x81,0x7f,0x40000000,0xabcdef01,0x40800000,0x12345678,c.channel)
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2304)};put(m,s['D_800A0270'],c.coefficient);put(m,0x70000,0x13579bdf);return m
def values(c):
 first=bits(floating(c.z)+15.0);second=bits(floating(c.random)*30.0);z=bits(floating(first)-floating(second));coefficient=bits(.125)if c.mutation else c.coefficient;scaled=bits(floating(z)*floating(coefficient));v=floating(scaled);assert math.isfinite(v)and -2147483648<=v<2147483648
 return z,(math.trunc(v)-64)&65535
def expected(initial,base,c):
 m=dict(initial);z,angle=values(c)
 for at,width,value in FIELDS+[(0,4,c.x),(4,4,c.y),(8,4,z),(40,2,angle)]:put(m,base+at,value,width)
 return bytes(m[base+i]for i in range(136))
class ConversionBoundary(Exception):pass
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None,args=None):
  syms=S if s is None else s;super().__init__(words,initial,c,entry=entry,s=syms,arguments=arguments(c)if args is None else args,connected=connected);self.s=syms;self.before=self.r[:];self.fp_before=self.f[:];self.snapshots=[];self.random_prefix=[];self.target_home=STACK+c.phase
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==13:
   v=floating(self.f[w>>11&31])
   if not math.isfinite(v)or not -2147483648<=v<2147483648:raise ConversionBoundary
   self.f[w>>6&31]=math.trunc(v)&0xffffffff;return
  return super().execute(w)
 def record_call(self,t):
  assert t in [ENTRY,self.s['func_150ADA68'],self.s['func_15151A38']];n=15 if t==ENTRY else 0 if t==self.s['func_150ADA68']else 3;a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==ENTRY:self.target_home=self.r[29]
  elif t==self.s['func_150ADA68']:self.random_prefix.append(bytes(self.memory[self.r[29]+24+i]for i in range(8)))
  else:self.snapshots.append(bytes(self.memory[a[0]+i]for i in range(136)))
 def hook(self,t):
  c=self.case
  if t==self.s['func_150ADA68']:
   if c.mutation:put(self.memory,self.s['D_800A0270'],bits(.125))
   answer=c.random
  else:
   assert t==self.s['func_15151A38'];a=self.calls[-1][1];assert a[1:]==(c.channel&255,1)
   if c.mutation:
    for i in range(136):self.memory[a[0]+i]^=0x55
   put(self.memory,0x70000,0xcafebabe);answer=0xdeadbeef
  for i in range(4):put(self.memory,self.r[29]+i*4,0xb5000000+i)
  for reg in [1,2,3,*range(4,16),24,25]:self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=0xdeadbeef;self.lo=0x12345678
  if t==self.s['func_150ADA68']:self.f[0]=answer
def streams(s=None):
 s=S if s is None else s
 return {label:bound_blob(*payload(path,p.FUNCTION),s)for label,path in [('retail',o/'original-target.o'),('raw',o/'selected-final/owner-candidate.o'),('generic',o/'qualified-owner/generic.o'),('generated',o/'qualified-owner/generated.o')]}
def state(m):return m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.snapshots,m.trace,m.events,m.random_prefix
def main():
 programs=streams();assert struct.pack('>106I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0xefa08:0xefbb0];count=0;visited=set()
 for c in cases():
  initial=fixture(c);home=STACK+c.phase;base=home-136;models=[]
  for words in programs.values():
   m=Oracle(words,initial,c);m.run();assert m.snapshots==[expected(initial,base,c)];assert m.random_prefix==[struct.pack('>II',c.x,c.y)];assert m.calls==[(RNG,()),(HELPER,(base,c.channel&255,1))];assert m.r[2]==1 and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.fp_before[20:];models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]);visited|=models[0].visits;count+=1
 invalid=0
 for z in [0x7fc12345,0x7f800000,0xff800000,0x4f000000]:
  c=Case(z=z,coefficient=0x3f800000,random=0);initial=fixture(c);models=[]
  for words in programs.values():
   m=Oracle(words,initial,c)
   try:m.run()
   except ConversionBoundary:pass
   else:raise AssertionError('invalid conversion accepted')
   models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]);invalid+=1
 q=dict(cases_per_stream=count,streams=4,visited_words=sum(ENTRY+4*i in visited for i in range(106)),all136_packet_bytes_and_machine_states_equal=True,INT32_MIN_unsigned_subtract_case=True,invalid_conversion_identical_preboundary_quads=invalid,invalid_C_cast_result_unclaimed=True,arbitrary_FCSR_relation_from_independent_block_proof=True,source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 count=0;programs={k:v for k,v in streams().items()if k!='raw'}
 for c in [Case(),Case(0xffffffff,9,8,mutation=1)]:
  initial=fixture(c);full=Oracle(programs['retail'],initial,c);full.run()
  for cut in range(full.all_accesses):
   states=[]
   for words in programs.values():
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('missing fault')
    states.append(state(m))
   assert all(v==states[0]for v in states);count+=1
 q=dict(normalized_retail_fault_prefix_triples=count,raw_prefix_excluded=True);(o/'faults.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();parent=struct.unpack_from('>16I',rom,0x179874);begin,end,zero=0x1514c3c4,0x1514c404,0x1514c42c;count=controls=0
 class CallerCode(WindowCode):
  def __getitem__(self,pc):
   if pc in self.ends:self.owner.stopped_pc=pc
   return super().__getitem__(pc)
 for c in [Case(channel=a,seed=a,phase=8*(a&1),mutation=a&1)for a in [0,1,127,128,255]]:
  initial=fixture(c);models=[]
  for label,body in streams().items():
   def machine(target):
    code=dict(zip(range(ENTRY,ENTRY+424,4),target));code[end]=code[zero]=0;m=Oracle(parent,initial,c,entry=begin,connected=code,args=(1,7,c.x,c.y));m.r[2]=ENTRY;m.r[18]=0x81;m.r[20]=8;m.r[22]=9;m.r[23]=10;m.r[30]=c.channel&255
    for reg,v in [(2,c.z),(6,bits(1.25)),(22,bits(2.)),(24,c.y),(26,bits(0.)),(28,c.z),(30,bits(4.))]:m.f[reg]=v
    m.code=CallerCode(m.code,m);m.code.ends=(end,zero);return m
   m=machine(body)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('window escaped')
   expected_args=(1,7,c.x,c.y,c.z,bits(0.),c.y,c.z,0x81,8,bits(2.),9,bits(4.),10,c.channel&255);assert m.calls[0]==(ENTRY,expected_args);assert m.r[2]==1 and m.stopped_pc==end;assert m.snapshots==[expected(initial,STACK+c.phase-136,c)];models.append(m)
   if count==0:
    wrong=list(body);assert wrong[-5]==0x24020001;wrong[-5]=0x24020000;bad=machine(wrong)
    try:bad.run()
    except WindowBoundary:pass
    else:raise AssertionError('return control escaped')
    assert bad.r[2]==0 and bad.stopped_pc==zero;controls+=1
  assert all(state(m)==state(models[0])for m in models[1:]);count+=1
 q=dict(original_caller_window_words=16,cases_per_stream=count,all15_argument_words_checked=True,effective_return_zero_controls=controls,registry='D_8008AA00[1]',complete_parent_execution_claim=False,helper_ABI_reused_unchanged_from_N17=True);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();faults();callers()
