"""Independent public model, adversarial providers and literal caller window."""
from dataclasses import dataclass
import json,struct
from tools.experiments import game_resource_cache_sweep_15114a1c_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_resource_cache_sweep_15114a1c_symbolic import proof
r,o=p.ROOT,p.OUT;ENTRY=0x15114A1C
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
RECORDS=(0x30000,0x31000);TABLES=(0x50000,0x51000);AGES=(0x60000,0x61000);RESOURCES=(0x70000,0x71000)
u32=lambda x:x&0xffffffff
signed=lambda x:((x&0xffffffff)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 seed:int=0
 count:int=8
 mutation:int=0
 phase:int=0
def cases():
 for seed in range(512):yield Case(seed,(-2147483648,-1,0,1,2,4,7,8)[seed%8],(seed//8)%16,8*(seed&1))
 for seed in range(64):yield Case(seed+1024,8,seed%16,8*(seed&1))
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2304)}
 for bank in range(2):
  for base,n in((RECORDS[bank],1280),(TABLES[bank],32),(AGES[bank],8),(RESOURCES[bank],32)):
   m.update({base+i:(i*29+c.seed*11+0x51)&255 for i in range(-16,n+16)})
  for i in range(8):
   k=c.seed+i*13+bank*7;record=RECORDS[bank]+160*i;m[record+0x70]=(k*7)&255;m[record+0x6f]=(k*17)&255;m[record+0x4e]=(0,3,255,2)[(k//2)%4];m[AGES[bank]+i]=(0,1,2,127,128,255)[k%6]
   put(m,TABLES[bank]+4*i,0 if k%5==0 else RESOURCES[bank]+4*i);put(m,RESOURCES[bank]+4*i,0xc0de0000+bank*16+i)
 put(m,s['D_800DBEF0'],c.count)
 for name,bases in(('D_800DBEF4',RECORDS),('D_800DBEF8',TABLES),('D_800DBEFC',AGES)):put(m,s[name],bases[0])
 return m
def service(m,c,address,step,s):
 put(m,address,0xab000000+step)
 if step==1:
  if c.mutation&1:put(m,s['D_800DBEF8'],TABLES[1])
  if c.mutation&2:put(m,s['D_800DBEF4'],RECORDS[1]);put(m,s['D_800DBEFC'],AGES[1])
  if c.mutation&4:put(m,s['D_800DBEF0'],8)
  if c.mutation&8:put(m,s['D_800DBEF0'],-1)
 if c.mutation&2:
  bank=1 if step==1 else 0;m[RECORDS[bank]+7*160+0x70]^=1;m[AGES[bank]+7]=0
def reference(initial,c,s=None):
 s=S if s is None else s;m=initial.copy();calls=[];i=0
 while i<signed(read(m,s['D_800DBEF0'])):
  assert i<8,'Provider count exceeds allocated array contract'
  record=read(m,s['D_800DBEF4'])+i*160;flags=m[record+0x6f]
  owned=m[record+0x70]&1;table=read(m,s['D_800DBEF8']);resource=read(m,table+4*i)
  if owned:
   if not flags&128:put(m,table+4*i,0)
  elif resource:
   if m[record+0x4e]==3 or flags&128:
    age=read(m,s['D_800DBEFC'])+i
    if m[age]:m[age]-=1;i+=1;continue
   calls.append((s['func_10004074'],(resource,)));service(m,c,resource,len(calls),s)
   put(m,read(m,s['D_800DBEF8'])+4*i,0)
  i+=1
 return m,calls
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=S if s is None else s;self.free_count=0
  super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=(0x12345678,0xfedcba98,0x87654321,0xabcdef01))
  self.fp_before=list(self.f)
 def record_call(self,target):
  assert target in(self.s['func_10004074'],ENTRY),hex(target)
  a=tuple(map(u32,self.arguments(1)))if target!=ENTRY else();self.calls.append((target,a));self.events.append(('CALL',target,a))
 def hook(self,target):
  assert target==self.s['func_10004074'];self.free_count+=1;service(self.memory,self.c,self.calls[-1][1][0],self.free_count,self.s)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.dispatched_word)
def streams():return{label:bound_blob(*payload(o/path,p.FUNCTION),S)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def check(m,initial,c,s=None,caller=False):
 expected,calls=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert m.calls==([(ENTRY,())]if caller else[])+calls,(c,'calls',m.calls,calls)
 assert m.r[16:24]==m.before[16:24]and m.r[28:31]==m.before[28:31],(c,'saved')
 if not caller:assert m.r[31]==m.before[31]
 assert m.f[20:]==m.fp_before[20:]
def main():
 programs=streams();assert struct.pack('>94I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x141ecc:0x142044];sy=proof(programs['raw'],programs['retail']);visits=set();count=0
 for c in cases():
  initial=fixture(c);models=[]
  for label,words in programs.items():m=Oracle(words,initial,c);m.run();check(m,initial,c);models.append(m)
  assert state(models[1])==state(models[2])==state(models[3]);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,independent_public_memory_and_ordered_calls_equal=True,normalized_full_register_private_memory_and_trace_equal=True,unexecuted_original_words=[i for i in range(94)if ENTRY+4*i not in visits],symbolic=sy,source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def faults():
 programs=list(streams().values())[1:];count=0
 for c in(Case(1024),Case(1031,8,15),Case(1026,8,7),Case(1037,8,3),Case(4,0),Case(9,-1)):
  initial=fixture(c);complete=Oracle(programs[-1],initial,c);complete.run()
  for cut in range(complete.all_accesses):
   states=[]
   for words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access boundary did not fire')
    states.append(state(m))
   assert states[0]==states[1]==states[2];count+=1
 q=dict(normalized_complete_access_prefix_triples=count,raw_C_fault_identity_claimed=False);(o/'faults.json').write_text(json.dumps(q,indent=2)+'\n');return q
def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();needle=struct.pack('>4I',0x0d445287,0,0x0d45f3f1,0);at=rom.find(needle);assert at>=0 and rom.find(needle,at+1)==-1
 start=0x15000000+at-0x2d4b0;window=struct.unpack('>2I',needle[:8]);count=0
 for c in list(cases())[::12]:
  initial=fixture(c)
  for words in streams().values():
   m=Oracle(window,initial,c,entry=start,connected=dict(zip(range(ENTRY,ENTRY+4*len(words),4),words)));m.code[start+8]=0;m.code=WindowCode(m.code,m);m.code.ends={start+8}
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Actual caller continuation not reached')
   check(m,initial,c,caller=True)
  count+=1
 q=dict(actual_caller_window_address=hex(start),actual_words=2,next_call_is_func_1517CFC4=True,cases_per_stream=count,complete_caller_owner_code_bindings_and_production_object_unchanged=True,scope='Literal JAL and delay slot through target return; not the entire rendering loop or release-helper implementation.');(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');return q
if __name__=='__main__':main();print(json.dumps(faults()));print(json.dumps(callers()))
