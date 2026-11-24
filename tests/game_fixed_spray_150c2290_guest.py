"""Defined packet fields, seeded retained bytes, caller window and ABI stub."""
from dataclasses import dataclass
import json,struct
from tools.experiments import game_fixed_spray_150c2290_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
r,o=p.ROOT,p.OUT;ENTRY=0x150c2290;HELPER=0x15151a38
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
# Independent literal packet specification: offset, width, value. Float source
# addresses are handled separately. No observations read uninitialized C fields.
FIELDS=[(4,4,0x42200000),(16,4,0x421c0000),(24,4,0x3f800000),(28,4,0x42c80000),(32,4,0x42660000),(36,2,2),(38,2,3),(40,2,-41),(42,2,21),(44,2,-22),(46,2,22),(48,2,7),(50,2,0),(52,2,48),(54,2,21),(56,1,11),(57,1,1),(58,1,40),(60,4,1),(64,4,4),(68,4,0),(72,4,0),(76,4,0),(80,4,0),(84,1,255),(85,1,255),(86,1,0),(88,4,3),(92,4,255),(96,4,0),(100,4,0x220005),(104,4,0x1d0600),(108,4,1),(112,4,59),(116,4,128),(120,4,32),(124,1,0),(125,1,7),(128,2,12),(130,2,21)]
FLOATS=[(0,'D_800A0258'),(8,'D_800A025C'),(12,'D_800A0260'),(20,'D_800A0264')]
@dataclass(frozen=True)
class Case:
 channel:int=0;seed:int=0;phase:int=0;pattern:int=0;mutation:int=0
def cases():
 for channel in range(256):
  for pattern in range(4):yield Case((0,0xabcd0000,0x80000000,0xffffff00)[pattern]|channel,channel^pattern,8*(pattern&1),pattern,pattern&1)
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2304)}
 patterns=[(0,0x80000000,0x3f800000,0xbf800000),(1,0x007fffff,0x7f7fffff,0xff7fffff),(0x7f800000,0xff800000,0x7fc12345,0xffcabcde),(0x7f800001,0xff800001,0x12345678,0x87654321)]
 for (_,n),v in zip(FLOATS,patterns[c.pattern]):put(m,s[n],v)
 put(m,0x70000,0x13579bdf);return m
def expected(initial,base,s=None):
 s=S if s is None else s;m=dict(initial)
 for at,width,value in FIELDS:put(m,base+at,value,width)
 for at,n in FLOATS:put(m,base+at,read(initial,s[n]))
 return bytes(m[base+i]for i in range(136))
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None,arguments=None):
  super().__init__(words,initial,c,entry=entry,s=S if s is None else s,arguments=(c.channel,)if arguments is None else arguments,connected=connected)
  self.s=S if s is None else s;self.before=self.r[:];self.fp_before=self.f[:];self.snapshots=[]
 def record_call(self,t):
  assert t in(ENTRY,self.s['func_15151A38']);n=1 if t==ENTRY else 3;a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t!=ENTRY:self.snapshots.append(bytes(self.memory[a[0]+i]for i in range(136)))
 def hook(self,t):
  assert t==self.s['func_15151A38'];a=self.calls[-1][1];assert a[1:]==(self.case.channel&255,1)
  if self.case.mutation:
   for i in range(136):self.memory[a[0]+i]^=0x55
   for _,n in FLOATS:put(self.memory,self.s[n],0xdeadbeef)
  put(self.memory,0x70000,0xcafebabe)
  for i in range(4):put(self.memory,self.r[29]+i*4,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=0xdeadbeef;self.lo=0x12345678
def streams(s=None):
 s=S if s is None else s
 return {label:bound_blob(*payload(path,ENTRY_NAME),s)for label,path in [('retail',o/'original-target.o'),('raw',o/'selected-final/owner-candidate.o'),('generic',o/'qualified-owner/generic.o'),('generated',o/'qualified-owner/generated.o')]}
ENTRY_NAME='func_150C2290'
def state(m):return m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.snapshots,m.trace,m.events
def main():
 programs=streams();assert len({tuple(v)for k,v in programs.items()if k!='raw'})==1;assert struct.pack('>101I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0xef740:0xef8d4];count=0;visited=set()
 for c in cases():
  initial=fixture(c);base=STACK+c.phase-160+24;want=expected(initial,base);models=[]
  for label,words in programs.items():
   m=Oracle(words,initial,c);m.run();assert m.snapshots==[want];assert m.calls==[(HELPER,(base,c.channel&255,1))];assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.fp_before[20:];models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]);visited|=models[0].visits;count+=1
 q=dict(cases_per_stream=count,streams=4,visited_words=sum(ENTRY+4*i in visited for i in range(101)),all_136_seeded_packet_bytes_registers_and_memory_traces_equal=True,no_FPU_arithmetic=True,source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 count=0;programs={k:v for k,v in streams().items()if k!='raw'}
 for c in [Case(),Case(0xffffffff,7,8,3,1)]:
  initial=fixture(c);full=Oracle(programs['retail'],initial,c);full.run()
  for cut in range(full.all_accesses):
   result=[]
   for words in programs.values():
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('cut did not fire')
    result.append(state(m))
   assert all(s==result[0]for s in result);count+=1
 q=dict(normalized_retail_fault_prefix_triples=count,raw_fault_prefix_excluded=True,portable_C_fault_claim=False);(o/'faults.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();begin,end=0x150295e0,0x150295ec;words=struct.unpack_from('>3I',rom,0x56a90);count=0
 for c in [Case(0),Case(255,7,8,3,1),Case(0x87654321,91,0,1)]:
  initial=fixture(c);put(initial,STACK+c.phase+0xe0,c.channel);base=STACK+c.phase-160+24;want=expected(initial,base);models=[]
  for label,target in streams().items():
   code=dict(zip(range(ENTRY,ENTRY+404,4),target));code[end]=0;m=Oracle(words,initial,c,entry=begin,connected=code);m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('window escaped')
   assert m.snapshots==[want]and m.r[31]==end and m.r[29]==STACK+c.phase;models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]);count+=1
 # ABI-only stub: all three homes are permitted; descriptor/saved ABI fixed.
 helper=payload(o/'selected-final/helper-candidate.o','func_15151A38');assert helper==(bytes.fromhex('afa40000afa50004afa6000803e0000800000000'),{})
 stub=bound_blob(*helper,S)
 for c in [Case(),Case(255,9,8,3)]:
  initial=fixture(c);a=(0x50000,c.channel,0xffffffff);m=Oracle(stub,initial,c,entry=HELPER,arguments=a);m.run();want=dict(initial)
  for i,v in enumerate(a):put(want,STACK+c.phase+i*4,v)
  assert m.memory==want and m.r==m.before and m.f==m.fp_before
 q=dict(original_caller_window_words=3,cases_per_stream=count,helper_ABI_only_words=5,helper_matching_credit=0,helper_stub_cases=2,void_result_uncompared=True,enclosing_caller_and_original_helper_implementation_claim=False);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();faults();callers()
