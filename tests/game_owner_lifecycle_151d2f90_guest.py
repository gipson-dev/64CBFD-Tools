"""Independent lifecycle, reload/alias model and complete literal fault states."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_owner_lifecycle_151d2f90_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;ENTRY=0x151D2F90;RECORD=0x30000;ACTOR=0xA0000;FOLLOW=0x50000;OTHER_ACTOR=0xB0000;MARK=0x90000;DELTA=0x800BE9E4;TABLES=(0x8008FC4C,0x8008FC50,0x8008FC54,0x8008FC58);TARGETS=(0x1518F7C4,0x1518F89C,0x151D33B8,0x1518F858);FREE=0x1516972C;u32=lambda v:v&0xFFFFFFFF;half=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 object:int=RECORD
 actor:int=ACTOR
 gate:int=0
 flags:int=0
 available:int=1
 low_mode:int=0
 lifetime:int=300
 delta:int=1
 update:int=0
 expired:int=0
 answer:int=1
 mutation:int=0
 phase:int=0
 seed:int=0
def symbols():return dict(func_1516972C=FREE,D_800BE9E4=DELTA,**dict(zip(('D_8008FC4C','D_8008FC50','D_8008FC54','D_8008FC58'),TABLES)))
@lru_cache(None)
def retained():
 rom=(r/'conker/conker.us.bin').read_bytes();blob=rom[0x23470C:0x23471C];assert struct.unpack('>4I',blob)==TARGETS;old=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(old,TABLES[0],16);assert old[at:at+16]==blob;return blob
def public(memory,c):return{a:v for a,v in memory.items()if not STACK+c.phase-2048<=a<STACK+c.phase+1024}
def fixture(c):
 stack=set(range(STACK+c.phase-2048,STACK+c.phase+1024));assert all(not stack&set(range(base-16,base+0x230))for base in(c.object,c.actor,FOLLOW,OTHER_ACTOR)),'Actor/record bank accidentally overlaps oracle stack'
 m={STACK+c.phase+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for base in(c.object,c.actor,FOLLOW,OTHER_ACTOR):m.update({u32(base+i):(i*29+c.seed*11+0x5A)&255 for i in range(-16,0x230)})
 for i,v in enumerate(retained()):m[TABLES[0]+i]=v
 put(m,DELTA,c.delta)
 for actor in(c.actor,OTHER_ACTOR):
  put(m,actor,0 if c.gate==1 else 1);m[actor+4]=255 if c.gate==2 else 1;m[actor+0x3B]=42;m[actor+0x74]=c.low_mode;put(m,actor+0x1D4,0x12345000 if c.available else 0)
 for p,a in((c.object,c.actor),(FOLLOW,OTHER_ACTOR)):
  put(m,p+0x10,a);m[p+0x14]=43 if c.gate==3 else 42;put(m,p+0x16,c.lifetime,2);m[p+0x18]=c.flags;m[p+0x19]=c.update&255;m[p+0x1A]=m[p+0x1B]=0;m[p+0x1C]=c.expired&255
 put(m,MARK,0);return m
def effect(memory,c,stage,record,home):
 put(memory,MARK,read(memory,MARK)+1)
 if stage in(1,2,3):
  if c.mutation&1:
   memory[record+0x19]=255 if c.update==0 else 0;memory[record+0x18]^=0x81;put(memory,record+0x16,-3,2);put(memory,DELTA,0x80000001)
  if c.mutation&2:put(memory,home,FOLLOW);memory[FOLLOW+0x19]=0;put(memory,FOLLOW+0x24,0x76543210)
 if stage==4:put(memory,MARK+4,record)
def reference(initial,c,home=None,record=None):
 m=dict(initial);p=c.object if record is None else record;home=STACK+c.phase if home is None else home;calls=[];a=read(m,p+0x10);was=m[p+0x18]&2
 def call(stage):
  nonlocal p
  target=FREE if stage==4 else TARGETS[stage];calls.append((target,(p,)))
  if stage!=4:put(m,home,p)
  effect(m,c,stage,p,home)
  if stage!=4:p=read(m,home)
 if read(m,a)==0 or m[a+4]==255 or m[p+0x14]!=m[a+0x3B]:call(4);return m,calls
 m[p+0x18]=(m[p+0x18]|2)if read(m,a+0x1D4)!=0 and m[a+0x74]&15!=15 else(m[p+0x18]&253)
 if m[p+0x18]&1:
  put(m,p+0x16,u32(half(read(m,p+0x16,2))-read(m,DELTA)),2)
  if half(read(m,p+0x16,2))<0:
   if m[p+0x1C]!=255:assert m[p+0x1C]==0;call(3)
   call(4);return m,calls
 now=m[p+0x18]&2
 if now!=was:call(1 if now else 2)
 if m[p+0x19]!=255:
  assert m[p+0x19]==0;call(0)
  if u32(c.answer)==0:call(4)
 return m,calls
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;self.before_f=None;super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(c.object,)if arguments is None else arguments,s=symbols(),connected=connected);self.initial=dict(self.memory);self.before_f=self.f[:];self.fcsr=(c.seed&3)|4
 def record_call(self,t):
  assert t in(*TARGETS,FREE),hex(t);args=tuple(self.arguments(1));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  stage=4 if t==FREE else TARGETS.index(t);effect(self.memory,self.c,stage,self.calls[-1][1][0],STACK+self.c.phase)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(self.c.answer)if stage==0 else 0xDEADC0DE
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.current_pc,m.delay_of,m.condition,m.trace)
def check(words,c):
 m=Machine(words,c).run();memory,calls=reference(m.initial,c);assert(public(m.memory,c),m.calls)==(public(memory,c),calls),dict(case=str(c),actual=m.calls,wanted=calls);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(flags=f,available=a,low_mode=mode,lifetime=life,delta=d,update=s,expired=s,answer=answer)for f,a,mode,life,d,s,answer in itertools.product((0,1,2,3,252,255),(0,1),(0,15),(-1,0,32767),(0,1,0xFFFFFFFF),(-1,0),(0,0xFFFFFFFF))]
 rows +=[Case(gate=gate,flags=f,available=a,lifetime=life)for gate,f,a,life in itertools.product((1,2,3),(0,1,2,3,252,255),(0,1),(-32768,32767))]
 rows +=[Case(flags=f,available=a,update=u,expired=e,answer=answer,mutation=mutation,phase=phase)for f,a,(u,e),answer,mutation,phase in itertools.product((0,1,2,3),(0,1),((-1,-1),(0,0),(-1,0),(0,-1)),(0,1),(1,2,3),(0,8))]
 rows +=[Case(object=p,actor=a,flags=f,lifetime=-32768,delta=d,mutation=mutation)for p,a,f,d,mutation in((RECORD,RECORD,3,1,0),(RECORD,RECORD,2,1,3),(DELTA-0x18,ACTOR,3,1,0),(DELTA-0x14,ACTOR,1,0x80000000,1))]
 return[replace(c,seed=i)for i,c in enumerate(rows)]
def main():
 control_flow()
 streams=[bound_blob(*payload(o/f,'func_151D2F90'),symbols())for f in('original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o')];assert all(w==streams[0]for w in streams);seen=set();rows=cases()
 for c in rows:
  models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+416)
 cuts=0
 for c in(Case(),Case(gate=1),Case(flags=1,lifetime=0,mutation=2),Case(flags=2,available=0,mutation=3,phase=8),Case(object=DELTA-0x18,flags=3)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);cuts+=1
 # Four retail instructions are orphan copies after unconditional branches.
 # Preserve their exact words; do not pretend the normal entry executes them.
 unreachable={ENTRY+at for at in(0x54,0x88,0xF4,0x134)};assert seen==set(range(ENTRY,ENTRY+416,4))-unreachable,(len(seen),sorted(set(range(ENTRY,ENTRY+416,4))-seen))
 q=dict(cases_per_stream=len(rows),streams=5,preserved_words=104,executed_words=len(seen),unreachable_orphan_copy_offsets=['0x54','0x88','0xF4','0x134'],fault_prefix_quintuples=cuts,full_private_memory_GPR_FPR_HILO_FCSR_trace_and_fault_states_equal=True,independent_public_memory_calls_reference=True,owner_gates_attachment_transitions_signed_clocks_and_status_expiry=True,callback_mutations_incoming_home_redirection_actor_and_global_delta_aliases=True,callback_tables16bytes_pinned_and_valid_indices_zero_or_sentinel=True,other_services_opaque_and_void_return_not_claimed=True,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def control_flow():
 import hashlib
 raw,refs=payload(o/'original-target.o','func_151D2F90');words=list(struct.unpack('>104I',raw));todo=[0];seen=set();calls=[]
 while todo:
  at=todo.pop()
  if at in seen:continue
  assert 0<=at<len(raw)and at%4==0,hex(at);seen.add(at);w=words[at//4];op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
  if op in(1,4,5,6,7,20,21,22,23):
   imm=((w&65535)^32768)-32768;target=at+4+4*imm;seen.add(at+4);todo.append(target)
   if not(op==4 and rs==rt==0):todo.append(at+8)
  elif op==3 or(op==0 and fn==9):seen.add(at+4);todo.append(at+8);calls.append(at)
  elif op==0 and fn==8:assert rs==31;seen.add(at+4)
  else:assert op!=2;todo.append(at+4)
 missing=set(range(0,416,4))-seen;assert missing=={0x54,0x88,0xF4,0x134};assert all(words[(at-8)//4]>>26==4 and words[(at-8)//4]>>16&1023==0 for at in missing)
 q=dict(preserved_words=104,reachable_normal_entry_words=len(seen),unreachable_offsets=[hex(at)for at in sorted(missing)],orphan_instructions_after_unconditional_branch_delay=True,opaque_calls_assumed_returning_and_JR_RA_exit_only=True,conditional_and_likely_true_false_paths_conservatively_included=True,original_raw_sha256=hashlib.sha256(raw).hexdigest(),source_installed=target_packet.installed(),matching_credit=0);(o/'private-cfg.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
