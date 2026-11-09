"""Complete original caller with an independent modeled dispatch target."""
import itertools,json,struct
from dataclasses import replace
from tools.experiments import game_camera_transition_dispatch_15128540_match as match
from tools.tests import game_camera_transition_dispatch_15128540_oracle as guest
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=match.ROOT;out=root/match.BUILD
PARENT,ROM,WORDS=0x15122C5C,0x15010C,261
ACTOR,VECTOR0,VECTOR1,VIEWSTATES=0x50000,0x51000,0x52000,0x60000
class Caller(guest.Oracle):
 def __init__(self,words,initial,c,target,mode,plan):
  self.model=mode=='model';self.plan=plan;self.parent_calls=[];self.target_seen=False;self.target_observations=[]
  connected={}if self.model else dict(zip(range(guest.ENTRY,guest.ENTRY+320,4),target))
  super().__init__(words,initial,c,entry=PARENT,connected=connected)
 def in_target(self):return guest.ENTRY<=self.current_pc<guest.ENTRY+320
 def record_call(self,t):
  if t==guest.ENTRY:
   assert self.arguments(1)==(self.case.address,);self.target_seen=True;self.target_home=self.r[29]
   self.calls.append((t,(self.case.address,)));self.events.append(('CALL',t,(self.case.address,)))
  elif self.in_target():super().record_call(t)
  else:
   self.calls.append((t,()));self.events.append(('CALL',t,()));self.parent_calls.append(t)
 def clobber(self,value=0x87654321):
  for j in range(4):self.put(self.r[29]+j*4,0xB5000000+j,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
 def hook(self,t):
  if t==guest.ENTRY:
   assert self.model
   state,calls,snapshots,value=guest.reference(self.memory,self.case,self.target_home)
   self.memory=state;self.calls.extend(calls);self.snapshots.extend(snapshots)
   self.clobber(value)
  elif self.in_target():super().hook(t)
  else:
   # Providers are opaque; the target ABI and parent control route are observed.
   if t==0x15125DB4:
    if self.plan&8:put(self.memory,self.case.address+0x2C,self.case.override)
    if self.plan&16:self.memory[self.case.address+0x23C]^=1
   self.clobber()

def fixture(c,plan):
 m=guest.fixture(c);a=c.address
 for base,size in((ACTOR,0x400),(VECTOR0,64),(VECTOR1,64),(VIEWSTATES,0x800),
                  (0x800BE600,0x500),(0x800DBFF4,16),(0x800A34D0,16)):
  m.update({base+i:0 for i in range(size)})
 put(m,a+0x3D4,ACTOR);put(m,a+0x3D0,ACTOR)
 m[ACTOR+0x78]=0x91;m[ACTOR+0x120]=1 if plan&4 else 0;m[ACTOR+0x197]=1
 m[a+0x23C]=1 if plan&1 else 0;m[a+0x23D]=1 if plan&2 else 0
 m[a+0x23E]=0x26 if plan&4 else 0
 for off in(0x19C,0x1A0,0x1A4,0x1A8,0x35C):put(m,a+off,0x3F800000)
 put(m,a+0x84,(0x08000000 if plan&2 else 0)|(2 if plan&4 else 0)|(0x400 if plan&1 else 0))
 put(m,a+0x5F0,0xFFFFFFFF);put(m,a+0x7F4,plan&1,2)
 for i in range(2):
  put(m,0x800BE728+i*4,VECTOR0);put(m,0x800BE730+i*4,VECTOR1);put(m,0x800BE738+i*4,0x12345678)
  put(m,0x800BE710+i*2,0x9876,2);m[0x800DBFF4+i]=4 if plan&4 else 0
  put(m,VIEWSTATES+i*0x180+0x84,0x41400000)
 put(m,0x800BE628,VIEWSTATES);put(m,0x800A34D4,0x3F000000)
 return m


def caller_checks():
    image=(root/'conker/conker.us.bin').read_bytes();words=list(struct.unpack_from('>261I',image,ROM))
    truth=list(struct.unpack_from('>80I',image,0x1559F0))
    raw=bound_blob(*match.payload(out/'qualified-owner.o'),guest.SYMS);assert raw==truth
    cases=[guest.Case(flags=f,first=p,busy=b,fallback=t,mutation=mu,override=(f^0x180000)|0x100)
           for f,p,b,t in((0,0,0,0),(0,0,0,0x80000000),(0,0,1,1),(0,0x80000000,0,0),
                         (1<<19,0,0,0),(1<<20,0,0,0),(1<<21,0,0,0),(1<<22,0,0,0))for mu in(0,31)]
    visits=set();target_visits=set();n=0;skips=continues=0
    for c,plan in itertools.product(cases,range(32)):
     c=replace(c,phase=(plan&1)*8);initial=fixture(c,plan);pair=[]
     for mode in('retail','raw','model'):
      m=Caller(words,initial,c,raw if mode=='raw'else truth,mode,plan)
      try:m.run()
      except Exception:
       print('caller failure',hex(m.current_pc),c,plan,mode,{i:hex(m.r[i])for i in(4,5,6,7,8,9,13,14,15,16,24,25)},flush=True);raise
      assert m.target_seen;pair.append(m)
      if mode!='model':
       visits.update(p for p in m.visits if PARENT<=p<PARENT+WORDS*4)
       target_visits.update(p for p in m.visits if guest.ENTRY<=p<guest.ENTRY+320)
     assert guest.state(pair[0])==guest.state(pair[1])
     literal,model=pair[0],pair[2]
     assert(guest.public(literal.memory),literal.calls,literal.snapshots,literal.r[2])==(
            guest.public(model.memory),model.calls,model.snapshots,model.r[2]),(c,plan)
     assert literal.r[16]==literal.before[16] and literal.r[29]==STACK+c.phase
     skip=0x15130230 not in literal.parent_calls;skips+=skip;continues+=not skip;n+=1
     if n%128==0:print('caller cases',n,flush=True)
    assert skips and continues
    report=dict(cases_per_body=n,caller_words=261,caller_words_visited=len(visits),target_words_visited=len(target_visits),
                modeled_target_comparisons=n,skipped_tail=skips,continued_tail=continues,
                parent_C_still_zero_return_stub=True,complete_original_entry_to_return=True,
                opaque_parent_provider_arguments_or_gameplay_claim=False,live_pre_target_flag_mutations=True,
                target_argument='original saved fullword camera address',return_contract='nonzero skips tail')
    (out/'caller-contract.json').write_text(json.dumps(report,indent=2)+'\n');return report
