"""Direct paired requests, packed factory/allocator chain, callers and full faults."""
from pathlib import Path
import itertools,json,struct,sys
from functools import lru_cache
from tools.experiments import game_opposed_effect_spawn_150bef7c_match as checkpoint
r,o=checkpoint.ROOT,checkpoint.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_record_factory import STORES
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
ENTRY=0x150BEF7C;FACTORY=0x1516D99C;ALLOCATOR=0x15167A68;HEAP=0x10003C6C;REGISTER=0x15168A4C;OUTPUT=0x50000;MARK=0x51000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
u32=lambda n:n&0xFFFFFFFF
def packet(value,index):
 return (8155,37,u32(380 if index==0 else-380),13,0,80,143,0,0,0,0,0,8,200,10,0,0,0,0,0,40,40,4,0,0,0,0,1365,1365,1365,1365,value&65535,50,0,255,20,4000,2000,1,6,0,1,0,0,0,0,3,255,0)
def fixture(seed=0,phase=0):
 m={STACK+i:(i*17+seed*13+0xA5)&255 for i in range(-640,2304)}
 for start,n in((OUTPUT-16,0x200+32),(MARK,32)):
  m.update({start+i:(i*29+seed*11+0x51)&255 for i in range(n)})
 return m
def public(m):return {a:b for a,b in m.items()if not STACK-640<=a<STACK+2304}
def record_effect(m,address,args):
 m[address]=17;m[address+1]=0;m[address+12]=255
 for offset,index,size in STORES+[(32,31,2),(60,31,1),(59,26,1)]+[(off,ind,1)for off,ind in zip(range(61,65),range(32,36))]+[(28,36,2),(30,37,2),(34,38,2),(65,39,1),(67,40,1),(68,41,1),(69,42,1),(70,43,1),(71,45,1),(72,46,1)]:put(m,address+offset,args[index],size)
 m[address+66]=0
def reference(initial,value,outcomes,connected=False):
 m=initial.copy();calls=[]
 for i in range(2):
  args=packet(value,i);calls.append((FACTORY,args));put(m,MARK+4*i,(args[31]<<16)|(i+1))
  if connected:
   calls.extend([(ALLOCATOR,(17,0,76,0,255,1)),(HEAP,(76,1,0,0,1))])
   if outcomes>>i&1:
    address=OUTPUT+i*0x100;calls.append((REGISTER,(address,17)));record_effect(m,address,args)
 return m,calls
@lru_cache(maxsize=1)
def helper_code():
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();code={}
 for name,entry,offset,n in(('func_1516D99C',FACTORY,0x19AE4C,125),('func_15167A68',ALLOCATOR,0x194F18,28)):
  ws=struct.unpack_from('>%dI'%n,rom,offset);assert elf[elf_slot_offset(elf,entry,4*n):elf_slot_offset(elf,entry,4*n)+4*n]==struct.pack('>%dI'%n,*ws),name
  code.update(zip(range(entry,entry+4*n,4),ws))
 return code
class Oracle(Base):
 def __init__(self,words,initial,value=0,outcomes=3,phase=0,mutation=0,connected=False,entry=ENTRY,extra=None):
  code=helper_code()if connected else{}
  if extra:code.update(extra)
  self.value=value;self.outcomes=outcomes;self.mutation=mutation;self.round=-1;self.connected_chain=connected
  super().__init__(words,initial.copy(),Case(phase=phase),entry=entry,s={},connected=code,arguments=(u32(value),))
 def record_call(self,target):
  counts={ENTRY:1,FACTORY:49,ALLOCATOR:6,HEAP:5,REGISTER:2};assert target in counts,hex(target)
  args=tuple(map(u32,self.arguments(counts[target])));self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==FACTORY:
   self.round+=1;assert 0<=self.round<=1;put(self.memory,MARK+self.round*4,(args[31]<<16)|(self.round+1))
 def hook(self,target):
  i=self.round;answer=0xA5001234+i
  if target==HEAP:answer=OUTPUT+i*0x100 if self.outcomes>>i&1 else 0
  elif target==REGISTER:
   args=self.calls[-1][1];self.put(args[0],args[1],1)
  else:assert target==FACTORY,hex(target)
  if self.mutation:
   put(self.memory,self.target_home,0xCAFE4321+i)
   for j in range(4):put(self.memory,self.r[29]+4*j,0xB5000000+i*16+j)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+i*256+reg
  self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(answer)
def streams():return {label:bound_blob(*payload(o/path,'func_150BEF7C'),S)for label,path in dict(raw='selected-final/candidate.o',padded='qualified-owner/generated_EC420.c.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.trace,m.events,m.calls,m.r,m.f,m.hi,m.lo)
def values():return [0,1,255,256,32767,32768,65535,65536,0x7FFFFFFF,0x80000000,0xFFFFFFFF]+[u32(i*0x01010101^0xCAFE0000)for i in range(64)]
def main():
 programs=streams();visits=set();cases=0;connected_cases=0
 for value,phase,mutation in itertools.product(values(),(0,8),(0,1)):
  initial=fixture(value&255,phase);expected,calls=reference(initial,value,3)
  models=[Oracle(ws,initial,value,phase=phase,mutation=mutation).run()for ws in programs.values()]
  assert state(models[0])==state(models[1])==state(models[2]);assert(public(models[0].memory),models[0].calls)==(public(expected),calls),(value,phase,mutation)
  visits.update(models[0].visits);cases+=1
 for value,outcome,phase,mutation in itertools.product(values()[::3],range(4),(0,8),(0,1)):
  initial=fixture(value&255,phase);expected,calls=reference(initial,value,outcome,True)
  models=[Oracle(ws,initial,value,outcome,phase,mutation,True).run()for ws in programs.values()]
  assert state(models[0])==state(models[1])==state(models[2]);assert(public(models[0].memory),models[0].calls)==(public(expected),calls),(value,outcome,phase,mutation)
  connected_cases+=1
 q=dict(direct_cases_per_stream=cases,complete_factory_chain_cases_per_stream=connected_cases,streams=list(programs),unexecuted_target_words=[i for i in range(94)if ENTRY+4*i not in visits],factory_words=125,allocator_wrapper_words=28,all_49_arguments_and_2_records_and_opaque_bytes_checked=True,full_private_machine_state_three_way_equal=True,source_installed=checkpoint.installed(),matching_credit=0,limits='Complete target and fixed factory/allocator wrapper; heap allocation and registration are bounded providers. No complete dispatcher, hardware or gameplay claim.')
 assert not q['unexecuted_target_words'];(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def faults():
 programs=streams();count=0
 for value,phase,connected,mutation in((0,0,False,0),(0xABCD8001,8,False,1),(0xFFFFFFFF,0,True,1)):
  initial=fixture(value&255,phase);complete=Oracle(programs['retail'],initial,value,3,phase,mutation,connected).run()
  for cut in range(complete.all_accesses):
   states=[]
   for ws in programs.values():
    m=Oracle(ws,initial,value,3,phase,mutation,connected);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Expected fired memory cut')
    states.append(state(m))
   assert states[0]==states[1]==states[2],(value,cut);count+=1
 q=dict(full_memory_GPR_FPR_HI_LO_trace_calls_prefix_triples=count,actual_dispatched_access_cuts=True,source_installed=checkpoint.installed(),matching_credit=0);(o/'faults.json').write_text(json.dumps(q,indent=2)+'\n');return q
def callers():
 programs=streams();rom=(r/'conker/conker.us.bin').read_bytes();count=0
 for window,end,kind in((0x15027058,0x15029BA4,'incoming-home'),(0x1509D534,0x1509D76C,'record-word')):
  words=struct.unpack_from('>4I',rom,window-0x15000000+0x2D4B0)
  for value,phase in itertools.product(values(),(0,8)):
   initial=fixture(value&255,phase);put(initial,STACK+phase+0x6A8,value);put(initial,0x52004,value)
   expected,calls=reference(initial,value,3);states=[]
   for ws in programs.values():
    code=dict(zip(range(ENTRY,ENTRY+376,4),ws));m=Oracle(words,initial,value,3,phase,1,False,window,code);m.r[16]=0x52000;m.before=m.r[:]
    m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller boundary missing')
    assert m.r[2]==1 and public(m.memory)==public(expected)and m.calls==[(ENTRY,(u32(value),)),*calls],(kind,value)
    states.append(state(m))
   assert states[0]==states[1]==states[2];count+=1
 q=dict(real_4_word_caller_windows=2,cases_per_stream=count,loaded_full_word_argument_and_discarded_return_verified=True,source_installed=checkpoint.installed(),matching_credit=0,limits='Original JAL/delay-load and branch/delay-return windows only; complete dispatchers are not executed.')
 (o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');return q
if __name__=='__main__':
 main();print(json.dumps(faults()),flush=True);print(json.dumps(callers()),flush=True)
