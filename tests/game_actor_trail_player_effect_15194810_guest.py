"""Bounded MIPS actor-kind dispatch, float snapshot and unsigned sound range."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,sys
from tools.experiments import game_actor_trail_player_effect_15194810_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
ENTRY=0x15194810;ROM=0x1C1CC0;ACTOR=0x30000;SOURCE=0x31000;MARK=0x70000
SURFACE=0x1504715C;SUBMIT=0x15153F18;RNG=0x150ADA20;SOUND=0x151D8868
TABLE=0x800A82D0;RAW_TABLE=0x800A82A8;GLOBALS=(0x800A82E4,0x800A82E8,0x800A82EC)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 kind:int=0;rng:int=0;mode:int=0;phase:int=0;seed:int=0;y:int=0x3F800000;alias:int=0;unused:int=0x87654321
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-512,512)}
 for base,n in((ACTOR,0x340),(SOURCE,0x340),(MARK,32)):m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 m[ACTOR+4]=c.kind
 for off,v in((0x14,bits(10.)),(0x18,c.y),(0x1C,bits(-20.))):put(m,ACTOR+off,v)
 for a,v in zip(GLOBALS,(0x3F2CCCCD,0x3E6C8B44,0x41C8CCCD)):put(m,a,v)
 for base in(TABLE,RAW_TABLE):
  for i in range(5):put(m,base+4*i,ENTRY+80)
 return m
def effect(m,c,t,args):
 if t==SURFACE:
  assert args[1]==ACTOR
  for i in range(36):m[args[0]+i]=(i*7+c.seed*11+0x63)&255
  if c.mode&1:
   m[ACTOR+4]=255
   for i,v in enumerate((42.,-13.,17.)):put(m,ACTOR+0x14+4*i,bits(v))
  if c.mode&2:
   for a,v in zip(GLOBALS,(-.5,2.,.25)):put(m,a,bits(v))
 elif t==SUBMIT:
  put(m,MARK,0x12345678)
  if c.mode&4:
   for i,v in enumerate((-32.,2.,80.)):put(m,ACTOR+0x14+4*i,bits(v))
 elif t==RNG:put(m,MARK+4,c.rng)
 elif t==SOUND:put(m,MARK+8,0x87654321)
def descriptor(m,x,y,z):
 return [(0,4,x),(4,4,y),(8,4,z),(12,4,bits(10.)),(16,4,bits(5.)),(20,4,read(m,GLOBALS[0])),
  (24,4,read(m,GLOBALS[1])),(28,4,bits(5.)),(32,4,read(m,GLOBALS[2])),(36,2,15),(38,2,10),
  (40,2,3),(42,2,2),(44,2,70),(46,2,22),(48,2,155),(50,2,100),(52,1,0),
  (56,4,bits(.5)),(60,2,16),(62,2,15),(64,4,0)]
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,connected=None):
  self.c=c;source=ACTOR if c.alias else SOURCE
  super().__init__(words,fixture(c),c,entry=entry,arguments=(source,ACTOR,c.unused),connected=connected)
  self.initial=dict(self.memory);self.obs=[];self.before_f=self.f[:]
 def record_call(self,t):
  assert t in(SURFACE,SUBMIT,RNG,SOUND,ENTRY),hex(t)
  args=tuple(self.arguments({SURFACE:2,SUBMIT:5,RNG:0,SOUND:4,ENTRY:3}[t]));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==SUBMIT:
   angles,trail,surface,channel,category=args
   self.obs.append(('trail',[read(self.memory,angles+2*i,2)for i in range(4)],[(off,n,read(self.memory,trail+off,n))for off,n,_ in descriptor(self.memory,0,0,0)],bytes(self.memory[surface+i]for i in range(36))))
  elif t==SOUND:self.obs.append(('sound',bytes(self.memory[args[0]+i]for i in range(8))))
 def hook(self,t):
  effect(self.memory,self.c,t,self.calls[-1][1])
  if self.c.mode&8 and t==SURFACE:
   for i in range(3):put(self.memory,self.target_home+4*i,0xDEAD0000+i)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  self.r[2]=self.c.rng if t==RNG else 0x87654321
def programs():
 lookup={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n};lookup['.rodata']=lookup['jtbl_800A8258_game']
 paths=(out/'qualified-source/candidate.o',out/'image-qualification/padded.o',out/'image-qualification/retail.o')
 streams=[bound_blob(*payload(p,'func_15194810'),lookup)for p in paths]
 truth=list(struct.unpack_from('>116I',(root/'conker/conker.us.bin').read_bytes(),ROM))
 assert streams[1]==streams[2]==truth and sum(a!=b for a,b in zip(streams[0],truth))==6
 return streams
def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+512}
def state(m):return(m.memory,m.r,m.f,m.calls,m.obs,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
def final_state(m):return(m.memory,m.r,m.f,m.calls,m.obs,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
def normalized_trace(m):
 return [(op,a+TABLE-RAW_TABLE if op=='R' and RAW_TABLE<=a<RAW_TABLE+20 else a,n,v)for op,a,n,v in m.trace]
def check(words,c):
 m=Oracle(words,c).run();expected=dict(m.initial);sp=STACK+c.phase-168;surface=sp+44
 accepted=c.kind<5 or c.kind==83;calls=[]
 if accepted:
  x=read(expected,ACTOR+0x14);y=bits(floating(read(expected,ACTOR+0x18))+95.);z=read(expected,ACTOR+0x1C)
  args=(surface,ACTOR);calls.append((SURFACE,args));effect(expected,c,SURFACE,args)
  trail=('trail',[0,255,0xFFC1,57],descriptor(expected,x,y,z),bytes(expected[surface+i]for i in range(36)))
  args=(sp+80,sp+88,surface,255,1);calls.append((SUBMIT,args));effect(expected,c,SUBMIT,args)
  calls.append((RNG,()));effect(expected,c,RNG,())
  packet=bytearray(m.initial[sp+36+i]for i in range(8));packet[0]=1;packet[2:4]=struct.pack('>H',c.rng%11+20);packet[4:7]=bytes((8,1,255))
  args=(sp+36,0,255,0);calls.append((SOUND,args));effect(expected,c,SOUND,args)
  assert m.obs==[trail,('sound',bytes(packet))],(c,m.obs,trail,packet)
 else:assert not m.obs
 if accepted and c.mode&8:
  for i in range(3):put(expected,STACK+c.phase+4*i,0xDEAD0000+i)
 assert m.calls==calls,(c,m.calls,calls)
 assert public(m.memory)==public(expected),(c,'public memory')
 assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
 return m
def main():
 streams=programs();cases=[Case(kind=i,rng=(i*0x01010101)&0xFFFFFFFF,seed=i%7)for i in range(256)]
 cases += [Case(kind=k,rng=r,mode=mode,phase=phase,y=y,alias=mode&1)for k,r,mode,phase,y in itertools.product((0,4,5,82,83,84,255),(0,10,11,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,2,4,7,15),(0,8),(0,0x80000000,0x7FC12345,0x7F800000,0xFF800000,1))]
 visits=set()
 for c in cases:
  machines=[check(ws,c)for ws in streams];visits.update(machines[1].visits)
  assert final_state(machines[0])==final_state(machines[1])==final_state(machines[2]),c
  assert normalized_trace(machines[0])==normalized_trace(machines[1])==normalized_trace(machines[2]),c
 assert {ENTRY+4*i for i in range(116)}<=visits,sorted({ENTRY+4*i for i in range(116)}-visits)
 faults=0
 for c in(Case(),Case(kind=83),Case(kind=255),Case(rng=0xFFFFFFFF,mode=15,phase=8)):
  full=check(streams[1],c)
  for cut in range(full.all_accesses):
   states=[]
   for ws in streams[1:]:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(m))
   assert states[0]==states[1];faults+=1
 r=dict(cases_per_stream=len(cases),streams=3,covered_words=116,actor_kind_bytes=256,raw_complete_end_states_equal=True,raw_trace_rebases_only_packed_table=True,normalized_original_access_fault_pairs=faults,helper_internals_executed=False,source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
