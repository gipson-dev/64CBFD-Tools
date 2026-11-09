import itertools,json,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments import game_secondary_camera_position_1512e4b0_match as match
root=match.ROOT;out=root/match.BUILD
from tools.tests import game_secondary_camera_position_1512e4b0_oracle as guest
from tools.tests import game_camera_transition_dispatch_15128540_oracle as legacy
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
PARENT=legacy.ENTRY
@dataclass(frozen=True)
class Plan:
 flags:int=1<<20
 first:int=0
 busy:int=0
 fallback:int=0
 mutation:int=0
 override:int=0

def observation(m,c,t):return(t,guest.read(m,c.camera+0x2C),tuple(guest.read(m,c.camera+j)for j in(0x2BC,0x2C0,0x2C4,0x2F8,0x2FC,0x300)),m[c.camera+0x23D])
def effect(m,c,p,t):
 if(t==legacy.PREDICATE and p.mutation&1)or(t==legacy.BUSY and p.mutation&2):guest.put(m,c.camera+0x2C,p.override)
 guest.put(m,c.camera+0x310,t^p.mutation)
def returned(p,t):return p.first if t==legacy.PREDICATE else p.busy if t==legacy.BUSY else p.fallback if t==legacy.FALLBACK else 0x87654321
def reference(initial,c,p):
 m=dict(initial);calls=[];snapshots=[];home=guest.STACK+c.phase-0x20
 def call(t):
  calls.append((t,(c.camera,)));snapshots.append(observation(m,c,t));effect(m,c,p,t);return returned(p,t)
 if call(legacy.PREDICATE):return m,calls,snapshots,1
 if call(legacy.BUSY):return m,calls,snapshots,0
 flags=guest.read(m,c.camera+0x2C);pick=next((t for bit,t in zip((19,20,21,22),(legacy.FIRST,legacy.SECOND,legacy.THIRD,legacy.FOURTH))if flags&(1<<bit)),None)
 if pick is not None:
  if pick==legacy.SECOND:
   calls.append((pick,(c.camera,)));snapshots.append(observation(m,c,pick))
   m,child_calls,child_snaps,_,_=guest.reference(m,c,home);calls.extend(child_calls);snapshots.extend(child_snaps)
  else:call(pick)
  if pick==legacy.FIRST:
   words=[guest.read(m,c.camera+0x2A4+j*4)for j in range(3)]
   for j,w in enumerate(words):guest.put(m,c.camera+0x2BC+j*4,w)
   call(legacy.INITIALIZE)
  call(legacy.UPDATE);call(legacy.FINISH);return m,calls,snapshots,1
 if call(legacy.FALLBACK):call(legacy.FINISH);return m,calls,snapshots,1
 return m,calls,snapshots,0

class Dispatcher(guest.Oracle):
 def __init__(self,words,initial,c,p,target,mode):
  self.plan=p;self.model=mode=='model';self.target_seen=False
  connected={}if self.model else dict(zip(range(guest.ENTRY,guest.ENTRY+308,4),target))
  super().__init__(words,initial,c,entry=PARENT,connected=connected)
 def in_target(self):return guest.ENTRY<=self.current_pc<guest.ENTRY+308
 def record_call(self,t):
  if t in(guest.SIN,guest.COS):return super().record_call(t)
  assert t in legacy.HELPERS,(hex(t),hex(self.current_pc))
  args=self.arguments(1);assert args==(self.case.camera,)
  self.calls.append((t,args));self.snapshots.append(observation(self.memory,self.case,t));self.events.append(('CALL',t,args))
  if t==guest.ENTRY:self.target_seen=True;self.semantic_home=self.r[29]
 def clobber(self,value):
  for j in range(4):self.put(self.r[29]+j*4,0xB5000000+j,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
 def hook(self,t):
  if t in(guest.SIN,guest.COS):return super().hook(t)
  if t==guest.ENTRY:
   assert self.model
   m,calls,snaps,_,_=guest.reference(self.memory,self.case,self.semantic_home)
   self.memory=m;self.calls.extend(calls);self.snapshots.extend(snaps);self.clobber(0x87654321)
  else:effect(self.memory,self.case,self.plan,t);self.clobber(returned(self.plan,t))

def cases():
 for flags,mode,view,phase in itertools.product(range(16),range(4),(0,3),(0,8)):
  p=Plan(flags=flags<<19,first=(0,1,0x80000000,0)[mode],busy=0x80000000 if mode==3 else 0,fallback=1)
  yield guest.Case(view=view,heading=0x8000,speed=guest.bits(.125),phase=phase),p
 for mutation,mode in itertools.product(range(128),range(4)):
  p=Plan(mutation=mode,override=(0 if mode==1 else 1<<19 if mode==2 else 1<<20))
  yield guest.Case(view=3 if mutation&2 else 0,heading=0xFFFF,speed=guest.bits(17.25),mutation=mutation,phase=(mutation&1)*8),p

def caller_checks():
 rom=(root/'conker/conker.us.bin').read_bytes();words=list(struct.unpack_from('>80I',rom,0x1559F0));truth=list(struct.unpack_from('>77I',rom,0x15B960));raw=guest.raw_words()
 text,fs,rs=parse_object(out/'qualified-caller.o');f=fs['func_15128540'];refs={a-f['value']:v for a,v in rs.items()if f['value']<=a<f['value']+f['size']};assert bound_blob(text[f['value']:f['value']+f['size']],refs,legacy.SYMS)==words
 n=entered=skipped=0;visits=set()
 for c,p in cases():
  initial=guest.fixture(c);guest.put(initial,c.camera+0x2C,p.flags);expected,calls,snaps,result=reference(initial,c,p);pair=[]
  for mode in('retail','raw','model'):
   m=Dispatcher(words,initial,c,p,raw if mode=='raw'else truth,mode).run()
   assert(guest.public(m.memory),m.calls,m.snapshots,m.r[2])==(guest.public(expected),calls,snaps,result),(c,p,mode)
   pair.append(m)
   if mode!='model':visits.update(m.visits)
  assert guest.state(pair[0])==guest.state(pair[1]);entered+=pair[0].target_seen;skipped+=not pair[0].target_seen;n+=1
  if n%256==0:print('caller cases',n,flush=True)
 report=dict(cases_per_body=n,target_entered=entered,target_skipped=skipped,caller_words=80,caller_reachable_words_visited=sum(PARENT<=p<PARENT+320 for p in visits),target_body_words_visited=sum(guest.ENTRY<=p<guest.ENTRY+308 for p in visits),complete_original_dispatcher=True,typed_void_pointer_repair_machine_code_fixed=True,other_helper_providers_opaque=True,gameplay_claim=False)
 (out/'caller-contract.json').write_text(json.dumps(report,indent=2)+'\n');return report
