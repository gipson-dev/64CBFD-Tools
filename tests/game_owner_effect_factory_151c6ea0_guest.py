"""Literal/direct execution, initialized fields, retained padding and payload lifetime."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_owner_effect_factory_151c6ea0_match as target_packet
o=target_packet.OUT;ENTRY=0x151c6ea0;FACTORY=0x1513264c;COPY=0x10022ec0;CONSTANT=0x800a5480;POINT=0x30000;OUTPUT=0x60000;MARK=0x35000
HOLES=(89,90,91,107,113,118,119);u32=lambda v:v&0xffffffff
@dataclass(frozen=True)
class Case:
 slot:int=255
 context:int=1
 identity:int=127
 outcome:int=1
 mutation:int=0
 seed:int=0
 phase:int=0
 rm:int=0
 ghost_homes:bool=False
 point:int=POINT
 defaults:tuple=(0,0,0)
def home(c):return STACK+c.phase
def packet(c):return home(c)-124
def tail(c):return home(c)-128
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not home(c)-176<=a<home(c)}
def arguments(c):return c.point,u32(c.slot),u32(c.context)
def symbols():return dict(func_1513264C=FACTORY,memcpy=COPY,D_800A5480=CONSTANT)
def fixture(c):
 m={home(c)+i:(i*17+c.seed*13+165)&255 for i in range(-1536,512)}
 for base,n in ((c.point-8,80),(OUTPUT-32,448),(MARK,16)):m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 m[c.point+59]=c.identity&255
 for i,v in enumerate(c.defaults):put(m,CONSTANT+4*i,v)
 put(m,MARK,0);return m
def expected_packet(m,c):
 result={i:m[packet(c)+i]for i in range(124)};words={0:0x3f800000,4:0x3f800000,8:0x3f800000,12:0x3f800000,28:0x3f800000,32:0x3f800000,36:0x3f800000,76:0,80:0x11900,92:0,108:c.point,120:0}
 for base in (16,40,52,64):
  for i in range(3):words[base+4*i]=read(m,CONSTANT+4*i)
 halves={84:300,86:15,114:1,116:255};small={88:0,96:100,97:23,98:0,99:0,100:0,101:0,102:0,103:0,104:5,105:255,106:1,112:m[c.point+59]}
 assert{i for at in words for i in range(at,at+4)}|{i for at in halves for i in range(at,at+2)}|set(small)==set(range(124))-set(HOLES)
 for at,v in words.items():put(result,at,v)
 for at,v in halves.items():put(result,at,v,2)
 result.update(small);return bytes(result[i]for i in range(124))
def observation(m,c,t,a,fcsr):return public(m,c),data(m,a[0]if t==FACTORY else a[1],124 if t==FACTORY else a[2]),data(m,home(c)-176,176),data(m,home(c),12),fcsr
def effect(m,c,t,a):
 put(m,MARK,read(m,MARK)+1)
 if t==FACTORY:
  if c.mutation&1:
   for i in range(64):m[c.point+i]=(i*13+c.seed)&255
  if c.mutation&2:
   for i in range(3):put(m,CONSTANT+4*i,0x41000000+i*0x10000)
  if c.mutation&4:
   for i in range(124):m[a[0]+i]=(i*7+c.seed*11+49)&255
  if c.ghost_homes:
   for i,v in enumerate((0x31000,0x1234007f,0x87654321)):put(m,home(c)+4*i,v)
  if c.outcome:
   for i,v in enumerate(data(m,a[0],124)):m[OUTPUT+16+i]=v
  return OUTPUT if c.outcome else 0
 assert t==COPY and 0<=a[2]<=4
 for i,v in enumerate(data(m,a[1],a[2])):m[a[0]+i]=v
 return a[0]
def reference(initial,c,ra):
 m=dict(initial);sp=home(c)-176;put(m,sp+36,ra)
 for i,v in enumerate(arguments(c)):put(m,home(c)+4*i,v)
 m[tail(c)]=0
 for i,v in enumerate(expected_packet(m,c)):m[packet(c)+i]=v
 for at,v in ((16,1),(20,c.slot&255),(24,u32(c.context))):put(m,sp+at,v)
 calls=[];obs=[];fcsr=c.rm
 def call(t,a):
  nonlocal fcsr
  calls.append((t,a));obs.append(observation(m,c,t,a,fcsr));value=effect(m,c,t,a)
  for i in range(4):put(m,sp+4*i,0xb5000000+i)
  fcsr=c.rm|0x100*len(calls);return value
 value=call(FACTORY,(packet(c),3,255,0,1,c.slot&255,u32(c.context)))
 if value:value=call(COPY,(value+0x170,tail(c),1))
 return m,calls,obs,fcsr,value
class Machine(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,memory=None,args=None,connected=None):
  self.c=c;self.fcsr=c.rm;super().__init__(words,fixture(c)if memory is None else memory,c,entry=entry,arguments=arguments(c)if args is None else args,connected=connected);self.initial=dict(self.memory);self.observations=[];self.frames=[];self.before_f=self.f[:]
 def record_call(self,t):
  assert t in(FACTORY,COPY),hex(t);a=tuple(map(u32,self.arguments(7 if t==FACTORY else 3)));self.calls.append((t,a));self.observations.append(observation(self.memory,self.c,t,a,self.fcsr));self.frames.append(data(self.memory,home(self.c)-176,176))
 def hook(self,t):
  v=effect(self.memory,self.c,t,self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=v;self.fcsr=self.c.rm|0x100*len(self.calls)
def check(words,c):
 m=Machine(words,c).run();wanted,calls,obs,fcsr,v0=reference(m.initial,c,m.before[31]);assert(m.memory,m.calls,m.observations,m.fcsr,m.r[2])==(wanted,calls,obs,fcsr,v0),(c,'complete frame/public/provider comparison')
 assert all(m.r[i]==m.before[i]for i in (*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(slot=0x12340000|i,context=u32(i*0x87654321),identity=(i*73+31)&255,mutation=i%8,outcome=outcome,seed=i&15,phase=(i&1)*8,rm=i%4)for i,outcome in itertools.product(range(256),(0,1))]
 rows +=[Case(slot=s,context=context,identity=(context+s*17)&255,mutation=mode,outcome=outcome,phase=phase)for s,context,mode,outcome,phase in itertools.product((0,255),(0,1,0x80000000,0xffffffff),range(8),(0,1),(0,8))]
 rows +=[Case(ghost_homes=True,mutation=i%8,outcome=i&1,seed=i,point=STACK+(i&1)*8+32,phase=(i&1)*8)for i in range(16)]
 rows +=[Case(defaults=(v,0x80000000,0x7fc12345),outcome=outcome,rm=rm)for v,outcome,rm in itertools.product((1,0x00800000,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc98765,0xffc54321),(0,1),range(4))]
 return rows
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.frames,m.trace,m.current_pc,m.delay_of,m.condition
def main():
 files=['normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o','original-target.o','selected-owner.o'];streams=[bound_blob(*payload(o/f,'func_151C6EA0'),symbols())for f in files];assert all(w==streams[0]for w in streams);rows=cases();seen=set()
 for c in rows:
  models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(models[0].visits)
 prefixes=0
 for c in (Case(),Case(mutation=7,phase=8),Case(outcome=0,mutation=7),Case(ghost_homes=True)):
  complete=Machine(streams[0],c).run()
  for cut in range(complete.all_accesses):
   models=[]
   for w in streams:
    m=Machine(w,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access boundary')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 assert seen==set(range(ENTRY,ENTRY+408,4));controls=[]
 for name,old,new in [('initial-byte',0xa3a00030,0xa3a50030),('resource',0x2418000f,0x2418000e),('lifetime',0x240b012c,0x240b012d),('payload-size',0x240d0001,0x240d0002),('copy-width',0x24060001,0x24060002),('copy-destination',0x24440170,0x24440171)]:
  ws=list(streams[0]);assert ws.count(old)==1,name;ws[ws.index(old)]=new;c=Case(mutation=7);m=Machine(ws,c).run();expected=reference(m.initial,c,m.before[31]);assert m.memory!=expected[0]or m.calls!=expected[1]or m.observations!=expected[2];controls.append(dict(name=name,supported_complete_execution=True,rejected=True))
 q=dict(cases_per_stream=len(rows),streams=5,all_streams_raw_retail_identical=True,executed_words=len(seen),fault_prefix_quintuples=prefixes,descriptor_bytes=124,initialized_descriptor_bytes=117,unwritten_descriptor_bytes=7,workspace_bytes=128,implicit_workspace_padding_bytes=3,full_frame_bytes=176,full_memory_frames_incoming_homes_provider_observations_and_incidental_V0_equal=True,C_return_type_void_and_no_semantic_return_claim=True,all_slots_and_identity_bytes_and_context_classes=True,source_default_packet_and_incoming_home_mutations=True,all_four_rounding_modes_and_opaque_provider_FCSR=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0)
 (o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
